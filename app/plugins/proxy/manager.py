from importlib.metadata import entry_points


class ProxyManager:
    GROUP = "tgdrive.proxy"

    def __init__(self):
        self.providers = {}
        self._load_plugins()

    def _load_plugins(self):
        for entry_point in entry_points(group=self.GROUP):
            try:
                self.providers[entry_point.name] = entry_point.load()
            except Exception as exc:
                print(
                    f"[PLUGIN] failed to load proxy {entry_point.name}: {exc!r}",
                    flush=True,
                )

        # Direct connection remains a core-safe fallback. All actual proxy
        # implementations are external distributions discovered by entry point.
        from .providers.none import NoneProxy
        self.providers.setdefault("none", NoneProxy)

    def get_plugin(self, name):
        provider = self.providers.get(name)
        if provider is None:
            raise RuntimeError(f"Unknown proxy plugin: {name}")
        return provider()

    def get_proxy(self):
        import os

        if os.getenv("ENABLE_PROXY", "false").lower() != "true":
            return None

        name = os.getenv("PROXY_PLUGIN", "socks5")
        return self.get_plugin(name).get_proxy()

    def list_plugins(self):
        return sorted(self.providers)
