from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from auth.dependencies import current_principal
from auth.models import Principal
from auth.repository import UserRepository
from auth.security import create_token, verify_password
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])
user_repository = UserRepository()


class LoginRequest(BaseModel):
    username: str
    password: str


@login = None
@router.post("/login")
def login(data: LoginRequest, response: Response):
    user = user_repository.get_by_username(data.username)
    if not user or not user["enabled"] or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid credentials")
    response.set_cookie(
        "tgdrive_session",
        create_token(str(user["id"]), user["role"]),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.AUTH_TOKEN_TTL,
        path="/",
    )
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


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


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("tgdrive_session", path="/")
    return {"status": "ok"}
