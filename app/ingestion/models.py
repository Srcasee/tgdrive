from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramFileObservation:
    """Normalized Telegram media observation passed from discovery to ingestion."""

    account_id: int
    chat_id: int
    message_id: int
    filename: str
    size: int | None
    mime_type: str | None
    upload_time: int

    @property
    def resource_metadata(self):
        return {
            "filename": self.filename,
            "size": self.size,
            "mime_type": self.mime_type,
        }

    @property
    def file_metadata(self):
        return {
            "filename": self.filename,
            "size": self.size,
            "mime_type": self.mime_type,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "upload_time": self.upload_time,
            "account_id": self.account_id,
        }
