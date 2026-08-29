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
    """Hash an explicitly supplied full-content byte stream without persistence."""
    digest = new_hasher()
    async for chunk in stream:
        update_hasher(digest, chunk)
    return finalize_hasher(digest)
