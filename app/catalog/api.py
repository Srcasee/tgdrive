import json

from fastapi import APIRouter, Depends, Query

from auth.dependencies import require_user
from auth.models import Principal
from common.response import api_error, api_success
from catalog.repository import CatalogRepository
from catalog.service import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])
service = CatalogService(CatalogRepository())

_DETAIL_LABELS = {
    "id": "资源 ID", "content_hash": "内容哈希", "filename": "文件名",
    "size": "文件大小（字节）", "mime_type": "文件类型", "status": "资源状态",
    "source_count": "来源数量", "sources": "资源来源", "shares": "分享记录",
    "file_id": "文件记录 ID", "account_id": "账号 ID", "account_name": "账号名称",
    "telegram_chat_id": "群组 ID", "chat_name": "群组名称", "message_id": "消息 ID",
    "topic_id": "话题 ID", "topic_name": "话题名称", "upload_time": "上传时间",
    "token": "分享令牌", "url": "分享链接", "created_at": "创建时间",
}


def _format_detail_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return "" if value is None else str(value)


def _resource_detail(resource):
    if not resource:
        return []
    return [
        {"key": key, "label": _DETAIL_LABELS.get(key, key), "value": _format_detail_value(value)}
        for key, value in resource.items()
        if key != "category_ids"
    ]


@router.get("")
def list_resources(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    account_id: int | None = Query(None, ge=1),
    chat_id: int | None = Query(None),
    topic_id: int | None = Query(None, ge=0),
    sort: str = Query("id"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    _: Principal = Depends(require_user),
):
    total, items = service.list_resources(page, size, sort, order, account_id, chat_id, topic_id)
    return api_success({"total": total, "page": page, "size": size, "items": items})


@router.get("/search")
def search_resources(
    q: str = Query("", min_length=1),
    account_id: int | None = Query(None, ge=1),
    chat_id: int | None = Query(None),
    topic_id: int | None = Query(None, ge=0),
    limit: int = Query(100, ge=1, le=200),
    _: Principal = Depends(require_user),
):
    return api_success(service.search(q, limit, account_id, chat_id, topic_id))


@router.get("/tree")
def resource_tree(_: Principal = Depends(require_user)):
    return api_success(service.get_tree())


@router.get("/{resource_id}")
def get_resource(resource_id: int, _: Principal = Depends(require_user)):
    resource = service.get(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    return api_success(_resource_detail(resource))
