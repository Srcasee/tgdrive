from telegram.client import get_client
from telegram.downloader import TelegramDownloader


class TelegramSourceSelector:
    """Select and fail over between Telegram backing locations for a Resource."""

    def __init__(self, file_repository, client_factory=get_client, downloader_factory=TelegramDownloader):
        self.file_repository = file_repository
        self.client_factory = client_factory
        self.downloader_factory = downloader_factory

    def candidates(self, resource_id):
        return self.file_repository.list_resource_sources(resource_id)

    async def get_file_info(self, resource_id):
        last_error = None
        for row in self.candidates(resource_id):
            if row["account_id"] is None:
                continue
            try:
                downloader = self.downloader_factory(self.client_factory(row["account_id"]))
                file_info = await downloader.get_file_info(row["telegram_chat_id"], row["message_id"])
                return row, downloader, file_info
            except Exception as exc:
                last_error = exc
                print("[FAILOVER] source unavailable", row["id"], repr(exc), flush=True)
        raise RuntimeError("no available Telegram source") from last_error

    async def stream_resource(self, resource_id, offset=0):
        position = offset
        last_error = None
        for row in self.candidates(resource_id):
            if row["account_id"] is None:
                continue
            try:
                downloader = self.downloader_factory(self.client_factory(row["account_id"]))
                file_info = await downloader.get_file_info(row["telegram_chat_id"], row["message_id"])
                async for chunk in downloader.stream(file_info, offset=position):
                    if chunk:
                        position += len(chunk)
                        yield chunk
                return
            except Exception as exc:
                last_error = exc
                print("[FAILOVER] stream source failed", row["id"], repr(exc), flush=True)
                continue
        raise RuntimeError("all Telegram sources failed") from last_error
