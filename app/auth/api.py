from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from auth.repository import UserRepository
from auth.security import create_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
user_repository = UserRepository()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(data: LoginRequest, response: Response):
    user = user_repository.get_by_username(data.username)
    if not user or not user["enabled"] or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="invalid credentials")
    response.set_cookie(
        "tgdrive_session",
        create_token(str(user["id"]), user["role"]),
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=86400,
        path="/",
    )
    return {"id": user["id"], "username": user["username"], "role": user["role"]}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("tgdrive_session", path="/")
    return {"status": "ok"}
