import asyncio

import pytest

from download.source_selector import TelegramSourceSelector


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
        if self.client.get("fail_after_chunk") and offset == 0:
            yield self.client.get("first_chunk", b"part")
            raise RuntimeError("connection lost")
        yield self.client.get("bytes", b"payload")[offset:]


def row(file_id=1, account_id=12, size=7, content_hash=None):
    return {
        "id": file_id,
        "account_id": account_id,
        "telegram_chat_id": 100,
        "message_id": file_id + 10,
        "size": size,
        "content_hash": content_hash,
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



def test_selector_resumes_from_matching_digest_source_after_partial_output():
    digest = "a" * 64
    rows = [
        row(file_id=1, account_id=12, content_hash=digest),
        row(file_id=2, account_id=13, content_hash=digest),
    ]
    clients = {
        "session-12": {"size": 7, "fail_after_chunk": True, "first_chunk": b"payl"},
        "session-13": {"size": 7, "bytes": b"payload"},
    }

    class Accounts:
        def get_session(self, account_id):
            return f"session-{account_id}"

    selector = TelegramSourceSelector(
        FakeFileRepository(rows),
        account_repository=Accounts(),
        client_factory=lambda session: clients[session],
        downloader_factory=FakeDownloader,
    )

    async def run():
        received = []
        async for chunk in selector.stream_resource(55, expected_bytes=7):
            received.append(chunk)
        assert b"".join(received) == b"payload"

    asyncio.run(run())


def test_selector_does_not_resume_across_sources_with_different_digests():
    rows = [
        row(file_id=1, account_id=12, content_hash="a" * 64),
        row(file_id=2, account_id=13, content_hash="b" * 64),
    ]
    clients = {
        "session-12": {"size": 7, "fail_after_chunk": True},
        "session-13": {"size": 7, "bytes": b"payload"},
    }

    class Accounts:
        def get_session(self, account_id):
            return f"session-{account_id}"

    selector = TelegramSourceSelector(
        FakeFileRepository(rows),
        account_repository=Accounts(),
        client_factory=lambda session: clients[session],
        downloader_factory=FakeDownloader,
    )

    async def run():
        received = []
        with pytest.raises(RuntimeError, match="all Telegram sources failed"):
            async for chunk in selector.stream_resource(55, expected_bytes=7):
                received.append(chunk)
        assert received == [b"part"]

    asyncio.run(run())
