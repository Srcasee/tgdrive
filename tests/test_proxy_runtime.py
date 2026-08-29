from plugins.runtime import PluginRuntime


def test_proxy_capability_is_optional(monkeypatch):
    monkeypatch.delenv("TG_PROXY_ENABLED", raising=False)
    runtime = PluginRuntime()
    proxy_plugin = runtime.get_capability("telegram.proxy")
    assert proxy_plugin is not None
    assert proxy_plugin.get_proxy() is None


def test_proxy_plugin_supports_socks5(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_TYPE", "socks5")
    monkeypatch.setenv("TG_PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("TG_PROXY_PORT", "1080")
    runtime = PluginRuntime()
    proxy_plugin = runtime.get_capability("telegram.proxy")
    proxy = proxy_plugin.get_proxy()
    assert proxy[1] == "127.0.0.1"
    assert proxy[2] == 1080


def test_proxy_plugin_supports_http(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_TYPE", "http")
    monkeypatch.setenv("TG_PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("TG_PROXY_PORT", "8080")
    runtime = PluginRuntime()
    proxy_plugin = runtime.get_capability("telegram.proxy")
    proxy = proxy_plugin.get_proxy()
    assert proxy[1] == "127.0.0.1"
    assert proxy[2] == 8080


def test_refresh_increments_generation():
    runtime = PluginRuntime()
    before = runtime.generation
    runtime.refresh()
    assert runtime.generation == before + 1
