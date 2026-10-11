import asyncio
import inspect

from repositories.resources import ResourceRepository

from download.repository import DownloadRepository


class DownloadService:
    """Own download-record lifecycle; transfer code only supplies byte chunks."""

    def __init__(self, repository=None, resource_repository=None):
        self.repository = repository or DownloadRepository()
        self.resource_repository = resource_repository or ResourceRepository()

    def start(self, resource_id, created_by=None):
        resource = self.resource_repository.get(resource_id)
        if not resource:
            return None
        return self.repository.create(resource, created_by=created_by)

    async def track_stream(self, record_id, chunks, expected_bytes, on_chunk=None, on_complete=None):
        """Yield a transfer stream while reliably recording its terminal state.

        Callbacks allow integrity verification without coupling this service to
        Telegram or HTTP response types. The byte count is the number of bytes
        emitted by this application, not a guarantee they reached client disk.
        """
        transferred = 0
        try:
            async for chunk in chunks:
                if not chunk:
                    continue
                remaining = expected_bytes - transferred
                if remaining <= 0:
                    break
                chunk = chunk[:remaining]
                transferred += len(chunk)
                if on_chunk:
                    result = on_chunk(chunk)
                    if inspect.isawaitable(result):
                        await result
                yield chunk

            if transferred != expected_bytes:
                raise RuntimeError(
                    f"transfer ended early: expected {expected_bytes} bytes, got {transferred}"
                )
            if on_complete:
                result = on_complete(transferred)
                if inspect.isawaitable(result):
                    await result
            if record_id is not None:
                self.complete(record_id, transferred)
        except asyncio.CancelledError:
            if record_id is not None:
                self.fail(record_id, transferred, "download cancelled by client")
            raise
        except Exception as exc:
            if record_id is not None:
                self.fail(record_id, transferred, str(exc))
            raise

    def complete(self, record_id, bytes_transferred):
        self.repository.complete(record_id, bytes_transferred)

    def fail(self, record_id, bytes_transferred, error):
        self.repository.fail(record_id, bytes_transferred, error)

    def delete(self, record_id):
        return self.repository.delete(record_id)

    def active(self, limit=100):
        return self.repository.list_active(limit)

    def history(self, limit=100):
        return self.repository.list_history(limit)
