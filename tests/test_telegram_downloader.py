import pytest

from download.downloader import TELEGRAM_REQUEST_SIZE, TelegramDownloader


def test_default_request_size_matches_telegram_limit():
    downloader = TelegramDownloader(object())
    assert downloader.chunk_size == TELEGRAM_REQUEST_SIZE == 512 * 1024


@pytest.mark.parametrize("size", [0, 1, 500000, 1024 * 1024])
def test_request_size_rejects_invalid_values(size):
    with pytest.raises(ValueError):
        TelegramDownloader(object(), chunk_size=size)


def test_request_size_accepts_4096_multiple():
    downloader = TelegramDownloader(object(), chunk_size=256 * 1024)
    assert downloader.chunk_size == 256 * 1024


def test_stream_passes_offset_and_closes_telegram_iterator():
    import asyncio

    from download.downloader import TelegramFileInfo

    class Iterator:
        def __init__(self):
            self.items = [b"abc", b"def"]
            self.closed = False

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self.items:
                raise StopAsyncIteration
            return self.items.pop(0)

        async def aclose(self):
            self.closed = True

    class Client:
        def __init__(self):
            self.calls = []
            self.iterator = Iterator()

        def iter_download(self, media, **kwargs):
            self.calls.append((media, kwargs))
            return self.iterator

    async def run():
        client = Client()
        downloader = TelegramDownloader(client, chunk_size=256 * 1024)
        info = TelegramFileInfo(
            chat_id=1,
            message_id=2,
            filename="file.bin",
            size=6,
            mime_type="application/octet-stream",
            media=object(),
        )
        chunks = [chunk async for chunk in downloader.stream(info, offset=4096)]
        assert chunks == [b"abc", b"def"]
        assert client.calls[0][1]["offset"] == 4096
        assert client.calls[0][1]["chunk_size"] == 256 * 1024
        assert client.calls[0][1]["request_size"] == 256 * 1024
        assert client.iterator.closed

    asyncio.run(run())
