import asyncio
import hashlib

from ingestion.verification import ContentVerificationService


class FakeResources:
    def __init__(self):
        self.calls = []

    def verify(self, resource_id, content_hash):
        self.calls.append((resource_id, content_hash))
        return 99


async def stream():
    yield b"hello "
    yield b"world"


def test_verification_hashes_only_explicit_stream():
    repo = FakeResources()
    service = ContentVerificationService(repo)

    result = asyncio.run(service.verify(7, stream()))

    assert result == 99
    assert repo.calls == [(7, hashlib.sha256(b"hello world").hexdigest())]
