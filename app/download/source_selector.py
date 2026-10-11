from repositories.accounts import AccountRepository
from telegram.client import get_client
from download.downloader import TelegramDownloader


class TelegramSourceSelector:
    """Select a physical Telegram file from the catalog's indexed Resource sources."""

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
                print("[DELIVERY] source unavailable", row["id"], repr(exc), flush=True)
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

    async def stream_resource(self, resource_id, offset=0, on_source=None):
        last_error = None
        for row in self.candidates(resource_id):
            emitted = False
            try:
                downloader = self._downloader_for(row)
                info = await downloader.get_file_info(row["telegram_chat_id"], row["message_id"])
                self._validate_source_size(row, info)
                if on_source:
                    on_source(row)
                async for chunk in downloader.stream(info, offset=offset):
                    if chunk:
                        emitted = True
                        yield chunk
                return
            except Exception as exc:
                # Fallback is safe only before the response has emitted any bytes.
                if emitted:
                    print("[DELIVERY] source failed after bytes were emitted", row["id"], repr(exc), flush=True)
                    raise
                last_error = exc
                print("[DELIVERY] source failed before bytes were emitted", row["id"], repr(exc), flush=True)
        raise RuntimeError("all Telegram sources failed") from last_error
