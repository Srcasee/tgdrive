import asyncio
import logging

from repositories.accounts import AccountRepository
from telegram.client import get_client
from download.downloader import TelegramDownloader

logger = logging.getLogger(__name__)


class TelegramSourceSelector:
    """Select Telegram access accounts for the same underlying message."""

    def __init__(
        self,
        file_repository,
        client_factory=get_client,
        downloader_factory=TelegramDownloader,
        account_repository=None,
        failover_delay=15.0,
    ):
        self.file_repository = file_repository
        self.account_repository = account_repository or AccountRepository()
        self.client_factory = client_factory
        self.downloader_factory = downloader_factory
        self.failover_delay = max(0.0, float(failover_delay))

    def candidates(self, resource_id):
        # The business model stores one Telegram message, readable by multiple
        # accounts. The repository returns each account's indexed access path.
        return self.file_repository.list_resource_sources(resource_id)

    @staticmethod
    def _same_message(row, canonical):
        return (
            row.get("telegram_chat_id") == canonical.get("telegram_chat_id")
            and row.get("message_id") == canonical.get("message_id")
        )

    def _downloader_for(self, row):
        account_id = row.get("account_id")
        if account_id is None:
            raise RuntimeError("Telegram source has no account")
        session_name = self.account_repository.get_session(account_id)
        if not session_name:
            raise RuntimeError(f"Telegram account {account_id} is missing or disabled")
        return self.downloader_factory(self.client_factory(session_name))

    async def get_file_info(self, resource_id):
        rows = self.candidates(resource_id)
        if not rows:
            raise RuntimeError("no available Telegram source")
        canonical = rows[0]
        rows = [row for row in rows if self._same_message(row, canonical)]

        last_error = None
        for row in rows:
            try:
                downloader = self._downloader_for(row)
                info = await downloader.get_file_info(row["telegram_chat_id"], row["message_id"])
                self._validate_source_size(row, info)
                return row, downloader, info
            except Exception as exc:
                last_error = exc
                logger.warning("telegram_source_unavailable", extra={"resource_id": resource_id, "source_id": row.get("id"), "error": repr(exc)})
        raise RuntimeError("no available Telegram source") from last_error

    @staticmethod
    def _validate_source_size(row, info):
        expected = row.get("size")
        actual = getattr(info, "size", None)
        if expected is not None and actual is not None and int(expected) != int(actual):
            raise RuntimeError(
                f"Telegram source size mismatch for file {row['id']}: "
                f"indexed={expected}, telegram={actual}"
            )

    async def stream_resource(
        self, resource_id, offset=0, on_source=None, expected_hash=None, expected_bytes=None
    ):
        """Stream and fail over between accounts for the same Telegram message.

        Message identity (chat_id + message_id) defines the shared Telegram
        object in this business model. Hashes are deliberately not required for
        source selection or resuming; offset tracks the byte position.
        expected_hash remains accepted for API compatibility but is not used
        to decide whether an account can access the same message.
        """
        rows = self.candidates(resource_id)
        if not rows:
            raise RuntimeError("no available Telegram source")

        # Never splice bytes from another message merely because it maps to
        # the same Resource. All failover candidates must expose this message.
        canonical = rows[0]
        rows = [row for row in rows if self._same_message(row, canonical)]

        last_error = None
        position = offset
        attempted = set()

        for row_index, row in enumerate(rows):
            source_id = row.get("id")
            if source_id in attempted:
                continue
            attempted.add(source_id)

            emitted = 0
            try:
                downloader = self._downloader_for(row)
                info = await downloader.get_file_info(row["telegram_chat_id"], row["message_id"])
                self._validate_source_size(row, info)
                if on_source:
                    on_source(row)

                async for chunk in downloader.stream(info, offset=position):
                    if not chunk:
                        continue
                    if expected_bytes is not None:
                        remaining = expected_bytes - (position - offset)
                        if remaining <= 0:
                            return
                        chunk = chunk[:remaining]
                    if not chunk:
                        continue
                    emitted += len(chunk)
                    position += len(chunk)
                    yield chunk
                    if expected_bytes is not None and position - offset >= expected_bytes:
                        return

                if expected_bytes is not None and position - offset < expected_bytes:
                    raise RuntimeError(
                        f"Telegram source ended early at offset {position}; "
                        f"expected {expected_bytes} bytes from offset {offset}"
                    )
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "telegram_source_failed",
                    extra={
                        "resource_id": resource_id,
                        "source_id": source_id,
                        "bytes_emitted": emitted,
                        "resume_offset": position,
                        "error": repr(exc),
                    },
                )
                # Give a transient network interruption 15 seconds to settle
                # before switching accounts. The failed stream is not assumed
                # recoverable; after the grace period, the next account resumes
                # the same Telegram message at the exact current byte offset.
                if row_index < len(rows) - 1 and self.failover_delay:
                    logger.info(
                        "telegram_failover_wait",
                        extra={
                            "resource_id": resource_id,
                            "source_id": source_id,
                            "delay_seconds": self.failover_delay,
                            "resume_offset": position,
                        },
                    )
                    await asyncio.sleep(self.failover_delay)
                continue

        raise RuntimeError("all Telegram sources failed or no available source matches the message") from last_error
