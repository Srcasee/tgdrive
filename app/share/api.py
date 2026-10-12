from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import HTMLResponse
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


@router.get("/share/{token}", response_class=HTMLResponse)
async def shared_resource_page(token: str):
    """Public landing page for a valid share link; the file is downloaded separately."""
    resource_id = share_repository.get_resource_id(token)
    if resource_id is None:
        return api_error("not_found", "share link not found", 404)
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)

    filename = escape(str(resource.get("filename") or "未命名资源"))
    mime_type = escape(str(resource.get("mime_type") or "未知"))
    size = resource.get("size")
    try:
        size_text = f"{int(size):,} 字节" if size is not None else "未知"
    except (TypeError, ValueError):
        size_text = "未知"
    download_url = f"/share/{escape(token, quote=True)}/download"
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>分享文件 - {filename}</title>
  <style>
    :root {{ color-scheme: light dark; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: Canvas; color: CanvasText; }}
    main {{ box-sizing: border-box; width: min(560px, calc(100% - 32px)); padding: 28px; border: 1px solid color-mix(in srgb, CanvasText 18%, transparent); border-radius: 16px; }}
    h1 {{ font-size: 1.35rem; overflow-wrap: anywhere; }}
    dl {{ display: grid; grid-template-columns: 90px minmax(0, 1fr); gap: 12px; }}
    dt {{ opacity: .65; }} dd {{ margin: 0; overflow-wrap: anywhere; }}
    a {{ display: inline-flex; margin-top: 12px; padding: 11px 18px; border-radius: 8px; background: #2563eb; color: white; text-decoration: none; font-weight: 600; }}
    .hint {{ opacity: .7; font-size: .9rem; }}
  </style>
</head>
<body>
  <main>
    <h1>分享文件</h1>
    <dl>
      <dt>文件名</dt><dd>{filename}</dd>
      <dt>文件大小</dt><dd>{size_text}</dd>
      <dt>文件类型</dt><dd>{mime_type}</dd>
    </dl>
    <a href="{download_url}">下载文件</a>
    <p class="hint">此链接可供持有链接的人访问。请仅向可信任的人分享。</p>
  </main>
</body>
</html>"""
    return HTMLResponse(
        html,
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"},
    )


@router.get("/share/{token}/download")
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
