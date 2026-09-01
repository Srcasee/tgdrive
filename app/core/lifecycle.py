import asyncio

from auth.repository import UserRepository
from auth.security import hash_password
from config import settings, validate_telegram_credentials
from database_pool import close_pool, open_pool, initialize
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository
from telegram.client import get_clients
from telegram.scanner import scanner_loop
from telegram.runtime_events import initialize_source_change_event, wait_for_source_change


RECONCILIATION_INTERVAL = 3600


class ApplicationLifecycle:
    def __init__(self):
        self.scanner_task = None
        self.scanner_tasks = {}
        self.dialogs_refreshed = set()
        self.authorized_accounts = set()
        self.telegram_enabled = False
        self.account_repository = AccountRepository()
        self.dialog_repository = DialogRepository()
        self.source_repository = SourceRepository()
        self.user_repository = UserRepository()

    async def startup(self):
        open_pool()
        initialize()
        self._bootstrap_admin()

        if not self._telegram_configured():
            print("[TG] Telegram is not configured; Telegram runtime disabled", flush=True)
            return

        initialize_source_change_event()
        self.scanner_task = asyncio.create_task(self._run_scanners())
        print("[TG] Telegram runtime reconciliation started", flush=True)

    async def _refresh_dialogs(self, client, account_id, account_name):
        if account_id is None:
            return
        dialogs = []
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            row = {
                "id": dialog.id,
                "name": dialog.name,
                "username": getattr(entity, "username", None),
                "entity_type": type(entity).__name__,
                "is_group": bool(dialog.is_group),
                "is_channel": bool(dialog.is_channel),
            }
            dialogs.append(row)
            print(
                "[TG] dialog: "
                f"{account_name} id={row['id']} "
                f"name={row['name']!r} "
                f"username={row['username']!r} "
                f"type={row['entity_type']} "
                f"group={row['is_group']} channel={row['is_channel']}",
                flush=True,
            )
        self.dialog_repository.replace_for_account(account_id, dialogs)
        selectable = [row for row in dialogs if row["is_group"] or row["is_channel"]]
        print(f"[TG] resource candidates: {account_name} ({len(selectable)})", flush=True)
        for row in selectable:
            print(
                "[TG] candidate: "
                f"id={row['id']} name={row['name']!r} "
                f"type={row['entity_type']} "
                f"group={row['is_group']} channel={row['is_channel']}",
                flush=True,
            )
        print(f"[TG] dialogs refreshed: {account_name} ({len(dialogs)})", flush=True)

    @staticmethod
    def _telegram_configured():
        try:
            validate_telegram_credentials()
        except RuntimeError:
            return False
        return True

    def _bootstrap_admin(self):
        if not settings.AUTH_SECRET:
            raise RuntimeError("AUTH_SECRET must be configured")
        if settings.ADMIN_USERNAME and settings.ADMIN_PASSWORD:
            self.user_repository.ensure_admin(settings.ADMIN_USERNAME, hash_password(settings.ADMIN_PASSWORD))

    async def _run_scanners(self):
        while True:
            try:
                clients = get_clients()
                enabled = {
                    row["session"]: row["id"]
                    for row in self.account_repository.list_enabled_sessions()
                }

                for name, account_id in enabled.items():
                    client = clients.get(name)
                    if client is None:
                        continue

                    if not client.is_connected():
                        self.authorized_accounts.discard(name)
                        self.dialogs_refreshed.discard(name)
                        try:
                            print(f"[TG] connecting: {name}", flush=True)
                            await client.connect()
                        except Exception as exc:
                            print(f"[TG] connect failed: {name}: {exc!r}", flush=True)
                            continue

                    if name not in self.authorized_accounts:
                        try:
                            if not await client.is_user_authorized():
                                print(f"[TG] session not authorized: {name}", flush=True)
                                continue
                            self.telegram_enabled = True
                            me = await client.get_me()
                            print(
                                f"[TG] authorized: {name} / "
                                f"{me.username or me.first_name or me.id}",
                                flush=True,
                            )
                            self.authorized_accounts.add(name)
                        except Exception as exc:
                            print(f"[TG] authorization check failed: {name}: {exc!r}", flush=True)
                            self.authorized_accounts.discard(name)
                            continue

                    if name not in self.dialogs_refreshed:
                        try:
                            await self._refresh_dialogs(client, account_id, name)
                            self.dialogs_refreshed.add(name)
                        except Exception as exc:
                            print(f"[TG] dialog refresh failed: {name}: {exc!r}", flush=True)
                            continue

                    sources = self.source_repository.list_enabled_for_account(account_id)
                    if sources:
                        task = self.scanner_tasks.get(name)
                        if task is None or task.done():
                            self.scanner_tasks[name] = asyncio.create_task(
                                self._run_one(account_id, name, client)
                            )
                            print(
                                f"[SCAN] starting: {name} ({len(sources)} source(s))",
                                flush=True,
                            )
                    else:
                        task = self.scanner_tasks.pop(name, None)
                        if task is not None:
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                            print(f"[SCAN] stopped: {name} (no enabled sources)", flush=True)
                        print(f"[TG] scanner idle: {name} (no enabled sources)", flush=True)

                for name, task in list(self.scanner_tasks.items()):
                    if name in enabled:
                        continue
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    self.scanner_tasks.pop(name, None)
                    self.authorized_accounts.discard(name)
                    self.dialogs_refreshed.discard(name)
                    print(f"[SCAN] stopped: {name}", flush=True)

                changed = await wait_for_source_change(RECONCILIATION_INTERVAL)
                if changed:
                    print("[SCAN] source configuration changed; reconciling now", flush=True)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[SCAN] account reconciliation error: {exc!r}", flush=True)
                await asyncio.sleep(60)

    async def _run_one(self, account_id, account_name, client):
        try:
            await scanner_loop(client, account_id)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"[SCAN] {account_name} crashed: {exc!r}", flush=True)

    async def shutdown(self):
        if self.scanner_task:
            self.scanner_task.cancel()
            try:
                await self.scanner_task
            except asyncio.CancelledError:
                pass

        for name, task in list(self.scanner_tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.scanner_tasks.clear()
        self.authorized_accounts.clear()
        self.dialogs_refreshed.clear()

        if self.telegram_enabled:
            for name, client in get_clients().items():
                if client.is_connected():
                    await client.disconnect()
                    print(f"[TG] disconnected: {name}", flush=True)
        close_pool()
