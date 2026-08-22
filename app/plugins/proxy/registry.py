from .providers.none import NoneProxy
from .providers.socks5 import Socks5Proxy


class ProxyRegistry:
    providers = {
        "none": NoneProxy,
        "socks5": Socks5Proxy,
    }

    @classmethod
    def get(cls, name):
        provider = cls.providers.get(name)

        if provider is None:
            raise RuntimeError(f"Unknown proxy plugin: {name}")

        return provider()
