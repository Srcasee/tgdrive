import asyncio

import pytest

from download.transfer import tracked_stream


class FakeService:
    def __init__(self):
        self.events = []

    def complete(self, record_id, count):
        self.events.append(("completed", record_id, count))

    def fail(self, record_id, count, error):
        self.events.append(("failed", record_id, count, error))


async def collect(stream):
    return [chunk async for chunk in stream]


def test_tracked_stream_completes_after_expected_bytes():
    service = FakeService()

    async def chunks():
        yield b"abc"
        yield b"def"

    result = asyncio.run(collect(tracked_stream(
        chunks(), service=service, record_id=7, expected_bytes=5
    )))
    assert result == [b"abc", b"de"]
    assert service.events == [("completed", 7, 5)]


def test_tracked_stream_fails_when_source_ends_early():
    service = FakeService()

    async def chunks():
        yield b"abc"

    async def run():
        with pytest.raises(RuntimeError, match="ended early"):
            await collect(tracked_stream(
                chunks(), service=service, record_id=8, expected_bytes=5
            ))

    asyncio.run(run())
    assert service.events[0][0:3] == ("failed", 8, 3)


def test_tracked_stream_verifies_hash_before_completing():
    import hashlib

    service = FakeService()

    async def chunks():
        yield b"payload"

    result = asyncio.run(collect(tracked_stream(
        chunks(),
        service=service,
        record_id=9,
        expected_bytes=7,
        hash_content=True,
        verify=lambda digest: (_ for _ in ()).throw(ValueError("hash mismatch"))
        if digest != hashlib.sha256(b"other").hexdigest() else None,
    )))
    assert result == [b"payload"]
    assert service.events[0][0] == "completed"
