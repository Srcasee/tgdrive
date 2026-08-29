import asyncio
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import StreamingResponse

from auth.dependencies import require_user
from auth.models import Principal
from common.response import api_error, api_success
from delivery.range import InvalidRange, parse_single_range
from delivery.source_selector import TelegramSourceSelector
from delivery.streaming import VideoStreamService
from repositories.files import FileRepository
from repositories.resources import ResourceRepository
from cache.video import CHUNK_SIZE

router = APIRouter(prefix="/resources", tags=["delivery"])
file_repository = FileRepository()
resource_repository = ResourceRepository()
source_selector = TelegramSourceSelector(file_repository)
stream_service = VideoStreamService(source_selector)


def _parse_range_or_416(value, size):
    try:
        return parse_single_range(value, size)
    except InvalidRange:
        return None


def _resource(resource_id):
    return resource_repository.get(resource_id)


@router.get("/{resource_id}/download")
async def download_resource(resource_id: int, range_header: str | None = Header(default=None, alias="Range"), _: Principal = Depends(require_user)):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    parsed = _parse_range_or_416(range_header, resource["size"])
    if parsed is None:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{resource['size']}"})
    start, end, partial = parsed
    content_length = end - start + 1

    async def stream():
        downloaded = 0
        async for chunk in source_selector.stream_resource(resource_id, offset=start):
            remaining = content_length - downloaded
            if remaining <= 0:
                break
            chunk = chunk[:remaining]
            downloaded += len(chunk)
            yield chunk
            if downloaded >= content_length:
                break

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(resource['filename'])}",
        "Content-Length": str(content_length),
    }
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{resource['size']}"
    return StreamingResponse(stream(), status_code=206 if partial else 200, media_type=resource["mime_type"] or "application/octet-stream", headers=headers)


@router.head("/{resource_id}/download")
async def download_head(resource_id: int, _: Principal = Depends(require_user)):
    resource = _resource(resource_id)
    if not resource:
        return Response(status_code=404)
    return Response(headers={
        "Accept-Ranges": "bytes",
        "Content-Length": str(resource["size"]),
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(resource['filename'])}",
        "Content-Type": resource["mime_type"] or "application/octet-stream",
    })


@router.get("/{resource_id}/stream")
async def stream_resource(resource_id: int, range_header: str | None = Header(None, alias="Range"), _: Principal = Depends(require_user)):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    parsed = _parse_range_or_416(range_header, resource["size"])
    if parsed is None:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{resource['size']}"})
    start, end, partial = parsed
    length = end - start + 1

    async def generator():
        first_chunk = start // CHUNK_SIZE
        last_chunk = end // CHUNK_SIZE
        try:
            for index in range(first_chunk, last_chunk + 1):
                data = await stream_service.get_chunk(resource_id, index)
                if not data:
                    break
                chunk_start = index * CHUNK_SIZE
                offset_start = max(0, start - chunk_start)
                offset_end = min(len(data), end - chunk_start + 1)
                if offset_start < offset_end:
                    yield data[offset_start:offset_end]
        except asyncio.CancelledError:
            print("[VIDEO STREAM] client disconnected", "resource=", resource_id, "range=", f"{start}-{end}", flush=True)
            raise

    headers = {"Accept-Ranges": "bytes", "Content-Length": str(length), "Content-Disposition": "inline"}
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{resource['size']}"
    return StreamingResponse(generator(), status_code=206 if partial else 200, media_type=resource["mime_type"] or "application/octet-stream", headers=headers)


@router.head("/{resource_id}/stream")
async def stream_head(resource_id: int, _: Principal = Depends(require_user)):
    resource = _resource(resource_id)
    if not resource:
        return Response(status_code=404)
    return Response(headers={
        "Accept-Ranges": "bytes",
        "Content-Length": str(resource["size"]),
        "Content-Disposition": "inline",
        "Content-Type": resource["mime_type"] or "application/octet-stream",
    })
