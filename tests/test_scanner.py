import asyncio
from types import SimpleNamespace

import ingestion.scanner as scanner


def make_message(message_id, *, media=True, reply_to=None, forum_topic_id=None):
    return SimpleNamespace(
        id=message_id,
        media=media,
        file=(
            SimpleNamespace(
                name=f" {message_id}.bin ",
                size=10,
                mime_type="application/octet-stream",
            )
            if media else None
        ),
        date=SimpleNamespace(timestamp=lambda: 1700000000),
        reply_to=reply_to,
        forum_topic_id=forum_topic_id,
    )


class FakeClient:
    def __init__(self, messages):
        self.messages = messages

    async def iter_dialogs(self):
        yield SimpleNamespace(id=123, entity="entity", name="source")

    async def get_messages(self, entity, ids):
        assert entity == "entity"
        assert ids == 42
        return SimpleNamespace(action=SimpleNamespace(title="Release notes"))

    async def iter_messages(self, entity, **kwargs):
        assert entity == "entity"
        assert kwargs == {}
        for message in self.messages:
            yield message


def test_find_source_dialog_matches_chat_id():
    source = {"telegram_chat_id": 123}
    dialog = asyncio.run(scanner.find_source_dialog(FakeClient([]), source))
    assert dialog.id == 123


def test_iter_observations_only_yields_recognized_media():
    client = FakeClient([make_message(1, media=False), make_message(2)])
    dialog = SimpleNamespace(id=123, entity="entity", name="source")

    async def collect():
        return [
            observation async for observation
            in scanner.iter_observations(client, dialog, account_id=7)
        ]

    observations = asyncio.run(collect())
    assert len(observations) == 1
    assert observations[0].message_id == 2
    assert observations[0].file_metadata["topic_id"] is None


def test_recognizer_extracts_topic_id_from_telethon_reply_header():
    message = make_message(
        9,
        reply_to=SimpleNamespace(
            forum_topic=True,
            reply_to_top_id=42,
            reply_to_msg_id=47,
        ),
    )
    observation = scanner.recognizer.recognize(message, chat_id=123, account_id=7)
    assert observation.topic_id == 42
    assert observation.file_metadata["topic_id"] == 42


def test_recognizer_uses_topic_root_message_id_when_top_id_missing():
    message = make_message(
        9,
        reply_to=SimpleNamespace(
            forum_topic=True,
            reply_to_top_id=None,
            reply_to_msg_id=42,
        ),
    )
    observation = scanner.recognizer.recognize(message, chat_id=123, account_id=7)
    assert observation.topic_id == 42


def test_recognizer_prefers_telethon_forum_topic_id_property():
    message = make_message(9, forum_topic_id=42)
    observation = scanner.recognizer.recognize(message, chat_id=123, account_id=7)
    assert observation.topic_id == 42


def test_non_forum_reply_does_not_become_topic_id():
    message = make_message(
        9,
        reply_to=SimpleNamespace(
            forum_topic=False,
            reply_to_top_id=42,
            reply_to_msg_id=47,
        ),
    )
    observation = scanner.recognizer.recognize(message, chat_id=123, account_id=7)
    assert observation.topic_id is None


def test_iter_observations_resolves_topic_name_from_root_message():
    client = FakeClient([make_message(9, forum_topic_id=42)])
    dialog = SimpleNamespace(id=123, entity="entity", name="source")

    async def collect():
        return [observation async for observation in scanner.iter_observations(client, dialog, account_id=7)]

    observations = asyncio.run(collect())
    assert observations[0].topic_id == 42
    assert observations[0].topic_name == "Release notes"
    assert observations[0].file_metadata["topic_name"] == "Release notes"
