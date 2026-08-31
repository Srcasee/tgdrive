import asyncio


_CHUNK_TASKS = {}
_CHUNK_TASKS_LOCK = asyncio.Lock()
_DOWNLOAD_SEMAPHORE = asyncio.Semaphore(4)
_CHUNK_SIZE = 4 * 1024 * 1024


class StreamService:
    """Core HTTP range streaming over Telegram-backed Resource sources."""

    def __init__(self, source_selector):
        self.source_selector = source_selector
        self.chunk_size = _CHUNK_SIZE

    async def _fill_chunk(self, resource_id, chunk_index):
        async with _DOWNLOAD_SEMAPHORE:
            offset = chunk_index * self.chunk_size
            data = bytearray()
            iterator = self.source_selector.stream_resource(resource_id, offset=offset)
            async for chunk in iterator:
                remain = self.chunk_size - len(data)
                if remain <= 0:
                    break
                data.extend(chunk[:remain])
                if len(data) >= self.chunk_size:
                    break
            return bytes(data)

    async def _get_or_create_task(self, resource_id, chunk_index):
        key = (resource_id, chunk_index)
        async with _CHUNK_TASKS_LOCK:
            task = _CHUNK_TASKS.get(key)
            if task is None or task.done():
                task = asyncio.create_task(self._fill_chunk(resource_id, chunk_index))
                _CHUNK_TASKS[key] = task
                task.add_done_callback(
                    lambda done, task_key=key: _CHUNK_TASKS.pop(task_key, None)
                    if _CHUNK_TASKS.get(task_key) is done else None
                )
            return task

    async def get_chunk(self, resource_id, chunk_index):
        task = await self._get_or_create_task(resource_id, chunk_index)
        return await asyncio.shield(task)
