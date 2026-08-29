import asyncio

from cache.video import VideoCache, CHUNK_SIZE

_CHUNK_TASKS = {}
_CHUNK_TASKS_LOCK = asyncio.Lock()
_PREFETCH_TASKS = set()
_DOWNLOAD_SEMAPHORE = asyncio.Semaphore(4)


class VideoStreamService:
    def __init__(self, downloader):
        self.downloader = downloader
        self.cache = VideoCache()

    async def _fill_chunk(self, file_id, file_info, chunk_index):
        async with _DOWNLOAD_SEMAPHORE:
            cached = self.cache.read(file_id, chunk_index)
            if cached:
                return cached
            offset = chunk_index * CHUNK_SIZE
            data = bytearray()
            try:
                if hasattr(self.downloader, "stream_resource"):
                    iterator = self.downloader.stream_resource(file_id, offset=offset)
                else:
                    iterator = self.downloader.stream(file_info, offset=offset)
                async for chunk in iterator:
                    remain = CHUNK_SIZE - len(data)
                    if remain <= 0:
                        break
                    data.extend(chunk[:remain])
                    if len(data) >= CHUNK_SIZE:
                        break
            except asyncio.CancelledError:
                print("[VIDEO CACHE TASK] cancelled", file_id, chunk_index, flush=True)
                raise
            result = bytes(data)
            if result:
                self.cache.write(file_id, chunk_index, result)
            return result

    async def _get_or_create_task(self, file_id, file_info, chunk_index):
        key = (file_id, chunk_index)
        async with _CHUNK_TASKS_LOCK:
            task = _CHUNK_TASKS.get(key)
            if task is None or task.done():
                task = asyncio.create_task(self._fill_chunk(file_id, file_info, chunk_index))
                _CHUNK_TASKS[key] = task
                def cleanup(done_task, task_key=key):
                    if _CHUNK_TASKS.get(task_key) is done_task:
                        _CHUNK_TASKS.pop(task_key, None)
                task.add_done_callback(cleanup)
            return task

    async def _prefetch_chunks(self, file_id, file_info, chunk_index):
        for index in (chunk_index + 1, chunk_index + 2):
            key = (file_id, index)
            if key in _PREFETCH_TASKS or self.cache.exists(file_id, index):
                continue
            _PREFETCH_TASKS.add(key)
            async def run(idx=index, task_key=key):
                try:
                    await self.get_chunk(file_id, file_info, idx)
                finally:
                    _PREFETCH_TASKS.discard(task_key)
            asyncio.create_task(run())

    async def get_chunk(self, file_id, file_info, chunk_index):
        cached = self.cache.read(file_id, chunk_index)
        if cached:
            return cached
        task = await self._get_or_create_task(file_id, file_info, chunk_index)
        result = await asyncio.shield(task)
        asyncio.create_task(self._prefetch_chunks(file_id, file_info, chunk_index))
        return result
