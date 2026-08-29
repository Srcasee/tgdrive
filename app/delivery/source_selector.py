from telegram.client import get_client
from telegram.downloader import TelegramDownloader


class TelegramSourceSelector:
    """Select a usable Telegram backing location for a logical Resource."""

    def __init__(self, file_repository, client_factory=get_client, downloader_factory=TelegramDownloader):
        self.file_repository = file_repository
        self.client_factory = client_factory
        self.downloader_factory = downloader_factory

    def candidates(self, resource_id):
        return self.file_repository.list_resource_sources(resource_id)

    async def get_file_info(self, resource_id):
        last_error = None
        for row in self.candidates(resource_id):
            account_id = row["account_id"]
            if account_id is None:
                continue
            try:
                downloader = self.downloader_factory(self.client_factory(account_id))
                info = await downloader.get_file_info(row["telegram_chat_id"], row["message_id"])
                return row, downloader, info
            except Exception as exc:
                last_error = exc
                print("[DELIVERY] source unavailable", row["id"], repr(exc), flush=True)
        raise RuntimeError("no available Telegram source") from last_error

    async def stream_resource(self, resource_id, offset=0):
        last_error = None
        for row in self.candidates(resource_id):
            account_id = row["account_id"]
            if account_id is None:
                continue
            position = offset
            try:
                downloader = self.downloader_factory(self.client_factory(account_id))
                info = await downloader.get_file_info(row["telegram_chat_id"], row["message_id"])
                async for chunk in downloader.stream(info, offset=offset):
                    if chunk:
                        position += len(chunk)
                        yield chunk
                return
            except Exception as exc:
                last_error = exc
                print("[DELIVERY] source failed", row["id"], repr(exc), flush=True)
        raise RuntimeError("all Telegram sources failed") from last_error
