from .models import TelegramFileObservation


class TelegramMessageRecognizer:
    """Turn raw Telegram messages into deterministic, normalized observations."""

    @staticmethod
    def _topic_id(message):
        # Telethon exposes this convenience property on newer Message versions.
        topic_id = getattr(message, "forum_topic_id", None)
        if topic_id:
            return topic_id

        # In Telethon's MessageReplyHeader, forum_topic distinguishes forum
        # topics from ordinary message threads. Root-level topic messages use
        # reply_to_msg_id; replies within a topic use reply_to_top_id.
        reply_to = getattr(message, "reply_to", None)
        if reply_to is not None and getattr(reply_to, "forum_topic", False):
            return (
                getattr(reply_to, "reply_to_top_id", None)
                or getattr(reply_to, "reply_to_msg_id", None)
            )
        return None

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
            topic_id=TelegramMessageRecognizer._topic_id(message),
        )
