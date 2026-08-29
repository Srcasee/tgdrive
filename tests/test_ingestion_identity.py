import asyncio

from ingestion.identity import hash_telegram_file


class FakeDownloader:
    async def stream(self, file_info, offset=0):
        assert offset == 0
        yield b"hello "
        yield b"world"


def test_hash_telegram_file_is_content_based():
    result = asyncio.run(hash_telegram_file(FakeDownloader(), object()))
    assert result == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
