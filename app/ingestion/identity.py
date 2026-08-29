import hashlib


HASH_ALGORITHM = "sha256"
HASH_CHUNK_SIZE = 1024 * 1024


def new_hasher():
    """Create the canonical content hasher used for verified Resource identity."""
    return hashlib.new(HASH_ALGORITHM)


def update_hasher(digest, chunk):
    if not isinstance(chunk, (bytes, bytearray, memoryview)):
        raise TypeError("content chunks must be bytes-like")
    digest.update(chunk)


def finalize_hasher(digest):
    return digest.hexdigest()


async def hash_stream(stream):
    """Hash an already-consumed-by-the-caller async byte stream.

    This helper never opens a Telegram client and never writes content to disk.
    It is intended for an explicit full-content delivery/verification path.
    """
    digest = new_hasher()
    async for chunk in stream:
        update_hasher(digest, chunk)
    return finalize_hasher(digest)


async def hash_telegram_file(downloader, file_info):
    """Compatibility helper for explicit callers that intentionally verify a file."""
    return await hash_stream(downloader.stream(file_info, offset=0))
