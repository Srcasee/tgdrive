import hashlib


HASH_ALGORITHM = "sha256"
HASH_CHUNK_SIZE = 1024 * 1024


async def hash_telegram_file(downloader, file_info):
    """Hash the complete Telegram payload so Resource identity is content-based."""
    digest = hashlib.sha256()
    async for chunk in downloader.stream(file_info, offset=0):
        digest.update(chunk)
    return digest.hexdigest()
