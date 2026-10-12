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
from repositories.telegram_files import TelegramFileRepository

router = APIRouter(prefix="/resources", tags=["delivery"])
telegram_file_repository = TelegramFileRepository()
resource_repository = ResourceRepository()
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


def _resource_etag(resource):
    """Return a stable validator without hashing every delivered file.

    A recorded SHA-256 is preferred when present. Under TGDrive's immutable
    Resource-to-Telegram-message model, the Resource ID and size also identify
    the same representation across authorized accounts.
    """
    digest = resource.get("content_hash")
    if isinstance(digest, str) and len(digest) == 64:
        try:
            int(digest, 16)
        except ValueError:
            pass
        else:
            return f'"sha256:{digest.lower()}"'

    resource_id = resource.get("id")
    size = resource.get("size")
    if resource_id is not None and size is not None:
        return f'"resource:{resource_id}:{int(size)}"'
    return None


def _content_disposition(filename, disposition="attachment"):
    safe_ascii = "".join(
        ch if 32 <= ord(ch) < 127 and ch not in '\\\"' else "_"
        for ch in filename
    ) or "download"
    return f'{disposition}; filename="{safe_ascii}"; filename*=UTF-8\'\'{quote(filename, safe="")}'


async def _empty_stream():
    if False:
        yield b""


def _stream_response(resource_id, range_header, disposition, created_by=None, if_range=None):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)

    size = int(resource["size"])
    etag = _resource_etag(resource)

    # If-Range allows a partial response only when the stable Resource
    # validator matches. Resource identity is immutable in this business model.
    if range_header is not None and if_range is not None and if_range != etag:
        range_header = None

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
            expected_bytes=content_length,
        )
    )
    body = download_service.stream(
        chunks,
        record_id,
        content_length,
        # Normal delivery does not compute or persist SHA-256. Existing trusted
        # hashes may still be used for ETag/If-Range, but are not required to
        # switch accounts for the same Telegram message.
    )

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Disposition": disposition,
    }
    if etag is not None:
        headers["ETag"] = etag
    if partial:
        headers["Content-Range"] = f"bytes {start}-{end}/{size}"
    return StreamingResponse(
        body,
        status_code=206 if partial else 200,
        media_type=resource["mime_type"] or "application/octet-stream",
        headers=headers,
    )


@router.get("/{resource_id}/download")
async def download_resource(
    resource_id: int,
    range_header: str | None = Header(default=None, alias="Range"),
    if_range: str | None = Header(default=None, alias="If-Range"),
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
        if_range=if_range,
    )


@router.head("/{resource_id}/download")
async def download_head(resource_id: int, _: Principal = Depends(require_user)):
    resource = _resource(resource_id)
    if not resource:
        return Response(status_code=404)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(resource["size"]),
        "Content-Disposition": _content_disposition(resource["filename"]),
        "Content-Type": resource["mime_type"] or "application/octet-stream",
    }
    etag = _resource_etag(resource)
    if etag is not None:
        headers["ETag"] = etag
    return Response(headers=headers)


@router.get("/{resource_id}/stream")
async def stream_resource(
    resource_id: int,
    range_header: str | None = Header(None, alias="Range"),
    if_range: str | None = Header(None, alias="If-Range"),
    principal: Principal = Depends(require_user),
):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    return _stream_response(
        resource_id,
        range_header,
        "inline",
        created_by=principal.subject,
        if_range=if_range,
    )


@router.head("/{resource_id}/stream")
async def stream_head(resource_id: int, _: Principal = Depends(require_user)):
    resource = _resource(resource_id)
    if not resource:
        return Response(status_code=404)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(resource["size"]),
        "Content-Disposition": "inline",
        "Content-Type": resource["mime_type"] or "application/octet-stream",
    }
    etag = _resource_etag(resource)
    if etag is not None:
        headers["ETag"] = etag
    return Response(headers=headers)
