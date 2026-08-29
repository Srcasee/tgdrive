import os


class Socks5Proxy:
    name = "socks5"

    def get_proxy(self):
        return {
            "proxy_type": os.getenv("PROXY_TYPE", "socks5"),
            "addr": os.getenv("PROXY_HOST", "proxy"),
            "port": int(os.getenv("PROXY_PORT", "1080")),
            "rdns": True,
        }
