import asyncio
from types import SimpleNamespace

import pytest

import telegram.scanner as scanner


class FakeSourceRepository:
    def __init__(self):
        self.status = []
        self.source = {
            "id": 7,
            "telegram_chat_id": 123,
            "name": "source",
            "last_message_id": 10,
            "sync_mode": "full",
        }

    def list_enabled_for_account(self, account_id):
        return [self.source]

    def mark_scanning(self, source_id):
        self.status.append(("scanning", source_id))

    def mark_success(self, source_id, last_message_id):
        self.status.append(("success", source_id, last_message_id))

    def mark_failed(self, source_id):
        self.status.append(("failed", source_id))


class FakeFileRepository:
    def __init__(self):
        self.calls = []

    def mark_checking(self, account_id, chat_id):
        self.calls.append(("checking", account_id, chat_id))

    def mark_unverified_deleted(self, account_id, chat_id):
        self.calls.append(("deleted", account_id, chat_id))

    def reset_checking(self, account_id, chat_id):
        self.calls.append(("reset", account_id, chat_id))

    def upsert_verified_message(self, **kwargs):
        self.calls.append(("upsert", kwargs["message_id"]))


class FakeClient:
    def __init__(self, messages, fail=False):
        self.messages = messages
        self.fail = fail

    async def iter_dialogs(self):
        yield SimpleNamespace(id=123, entity="entity", name="source")

    async def iter_messages(self, entity, **kwargs):
        if self.fail:
            raise RuntimeError("telegram failure")
        assert kwargs == {}  # full sync must not pass min_id
        for message in self.messages:
            yield message


def message(message_id):
    return SimpleNamespace(
        id=message_id,
        media=True,
        file=SimpleNamespace(name=f"{message_id}.bin", size=10, mime_type="application/octet-stream"),
        date=SimpleNamespace(timestamp=lambda: 1700000000),
    )


@pytest.mark.asyncio
async def test_full_sync_scans_history_and_finalizes(monkeypatch):
    sources = FakeSourceRepository()
    files = FakeFileRepository()
    monkeypatch.setattr(scanner, "source_repository", sources)
    monkeypatch.setattr(scanner, "file_repository", files)

    await scanner.scan_dialogs(FakeClient([message(5), message(20)]), 1)

    assert ("checking", 1, 123) in files.calls
    assert ("upsert", 5) in files.calls
    assert ("upsert", 20) in files.calls
    assert ("deleted", 1, 123) in files.calls
    assert ("success", 7, 20) in sources.status
    assert not any(call[0] == "failed" for call in sources.status)


@pytest.mark.asyncio
async def test_failed_full_sync_does_not_delete(monkeypatch):
    sources = FakeSourceRepository()
    files = FakeFileRepository()
    monkeypatch.setattr(scanner, "source_repository", sources)
    monkeypatch.setattr(scanner, "file_repository", files)

    with pytest.raises(RuntimeError):
        await scanner.scan_dialogs(FakeClient([], fail=True), 1)

    assert ("checking", 1, 123) in files.calls
    assert ("reset", 1, 123) in files.calls
    assert not any(call[0] == "deleted" for call in files.calls)
    assert ("failed", 7) in sources.status
    assert not any(call[0] == "success" for call in sources.status)
