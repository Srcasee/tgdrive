import os


def _optional_int(name: str):
    value = os.getenv(name)
    if value in (None, ""):
        return None
    return int(value)


class Settings:
    TG_API_ID = _optional_int("TG_API_ID")
    TG_API_HASH = os.getenv("TG_API_HASH") or None
    TG_PHONE = os.getenv("TG_PHONE") or None
    TG_SESSION_DIR = os.getenv("TG_SESSION_DIR", "/data/accounts")
    TG_SESSION = os.getenv("TG_SESSION", "/data/accounts/default")
    TG_CONNECT_TIMEOUT = int(os.getenv("TG_CONNECT_TIMEOUT", "60"))
    DOWNLOAD_CHUNK_SIZE = int(os.getenv("DOWNLOAD_CHUNK_SIZE", "1048576"))
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://tgdrive:tgdrive@postgres:5432/tgdrive",
    )
    DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
    DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "10"))
    DB_POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "30"))
    AUTH_SECRET = os.getenv("AUTH_SECRET", "")
    AUTH_TOKEN_TTL = int(os.getenv("AUTH_TOKEN_TTL", "86400"))
    AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "true").lower() == "true"
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


settings = Settings()


def validate_telegram_credentials():
    """Validate Telegram API credentials only when Telegram functionality is used."""
    missing = []
    if settings.TG_API_ID is None:
        missing.append("TG_API_ID")
    if not settings.TG_API_HASH:
        missing.append("TG_API_HASH")
    if missing:
        raise RuntimeError(
            "Telegram is not configured; missing: " + ", ".join(missing)
        )
    if settings.TG_API_ID <= 0:
        raise RuntimeError("TG_API_ID must be a positive integer")
