import asyncio
import hashlib

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
    service = FakeService()
    seen = []

    async def chunks():
        yield b"payload"

    result = asyncio.run(collect(tracked_stream(
        chunks(),
        service=service,
        record_id=9,
        expected_bytes=7,
        hash_content=True,
        verify=seen.append,
    )))
    assert result == [b"payload"]
    assert seen == [hashlib.sha256(b"payload").hexdigest()]
    assert service.events == [("completed", 9, 7)]


def test_tracked_stream_marks_hash_verification_failure():
    service = FakeService()

    async def chunks():
        yield b"payload"

    async def run():
        with pytest.raises(ValueError, match="hash mismatch"):
            await collect(tracked_stream(
                chunks(),
                service=service,
                record_id=10,
                expected_bytes=7,
                hash_content=True,
                verify=lambda _: (_ for _ in ()).throw(ValueError("hash mismatch")),
            ))

    asyncio.run(run())
    assert service.events[0][0:3] == ("failed", 10, 7)
