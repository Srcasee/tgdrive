import asyncio

from auth.repository import UserRepository
from auth.security import hash_password
from config import settings, validate_telegram_credentials
from database_pool import close_pool, open_pool, initialize
from repositories.accounts import AccountRepository
from telegram.client import get_clients
from telegram.scanner import scanner_loop


class ApplicationLifecycle:
    def __init__(self):
        self.scanner_task = None
        self.telegram_enabled = False
        self.account_repository = AccountRepository()
        self.user_repository = UserRepository()

    async def startup(self):
        open_pool()
        initialize()
        self._bootstrap_admin()

        if not self._telegram_configured():
            print("[TG] Telegram is not configured; Telegram runtime disabled", flush=True)
            return

        clients = get_clients()
        if not clients:
            print("[TG] No Telegram sessions found; Telegram runtime idle", flush=True)
            return

        connected = False
        for name, client in clients.items():
            print(f"[TG] connecting: {name}", flush=True)
            await client.connect()
            if not await client.is_user_authorized():
                print(f"[TG] session not authorized: {name}", flush=True)
                await client.disconnect()
                continue
            connected = True
            me = await client.get_me()
            print(
                f"[TG] authorized: {name} / {me.username or me.first_name or me.id}",
                flush=True,
            )

        self.telegram_enabled = connected
        if connected:
            self.scanner_task = asyncio.create_task(self._run_scanners())
            print("[SCAN] background scanner started", flush=True)

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
        tasks = []
        for name, client in get_clients().items():
            account_id = self.account_repository.get_id_by_session(name)
            if account_id is None:
                print(f"[SCAN] account not found: {name}", flush=True)
                continue
            if not client.is_connected() or not await client.is_user_authorized():
                continue
            tasks.append(asyncio.create_task(self._run_one(account_id, name, client)))
        if tasks:
            await asyncio.gather(*tasks)

    async def _run_one(self, account_id, account_name, client):
        try:
            print(f"[SCAN] starting: {account_name}", flush=True)
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

        if self.telegram_enabled:
            for name, client in get_clients().items():
                if client.is_connected():
                    await client.disconnect()
                    print(f"[TG] disconnected: {name}", flush=True)
        close_pool()
