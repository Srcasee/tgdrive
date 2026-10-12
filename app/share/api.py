from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel

from auth.dependencies import require_user
from auth.models import Principal
from common.response import api_error
from download.api import _content_disposition, _resource, _stream_response
from repositories.shares import ShareRepository

router = APIRouter(tags=["sharing"])
share_repository = ShareRepository()


class ShareCreateInput(BaseModel):
    expires_at: datetime | None = None


@router.post("/resources/{resource_id}/share")
async def create_share(
    resource_id: int,
    request: Request,
    data: ShareCreateInput | None = None,
    _: Principal = Depends(require_user),
):
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)

    expires_at = None
    if data is not None and data.expires_at is not None:
        if data.expires_at.tzinfo is None or data.expires_at.utcoffset() is None:
            return api_error("invalid_expiration", "expires_at must include a timezone", 400)
        expires_at = int(data.expires_at.astimezone(timezone.utc).timestamp())
        if expires_at <= int(datetime.now(timezone.utc).timestamp()):
            return api_error("invalid_expiration", "expires_at must be in the future", 400)

    share = share_repository.create(resource_id, expires_at)
    token = share["token"] if isinstance(share, dict) else share
    share_id = share.get("id") if isinstance(share, dict) else None
    return {
        "id": share_id,
        "url": f"{str(request.base_url).rstrip('/')}/share/{token}",
        "resource_id": resource_id,
        "created_at": share.get("created_at") if isinstance(share, dict) else None,
        "expires_at": share.get("expires_at") if isinstance(share, dict) else expires_at,
    }


@router.get("/share/{token}")
async def shared_download(
    token: str,
    range_header: str | None = Header(None, alias="Range"),
    if_range: str | None = Header(None, alias="If-Range"),
):
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
        if_range=if_range,
    )
