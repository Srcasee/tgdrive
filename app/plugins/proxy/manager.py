from importlib.metadata import entry_points


class ProxyManager:
    GROUP = "tgdrive.proxy"

    def __init__(self):
        self.providers = {}
        self._load_plugins()

    def _load_plugins(self):
        for entry_point in entry_points(group=self.GROUP):
            try:
                provider = entry_point.load()
                self.providers[entry_point.name] = provider
            except Exception as exc:
                print(
                    f"[PLUGIN] failed to load proxy {entry_point.name}: {exc!r}",
                    flush=True,
                )

        # Keep the original built-ins available during the migration.
        from .providers.none import NoneProxy
        from .providers.socks5 import Socks5Proxy
        self.providers.setdefault("none", NoneProxy)
        self.providers.setdefault("socks5", Socks5Proxy)

    def get_plugin(self, name):
        provider = self.providers.get(name)
        if provider is None:
            raise RuntimeError(f"Unknown proxy plugin: {name}")
        return provider()

    def get_proxy(self):
        import os

        if os.getenv("ENABLE_PROXY", "false").lower() != "true":
            return None

        name = os.getenv("PROXY_PLUGIN", os.getenv("PROXY_TYPE", "socks5"))
        return self.get_plugin(name).get_proxy()

    def list_plugins(self):
        return sorted(self.providers)
