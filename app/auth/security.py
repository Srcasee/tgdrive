import base64
import hashlib
import hmac
import json
import secrets
import time
import struct
import urllib.parse

from config import settings



def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def verify_totp(secret: str, code: str, now: int | None = None, window: int = 1) -> bool:
    if not secret or not isinstance(code, str) or not code.isdigit() or len(code) != 6:
        return False
    try:
        key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    except (ValueError, TypeError):
        return False
    counter = int((time.time() if now is None else now) // 30)
    for offset in range(-window, window + 1):
        if counter + offset < 0:
            continue
        digest = hmac.new(key, struct.pack(">Q", counter + offset), hashlib.sha1).digest()
        index = digest[-1] & 0x0F
        value = (struct.unpack(">I", digest[index:index + 4])[0] & 0x7FFFFFFF) % 1_000_000
        if hmac.compare_digest(f"{value:06d}", code):
            return True
    return False


def totp_provisioning_uri(secret: str, username: str, issuer: str = "TGDrive") -> str:
    label = urllib.parse.quote(f"{issuer}:{username}", safe="")
    return f"otpauth://totp/{label}?secret={secret}&issuer={urllib.parse.quote(issuer)}&algorithm=SHA1&digits=6&period=30"


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
    if not payload.get("sub") or not isinstance(payload.get("role"), str) or not payload["role"]:
        raise InvalidToken()
    return payload
