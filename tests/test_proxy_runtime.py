from plugins.proxy.runtime import ProxyRuntime


def test_direct_mode_is_default(monkeypatch):
    monkeypatch.delenv("TG_PROXY_ENABLED", raising=False)
    runtime = ProxyRuntime()
    assert runtime.configured_plugin() == "none"
    assert runtime.resolve() is None


def test_socks5_is_explicitly_configured(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_PLUGIN", "socks5")
    monkeypatch.setenv("TG_PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("TG_PROXY_PORT", "1080")
    runtime = ProxyRuntime()
    proxy = runtime.resolve()
    assert proxy[1] == "127.0.0.1"
    assert proxy[2] == 1080


def test_account_override_does_not_change_default(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_PLUGIN", "socks5")
    monkeypatch.setenv("TG_PROXY_ACCOUNT_A_PLUGIN", "none")
    runtime = ProxyRuntime()
    assert runtime.configured_plugin("account-a") == "none"
    assert runtime.configured_plugin("account-b") == "socks5"


def test_refresh_increments_generation():
    runtime = ProxyRuntime()
    before = runtime.generation
    runtime.refresh()
    assert runtime.generation == before + 1
    assert "none" in runtime.list_plugins()
