import asyncio
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import StreamingResponse

from auth.dependencies import require_user
from auth.models import Principal
from common.response import api_success
from files.stream_service import VideoStreamService
from repositories.files import FileRepository
from telegram.client import get_client
from telegram.downloader import TelegramDownloader


router = APIRouter(prefix="/files", tags=["files"])
file_repository = FileRepository()


@router.get("")
def list_files(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    _: Principal = Depends(require_user),
):
    total, rows = file_repository.list_available(size, (page - 1) * size)
    return api_success({
        "total": total,
        "page": page,
        "size": size,
        "items": rows,
    })


@router.get("/search")
def search_files(q: str = Query("", min_length=1), _: Principal = Depends(require_user)):
    return file_repository.search(q)


@router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    range_header: str | None = Header(default=None, alias="Range"),
    _: Principal = Depends(require_user),
):
    row = file_repository.get_download_info(file_id)
    if not row:
        return {"error": "file not found"}
    if not row["is_available"]:
        return {"error": "file unavailable"}

    filename = row["filename"]
    file_size = row["size"]
    mime = row["mime_type"] or "application/octet-stream"
    tg_client = get_client(row["account_id"])
    downloader = TelegramDownloader(tg_client)
    file_info = await downloader.get_file_info(row["telegram_chat_id"], row["message_id"])

    start, end = 0, file_size - 1
    if range_header:
        value = range_header.removeprefix("bytes=")
        parts = value.split("-", 1)
        try:
            if parts[0]:
                start = int(parts[0])
            if len(parts) > 1 and parts[1]:
                end = int(parts[1])
        except ValueError:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    if start < 0 or end < start or end >= file_size:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    content_length = end - start + 1

    async def stream():
        downloaded = 0
        async for chunk in downloader.stream(file_info, offset=start):
            if downloaded + len(chunk) > content_length:
                chunk = chunk[:content_length - downloaded]
            downloaded += len(chunk)
            yield chunk
            if downloaded >= content_length:
                break

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        "Content-Length": str(content_length),
    }
    status_code = 200
    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        status_code = 206

    return StreamingResponse(stream(), status_code=status_code, media_type=mime, headers=headers)


@router.head("/{file_id}/download")
async def download_head(file_id: int, _: Principal = Depends(require_user)):
    row = file_repository.get_head_info(file_id)
    if not row or not row["is_available"]:
        return Response(status_code=404)
    return Response(
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(row["size"]),
            "Content-Disposition": "inline",
        }
    )


@router.get("/{file_id}/stream")
@router.head("/{file_id}/stream")
async def stream_file(
    file_id: int,
    range_header: str | None = Header(None, alias="Range"),
    _: Principal = Depends(require_user),
):
    row = file_repository.get_stream_info(file_id)
    if not row:
        return {"error": "file not found"}
    if not row["is_available"]:
        return Response(status_code=404)

    tg_client = get_client(row["account_id"])
    downloader = TelegramDownloader(tg_client)
    file_info = await downloader.get_file_info(row["telegram_chat_id"], row["message_id"])

    size = row["size"]
    start, end = 0, size - 1
    if range_header:
        value = range_header.removeprefix("bytes=")
        parts = value.split("-", 1)
        try:
            if parts[0]:
                start = int(parts[0])
            if len(parts) > 1 and parts[1]:
                end = int(parts[1])
        except ValueError:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})

    from cache.video import CHUNK_SIZE
    if end - start + 1 > CHUNK_SIZE:
        end = min(start + CHUNK_SIZE - 1, size - 1)
    if start < 0 or end < start or start >= size or end >= size:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})

    length = end - start + 1
    stream_service = VideoStreamService(downloader)
    chunk_size = 4 * 1024 * 1024

    async def generator():
        first_chunk = start // chunk_size
        last_chunk = end // chunk_size
        try:
            for index in range(first_chunk, last_chunk + 1):
                data = await stream_service.get_chunk(file_id, file_info, index)
                if not data:
                    break
                chunk_start = index * chunk_size
                offset_start = max(0, start - chunk_start)
                offset_end = min(len(data), end - chunk_start + 1)
                if offset_start < offset_end:
                    yield data[offset_start:offset_end]
        except asyncio.CancelledError:
            print("[VIDEO STREAM] client disconnected", "file=", file_id, "range=", f"{start}-{end}", flush=True)
            raise

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Disposition": "inline",
        "Content-Type": row["mime_type"] or "application/octet-stream",
    }
    if range_header:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"

    return StreamingResponse(
        generator(),
        status_code=206 if range_header else 200,
        media_type=row["mime_type"] or "application/octet-stream",
        headers=headers,
    )
