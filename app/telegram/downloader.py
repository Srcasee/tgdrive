import asyncio
from dataclasses import dataclass


TELEGRAM_REQUEST_SIZE = 512 * 1024
MAX_STREAM_RETRIES = 8
RETRY_BACKOFF_SECONDS = 1


@dataclass
class TelegramFileInfo:
    chat_id: int
    message_id: int
    filename: str
    size: int | None
    mime_type: str
    media: object


class TelegramDownloader:
    def __init__(self, client, chunk_size=TELEGRAM_REQUEST_SIZE):
        if chunk_size <= 0 or chunk_size > TELEGRAM_REQUEST_SIZE or chunk_size % 4096:
            raise ValueError("chunk_size must be a positive multiple of 4096 and <= 512 KiB")
        self.client = client
        self.chunk_size = chunk_size

    async def get_file_info(self, chat_id: int, message_id: int) -> TelegramFileInfo:
        message = await self.client.get_messages(int(chat_id), ids=int(message_id))
        if not message:
            raise RuntimeError("telegram message not found")
        if not message.media:
            raise RuntimeError("telegram message has no media")

        file = getattr(message, "file", None)
        return TelegramFileInfo(
            chat_id=int(chat_id),
            message_id=int(message_id),
            filename=getattr(file, "name", None) or f"{message_id}.bin",
            size=getattr(file, "size", None),
            mime_type=getattr(file, "mime_type", None) or "application/octet-stream",
            media=message.media,
        )

    async def stream(self, file_info: TelegramFileInfo, offset: int = 0):
        """
        Stream Telegram media with resumable retry.

        Telegram MTProto streams are not identical to HTTP downloads. A TCP
        interruption after data has already been yielded must not restart from
        the original offset, otherwise HTTP clients may restart the download or
        receive duplicate ranges.
        """
        current_offset = max(0, int(offset))
        last_error = None

        for attempt in range(MAX_STREAM_RETRIES):
            iterator = None
            try:
                iterator = self.client.iter_download(
                    file_info.media,
                    offset=current_offset,
                    chunk_size=self.chunk_size,
                    request_size=self.chunk_size,
                )

                async for chunk in iterator:
                    if not chunk:
                        continue

                    current_offset += len(chunk)
                    yield chunk

                return

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = exc
                print(
                    "[TELEGRAM STREAM] resume",
                    "message=", file_info.message_id,
                    "offset=", current_offset,
                    "attempt=", attempt + 1,
                    repr(exc),
                    flush=True,
                )

                if attempt + 1 < MAX_STREAM_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue

            finally:
                close = getattr(iterator, "aclose", None) if iterator else None
                if close:
                    try:
                        result = close()
                        if hasattr(result, "__await__"):
                            await result
                    except Exception:
                        pass

        raise RuntimeError("telegram stream failed after resumable retries") from last_error
