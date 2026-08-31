from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.dependencies import require_admin
from auth.models import Principal
from catalog.repository import CatalogRepository
from repositories.categories import CategoryRepository

router = APIRouter(prefix="/api/admin", tags=["admin"])
category_repository = CategoryRepository()
catalog_repository = CatalogRepository()


class CategoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ResourceCategoriesInput(BaseModel):
    category_ids: list[int] = Field(default_factory=list, max_length=100)


@router.get("/categories")
def list_categories(_: Principal = Depends(require_admin)):
    return category_repository.list_all()


@router.post("/categories")
def create_category(data: CategoryInput, _: Principal = Depends(require_admin)):
    try:
        return category_repository.create(data.name)
    except Exception as exc:
        raise HTTPException(status_code=409, detail="category already exists") from exc


@router.put("/categories/{category_id}")
def update_category(category_id: int, data: CategoryInput, _: Principal = Depends(require_admin)):
    category = category_repository.update(category_id, data.name)
    if not category:
        raise HTTPException(status_code=404, detail="category not found")
    return category


@router.delete("/categories/{category_id}")
def delete_category(category_id: int, _: Principal = Depends(require_admin)):
    deleted = category_repository.delete(category_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="category not found")
    return {"status": "ok"}


@router.put("/resources/{resource_id}/categories")
def set_resource_categories(
    resource_id: int,
    data: ResourceCategoriesInput,
    _: Principal = Depends(require_admin),
):
    try:
        updated = catalog_repository.set_categories(resource_id, data.category_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="resource not found")
    return updated
