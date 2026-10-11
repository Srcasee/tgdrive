import asyncio

from fastapi.responses import JSONResponse, StreamingResponse

from transfer import api


class FakeResourceRepository:
    def get(self, resource_id):
        if resource_id != 1:
            return None
        return {
            "id": 1,
            "filename": "example.bin",
            "size": 5,
            "mime_type": "application/octet-stream",
            "status": "active",
            "is_available": True,
        }


class FakeSelector:
    def __init__(self):
        self.calls = []

    async def _chunks(self):
        yield b"cde"

    def stream_resource(self, resource_id, offset=0, on_source=None):
        self.calls.append((resource_id, offset, on_source is not None))
        return self._chunks()


class FakeDownloadService:
    def __init__(self):
        self.calls = []

    def start(self, resource_id, created_by=None):
        self.calls.append(("start", resource_id, created_by))
        return 17

    async def track_stream(self, record_id, chunks, expected_bytes, on_chunk=None, on_complete=None):
        received = 0
        async for chunk in chunks:
            remaining = expected_bytes - received
            if remaining <= 0:
                break
            chunk = chunk[:remaining]
            received += len(chunk)
            if on_chunk:
                on_chunk(chunk)
            yield chunk
        if received != expected_bytes:
            raise RuntimeError("transfer ended early")
        if on_complete:
            on_complete(received)
        self.calls.append(("complete", record_id, received))


def test_unknown_resource_returns_not_found():
    response = api._stream_response(999, None, "attachment")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 404


def test_invalid_range_returns_416_with_unsatisfied_content_range(monkeypatch):
    monkeypatch.setattr(api, "resource_repository", FakeResourceRepository())
    response = api._stream_response(1, "bytes=5-", "attachment")
    assert response.status_code == 416
    assert response.headers["content-range"] == "bytes */5"


def test_partial_range_response_contract(monkeypatch):
    selector = FakeSelector()
    service = FakeDownloadService()
    monkeypatch.setattr(api, "resource_repository", FakeResourceRepository())
    monkeypatch.setattr(api, "source_selector", selector)
    monkeypatch.setattr(api, "download_service", service)

    response = api._stream_response(1, "bytes=2-4", "attachment", created_by="user-1")

    assert isinstance(response, StreamingResponse)
    assert response.status_code == 206
    assert response.headers["content-length"] == "3"
    assert response.headers["content-range"] == "bytes 2-4/5"
    assert response.headers["accept-ranges"] == "bytes"
    assert selector.calls == [(1, 2, False)]
    assert service.calls == [("start", 1, "user-1")]

    async def read_body():
        return b"".join([chunk async for chunk in response.body_iterator])

    assert asyncio.run(read_body()) == b"cde"
    assert service.calls[-1] == ("complete", 17, 3)


def test_head_and_transfer_routes_keep_public_paths():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in api.router.routes}
    assert ("/resources/{resource_id}/download", ("GET",)) in paths
    assert ("/resources/{resource_id}/download", ("HEAD",)) in paths
    assert ("/resources/{resource_id}/stream", ("GET",)) in paths
    assert ("/resources/{resource_id}/stream", ("HEAD",)) in paths
