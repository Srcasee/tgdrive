import asyncio

import pytest

from delivery.source_selector import TelegramSourceSelector


class FakeAccounts:
    def __init__(self, session="acct-session"):
        self.session = session
        self.requested = []

    def get_session(self, account_id):
        self.requested.append(account_id)
        return self.session


class FakeFileRepository:
    def __init__(self, rows):
        self.rows = rows

    def list_resource_sources(self, resource_id):
        return self.rows


class FakeDownloader:
    def __init__(self, client):
        self.client = client

    async def get_file_info(self, chat_id, message_id):
        return type("Info", (), {
            "size": self.client["size"],
            "chat_id": chat_id,
            "message_id": message_id,
        })()

    async def stream(self, info, offset=0):
        if self.client.get("fail_after_chunk"):
            yield b"part"
            raise RuntimeError("connection lost")
        yield self.client.get("bytes", b"payload")


def row(file_id=1, account_id=12, size=7):
    return {
        "id": file_id,
        "account_id": account_id,
        "telegram_chat_id": 100,
        "message_id": file_id + 10,
        "size": size,
    }


def make_selector(rows, accounts=None, clients=None):
    accounts = accounts or FakeAccounts()
    clients = clients or {}

    def client_factory(session):
        return clients.setdefault(session, {"size": 7, "bytes": b"payload"})

    return TelegramSourceSelector(
        FakeFileRepository(rows),
        account_repository=accounts,
        client_factory=client_factory,
        downloader_factory=FakeDownloader,
    ), accounts


def test_selector_resolves_account_id_to_session_name():
    selector, accounts = make_selector([row()])
    selected, _, info = asyncio.run(selector.get_file_info(55))
    assert selected["id"] == 1
    assert info.size == 7
    assert accounts.requested == [12]


def test_selector_rejects_disabled_or_missing_account_session():
    selector, _ = make_selector([row()], accounts=FakeAccounts(session=None))
    with pytest.raises(RuntimeError, match="no available Telegram source"):
        asyncio.run(selector.get_file_info(55))


def test_selector_skips_source_with_mismatched_indexed_size():
    rows = [row(file_id=1, size=8), row(file_id=2, size=7)]
    selector, _ = make_selector(rows)
    selected, _, _ = asyncio.run(selector.get_file_info(55))
    assert selected["id"] == 2


def test_selector_does_not_fallback_after_emitting_bytes():
    clients = {
        "acct-session": {"size": 7, "fail_after_chunk": True, "bytes": b"payload"}
    }
    selector, _ = make_selector([row()], clients=clients)

    async def run():
        received = []
        with pytest.raises(RuntimeError, match="connection lost"):
            async for chunk in selector.stream_resource(55):
                received.append(chunk)
        assert received == [b"part"]

    asyncio.run(run())
