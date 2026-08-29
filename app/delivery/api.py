import asyncio
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import StreamingResponse

from auth.dependencies import require_user
from auth.models import Principal
from common.response import api_error, api_success
from delivery.range import InvalidRange, parse_single_range
from delivery.source_selector import TelegramSourceSelector
from delivery.streaming import VideoStreamService
from repositories.files import FileRepository

router = APIRouter(prefix="/files", tags=["delivery"])
file_repository = FileRepository()
source_selector = TelegramSourceSelector(file_repository)
stream_service = VideoStreamService(source_selector)


def _parse_range_or_416(value, size):
    try:
        return parse_single_range(value, size)
    except InvalidRange:
        return None


@router.get("")
def list_files(page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200), _: Principal = Depends(require_user)):
    total, rows = file_repository.list_available(size, (page - 1) * size)
    return api_success({"total": total, "page": page, "size": size, "items": rows})


@router.get("/search")
def search_files(q: str = Query("", min_length=1), _: Principal = Depends(require_user)):
    return api_success(file_repository.search(q))


@router.get("/{file_id}/download")
async def download_file(file_id: int, range_header: str | None = Header(default=None, alias="Range"), _: Principal = Depends(require_user)):
    row = file_repository.get_download_info(file_id)
    if not row:
        return api_error("not_found", "file not found", 404)
    if not row["is_available"]:
        return api_error("unavailable", "file unavailable", 404)
    parsed = _parse_range_or_416(range_header, row["size"])
    if parsed is None:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{row['size']}"})
    start, end, partial = parsed
    content_length = end - start + 1

    async def stream():
        downloaded = 0
        async for chunk in source_selector.stream_resource(row["resource_id"], offset=start):
            remaining = content_length - downloaded
            if remaining <= 0:
                break
            chunk = chunk[:remaining]
            downloaded += len(chunk)
            yield chunk
            if downloaded >= content_length:
                break

    headers = {"Accept-Ranges": "bytes", "Content-Disposition": f"attachment; filename*=UTF-8''{quote(row['filename'])}", "Content-Length": str(content_length)}
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{row['size']}"
    return StreamingResponse(stream(), status_code=206 if partial else 200, media_type=row["mime_type"] or "application/octet-stream", headers=headers)


@router.head("/{file_id}/download")
async def download_head(file_id: int, _: Principal = Depends(require_user)):
    row = file_repository.get_head_info(file_id)
    if not row or not row["is_available"]:
        return Response(status_code=404)
    return Response(headers={"Accept-Ranges": "bytes", "Content-Length": str(row["size"]), "Content-Disposition": "inline"})


@router.get("/{file_id}/stream")
async def stream_file(file_id: int, range_header: str | None = Header(None, alias="Range"), _: Principal = Depends(require_user)):
    row = file_repository.get_stream_info(file_id)
    if not row:
        return api_error("not_found", "file not found", 404)
    if not row["is_available"]:
        return Response(status_code=404)
    parsed = _parse_range_or_416(range_header, row["size"])
    if parsed is None:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{row['size']}"})
    start, end, partial = parsed
    length = end - start + 1

    async def generator():
        first_chunk = start // 4_000_000
        last_chunk = end // 4_000_000
        try:
            for index in range(first_chunk, last_chunk + 1):
                data = await stream_service.get_chunk(row["resource_id"], index)
                if not data:
                    break
                chunk_start = index * 4_000_000
                offset_start = max(0, start - chunk_start)
                offset_end = min(len(data), end - chunk_start + 1)
                if offset_start < offset_end:
                    yield data[offset_start:offset_end]
        except asyncio.CancelledError:
            print("[VIDEO STREAM] client disconnected", "file=", file_id, "range=", f"{start}-{end}", flush=True)
            raise

    headers = {"Accept-Ranges": "bytes", "Content-Length": str(length), "Content-Disposition": "inline"}
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{row['size']}"
    return StreamingResponse(generator(), status_code=206 if partial else 200, media_type=row["mime_type"] or "application/octet-stream", headers=headers)


@router.head("/{file_id}/stream")
async def stream_head(file_id: int, _: Principal = Depends(require_user)):
    row = file_repository.get_head_info(file_id)
    if not row or not row["is_available"]:
        return Response(status_code=404)
    return Response(headers={"Accept-Ranges": "bytes", "Content-Length": str(row["size"]), "Content-Disposition": "inline", "Content-Type": row["mime_type"] or "application/octet-stream"})
