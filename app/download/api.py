from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import StreamingResponse

from auth.dependencies import require_user
from auth.models import Principal
from common.response import api_error
from download.range import InvalidRange, parse_single_range
from download.source_selector import TelegramSourceSelector
from download.service import DownloadService
from repositories.resources import ResourceRepository
from repositories.shares import ShareRepository
from repositories.telegram_files import TelegramFileRepository

router = APIRouter(prefix="/resources", tags=["delivery"])
telegram_file_repository = TelegramFileRepository()
resource_repository = ResourceRepository()
share_repository = ShareRepository()
source_selector = TelegramSourceSelector(telegram_file_repository)
download_service = DownloadService(resource_repository=resource_repository)


def _parse_range_or_416(value, size):
    try:
        return parse_single_range(value, size)
    except InvalidRange:
        return None


def _resource(resource_id):
    resource = resource_repository.get(resource_id)
    if not resource:
        return None
    if resource.get("status") != "active" or resource.get("is_available") is False:
        return None
    return resource


def _content_disposition(filename, disposition="attachment"):
    safe_ascii = "".join(
        ch if 32 <= ord(ch) < 127 and ch not in '\\\"' else "_"
        for ch in filename
    ) or "download"
    return f'{disposition}; filename="{safe_ascii}"; filename*=UTF-8\'\'{quote(filename, safe="")}'


async def _empty_stream():
    if False:
        yield b""


def _stream_response(resource_id, range_header, disposition, created_by=None):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)

    size = int(resource["size"])
    if size == 0 and range_header is None:
        start, end, partial = 0, -1, False
        content_length = 0
    else:
        parsed = _parse_range_or_416(range_header, size)
        if parsed is None:
            return Response(
                status_code=416,
                headers={"Content-Range": f"bytes */{size}"},
            )
        start, end, partial = parsed
        content_length = end - start + 1

    hash_full_content = not partial and start == 0 and content_length == size
    source_holder = {}
    record_id = download_service.start(resource_id, created_by=created_by)

    def on_source(row):
        source_holder["id"] = row["id"]

    def record_digest(digest):
        file_id = source_holder.get("id")
        if file_id is not None:
            resource_repository.verify_file(file_id, digest)

    chunks = (
        _empty_stream()
        if content_length == 0
        else source_selector.stream_resource(
            resource_id,
            offset=start,
            on_source=on_source if hash_full_content else None,
        )
    )
    body = download_service.stream(
        chunks,
        record_id,
        content_length,
        on_digest=record_digest if hash_full_content else None,
        hash_content=hash_full_content,
    )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": disposition,
    }
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(
        body,
        status_code=206 if partial else 200,
        media_type=resource["mime_type"] or "application/octet-stream",
        headers=headers,
    )


@router.post("/{resource_id}/share")
async def create_share(resource_id: int, _: Principal = Depends(require_user)):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    share = share_repository.create(resource_id)
    token = share["token"] if isinstance(share, dict) else share
    share_id = share.get("id") if isinstance(share, dict) else None
    return {"id": share_id, "url": f"/share/{token}", "resource_id": resource_id}


@router.get("/{resource_id}/download")
async def download_resource(
    resource_id: int,
    range_header: str | None = Header(default=None, alias="Range"),
    principal: Principal = Depends(require_user),
):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    return _stream_response(
        resource_id,
        range_header,
        _content_disposition(resource["filename"]),
        created_by=principal.subject,
    )


@router.head("/{resource_id}/download")
async def download_head(resource_id: int, _: Principal = Depends(require_user)):
    resource = _resource(resource_id)
    if not resource:
        return Response(status_code=404)
    return Response(headers={
        "Accept-Ranges": "bytes",
        "Content-Length": str(resource["size"]),
        "Content-Disposition": _content_disposition(resource["filename"]),
        "Content-Type": resource["mime_type"] or "application/octet-stream",
    })


@router.get("/{resource_id}/stream")
async def stream_resource(
    resource_id: int,
    range_header: str | None = Header(None, alias="Range"),
    principal: Principal = Depends(require_user),
):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    return _stream_response(
        resource_id, range_header, "inline", created_by=principal.subject
    )


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


share_router = APIRouter(prefix="/share", tags=["delivery"])


@share_router.get("/{token}")
async def shared_download(
    token: str,
    range_header: str | None = Header(None, alias="Range"),
):
    resource_id = share_repository.get_resource_id(token)
    if resource_id is None:
        return api_error("not_found", "share link not found", 404)
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    return _stream_response(
        resource_id, range_header, _content_disposition(resource["filename"])
    )
