import os
from importlib.metadata import entry_points

from .providers.none import NoneProxy
from .providers.socks5 import Socks5Proxy


class ProxyRuntime:
    """Deployment-local proxy runtime.

    Proxy selection is deliberately external to Core. Direct connectivity is
    the default; a deployment explicitly enables a provider. No geographic
    assumption is made by TGDrive.
    """

    GROUP = "tgdrive.proxy"

    def __init__(self):
        self.providers = {"none": NoneProxy, "socks5": Socks5Proxy}
        self.generation = 0
        self._load_external_plugins()

    def _load_external_plugins(self):
        for entry_point in entry_points(group=self.GROUP):
            try:
                self.providers[entry_point.name] = entry_point.load()
            except Exception as exc:
                print(f"[PROXY] failed to load plugin {entry_point.name}: {exc!r}", flush=True)

    def configured_plugin(self, account_name=None):
        """Resolve deployment/account configuration without geo assumptions."""
        if account_name:
            key = "".join(c if c.isalnum() else "_" for c in account_name).upper()
            override = os.getenv(f"TG_PROXY_{key}_PLUGIN")
            if override:
                return override
        if os.getenv("TG_PROXY_ENABLED", "false").lower() != "true":
            return "none"
        return os.getenv("TG_PROXY_PLUGIN", "socks5")

    def resolve(self, account_name=None):
        name = self.configured_plugin(account_name)
        provider_cls = self.providers.get(name)
        if provider_cls is None:
            raise RuntimeError(f"Unknown proxy plugin: {name}")
        return provider_cls().get_proxy()

    def refresh(self):
        self.providers = {"none": NoneProxy, "socks5": Socks5Proxy}
        self._load_external_plugins()
        self.generation += 1

    def list_plugins(self):
        return sorted(self.providers)
