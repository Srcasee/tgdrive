import asyncio

from telegram.client import get_clients


class ApplicationLifecycle:
    """
    FastAPI application lifecycle manager.

    Keeps startup/shutdown orchestration outside main.py.
    """

    def __init__(self):
        self.scanner_task = None

    async def startup(self):
        clients = get_clients()

        if not clients:
            raise RuntimeError("No Telegram sessions found")

        for name, client in clients.items():
            await client.connect()

            if not await client.is_user_authorized():
                await client.disconnect()
                continue

            me = await client.get_me()
            print(f"[TG] authorized: {name} / {me.username or me.id}", flush=True)

    async def shutdown(self):
        if self.scanner_task:
            self.scanner_task.cancel()

            try:
                await self.scanner_task
            except asyncio.CancelledError:
                pass

        for name, client in get_clients().items():
            if client.is_connected():
                await client.disconnect()
                print(f"[TG] disconnected: {name}", flush=True)
