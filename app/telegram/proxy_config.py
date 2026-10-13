"""Optional Telegram client-side proxy configuration.

The proxy service is deployed independently. Core only needs to know how to
connect to its SOCKS5/HTTP endpoint; it does not load the proxy service plugin.
"""
import os


def get_telegram_proxy():
    """Return Telethon's proxy mapping when explicitly enabled, else None."""
    if os.getenv("TG_PROXY_ENABLED", "false").strip().lower() != "true":
        return None

    proxy_type = os.getenv("TG_PROXY_TYPE", "socks5").strip().lower()
    if proxy_type not in {"socks5", "http"}:
        raise RuntimeError("TG_PROXY_TYPE must be socks5 or http")

    host = os.getenv("TG_PROXY_HOST", "proxy").strip()
    if not host:
        raise RuntimeError("TG_PROXY_HOST is required when proxy is enabled")

    try:
        port = int(os.getenv("TG_PROXY_PORT", "1080"))
    except ValueError as exc:
        raise RuntimeError("TG_PROXY_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("TG_PROXY_PORT must be between 1 and 65535")

    return {
        "proxy_type": proxy_type,
        "addr": host,
        "port": port,
        "rdns": True,
        "username": os.getenv("TG_PROXY_USERNAME") or None,
        "password": os.getenv("TG_PROXY_PASSWORD") or None,
    }
