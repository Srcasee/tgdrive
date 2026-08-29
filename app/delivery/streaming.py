import asyncio

from cache.video import VideoCache, CHUNK_SIZE

_CHUNK_TASKS = {}
_CHUNK_TASKS_LOCK = asyncio.Lock()
_PREFETCH_TASKS = set()
_DOWNLOAD_SEMAPHORE = asyncio.Semaphore(4)


class VideoStreamService:
    """Application delivery cache; bytes remain in memory/cache only as requested."""

    def __init__(self, source_selector):
        self.source_selector = source_selector
        self.cache = VideoCache()

    async def _fill_chunk(self, resource_id, chunk_index):
        async with _DOWNLOAD_SEMAPHORE:
            cached = self.cache.read(resource_id, chunk_index)
            if cached:
                return cached
            offset = chunk_index * CHUNK_SIZE
            data = bytearray()
            try:
                iterator = self.source_selector.stream_resource(resource_id, offset=offset)
                async for chunk in iterator:
                    remain = CHUNK_SIZE - len(data)
                    if remain <= 0:
                        break
                    data.extend(chunk[:remain])
                    if len(data) >= CHUNK_SIZE:
                        break
            except asyncio.CancelledError:
                print("[VIDEO CACHE TASK] cancelled", resource_id, chunk_index, flush=True)
                raise
            result = bytes(data)
            if result:
                self.cache.write(resource_id, chunk_index, result)
            return result

    async def _get_or_create_task(self, resource_id, chunk_index):
        key = (resource_id, chunk_index)
        async with _CHUNK_TASKS_LOCK:
            task = _CHUNK_TASKS.get(key)
            if task is None or task.done():
                task = asyncio.create_task(self._fill_chunk(resource_id, chunk_index))
                _CHUNK_TASKS[key] = task
                task.add_done_callback(lambda done, task_key=key: _CHUNK_TASKS.pop(task_key, None) if _CHUNK_TASKS.get(task_key) is done else None)
            return task

    async def _prefetch_chunks(self, resource_id, chunk_index):
        for index in (chunk_index + 1, chunk_index + 2):
            key = (resource_id, index)
            if key in _PREFETCH_TASKS or self.cache.exists(resource_id, index):
                continue
            _PREFETCH_TASKS.add(key)
            async def run(idx=index, task_key=key):
                try:
                    await self.get_chunk(resource_id, idx)
                finally:
                    _PREFETCH_TASKS.discard(task_key)
            asyncio.create_task(run())

    async def get_chunk(self, resource_id, chunk_index):
        cached = self.cache.read(resource_id, chunk_index)
        if cached:
            return cached
        task = await self._get_or_create_task(resource_id, chunk_index)
        result = await asyncio.shield(task)
        asyncio.create_task(self._prefetch_chunks(resource_id, chunk_index))
        return result
