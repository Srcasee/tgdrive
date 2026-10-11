import logging

from repositories.accounts import AccountRepository
from telegram.client import get_client
from download.downloader import TelegramDownloader

logger = logging.getLogger(__name__)


class TelegramSourceSelector:
    """Select and safely fail over between physical Telegram file locations."""

    def __init__(
        self,
        file_repository,
        client_factory=get_client,
        downloader_factory=TelegramDownloader,
        account_repository=None,
    ):
        self.file_repository = file_repository
        self.account_repository = account_repository or AccountRepository()
        self.client_factory = client_factory
        self.downloader_factory = downloader_factory

    def candidates(self, resource_id):
        # Reuse the same Resource -> indexed files -> enabled account/source chain
        # that the catalog exposes; do not discover resources again in Telegram.
        return self.file_repository.list_resource_sources(resource_id)

    def _downloader_for(self, row):
        account_id = row.get("account_id")
        if account_id is None:
            raise RuntimeError("Telegram source has no account")
        session_name = self.account_repository.get_session(account_id)
        if not session_name:
            raise RuntimeError(f"Telegram account {account_id} is missing or disabled")
        return self.downloader_factory(self.client_factory(session_name))

    async def get_file_info(self, resource_id):
        last_error = None
        for row in self.candidates(resource_id):
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

    @staticmethod
    def _digest(row):
        value = row.get("content_hash")
        if not isinstance(value, str) or len(value) != 64:
            return None
        try:
            int(value, 16)
        except ValueError:
            return None
        return value.lower()

    async def stream_resource(
        self, resource_id, offset=0, on_source=None, expected_hash=None, expected_bytes=None
    ):
        """Stream and resume only across sources with matching recorded SHA-256.

        A nonzero offset without a known digest is pinned to one source because
        filename/size/MIME equality does not prove byte equality. During a live
        stream, failover after output requires a recorded digest on both sources.
        """
        rows = self.candidates(resource_id)
        expected_hash = self._digest({"content_hash": expected_hash})
        if expected_hash:
            # A resource digest is a strong validator for both full and ranged
            # responses; never emit bytes from a source that contradicts it.
            rows = [row for row in rows if self._digest(row) == expected_hash]
        elif offset > 0:
                # If resource-level identity is ambiguous, resume only from a
                # source with a recorded digest, if available; otherwise pin to
                # the first source and never splice another source into the body.
                first_digest = next(
                    (self._digest(row) for row in rows if self._digest(row)),
                    None,
                )
                if first_digest:
                    rows = [row for row in rows if self._digest(row) == first_digest]
                    expected_hash = first_digest
                else:
                    rows = rows[:1]

        last_error = None
        position = offset
        required_digest = expected_hash
        attempted = set()

        for row in rows:
            source_id = row.get("id")
            if source_id in attempted:
                continue
            attempted.add(source_id)

            row_digest = self._digest(row)
            if position > offset and (
                required_digest is None or row_digest != required_digest
            ):
                continue
            if offset > 0 and expected_hash and row_digest != expected_hash:
                continue

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
                if emitted:
                    # Do not stitch unrelated files together. A recorded digest
                    # is required before attempting another source at this offset.
                    if row_digest is None:
                        logger.exception("telegram_source_failed_after_output_no_digest", extra={
                            "resource_id": resource_id, "source_id": source_id,
                            "bytes_emitted": emitted, "resume_offset": position,
                        })
                        raise
                    if required_digest is not None and required_digest != row_digest:
                        logger.exception("telegram_source_failed_after_output_digest_mismatch", extra={
                            "resource_id": resource_id, "source_id": source_id,
                            "bytes_emitted": emitted, "resume_offset": position,
                        })
                        raise
                    required_digest = row_digest
                    logger.warning("telegram_source_resume_attempt", extra={
                        "resource_id": resource_id, "source_id": source_id,
                        "bytes_emitted": emitted, "resume_offset": position,
                        "content_hash": row_digest,
                    })
                    continue

                logger.warning("telegram_source_failed_before_output", extra={
                    "resource_id": resource_id, "source_id": source_id,
                    "resume_offset": position, "error": repr(exc),
                })

        raise RuntimeError("all Telegram sources failed or no verified resume source exists") from last_error
