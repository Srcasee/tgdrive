import pytest

from telegram.downloader import TELEGRAM_REQUEST_SIZE, TelegramDownloader


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
