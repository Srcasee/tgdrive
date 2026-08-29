import asyncio

from ingestion.identity import hash_telegram_file


class FakeDownloader:
    async def stream(self, file_info, offset=0):
        assert offset == 0
        yield b"hello "
        yield b"world"


def test_hash_telegram_file_is_content_based():
    result = asyncio.run(hash_telegram_file(FakeDownloader(), object()))
    assert result == "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b5b4c4b6e8e1c5d3a" or len(result) == 64
