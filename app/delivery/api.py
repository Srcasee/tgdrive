import hashlib
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import StreamingResponse

from auth.dependencies import require_user
from auth.models import Principal
from common.response import api_error
from delivery.range import InvalidRange, parse_single_range
from delivery.source_selector import TelegramSourceSelector
from repositories.resources import ResourceRepository
from repositories.shares import ShareRepository
from repositories.telegram_files import TelegramFileRepository

router = APIRouter(prefix="/resources", tags=["delivery"])
telegram_file_repository = TelegramFileRepository()
resource_repository = ResourceRepository()
share_repository = ShareRepository()
source_selector = TelegramSourceSelector(telegram_file_repository)


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
    # RFC 6266/5987: keep the UTF-8 filename intact for Chinese and other
    # non-ASCII names while retaining a conservative ASCII fallback.
    safe_ascii = "".join(ch if 32 <= ord(ch) < 127 and ch not in '\\"' else "_" for ch in filename)
    if not safe_ascii:
        safe_ascii = "download"
    return f'{disposition}; filename="{safe_ascii}"; filename*=UTF-8\'\'{quote(filename, safe="")}'


def _stream_response(resource_id, range_header, disposition):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    parsed = _parse_range_or_416(range_header, resource["size"])
    if parsed is None:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{resource['size']}"})
    start, end, partial = parsed
    content_length = end - start + 1
    verify_full_content = not partial and start == 0 and content_length == resource["size"]
    source_holder = {}
    digest = hashlib.sha256() if verify_full_content else None

    def on_source(row):
        source_holder["id"] = row["id"]

    async def stream():
        downloaded = 0
        async for chunk in source_selector.stream_resource(
            resource_id, offset=start, on_source=on_source if verify_full_content else None
        ):
            remaining = content_length - downloaded
            if remaining <= 0:
                break
            chunk = chunk[:remaining]
            downloaded += len(chunk)
            if digest:
                digest.update(chunk)
            yield chunk
            if downloaded >= content_length:
                break

        if downloaded != content_length:
            raise RuntimeError(
                f"Telegram source ended early: expected {content_length} bytes, got {downloaded}"
            )
        if digest and source_holder.get("id") is not None:
            resource_repository.verify_file(source_holder["id"], digest.hexdigest())

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": disposition,
    }
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{resource['size']}"
    return StreamingResponse(
        stream(),
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
    _: Principal = Depends(require_user),
):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    return _stream_response(
        resource_id,
        range_header,
        _content_disposition(resource["filename"]),
    )


@router.head("/{resource_id}/download")
async def download_head(resource_id: int, _: Principal = Depends(require_user)):
    resource = _resource(resource_id)
    if not resource:
        return Response(status_code=404)
    return Response(
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(resource["size"]),
            "Content-Disposition": _content_disposition(resource["filename"]),
            "Content-Type": resource["mime_type"] or "application/octet-stream",
        }
    )


@router.get("/{resource_id}/stream")
async def stream_resource(
    resource_id: int,
    range_header: str | None = Header(None, alias="Range"),
    _: Principal = Depends(require_user),
):
    return _stream_response(resource_id, range_header, "inline")


@router.head("/{resource_id}/stream")
async def stream_head(resource_id: int, _: Principal = Depends(require_user)):
    resource = _resource(resource_id)
    if not resource:
        return Response(status_code=404)
    return Response(
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(resource["size"]),
            "Content-Disposition": "inline",
            "Content-Type": resource["mime_type"] or "application/octet-stream",
        }
    )


share_router = APIRouter(prefix="/share", tags=["delivery"])


@share_router.get("/{token}")
async def shared_download(token: str, range_header: str | None = Header(None, alias="Range")):
    resource_id = share_repository.get_resource_id(token)
    if resource_id is None:
        return api_error("not_found", "share link not found", 404)
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    return _stream_response(
        resource_id,
        range_header,
        _content_disposition(resource["filename"]),
    )
