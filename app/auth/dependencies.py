from fastapi import Cookie, HTTPException

from auth.models import Principal
from auth.security import InvalidToken, verify_token
from repositories.accounts import AccountRepository

user_repository = None


def _principal_from_cookie(token: str | None) -> Principal:
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        payload = verify_token(token)
    except InvalidToken:
        raise HTTPException(status_code=401, detail="invalid or expired session")
    return Principal(subject=str(payload["sub"]), role=payload["role"])


def current_principal(tgdrive_session: str | None = Cookie(default=None)) -> Principal:
    return _principal_from_cookie(tgdrive_session)


def require_user(principal: Principal = None) -> Principal:
    if principal is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return principal


def require_admin(principal: Principal = None) -> Principal:
    if principal is None:
        raise HTTPException(status_code=401, detail="authentication required")
    if not principal.is_admin:
        raise HTTPException(status_code=403, detail="admin permission required")
    return principal
