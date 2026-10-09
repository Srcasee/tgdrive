import asyncio
from types import SimpleNamespace

import ingestion.scanner as scanner
from ingestion.source_scan import SourceScanCoordinator


class FakeIngestionService:
    def __init__(self):
        self.calls = []

    def begin_source_scan(self, source, account_id, chat_id):
        self.calls.append(("begin", source["id"], account_id, chat_id))

    def ingest(self, observation):
        self.calls.append(("ingest", observation.message_id, observation.topic_id))

    def finish_source_scan(self, source, account_id, chat_id, current_max_message_id):
        self.calls.append(("finish", source["id"], current_max_message_id))

    def fail_source_scan(self, source, account_id, chat_id):
        self.calls.append(("fail", source["id"], account_id, chat_id))


class FakeClient:
    def __init__(self, messages, fail=False):
        self.messages = messages
        self.fail = fail

    async def iter_dialogs(self):
        yield SimpleNamespace(id=123, entity="entity", name="source")

    async def iter_messages(self, entity):
        if self.fail:
            raise RuntimeError("telegram failure")
        for message in self.messages:
            yield message


def make_message(message_id, *, topic_id=None):
    return SimpleNamespace(
        id=message_id,
        media=True,
        file=SimpleNamespace(name=f"{message_id}.bin", size=10, mime_type="application/octet-stream"),
        date=SimpleNamespace(timestamp=lambda: 1700000000),
        forum_topic_id=topic_id,
        reply_to=None,
    )


def test_coordinator_runs_full_scan_and_ingests_observations(monkeypatch):
    service = FakeIngestionService()
    coordinator = SourceScanCoordinator(service)
    source = {"id": 7, "telegram_chat_id": 123, "name": "source", "sync_mode": "incremental"}

    count = asyncio.run(coordinator.scan_source(FakeClient([make_message(5, topic_id=77), make_message(20)]), 1, source))

    assert count == 2
    assert ("begin", 7, 1, 123) in service.calls
    assert ("ingest", 5, 77) in service.calls
    assert ("ingest", 20, None) in service.calls
    assert ("finish", 7, 20) in service.calls


def test_coordinator_marks_failed_scan_and_reraises():
    service = FakeIngestionService()
    coordinator = SourceScanCoordinator(service)
    source = {"id": 7, "telegram_chat_id": 123, "name": "source"}

    try:
        asyncio.run(coordinator.scan_source(FakeClient([], fail=True), 1, source))
    except RuntimeError as exc:
        assert str(exc) == "telegram failure"
    else:
        raise AssertionError("expected scan failure")

    assert ("begin", 7, 1, 123) in service.calls
    assert ("fail", 7, 1, 123) in service.calls
    assert not any(call[0] == "finish" for call in service.calls)


def test_coordinator_does_not_begin_when_dialog_missing(monkeypatch):
    service = FakeIngestionService()
    coordinator = SourceScanCoordinator(service)

    class NoDialogClient:
        async def iter_dialogs(self):
            if False:
                yield None

    source = {"id": 7, "telegram_chat_id": 999, "name": "missing"}
    assert asyncio.run(coordinator.scan_source(NoDialogClient(), 1, source)) == 0
    assert service.calls == []
