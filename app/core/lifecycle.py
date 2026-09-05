import asyncio

from auth.repository import UserRepository
from auth.security import hash_password
from config import settings, validate_telegram_credentials
from database_pool import close_pool, initialize, open_pool
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository
from telegram.client import get_client, get_clients
from telegram.dialog_discovery import DialogDiscoveryService
from telegram.runtime_events import initialize_source_change_event, notify_source_change, wait_for_source_change
from telegram.scanner import scanner_loop
from telegram.scanner_manager import ScannerManager


RECONCILIATION_INTERVAL = 3600


class ApplicationLifecycle:
    def __init__(self):
        self.scanner_task = None
        self.authorized_accounts = set()
        self.discovered_accounts = set()
        self.telegram_enabled = False
        self.account_lock = asyncio.Lock()

        self.account_repository = AccountRepository()
        self.dialog_repository = DialogRepository()
        self.source_repository = SourceRepository()
        self.user_repository = UserRepository()

        self.dialog_discovery = DialogDiscoveryService(self.dialog_repository)
        self.scanner_manager = ScannerManager()

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

    async def set_account_enabled(self, account_id, enabled):
        """Persist account state; enabling performs the single Dialog discovery."""
        async with self.account_lock:
            account = self.account_repository.get(account_id)
            if not account:
                raise ValueError("account not found")

            session_name = account["session"]
            if account["enabled"] == enabled:
                return {"discovered": False}

            self.account_repository.set_enabled(account_id, enabled)

            if not enabled:
                self.authorized_accounts.discard(session_name)
                self.discovered_accounts.discard(session_name)
                dialog_error = None
                try:
                    self.dialog_repository.delete_all_for_account(account_id)
                except Exception as exc:
                    dialog_error = str(exc)
                    print(f"[TG] dialog cleanup failed: {session_name}: {exc!r}", flush=True)
                notify_source_change()
                result = {"discovered": False}
                if dialog_error:
                    result["dialog_cleanup_error"] = dialog_error
                return result

            discovered = False
            discovery_error = None
            try:
                client = get_client(account_id)
                if not client.is_connected():
                    await client.connect()
                if await client.is_user_authorized():
                    self.authorized_accounts.add(session_name)
                    self.telegram_enabled = True
                    await self.dialog_discovery.refresh(client, account_id, session_name)
                    self.discovered_accounts.add(session_name)
                    discovered = True
                else:
                    discovery_error = "Telegram 账号尚未授权"
            except Exception as exc:
                discovery_error = str(exc)
                print(f"[TG] dialog discovery failed: {session_name}: {exc!r}", flush=True)

            notify_source_change()
            result = {"discovered": discovered}
            if discovery_error:
                result["discovery_error"] = discovery_error
            return result

    async def _run_scanners(self):
        while True:
            try:
                clients = get_clients()
                enabled = {
                    row["session"]: row["id"]
                    for row in self.account_repository.list_enabled_sessions()
                }
                enabled_account_ids = set(enabled.values())

                for key, task in list(self.scanner_manager.tasks.items()):
                    account_id, _source_id = key
                    if account_id in enabled_account_ids:
                        continue
                    self.scanner_manager.tasks.pop(key, None)
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

                desired_tasks = set()
                for name, account_id in enabled.items():
                    client = clients.get(name)
                    if client is None:
                        continue

                    if not client.is_connected():
                        self.authorized_accounts.discard(name)
                        try:
                            await client.connect()
                        except Exception as exc:
                            print(f"[TG] connect failed: {name}: {exc!r}", flush=True)
                            continue

                    if name not in self.authorized_accounts:
                        try:
                            if not await client.is_user_authorized():
                                continue
                            self.telegram_enabled = True
                            self.authorized_accounts.add(name)
                        except Exception as exc:
                            print(f"[TG] authorization failed: {name}: {exc!r}", flush=True)
                            continue

                    sources = await asyncio.to_thread(
                        self.source_repository.list_enabled_for_account, account_id
                    )
                    for source in sources:
                        key = (account_id, source["id"])
                        desired_tasks.add(key)
                        task = self.scanner_manager.tasks.get(key)
                        if task is None or task.done():
                            self.scanner_manager.tasks[key] = asyncio.create_task(
                                scanner_loop(client, account_id, source)
                            )

                for key, task in list(self.scanner_manager.tasks.items()):
                    if key in desired_tasks:
                        continue
                    self.scanner_manager.tasks.pop(key, None)
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

                await wait_for_source_change(RECONCILIATION_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[SCAN] source reconciliation error: {exc!r}", flush=True)
                await asyncio.sleep(60)

    async def shutdown(self):
        if self.scanner_task:
            self.scanner_task.cancel()
            try:
                await self.scanner_task
            except asyncio.CancelledError:
                pass

        await self.scanner_manager.stop_all()
        self.authorized_accounts.clear()
        self.discovered_accounts.clear()

        if self.telegram_enabled:
            for name, client in get_clients().items():
                if client.is_connected():
                    await client.disconnect()
                    print(f"[TG] disconnected: {name}", flush=True)

        close_pool()
