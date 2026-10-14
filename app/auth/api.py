import time

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pathlib import Path

from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from auth.dependencies import current_principal
from auth.models import Principal
from auth.repository import UserRepository
from auth.security import create_token, hash_password, verify_password
from config import settings
from database_pool import connection

router = APIRouter(prefix="/auth", tags=["auth"])
user_repository = UserRepository()
AVATAR_DIR = Path("/data/avatars")
AVATAR_TYPES = {
    "image/jpeg": (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (".webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
}
MAX_AVATAR_SIZE = 2 * 1024 * 1024


class LoginRequest(BaseModel):
    username: str
    password: str


class ProfileUpdateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    current_password: str
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


@router.post("/login")
def login(data: LoginRequest, request: Request, response: Response):
    user = user_repository.get_by_username(data.username)
    if not user or not user["enabled"] or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid credentials")
    login_at = int(time.time())
    login_ip = request.client.host if request.client else None
    user_repository.record_login(user["id"], login_at, login_ip)
    response.set_cookie(
        "tgdrive_session",
        create_token(str(user["id"]), user["role"]),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.AUTH_TOKEN_TTL,
        path="/",
    )
    return {"id": user["id"], "username": user["username"], "role": user["role"], "last_login_at": login_at, "last_login_ip": login_ip}


@router.get("/me")
def me(response: Response, principal: Principal = Depends(current_principal)):
    user = user_repository.get_by_id(int(principal.subject))
    if not user:
        raise HTTPException(status_code=401, detail="user is missing")
    response.set_cookie(
        "tgdrive_session",
        create_token(str(user["id"]), user["role"]),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.AUTH_TOKEN_TTL,
        path="/",
    )
    return user


@router.put("/profile")
def update_profile(data: ProfileUpdateRequest, principal: Principal = Depends(current_principal)):
    user_id = int(principal.subject)
    current_user = user_repository.get_credentials_by_id(user_id)
    if not current_user:
        raise HTTPException(status_code=401, detail="user is missing")
    if not verify_password(data.current_password, current_user["password_hash"]):
        raise HTTPException(status_code=400, detail="current password is incorrect")

    username_owner = user_repository.get_by_username(data.username)
    if username_owner and int(username_owner["id"]) != user_id:
        raise HTTPException(status_code=409, detail="username already exists")

    password_hash = hash_password(data.new_password) if data.new_password else None
    try:
        updated = user_repository.update_credentials(user_id, data.username, password_hash)
    except Exception as exc:
        # The unique constraint is the final guard against concurrent username changes.
        raise HTTPException(status_code=409, detail="username already exists") from exc
    return updated



@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    principal: Principal = Depends(current_principal),
):
    image_type = AVATAR_TYPES.get(file.content_type or "")
    if not image_type:
        raise HTTPException(status_code=400, detail="仅支持 JPG、PNG 或 WebP 图片")

    content = await file.read(MAX_AVATAR_SIZE + 1)
    if not content or len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=413, detail="头像文件不能超过 2 MB")
    extension, validate_signature = image_type
    if not validate_signature(content):
        raise HTTPException(status_code=400, detail="图片文件格式无效")

    user_id = int(principal.subject)
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    destination = AVATAR_DIR / f"{user_id}{extension}"
    destination.write_bytes(content)
    for old_extension, _ in AVATAR_TYPES.values():
        old_path = AVATAR_DIR / f"{user_id}{old_extension}"
        if old_path != destination:
            old_path.unlink(missing_ok=True)

    avatar_url = f"/auth/avatar?v={int(time.time())}"
    updated = user_repository.update_avatar(user_id, avatar_url)
    if not updated:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=401, detail="user is missing")
    return updated


@router.get("/avatar")
def get_avatar(principal: Principal = Depends(current_principal)):
    user_id = int(principal.subject)
    for extension, media_type in ((".jpg", "image/jpeg"), (".png", "image/png"), (".webp", "image/webp")):
        avatar_path = AVATAR_DIR / f"{user_id}{extension}"
        if avatar_path.is_file():
            return FileResponse(avatar_path, media_type=media_type, headers={"Cache-Control": "no-cache"})
    raise HTTPException(status_code=404, detail="avatar not found")


@router.get("/permissions")
def get_my_permissions(principal: Principal = Depends(current_principal)):
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT permissions FROM roles WHERE code=%s", (principal.role,))
            row = cursor.fetchone()
    return row["permissions"] if row else None


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("tgdrive_session", path="/")
    return {"status": "ok"}
