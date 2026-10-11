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


def test_tracked_stream_records_digest_before_completing():
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
        on_digest=seen.append,
    )))
    assert result == [b"payload"]
    assert seen == [hashlib.sha256(b"payload").hexdigest()]
    assert service.events == [("completed", 9, 7)]


def test_tracked_stream_marks_digest_callback_failure():
    service = FakeService()

    async def chunks():
        yield b"payload"

    async def run():
        with pytest.raises(ValueError, match="digest callback failed"):
            await collect(tracked_stream(
                chunks(),
                service=service,
                record_id=10,
                expected_bytes=7,
                hash_content=True,
                on_digest=lambda _: (_ for _ in ()).throw(ValueError("digest callback failed")),
            ))

    asyncio.run(run())
    assert service.events[0][0:3] == ("failed", 10, 7)


def test_download_service_limits_concurrent_transfers():
    from download.service import DownloadService

    class Repository:
        def complete(self, record_id, count):
            pass

        def fail(self, record_id, count, error):
            pass

    async def run():
        service = DownloadService(repository=Repository(), resource_repository=object(), max_concurrent=1)
        active = 0
        peak = 0
        both_started = asyncio.Event()

        async def source():
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            if active == 1:
                await asyncio.sleep(0.02)
            else:
                both_started.set()
            yield b"x"
            active -= 1

        async def consume(record_id):
            await collect(service.stream(source(), record_id, 1))

        await asyncio.gather(consume(1), consume(2))
        assert peak == 1
        assert not both_started.is_set()

    asyncio.run(run())


def test_download_concurrency_limit_can_be_configured(monkeypatch):
    from download.service import DownloadService

    monkeypatch.setenv("TGDRIVE_MAX_CONCURRENT_DOWNLOADS", "3")
    service = DownloadService(repository=object(), resource_repository=object())
    assert service.max_concurrent == 3

    monkeypatch.setenv("TGDRIVE_MAX_CONCURRENT_DOWNLOADS", "invalid")
    with pytest.raises(ValueError, match="must be an integer"):
        DownloadService(repository=object(), resource_repository=object())


def test_download_queue_metrics_return_to_zero_after_transfers():
    from download.service import DownloadService

    class Repository:
        def complete(self, record_id, count):
            pass

        def fail(self, record_id, count, error):
            pass

    async def run():
        service = DownloadService(repository=Repository(), resource_repository=object(), max_concurrent=1)

        async def source():
            yield b"x"

        await asyncio.gather(
            collect(service.stream(source(), 1, 1)),
            collect(service.stream(source(), 2, 1)),
        )
        assert service._active_transfers == 0
        assert service._queued_transfers == 0

    asyncio.run(run())
