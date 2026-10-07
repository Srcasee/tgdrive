from fastapi import Cookie, Depends, HTTPException

from auth.models import Principal
from auth.security import InvalidToken, verify_token
from auth.repository import UserRepository

user_repository = UserRepository()


def current_principal(tgdrive_session: str | None = Cookie(default=None)) -> Principal:
    if not tgdrive_session:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        payload = verify_token(tgdrive_session)
    except InvalidToken:
        raise HTTPException(status_code=401, detail="invalid or expired session")
    user = user_repository.get_by_id(int(payload["sub"]))
    if not user or not user["enabled"]:
        raise HTTPException(status_code=401, detail="user is disabled or missing")
    return Principal(subject=str(user["id"]), role=user["role"])


def require_user(principal: Principal = Depends(current_principal)) -> Principal:
    return principal


def require_admin(principal: Principal = Depends(current_principal)) -> Principal:
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="admin permission required")
    return principal
