import asyncio

from auth.repository import UserRepository
from auth.security import hash_password
from catalog.repository import CatalogRepository
from config import settings, validate_telegram_credentials
from database_pool import close_pool, initialize, open_pool
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository
from telegram.account_lock import account_lock
from telegram.client import get_clients, refresh_clients
from telegram.dialog_discovery import DialogDiscoveryService
from telegram.runtime_events import initialize_runtime_events, wait_for_runtime_event
from telegram.scanner import scan_source
from telegram.scanner_manager import ScannerManager


RECONCILIATION_INTERVAL = 3600


class ApplicationLifecycle:
    def __init__(self):
        self.scanner_task = None
        self.authorized_accounts = set()
        self.telegram_enabled = False

        self.account_repository = AccountRepository()
        self.dialog_repository = DialogRepository()
        self.source_repository = SourceRepository()
        self.catalog_repository = CatalogRepository()
        self.user_repository = UserRepository()

        self.dialog_discovery = DialogDiscoveryService()
        self.scanner_manager = ScannerManager()

    async def startup(self):
        open_pool()
        initialize()
        self._bootstrap_admin()

        if not self._telegram_configured():
            print("[TG] Telegram is not configured; Telegram runtime disabled", flush=True)
            return

        initialize_runtime_events()
        self.scanner_task = asyncio.create_task(self._run_scanners())
        print("[TG] Telegram runtime reconciliation started", flush=True)

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
            self.user_repository.ensure_admin(
                settings.ADMIN_USERNAME,
                hash_password(settings.ADMIN_PASSWORD),
            )

    async def _run_scanners(self):
        first_run = True
        while True:
            try:
                async with account_lock:
                    await self._reconcile_accounts(discover_dialogs=first_run)
                first_run = False

                event = await wait_for_runtime_event(RECONCILIATION_INTERVAL)
                if event["dialog_refresh"] or event["timed_out"]:
                    async with account_lock:
                        await self._reconcile_accounts(discover_dialogs=True)
                elif event["source_change"]:
                    async with account_lock:
                        await self._reconcile_accounts(discover_dialogs=False)

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[SCAN] account reconciliation error: {exc!r}", flush=True)
                await asyncio.sleep(60)

    async def _reconcile_accounts(self, discover_dialogs):
        enabled_rows = self.account_repository.list_enabled_sessions()
        clients = refresh_clients(row["session"] for row in enabled_rows)
        enabled = {row["session"]: row["id"] for row in enabled_rows}

        await self._reconcile_disabled_accounts(enabled)

        for session_name, account_id in enabled.items():
            client = clients.get(session_name)
            if client is None:
                continue

            if not client.is_connected():
                self.authorized_accounts.discard(session_name)
                try:
                    await client.connect()
                except Exception as exc:
                    print(f"[TG] connect failed: {session_name}: {exc!r}", flush=True)
                    continue

            if session_name not in self.authorized_accounts:
                try:
                    if not await client.is_user_authorized():
                        continue
                    self.telegram_enabled = True
                    self.authorized_accounts.add(session_name)
                except Exception as exc:
                    print(f"[TG] authorization failed: {session_name}: {exc!r}", flush=True)
                    continue

            if discover_dialogs:
                await self._refresh_dialogs_for_account(
                    client,
                    account_id,
                    session_name,
                )

            await self._reconcile_sources(account_id, session_name, client)

    async def _refresh_dialogs_for_account(self, client, account_id, account_name):
        try:
            dialogs = await self.dialog_discovery.discover(client)
            dialog_ids = [dialog["id"] for dialog in dialogs]

            removed_chat_ids = self.source_repository.remove_missing_dialogs(
                account_id,
                dialog_ids,
            )
            removed_dialog_ids = self.dialog_repository.replace_for_account(
                account_id,
                dialogs,
            )

            stale_ids = sorted(set(removed_chat_ids) | set(removed_dialog_ids))
            if stale_ids:
                self.catalog_repository.deactivate_telegram_chats(
                    account_id,
                    stale_ids,
                )

            print(
                f"[TG] dialogs refreshed: {account_name} ({len(dialogs)})",
                flush=True,
            )
        except Exception as exc:
            print(
                f"[TG] dialog discovery failed: {account_name}: {exc!r}",
                flush=True,
            )

    async def _reconcile_disabled_accounts(self, enabled):
        enabled_ids = set(enabled.values())
        for key in list(self.scanner_manager.tasks):
            account_id, source_id = key
            if account_id in enabled_ids:
                continue
            task = self.scanner_manager.tasks.pop(key, None)
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.authorized_accounts.intersection_update(set(enabled))

    async def _reconcile_sources(self, account_id, account_name, client):
        sources = await asyncio.to_thread(
            self.source_repository.list_enabled_for_account,
            account_id,
        )
        enabled_ids = {source["id"] for source in sources}

        for key in list(self.scanner_manager.tasks):
            task_account, source_id = key
            if task_account != account_id or source_id in enabled_ids:
                continue
            task = self.scanner_manager.tasks.pop(key, None)
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        for source in sources:
            key = (account_id, source["id"])
            task = self.scanner_manager.tasks.get(key)
            if task is not None:
                continue
            self.scanner_manager.tasks[key] = asyncio.create_task(
                self._run_source(account_id, account_name, client, source)
            )

    async def _run_source(self, account_id, account_name, client, source):
        print(
            f"[SCAN] source scanner started: {source['name']} ({source['telegram_chat_id']})",
            flush=True,
        )
        try:
            while True:
                try:
                    count = await scan_source(client, account_id, source)
                    print(
                        f"[SCAN] source finished {source['name']} ({source['telegram_chat_id']}): {count} files",
                        flush=True,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    print(
                        f"[SCAN] source error {source['name']} ({source['telegram_chat_id']}): {exc!r}",
                        flush=True,
                    )

                await asyncio.sleep(source.get("scan_interval") or 300)
        finally:
            await asyncio.to_thread(self.source_repository.mark_idle, source["id"])

    async def shutdown(self):
        if self.scanner_task:
            self.scanner_task.cancel()
            try:
                await self.scanner_task
            except asyncio.CancelledError:
                pass

        await self.scanner_manager.stop_all()
        self.authorized_accounts.clear()

        if self.telegram_enabled:
            for name, client in get_clients().items():
                if client.is_connected():
                    await client.disconnect()
                    print(f"[TG] disconnected: {name}", flush=True)

        close_pool()

    # Account enable/disable is intentionally disabled for now.
    # Restore and login create active accounts; re-enable this lifecycle API
    # only when an explicit enable/disable feature is needed again.
    #
    # async def set_account_enabled(self, account_id, enabled):
    #     ...
