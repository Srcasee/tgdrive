import os

import socks

from ..interface import ProxyPlugin


class Socks5Proxy(ProxyPlugin):
    name = "socks5"

    def get_proxy(self):
        host = os.getenv("TG_PROXY_HOST")
        port = os.getenv("TG_PROXY_PORT")
        if not host or not port:
            raise RuntimeError("TG_PROXY_HOST and TG_PROXY_PORT are required")

        username = os.getenv("TG_PROXY_USERNAME") or None
        password = os.getenv("TG_PROXY_PASSWORD") or None
        return (socks.SOCKS5, host, int(port), True, username, password)
