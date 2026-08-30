import asyncio

import pytest

from delivery.source_selector import TelegramSourceSelector


class FakeRepo:
    def list_resource_sources(self, resource_id):
        return [
            {"id": 1, "account_id": 1, "telegram_chat_id": 10, "message_id": 100},
            {"id": 2, "account_id": 2, "telegram_chat_id": 20, "message_id": 200},
        ]


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
        yield b"ok"


class PartialFailureDownloader(FakeDownloader):
    async def stream(self, file_info, offset=0):
        if self.client == "bad":
            yield b"partial"
            raise RuntimeError("stream failed after bytes")
        yield b"backup"


def test_get_file_info_fails_over():
    clients = {1: "bad", 2: "good"}
    selector = TelegramSourceSelector(FakeRepo(), clients.__getitem__, FakeDownloader)
    row, _, info = asyncio.run(selector.get_file_info(1))
    assert row["account_id"] == 2
    assert info == (20, 200)


def test_stream_fails_over_before_bytes_are_emitted():
    clients = {1: "bad", 2: "good"}
    selector = TelegramSourceSelector(FakeRepo(), clients.__getitem__, FakeDownloader)

    async def collect():
        return [chunk async for chunk in selector.stream_resource(1)]

    assert asyncio.run(collect()) == [b"ok"]


def test_stream_does_not_retry_after_partial_response():
    clients = {1: "bad", 2: "good"}
    selector = TelegramSourceSelector(FakeRepo(), clients.__getitem__, PartialFailureDownloader)

    async def collect():
        return [chunk async for chunk in selector.stream_resource(1)]

    with pytest.raises(RuntimeError, match="stream failed after bytes"):
        asyncio.run(collect())
