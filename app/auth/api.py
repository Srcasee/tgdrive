import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from auth.dependencies import current_principal
from auth.models import Principal
from auth.repository import UserRepository
from auth.security import create_token, hash_password, verify_password
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
user_repository = UserRepository()


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


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("tgdrive_session", path="/")
    return {"status": "ok"}
