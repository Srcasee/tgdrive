import os

import socks


class ProxyPlugin:
    """Optional network proxy capability for Telegram clients."""

    name = "proxy"
    version = "0.2.0"
    capabilities = frozenset({"telegram.proxy"})

    def get_proxy(self, account_name=None):
        if os.getenv("TG_PROXY_ENABLED", "false").lower() != "true":
            return None

        proxy_type = os.getenv("TG_PROXY_TYPE", "socks5").lower()
        proxy_types = {
            "socks5": socks.SOCKS5,
            "socks5h": socks.SOCKS5,
            "http": socks.HTTP,
        }
        if proxy_type not in proxy_types:
            raise RuntimeError(
                f"Unsupported TG_PROXY_TYPE: {proxy_type}. "
                "Supported types: socks5, socks5h, http"
            )

        host = os.getenv("TG_PROXY_HOST")
        port = os.getenv("TG_PROXY_PORT")
        if not host or not port:
            raise RuntimeError("TG_PROXY_HOST and TG_PROXY_PORT are required")

        username = os.getenv("TG_PROXY_USERNAME") or None
        password = os.getenv("TG_PROXY_PASSWORD") or None
        return (proxy_types[proxy_type], host, int(port), True, username, password)
