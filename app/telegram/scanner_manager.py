import asyncio


class ScannerManager:
    def __init__(self):
        self.tasks = {}
        self.wakeup_event = asyncio.Event()

    def wakeup(self):
        self.wakeup_event.set()

    async def wait_or_wakeup(self, timeout):
        self.wakeup_event.clear()
        try:
            await asyncio.wait_for(self.wakeup_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def stop_all(self):
        for task in list(self.tasks.values()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self.tasks.clear()
