from repositories.resources import ResourceRepository

from download.repository import DownloadRepository


class DownloadService:
    """Track download lifecycle without owning the byte stream."""

    def __init__(self, repository=None, resource_repository=None):
        self.repository = repository or DownloadRepository()
        self.resource_repository = resource_repository or ResourceRepository()

    def start(self, resource_id, created_by=None):
        resource = self.resource_repository.get(resource_id)
        if not resource:
            return None
        return self.repository.create(resource, created_by=created_by)

    def complete(self, record_id, bytes_transferred): self.repository.complete(record_id, bytes_transferred)
    def fail(self, record_id, bytes_transferred, error): self.repository.fail(record_id, bytes_transferred, error)
    def delete(self, record_id): return self.repository.delete(record_id)
    def active(self, limit=100): return self.repository.list_active(limit)
    def history(self, limit=100): return self.repository.list_history(limit)
