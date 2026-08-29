from .models import TelegramFileObservation


class TelegramMessageRecognizer:
    """Turn raw Telegram messages into deterministic, normalized observations."""

    @staticmethod
    def recognize(message, *, chat_id, account_id):
        if not message.media or not message.file:
            return None

        filename = (message.file.name or f"{message.id}.bin").strip()
        if not filename:
            filename = f"{message.id}.bin"

        upload_time = int(message.date.timestamp()) if message.date else 0
        return TelegramFileObservation(
            account_id=account_id,
            chat_id=chat_id,
            message_id=message.id,
            filename=filename,
            size=message.file.size,
            mime_type=message.file.mime_type,
            upload_time=upload_time,
        )
