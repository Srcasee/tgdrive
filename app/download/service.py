from repositories.resources import ResourceRepository

from download.repository import DownloadRepository
from download.transfer import tracked_stream


class DownloadService:
    """Own download lifecycle and delegate physical byte reads to a source adapter."""

    def __init__(self, repository=None, resource_repository=None):
        self.repository = repository or DownloadRepository()
        self.resource_repository = resource_repository or ResourceRepository()

    def start(self, resource_id, created_by=None):
        resource = self.resource_repository.get(resource_id)
        if not resource:
            return None
        return self.repository.create(resource, created_by=created_by)

    def stream(self, chunks, record_id, expected_bytes, verify=None, hash_content=False):
        return tracked_stream(
            chunks,
            service=self,
            record_id=record_id,
            expected_bytes=expected_bytes,
            verify=verify,
            hash_content=hash_content,
        )

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
