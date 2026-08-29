import asyncio
from types import SimpleNamespace

import pytest

import telegram.scanner as scanner


class FakeSourceRepository:
    def __init__(self):
        self.source = {
            "id": 7,
            "telegram_chat_id": 123,
            "name": "source",
            "last_message_id": 10,
            "sync_mode": "full",
        }

    def list_enabled_for_account(self, account_id):
        return [self.source]


class FakeFileRepository:
    def __init__(self):
        self.rows = {}

    def get_by_telegram_location(self, account_id, chat_id, message_id):
        return self.rows.get((account_id, chat_id, message_id))


class FakeIngestionService:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def begin_source_scan(self, source, account_id, chat_id):
        self.calls.append(("begin", source["id"], account_id, chat_id))
        return source["sync_mode"] == "full"

    def ingest(self, observation, content_hash):
        self.calls.append((
            "ingest",
            observation.message_id,
            observation.filename,
            observation.account_id,
            content_hash,
        ))
        if self.fail:
            raise RuntimeError("ingestion failure")
        return 100

    def finish_source_scan(self, source, account_id, chat_id, current_max_message_id):
        self.calls.append(("finish", source["id"], current_max_message_id))

    def fail_source_scan(self, source, account_id, chat_id):
        self.calls.append(("fail", source["id"], account_id, chat_id))


class FakeDownloader:
    def __init__(self, client):
        self.client = client

    async def get_file_info(self, chat_id, message_id):
        return SimpleNamespace(chat_id=chat_id, message_id=message_id)

    async def stream(self, file_info, offset=0):
        yield b"test-content"


class FakeClient:
    def __init__(self, messages, fail=False):
        self.messages, self.fail = messages, fail

    async def iter_dialogs(self):
        yield SimpleNamespace(id=123, entity="entity", name="source")

    async def iter_messages(self, entity, **kwargs):
        if self.fail:
            raise RuntimeError("telegram failure")
        assert kwargs == {}
        for item in self.messages:
            yield item


def make_message(message_id):
    return SimpleNamespace(
        id=message_id,
        media=True,
        file=SimpleNamespace(
            name=f" {message_id}.bin ", size=10, mime_type="application/octet-stream"
        ),
        date=SimpleNamespace(timestamp=lambda: 1700000000),
    )


def test_full_sync_emits_observations_and_finishes(monkeypatch):
    sources = FakeSourceRepository()
    ingestion = FakeIngestionService()
    files = FakeFileRepository()
    monkeypatch.setattr(scanner, "source_repository", sources)
    monkeypatch.setattr(scanner, "ingestion_service", ingestion)
    monkeypatch.setattr(scanner, "file_repository", files)
    monkeypatch.setattr(scanner, "TelegramDownloader", FakeDownloader)
    monkeypatch.setattr(scanner, "hash_telegram_file", lambda *_: asyncio.sleep(0, result="a" * 64))

    count = asyncio.run(scanner.scan_dialogs(FakeClient([make_message(5), make_message(20)]), 1))

    assert count == 2
    assert ("begin", 7, 1, 123) in ingestion.calls
    assert ("ingest", 5, "5.bin", 1, "a" * 64) in ingestion.calls
    assert ("ingest", 20, "20.bin", 1, "a" * 64) in ingestion.calls
    assert ("finish", 7, 20) in ingestion.calls
    assert not any(call[0] == "fail" for call in ingestion.calls)


def test_failed_full_sync_notifies_ingestion(monkeypatch):
    sources = FakeSourceRepository()
    ingestion = FakeIngestionService()
    files = FakeFileRepository()
    monkeypatch.setattr(scanner, "source_repository", sources)
    monkeypatch.setattr(scanner, "ingestion_service", ingestion)
    monkeypatch.setattr(scanner, "file_repository", files)
    monkeypatch.setattr(scanner, "TelegramDownloader", FakeDownloader)

    with pytest.raises(RuntimeError):
        asyncio.run(scanner.scan_dialogs(FakeClient([], fail=True), 1))

    assert ("begin", 7, 1, 123) in ingestion.calls
    assert ("fail", 7, 1, 123) in ingestion.calls
    assert not any(call[0] == "finish" for call in ingestion.calls)
