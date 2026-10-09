from fastapi import APIRouter, Depends, Query

from auth.dependencies import require_user
from auth.models import Principal
from common.response import api_error, api_success
from catalog.repository import CatalogRepository
from catalog.service import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])
service = CatalogService(CatalogRepository())


@router.get("")
def list_resources(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    category_id: int | None = Query(None, ge=1),
    account_id: int | None = Query(None, ge=1),
    chat_id: int | None = Query(None),
    topic_id: int | None = Query(None, ge=0),
    sort: str = Query("id"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    _: Principal = Depends(require_user),
):
    total, items = service.list_resources(page, size, category_id, sort, order, account_id, chat_id, topic_id)
    return api_success({"total": total, "page": page, "size": size, "items": items})


@router.get("/search")
def search_resources(
    q: str = Query("", min_length=1),
    category_id: int | None = Query(None, ge=1),
    account_id: int | None = Query(None, ge=1),
    chat_id: int | None = Query(None),
    topic_id: int | None = Query(None, ge=0),
    limit: int = Query(100, ge=1, le=200),
    _: Principal = Depends(require_user),
):
    return api_success(service.search(q, limit, category_id, account_id, chat_id, topic_id))


@router.get("/tree")
def resource_tree(_: Principal = Depends(require_user)):
    return api_success(service.get_tree())


@router.get("/{resource_id}")
def get_resource(resource_id: int, _: Principal = Depends(require_user)):
    resource = service.get(resource_id)
    if not resource:
        return api_error("not_found", "resource not found", 404)
    return api_success(resource)
