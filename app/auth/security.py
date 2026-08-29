import base64
import hashlib
import hmac
import json
import secrets
import time

from config import settings


class InvalidToken(Exception):
    pass


def hash_password(password: str, salt: bytes | None = None) -> str:
    if not password:
        raise ValueError("password must not be empty")
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_token(subject: str, role: str, ttl: int | None = None) -> str:
    if not settings.AUTH_SECRET:
        raise RuntimeError("AUTH_SECRET is not configured")
    payload = {
        "sub": subject,
        "role": role,
        "exp": int(time.time()) + (ttl or settings.AUTH_TOKEN_TTL),
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(settings.AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify_token(token: str) -> dict:
    if not settings.AUTH_SECRET or "." not in token:
        raise InvalidToken()
    body, signature = token.split(".", 1)
    expected = _b64(hmac.new(settings.AUTH_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise InvalidToken()
    try:
        payload = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        raise InvalidToken()
    if payload.get("exp", 0) < int(time.time()):
        raise InvalidToken()
    if not payload.get("sub") or payload.get("role") not in {"user", "admin"}:
        raise InvalidToken()
    return payload
