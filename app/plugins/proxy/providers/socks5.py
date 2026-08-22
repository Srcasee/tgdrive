import os

from ..interface import ProxyPlugin


class Socks5Proxy(ProxyPlugin):
    name = "socks5"

    def get_proxy(self):
        enabled = os.getenv("ENABLE_PROXY", "false").lower() == "true"

        if not enabled:
            return None

        return {
            "proxy_type": os.getenv("PROXY_TYPE", "socks5"),
            "addr": os.getenv("PROXY_HOST", "proxy"),
            "port": int(os.getenv("PROXY_PORT", "1080")),
            "rdns": True,
        }
