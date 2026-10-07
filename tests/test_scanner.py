import asyncio
from types import SimpleNamespace

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


class FakeIngestionService:
    def __init__(self):
        self.calls = []

    def begin_source_scan(self, source, account_id, chat_id):
        self.calls.append(("begin", source["id"], account_id, chat_id))
        return source["sync_mode"] == "full"

    def ingest(self, observation):
        self.calls.append(("ingest", observation.message_id, observation.filename))
        return 100

    def finish_source_scan(self, source, account_id, chat_id, current_max_message_id):
        self.calls.append(("finish", source["id"], current_max_message_id))

    def fail_source_scan(self, source, account_id, chat_id):
        self.calls.append(("fail", source["id"], account_id, chat_id))


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


class MultiSourceRepository:
    def __init__(self):
        self.sources = [
            {"id": 1, "telegram_chat_id": 101, "name": "A", "sync_mode": "full"},
            {"id": 2, "telegram_chat_id": 202, "name": "B", "sync_mode": "full"},
        ]

    def list_enabled_for_account(self, account_id):
        return self.sources


class MultiSourceClient:
    async def iter_dialogs(self):
        yield SimpleNamespace(id=101, entity="entity-a", name="A")
        yield SimpleNamespace(id=202, entity="entity-b", name="B")

    async def iter_messages(self, entity, **kwargs):
        assert kwargs == {}
        if entity == "entity-a":
            raise RuntimeError("source A failed")
        yield make_message(20)


def make_message(message_id):
    return SimpleNamespace(
        id=message_id,
        media=True,
        file=SimpleNamespace(
            name=f" {message_id}.bin ", size=10, mime_type="application/octet-stream"
        ),
        date=SimpleNamespace(timestamp=lambda: 1700000000),
    )


def test_full_sync_is_metadata_only(monkeypatch):
    sources = FakeSourceRepository()
    ingestion = FakeIngestionService()
    monkeypatch.setattr(scanner, "source_repository", sources)
    monkeypatch.setattr(scanner, "ingestion_service", ingestion)

    count = asyncio.run(scanner.scan_dialogs(FakeClient([make_message(5), make_message(20)]), 1))

    assert count == 2
    assert ("begin", 7, 1, 123) in ingestion.calls
    assert ("ingest", 5, "5.bin") in ingestion.calls
    assert ("ingest", 20, "20.bin") in ingestion.calls
    assert ("finish", 7, 20) in ingestion.calls
    assert not any(call[0] == "fail" for call in ingestion.calls)


def test_failed_full_sync_notifies_ingestion(monkeypatch):
    sources = FakeSourceRepository()
    ingestion = FakeIngestionService()
    monkeypatch.setattr(scanner, "source_repository", sources)
    monkeypatch.setattr(scanner, "ingestion_service", ingestion)

    count = asyncio.run(scanner.scan_dialogs(FakeClient([], fail=True), 1))

    assert count == 0
    assert ("begin", 7, 1, 123) in ingestion.calls
    assert ("fail", 7, 1, 123) in ingestion.calls
    assert not any(call[0] == "finish" for call in ingestion.calls)


def test_one_failed_source_does_not_block_later_sources(monkeypatch):
    sources = MultiSourceRepository()
    ingestion = FakeIngestionService()
    monkeypatch.setattr(scanner, "source_repository", sources)
    monkeypatch.setattr(scanner, "ingestion_service", ingestion)

    count = asyncio.run(scanner.scan_dialogs(MultiSourceClient(), 1))

    assert count == 1
    assert ("begin", 1, 1, 101) in ingestion.calls
    assert ("fail", 1, 1, 101) in ingestion.calls
    assert ("begin", 2, 1, 202) in ingestion.calls
    assert ("ingest", 20, "20.bin") in ingestion.calls
    assert ("finish", 2, 20) in ingestion.calls


def test_scan_source_resolves_telegram_dialog_entity(monkeypatch):
    sources = MultiSourceRepository()
    ingestion = FakeIngestionService()
    monkeypatch.setattr(scanner, "source_repository", sources)
    monkeypatch.setattr(scanner, "ingestion_service", ingestion)

    count = asyncio.run(scanner.scan_source(MultiSourceClient(), 1, sources.sources[1]))

    assert count == 1
    assert ("begin", 2, 1, 202) in ingestion.calls
    assert ("ingest", 20, "20.bin") in ingestion.calls
    assert ("finish", 2, 20) in ingestion.calls
    assert not any(call[0] == "fail" for call in ingestion.calls)
