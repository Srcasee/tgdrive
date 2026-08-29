from importlib.metadata import entry_points

from .interface import Plugin


class PluginRuntime:
    """Discover and expose optional plugins through a generic capability API."""

    GROUP = "tgdrive.plugins"

    def __init__(self):
        self.plugins = {}
        self.generation = 0
        self.refresh()

    def refresh(self):
        self.plugins = {}
        for entry_point in entry_points(group=self.GROUP):
            try:
                plugin = entry_point.load()
                if isinstance(plugin, type):
                    plugin = plugin()
                if not isinstance(plugin, Plugin):
                    raise TypeError("plugin must implement app.plugins.Plugin")
                self.plugins[plugin.name] = plugin
            except Exception as exc:
                print(
                    f"[PLUGIN] failed to load {entry_point.name}: {exc!r}",
                    flush=True,
                )
        self.generation += 1

    def get(self, name):
        return self.plugins.get(name)

    def get_capability(self, capability):
        for plugin in self.plugins.values():
            if capability in plugin.capabilities:
                return plugin
        return None

    def list_plugins(self):
        return sorted(self.plugins)

    def list_capabilities(self):
        return sorted(
            capability
            for plugin in self.plugins.values()
            for capability in plugin.capabilities
        )
