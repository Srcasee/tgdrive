import asyncio
import logging
import os

from repositories.resources import ResourceRepository

from repositories.downloads import DownloadRepository
from download.transfer import tracked_stream

logger = logging.getLogger(__name__)


class DownloadService:
    """Own download lifecycle, concurrency limits and transfer observability."""

    def __init__(self, repository=None, resource_repository=None, max_concurrent=None):
        if max_concurrent is None:
            try:
                max_concurrent = int(os.getenv("TGDRIVE_MAX_CONCURRENT_DOWNLOADS", "8"))
            except ValueError as exc:
                raise ValueError("TGDRIVE_MAX_CONCURRENT_DOWNLOADS must be an integer") from exc
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")
        self.repository = repository or DownloadRepository()
        self.resource_repository = resource_repository or ResourceRepository()
        self.max_concurrent = max_concurrent
        self._transfer_slots = asyncio.Semaphore(max_concurrent)
        self._active_transfers = 0
        self._queued_transfers = 0

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

    async def _limited_stream(self, chunks, record_id, expected_bytes, on_digest, hash_content):
        wait_started = asyncio.get_running_loop().time()
        self._queued_transfers += 1
        acquired = False
        try:
            async with self._transfer_slots:
                self._queued_transfers -= 1
                acquired = True
                self._active_transfers += 1
                acquired_at = asyncio.get_running_loop().time()
                logger.info("download_slot_acquired", extra={
                    "download_id": record_id,
                    "queue_wait_seconds": acquired_at - wait_started,
                    "max_concurrent": self.max_concurrent,
                    "active_transfers": self._active_transfers,
                    "queued_transfers": self._queued_transfers,
                })
                try:
                    async for chunk in tracked_stream(
                        chunks, service=self, record_id=record_id,
                        expected_bytes=expected_bytes, on_digest=on_digest,
                        hash_content=hash_content,
                    ):
                        yield chunk
                finally:
                    self._active_transfers -= 1
                    logger.debug("download_slot_released", extra={
                        "download_id": record_id,
                        "active_transfers": self._active_transfers,
                        "queued_transfers": self._queued_transfers,
                    })
        finally:
            if not acquired:
                self._queued_transfers -= 1

    def stream(self, chunks, record_id, expected_bytes, on_digest=None, hash_content=False):
        return self._limited_stream(chunks, record_id, expected_bytes, on_digest, hash_content)

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
