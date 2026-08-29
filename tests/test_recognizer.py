from types import SimpleNamespace

from ingestion.recognizer import TelegramMessageRecognizer


def message(*, media=True, file=True, name="  report.pdf  ", size=42, mime_type="application/pdf", timestamp=1700000000):
    return SimpleNamespace(
        id=99,
        media=media,
        file=(SimpleNamespace(name=name, size=size, mime_type=mime_type) if file else None),
        date=(SimpleNamespace(timestamp=lambda: timestamp) if timestamp is not None else None),
    )


def test_recognizer_normalizes_file_metadata():
    observation = TelegramMessageRecognizer.recognize(
        message(), chat_id=123, account_id=7
    )

    assert observation.account_id == 7
    assert observation.chat_id == 123
    assert observation.message_id == 99
    assert observation.filename == "report.pdf"
    assert observation.size == 42
    assert observation.mime_type == "application/pdf"
    assert observation.upload_time == 1700000000
    assert observation.resource_metadata == {
        "filename": "report.pdf",
        "size": 42,
        "mime_type": "application/pdf",
    }


def test_recognizer_ignores_non_file_messages():
    assert TelegramMessageRecognizer.recognize(message(media=False), chat_id=1, account_id=2) is None
    assert TelegramMessageRecognizer.recognize(message(file=False), chat_id=1, account_id=2) is None


def test_recognizer_uses_message_id_for_missing_filename():
    observation = TelegramMessageRecognizer.recognize(
        message(name="   "), chat_id=1, account_id=2
    )
    assert observation.filename == "99.bin"
