import asyncio
import logging

from repositories.resources import ResourceRepository

from download.repository import DownloadRepository
from download.transfer import tracked_stream

logger = logging.getLogger(__name__)


class DownloadService:
    """Own download lifecycle, concurrency limits and transfer observability."""

    def __init__(self, repository=None, resource_repository=None, max_concurrent=8):
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")
        self.repository = repository or DownloadRepository()
        self.resource_repository = resource_repository or ResourceRepository()
        self.max_concurrent = max_concurrent
        self._transfer_slots = asyncio.Semaphore(max_concurrent)

    def start(self, resource_id, created_by=None):
        resource = self.resource_repository.get(resource_id)
        if not resource:
            return None
        record_id = self.repository.create(resource, created_by=created_by)
        logger.info("download_started", extra={
            "download_id": record_id, "resource_id": resource_id,
            "filename": resource.get("filename"), "expected_bytes": resource.get("size"),
        })
        return record_id

    async def _limited_stream(self, chunks, record_id, expected_bytes, verify, hash_content):
        wait_started = asyncio.get_running_loop().time()
        async with self._transfer_slots:
            acquired_at = asyncio.get_running_loop().time()
            logger.info("download_slot_acquired", extra={
                "download_id": record_id,
                "queue_wait_seconds": acquired_at - wait_started,
                "max_concurrent": self.max_concurrent,
            })
            try:
                async for chunk in tracked_stream(
                    chunks, service=self, record_id=record_id,
                    expected_bytes=expected_bytes, verify=verify,
                    hash_content=hash_content,
                ):
                    yield chunk
            finally:
                logger.debug("download_slot_released", extra={"download_id": record_id})

    def stream(self, chunks, record_id, expected_bytes, verify=None, hash_content=False):
        return self._limited_stream(chunks, record_id, expected_bytes, verify, hash_content)

    def complete(self, record_id, bytes_transferred):
        self.repository.complete(record_id, bytes_transferred)
        logger.info("download_completed", extra={
            "download_id": record_id, "bytes_transferred": bytes_transferred,
        })

    def fail(self, record_id, bytes_transferred, error):
        self.repository.fail(record_id, bytes_transferred, error)
        logger.warning("download_failed", extra={
            "download_id": record_id, "bytes_transferred": bytes_transferred,
            "error": error,
        })

    def delete(self, record_id):
        return self.repository.delete(record_id)

    def active(self, limit=100):
        return self.repository.list_active(limit)

    def history(self, limit=100):
        return self.repository.list_history(limit)
