import asyncio


class ScannerManager:
    """Own the lifecycle of per-source scan tasks."""

    def __init__(self):
        self.tasks = {}

    async def stop_accounts_except(self, enabled_account_ids):
        enabled_account_ids = set(enabled_account_ids)
        keys = [
            key for key in self.tasks
            if key[0] not in enabled_account_ids
        ]
        await self._cancel_tasks(keys)

    async def reconcile_sources(self, account_id, sources, task_factory):
        """Keep exactly one live task for each enabled source in an account."""
        sources_by_id = {source["id"]: source for source in sources}
        keys_to_stop = [
            key for key in self.tasks
            if key[0] == account_id and key[1] not in sources_by_id
        ]
        await self._cancel_tasks(keys_to_stop)

        for source_id, source in sources_by_id.items():
            key = (account_id, source_id)
            task = self.tasks.get(key)
            if task is not None and not task.done():
                continue
            if task is not None:
                # Retrieve any unobserved exception before replacing a finished task.
                if not task.cancelled():
                    task.exception()
            self.tasks[key] = asyncio.create_task(task_factory(source))

    async def _cancel_tasks(self, keys):
        tasks = []
        for key in keys:
            task = self.tasks.pop(key, None)
            if task is not None:
                if not task.done():
                    task.cancel()
                tasks.append(task)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_all(self):
        await self._cancel_tasks(list(self.tasks))
