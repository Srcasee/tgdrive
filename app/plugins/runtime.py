import importlib.util
import os
from pathlib import Path


class PluginRuntime:
    """Discover optional plugins through the generic tgdrive plugin contract."""

    def __init__(self, plugin_dirs=None):
        configured = plugin_dirs or os.getenv("TGDRIVE_PLUGIN_DIRS", "/opt/tgdrive-plugins")
        self.plugin_dirs = [Path(item) for item in configured.split(os.pathsep) if item]
        self.plugins = {}
        self.generation = 0
        self.refresh()

    def refresh(self):
        self.plugins = {}
        for root in self.plugin_dirs:
            if not root.is_dir():
                continue
            for plugin_dir in sorted(path for path in root.iterdir() if path.is_dir()):
                module_path = plugin_dir / "plugin.py"
                if not module_path.is_file():
                    continue
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"tgdrive_external_plugin_{plugin_dir.name}", module_path
                    )
                    if spec is None or spec.loader is None:
                        raise ImportError("unable to create plugin module spec")
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    plugin = getattr(module, "PLUGIN", None)
                    if plugin is None:
                        factory = getattr(module, "create_plugin", None)
                        plugin = factory() if factory else None
                    if plugin is None:
                        raise TypeError("plugin.py must expose PLUGIN or create_plugin()")
                    if not all(hasattr(plugin, attr) for attr in ("name", "version", "capabilities")):
                        raise TypeError("plugin must implement the generic tgdrive plugin contract")
                    self.plugins[plugin.name] = plugin
                except Exception as exc:
                    print(
                        f"[PLUGIN] failed to load {plugin_dir.name}: {exc!r}",
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
