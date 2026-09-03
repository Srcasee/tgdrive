import asyncio

from auth.repository import UserRepository
from auth.security import hash_password
from catalog.repository import CatalogRepository
from config import settings, validate_telegram_credentials
from database_pool import close_pool, initialize, open_pool
from repositories.accounts import AccountRepository
from repositories.dialogs import DialogRepository
from repositories.sources import SourceRepository
from telegram.client import get_clients
from telegram.dialog_discovery import DialogDiscoveryService
from telegram.runtime_events import initialize_source_change_event, wait_for_source_change
from telegram.scanner import scanner_loop
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

        self.dialog_discovery = DialogDiscoveryService(
            self.dialog_repository,
            self.source_repository,
            self.catalog_repository,
        )
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

                    try:
                        await self.dialog_discovery.refresh(client, account_id, name)
                    except Exception as exc:
                        print(f"[TG] dialog discovery failed: {name}: {exc!r}", flush=True)
                        continue

                    sources = self.source_repository.list_enabled_for_account(account_id)
                    if sources:
                        task = self.scanner_manager.tasks.get(name)
                        if task is None or task.done():
                            self.scanner_manager.tasks[name] = asyncio.create_task(
                                self._run_one(account_id, name, client)
                            )

                changed = await wait_for_source_change(RECONCILIATION_INTERVAL)
                if changed:
                    self.scanner_manager.wakeup()
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

        await self.scanner_manager.stop_all()
        self.authorized_accounts.clear()

        if self.telegram_enabled:
            for name, client in get_clients().items():
                if client.is_connected():
                    await client.disconnect()
                    print(f"[TG] disconnected: {name}", flush=True)

        close_pool()
