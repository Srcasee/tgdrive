import asyncio

from download.source_selector import TelegramSourceSelector


class FakeRepo:
    def list_resource_sources(self, resource_id):
        # Multiple accounts can read the same Telegram message.
        return [
            {"id": 1, "account_id": 1, "telegram_chat_id": 10, "message_id": 100},
            {"id": 2, "account_id": 2, "telegram_chat_id": 10, "message_id": 100},
        ]


class FakeAccounts:
    def get_session(self, account_id):
        return str(account_id)


class FakeDownloader:
    def __init__(self, client):
        self.client = client

    async def get_file_info(self, chat_id, message_id):
        if self.client == "bad":
            raise RuntimeError("source unavailable")
        return (chat_id, message_id)

    async def stream(self, file_info, offset=0):
        if self.client == "bad":
            raise RuntimeError("stream failed")
        yield b"payload"[offset:]


class PartialFailureDownloader(FakeDownloader):
    async def get_file_info(self, chat_id, message_id):
        return (chat_id, message_id)

    async def stream(self, file_info, offset=0):
        if self.client == "bad":
            yield b"pa"[offset:]
            raise RuntimeError("stream failed after bytes")
        yield b"payload"[offset:]


def make_selector(clients, downloader_factory=FakeDownloader):
    return TelegramSourceSelector(
        FakeRepo(),
        clients.__getitem__,
        downloader_factory,
        account_repository=FakeAccounts(),
    )


def test_get_file_info_fails_over_between_accounts_for_same_message():
    clients = {"1": "bad", "2": "good"}
    selector = make_selector(clients)
    row, _, info = asyncio.run(selector.get_file_info(1))
    assert row["account_id"] == 2
    assert info == (10, 100)


def test_stream_fails_over_before_bytes_are_emitted():
    clients = {"1": "bad", "2": "good"}
    selector = make_selector(clients)

    async def collect():
        return [chunk async for chunk in selector.stream_resource(1)]

    assert asyncio.run(collect()) == [b"payload"]


def test_stream_resumes_after_partial_response_using_current_offset():
    clients = {"1": "bad", "2": "good"}
    selector = make_selector(clients, PartialFailureDownloader)

    async def collect():
        return [chunk async for chunk in selector.stream_resource(1, expected_bytes=7)]

    chunks = asyncio.run(collect())
    assert b"".join(chunks) == b"payload"
