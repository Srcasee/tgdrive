import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.dependencies import require_admin
from auth.models import Principal
from download.service import DownloadService
from repositories.categories import CategoryRepository
from repositories.shares import ShareRepository
from database_pool import transaction

router = APIRouter(prefix="/admin", tags=["admin"])
category_repository = CategoryRepository()
share_repository = ShareRepository()
download_service = DownloadService()


@router.get("/categories")
def list_categories(_: Principal = Depends(require_admin)): return category_repository.list_all()


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


class RoleInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=2, max_length=50, pattern=r"^[a-z][a-z0-9_-]*$")
    status: int = Field(default=1, ge=0, le=1)
    sort: int = Field(default=1, ge=0, le=9999)
    description: str = Field(default="", max_length=500)


class RolePermissionsInput(BaseModel):
    permissions: list[str] = Field(default_factory=list, max_length=500)


def _role_row(row):
    if not row:
        return None
    result = dict(row)
    result["admin"] = result["code"] == "admin"
    return result


@router.get("/roles")
def list_roles(_: Principal = Depends(require_admin)):
    with transaction() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, code, status, sort, description,
                       to_char(to_timestamp(created_at), 'YYYY-MM-DD HH24:MI:SS') AS "createTime",
                       permissions
                FROM roles ORDER BY sort, id
            """)
            return [_role_row(row) for row in cursor.fetchall()]


@router.post("/roles")
def create_role(data: RoleInput, _: Principal = Depends(require_admin)):
    try:
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO roles(name, code, status, sort, description)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, name, code, status, sort, description,
                              to_char(to_timestamp(created_at), 'YYYY-MM-DD HH24:MI:SS') AS "createTime",
                              permissions
                """, (data.name.strip(), data.code, data.status, data.sort, data.description.strip()))
                return _role_row(cursor.fetchone())
    except Exception as exc:
        raise HTTPException(status_code=409, detail="角色名称或标识已存在") from exc


@router.put("/roles/{role_id}")
def update_role(role_id: int, data: RoleInput, _: Principal = Depends(require_admin)):
    try:
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT code FROM roles WHERE id=%s FOR UPDATE", (role_id,))
                existing = cursor.fetchone()
                if not existing:
                    raise HTTPException(status_code=404, detail="角色不存在")
                old_code = existing["code"]
                if old_code == "admin" and (data.code != "admin" or data.status != 1):
                    raise HTTPException(status_code=400, detail="系统管理员角色不可改标识或禁用")
                cursor.execute("""
                    UPDATE roles SET name=%s, code=%s, status=%s, sort=%s, description=%s
                    WHERE id=%s
                    RETURNING id, name, code, status, sort, description,
                              to_char(to_timestamp(created_at), 'YYYY-MM-DD HH24:MI:SS') AS "createTime",
                              permissions
                """, (data.name.strip(), data.code, data.status, data.sort, data.description.strip(), role_id))
                updated = cursor.fetchone()
                if old_code != data.code:
                    cursor.execute("UPDATE users SET role=%s WHERE role=%s", (data.code, old_code))
                return _role_row(updated)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=409, detail="角色名称或标识已存在") from exc


@router.delete("/roles/{role_id}")
def delete_role(role_id: int, _: Principal = Depends(require_admin)):
    with transaction() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT code FROM roles WHERE id=%s FOR UPDATE", (role_id,))
            existing = cursor.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="角色不存在")
            if existing["code"] == "admin":
                raise HTTPException(status_code=400, detail="系统管理员角色不可删除")
            cursor.execute("SELECT 1 FROM users WHERE role=%s LIMIT 1", (existing["code"],))
            if cursor.fetchone():
                raise HTTPException(status_code=409, detail="该角色仍被用户使用，无法删除")
            cursor.execute("DELETE FROM roles WHERE id=%s", (role_id,))
    return {"status": "ok"}


@router.get("/roles/by-code/{role_code}/permissions")
def get_role_permissions(role_code: str, _: Principal = Depends(require_admin)):
    with transaction() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT permissions FROM roles WHERE code=%s", (role_code,))
            row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="角色不存在")
    return row["permissions"]


@router.put("/roles/{role_id}/permissions")
def set_role_permissions(role_id: int, data: RolePermissionsInput, _: Principal = Depends(require_admin)):
    with transaction() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE roles SET permissions=%s::jsonb WHERE id=%s
                RETURNING id, code, permissions
            """, (json.dumps(sorted(set(data.permissions))), role_id))
            row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {"id": row["id"], "code": row["code"], "permissions": row["permissions"]}
