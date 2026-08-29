from pathlib import Path

import pytest

from plugins.runtime import PluginRuntime


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins"


def runtime():
    return PluginRuntime(str(PLUGIN_ROOT))


def test_proxy_capability_is_optional(monkeypatch):
    monkeypatch.delenv("TG_PROXY_ENABLED", raising=False)
    proxy_plugin = runtime().get_capability("telegram.proxy")
    assert proxy_plugin is not None
    assert proxy_plugin.get_proxy() is None


def test_proxy_plugin_supports_socks5(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_TYPE", "socks5")
    monkeypatch.setenv("TG_PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("TG_PROXY_PORT", "1080")
    proxy = runtime().get_capability("telegram.proxy").get_proxy()
    assert proxy == {"type": "socks5", "host": "127.0.0.1", "port": 1080, "username": None, "password": None}


def test_proxy_plugin_supports_http(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_TYPE", "http")
    monkeypatch.setenv("TG_PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("TG_PROXY_PORT", "8080")
    proxy = runtime().get_capability("telegram.proxy").get_proxy()
    assert proxy["type"] == "http"
    assert proxy["host"] == "127.0.0.1"
    assert proxy["port"] == 8080


def test_proxy_plugin_rejects_invalid_type(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_TYPE", "vless")
    with pytest.raises(RuntimeError, match="TG_PROXY_TYPE"):
        runtime().get_capability("telegram.proxy").get_proxy()


def test_proxy_plugin_rejects_invalid_port(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_PORT", "70000")
    with pytest.raises(RuntimeError, match="TG_PROXY_PORT"):
        runtime().get_capability("telegram.proxy").get_proxy()


def test_refresh_increments_generation():
    plugin_runtime = runtime()
    before = plugin_runtime.generation
    plugin_runtime.refresh()
    assert plugin_runtime.generation == before + 1
