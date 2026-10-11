import asyncio

import pytest

from download.service import DownloadService


class FakeRepository:
    def __init__(self):
        self.events = []

    def complete(self, record_id, transferred):
        self.events.append(("completed", record_id, transferred))

    def fail(self, record_id, transferred, error):
        self.events.append(("failed", record_id, transferred, error))


async def chunks(*values):
    for value in values:
        yield value


def test_track_stream_completes_after_expected_bytes():
    repository = FakeRepository()
    service = DownloadService(repository=repository)

    async def run():
        result = [chunk async for chunk in service.track_stream(7, chunks(b"abc", b"def"), 5)]

        assert result == [b"abc", b"de"]
        assert repository.events == [("completed", 7, 5)]

    asyncio.run(run())


def test_track_stream_marks_short_stream_as_failed():
    repository = FakeRepository()
    service = DownloadService(repository=repository)

    async def run():
        with pytest.raises(RuntimeError, match="expected 5 bytes, got 3"):
            [chunk async for chunk in service.track_stream(8, chunks(b"abc"), 5)]

        assert repository.events[0][:3] == ("failed", 8, 3)
        assert "expected 5 bytes, got 3" in repository.events[0][3]

    asyncio.run(run())


def test_track_stream_marks_source_errors_as_failed():
    repository = FakeRepository()
    service = DownloadService(repository=repository)

    async def broken_chunks():
        yield b"abc"
        raise RuntimeError("source failed")

    async def run():
        with pytest.raises(RuntimeError, match="source failed"):
            [chunk async for chunk in service.track_stream(9, broken_chunks(), 5)]

        assert repository.events[0][:3] == ("failed", 9, 3)
        assert repository.events[0][3] == "source failed"

    asyncio.run(run())


def test_track_stream_records_client_cancellation():
    repository = FakeRepository()
    service = DownloadService(repository=repository)

    async def run():
        async def cancelled_chunks():
            yield b"abc"
            raise asyncio.CancelledError()

        with pytest.raises(asyncio.CancelledError):
            [chunk async for chunk in service.track_stream(10, cancelled_chunks(), 5)]

        assert repository.events[0][:3] == ("failed", 10, 3)
        assert repository.events[0][3] == "download cancelled by client"

    asyncio.run(run())


def test_track_stream_runs_integrity_callback_before_completion():
    repository = FakeRepository()
    service = DownloadService(repository=repository)
    received = bytearray()
    completed = []

    async def run():
        result = [chunk async for chunk in service.track_stream(
            11,
            chunks(b"payload"),
            7,
            on_chunk=received.extend,
            on_complete=completed.append,
        )]

        assert result == [b"payload"]
        assert received == b"payload"
        assert completed == [7]
        assert repository.events == [("completed", 11, 7)]

    asyncio.run(run())
