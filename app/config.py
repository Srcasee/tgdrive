import os


class Settings:
    TG_API_ID = int(os.getenv("TG_API_ID", "0"))
    TG_API_HASH = os.getenv("TG_API_HASH")
    TG_PHONE = os.getenv("TG_PHONE")
    TG_SESSION_DIR = os.getenv("TG_SESSION_DIR", "/data/accounts")
    TG_SESSION = os.getenv("TG_SESSION", "/data/accounts/default")
    TG_CONNECT_TIMEOUT = int(os.getenv("TG_CONNECT_TIMEOUT", "60"))
    DOWNLOAD_CHUNK_SIZE = int(os.getenv("DOWNLOAD_CHUNK_SIZE", "1048576"))
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://tgdrive:tgdrive@postgres:5432/tgdrive",
    )


settings = Settings()
