from dataclasses import dataclass


@dataclass(frozen=True)
class DownloadRecord:
    id: int
    resource_id: int
    filename: str
    size: int
    status: str
    started_at: int
    completed_at: int | None
    bytes_transferred: int
    error: str | None
    created_by: str | None
