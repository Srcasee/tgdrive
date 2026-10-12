from datetime import datetime, timezone
from html import escape
import secrets


from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from auth.dependencies import require_user
from auth.models import Principal
from common.response import api_error
from download.api import _content_disposition, _resource, _stream_response
from repositories.shares import ShareRepository
from catalog.repository import CatalogRepository
from database_pool import connection, transaction

router = APIRouter(tags=["sharing"])
share_repository = ShareRepository()
catalog_repository = CatalogRepository()


def _topic_share_by_token(token):
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, account_id, chat_id, topic_id, token, created_at FROM topic_shares WHERE token=%s",
                (token,),
            )
            return cursor.fetchone()


def _topic_resources(share):
    resources = []
    page = 1
    while True:
        total, items = catalog_repository.list_resources(
            200, (page - 1) * 200, "id", "desc",
            share["account_id"], share["chat_id"], share["topic_id"],
        )
        resources.extend(items)
        if len(resources) >= total or not items:
            return resources
        page += 1


class ShareCreateInput(BaseModel):
    expires_at: datetime | None = None


class TopicShareCreateInput(BaseModel):
    account_id: int
    chat_id: int
    topic_id: int


@router.post("/topics/share")
async def create_topic_share(
    data: TopicShareCreateInput,
    request: Request,
    _: Principal = Depends(require_user),
):
    total, _items = catalog_repository.list_resources(
        1, 0, "id", "desc", data.account_id, data.chat_id, data.topic_id
    )
    if total <= 0:
        return api_error("not_found", "topic has no available resources", 404)

    token = "topic_" + secrets.token_urlsafe(32)
    with transaction() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO topic_shares(account_id, chat_id, topic_id, token)
                VALUES(%s, %s, %s, %s)
                ON CONFLICT (account_id, chat_id, topic_id) DO NOTHING
                RETURNING id, token, created_at
                """,
                (data.account_id, data.chat_id, data.topic_id, token),
            )
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    """
                    SELECT id, token, created_at FROM topic_shares
                    WHERE account_id=%s AND chat_id=%s AND topic_id=%s
                    """,
                    (data.account_id, data.chat_id, data.topic_id),
                )
                row = cursor.fetchone()
    return {
        "id": row["id"],
        "url": f"{str(request.base_url).rstrip('/')}/share/{row['token']}",
        "account_id": data.account_id,
        "chat_id": data.chat_id,
        "topic_id": data.topic_id,
        "created_at": row["created_at"],
    }


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
        # Topic links use a dedicated token prefix; avoid a database lookup for
        # unknown legacy resource tokens (and keep invalid-link handling cheap).
        if not token.startswith("topic_"):
            return api_error("not_found", "share link not found", 404)
        topic_share = _topic_share_by_token(token)
        if topic_share is None:
            return api_error("not_found", "share link not found", 404)
        resources = _topic_resources(topic_share)
        if not resources:
            return api_error("not_found", "topic has no available resources", 404)
        topic_name = f"话题 {topic_share['topic_id']}"
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT MAX(topic_name) AS topic_name FROM files
                    WHERE account_id=%s AND telegram_chat_id=%s AND topic_id=%s
                      AND is_available=TRUE AND status='active'
                    """,
                    (topic_share["account_id"], topic_share["chat_id"], topic_share["topic_id"]),
                )
                topic_row = cursor.fetchone()
                if topic_row and topic_row.get("topic_name"):
                    topic_name = topic_row["topic_name"]
        safe_topic_name = escape(str(topic_name))
        safe_token = escape(token, quote=True)
        table_rows = []
        for item in resources:
            filename = escape(str(item.get("filename") or "未命名资源"))
            mime_type = escape(str(item.get("mime_type") or "未知"))
            try:
                size_text = f"{int(item.get('size') or 0):,} 字节"
            except (TypeError, ValueError):
                size_text = "未知"
            table_rows.append(
                f'<tr><td><input class="pick" type="checkbox" value="{int(item["id"])}" aria-label="选择 {filename}"></td>'
                f'<td class="filename">{filename}</td><td>{escape(size_text)}</td><td>{mime_type}</td></tr>'
            )
        html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>话题分享 - {safe_topic_name}</title>
<style>
:root{{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#1f2937;background:#f5f7fb}}
*{{box-sizing:border-box}}body{{margin:0;padding:28px 16px}}main{{max-width:1040px;margin:auto;background:white;border:1px solid #e5e7eb;border-radius:14px;padding:24px;box-shadow:0 8px 28px #0f172a0b}}
h1{{font-size:22px;margin:0 0 8px;overflow-wrap:anywhere}}.meta{{color:#64748b;font-size:14px;margin-bottom:20px}}
.toolbar{{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin:14px 0}}button{{border:0;border-radius:8px;padding:10px 16px;cursor:pointer;background:#2563eb;color:white;font-weight:600}}button:disabled{{opacity:.45;cursor:not-allowed}}
.table-wrap{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{text-align:left;border-bottom:1px solid #e5e7eb;padding:12px 10px}}th{{background:#f8fafc;color:#475569;white-space:nowrap}}.filename{{min-width:220px;overflow-wrap:anywhere}}.hint{{color:#64748b;font-size:13px;line-height:1.6}}#status{{font-size:13px;color:#475569}}@media(max-width:600px){{main{{padding:16px}}body{{padding:12px 8px}}}}
</style></head><body><main>
<h1>{safe_topic_name}</h1><div class="meta">话题资源 · 共 {len(resources)} 项 · 选择需要下载的文件</div>
<div class="toolbar"><label><input id="all" type="checkbox"> 全选</label><button id="download" disabled>下载所选（0）</button><span id="status" role="status"></span></div>
<div class="table-wrap"><table><thead><tr><th>选择</th><th>文件名</th><th>大小</th><th>类型</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
<p class="hint">此页面仅展示分享话题中的可用资源。下载会通过服务端资源下载流程逐个发起；若浏览器提示拦截多个下载，请允许此网站下载多个文件。</p>
</main><script>
const boxes=[...document.querySelectorAll('.pick')],all=document.getElementById('all'),button=document.getElementById('download'),status=document.getElementById('status');
function update(){{const count=boxes.filter(x=>x.checked).length;button.disabled=count===0;button.textContent='下载所选（'+count+'）';all.checked=count===boxes.length;all.indeterminate=count>0&&count<boxes.length;}}
boxes.forEach(x=>x.addEventListener('change',update));all.addEventListener('change',()=>{{boxes.forEach(x=>x.checked=all.checked);update();}});
button.addEventListener('click',async()=>{{const ids=boxes.filter(x=>x.checked).map(x=>x.value);if(!ids.length)return;button.disabled=true;status.textContent='正在发起下载…';for(let i=0;i<ids.length;i++){{const a=document.createElement('a');a.href='/share/{safe_token}/download/'+encodeURIComponent(ids[i]);a.style.display='none';document.body.appendChild(a);a.click();a.remove();status.textContent='已发起 '+(i+1)+'/'+ids.length+' 项';await new Promise(resolve=>setTimeout(resolve,300));}}status.textContent='已发起全部下载，请在浏览器下载管理器中查看';update();}});
update();
</script></body></html>"""
        return HTMLResponse(html, headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"})
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


@router.get("/share/{token}/download/{resource_id}")
async def shared_topic_download(
    token: str,
    resource_id: int,
    range_header: str | None = Header(None, alias="Range"),
    if_range: str | None = Header(None, alias="If-Range"),
):
    topic_share = _topic_share_by_token(token)
    if topic_share is None:
        return api_error("not_found", "share link not found", 404)
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM files f
                JOIN resources r ON r.id=f.resource_id
                JOIN telegram_sources ts
                  ON ts.account_id=f.account_id
                 AND ts.telegram_chat_id=f.telegram_chat_id
                 AND ts.enabled=TRUE
                WHERE r.id=%s AND f.account_id=%s AND f.telegram_chat_id=%s
                  AND f.topic_id=%s AND f.is_available=TRUE AND f.status='active'
                  AND r.status='active'
                LIMIT 1
                """,
                (resource_id, topic_share["account_id"], topic_share["chat_id"], topic_share["topic_id"]),
            )
            if cursor.fetchone() is None:
                return api_error("not_found", "resource is not part of this shared topic", 404)
    resource = _resource(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    return _stream_response(
        resource_id, range_header, _content_disposition(resource["filename"]), if_range=if_range
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
