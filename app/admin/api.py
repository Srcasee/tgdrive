from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.dependencies import require_admin
from auth.models import Principal
from catalog.repository import CatalogRepository
from download.service import DownloadService
from repositories.categories import CategoryRepository
from repositories.shares import ShareRepository
from database_pool import transaction

router = APIRouter(prefix="/api/admin", tags=["admin"])
category_repository = CategoryRepository()
catalog_repository = CatalogRepository()
share_repository = ShareRepository()
download_service = DownloadService()


class CategoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ResourceCategoriesInput(BaseModel):
    category_ids: list[int] = Field(default_factory=list, max_length=100)


@router.get("/categories")
def list_categories(_: Principal = Depends(require_admin)): return category_repository.list_all()


# Manual category CRUD endpoints are disabled for now; implementation retained as comments.
# @router.post("/categories")
# def create_category(data: CategoryInput, _: Principal = Depends(require_admin)):
#     try: return category_repository.create(data.name)
#     except Exception as exc: raise HTTPException(status_code=409, detail="category already exists") from exc
#
# @router.put("/categories/{category_id}")
# def update_category(category_id: int, data: CategoryInput, _: Principal = Depends(require_admin)):
#     category = category_repository.update(category_id, data.name)
#     if not category: raise HTTPException(status_code=404, detail="category not found")
#     return category
#
# @router.delete("/categories/{category_id}")
# def delete_category(category_id: int, _: Principal = Depends(require_admin)):
#     if not category_repository.delete(category_id): raise HTTPException(status_code=404, detail="category not found")
#     return {"status":"ok"}


@router.delete("/topic-shares/{share_id}")
def delete_topic_share(share_id: int, _: Principal = Depends(require_admin)):
    with transaction() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM topic_shares WHERE id=%s RETURNING id", (share_id,))
            deleted = cursor.fetchone()
    if not deleted:
        raise HTTPException(status_code=404, detail="topic share link not found")
    return {"status": "ok"}


@router.delete("/shares/{share_id}")
def delete_share(share_id: int, _: Principal = Depends(require_admin)):
    if not share_repository.delete(share_id): raise HTTPException(status_code=404, detail="share link not found")
    return {"status":"ok"}


# Manual resource categorization is disabled for now; implementation retained as comments.
# @router.put("/resources/{resource_id}/categories")
# def set_resource_categories(resource_id: int, data: ResourceCategoriesInput, _: Principal = Depends(require_admin)):
#     try: updated = catalog_repository.set_categories(resource_id, data.category_ids)
#     except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
#     if not updated: raise HTTPException(status_code=404, detail="resource not found")
#     return updated


class BulkDeleteDownloadsInput(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


@router.get("/downloads")
def list_download_records(
    status: str = "active",
    page: int = 1,
    size: int = 50,
    _: Principal = Depends(require_admin),
):
    if status not in {"active", "completed", "failed"}:
        raise HTTPException(status_code=400, detail="invalid download status")
    if page < 1 or size < 1 or size > 200:
        raise HTTPException(status_code=400, detail="invalid pagination")
    return download_service.list_by_status(status, page=page, size=size)


@router.post("/downloads/bulk-delete")
def bulk_delete_download_records(
    data: BulkDeleteDownloadsInput,
    _: Principal = Depends(require_admin),
):
    deleted = download_service.bulk_delete(sorted(set(data.ids)))
    return {"status": "ok", "deleted": deleted}
