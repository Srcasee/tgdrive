import pytest

from telegram.proxy_config import get_telegram_proxy


def test_proxy_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("TG_PROXY_ENABLED", raising=False)
    assert get_telegram_proxy() is None


def test_proxy_supports_socks5(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_TYPE", "socks5")
    monkeypatch.setenv("TG_PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("TG_PROXY_PORT", "1080")
    monkeypatch.delenv("TG_PROXY_USERNAME", raising=False)
    monkeypatch.delenv("TG_PROXY_PASSWORD", raising=False)

    assert get_telegram_proxy() == {
        "proxy_type": "socks5",
        "addr": "127.0.0.1",
        "port": 1080,
        "rdns": True,
        "username": None,
        "password": None,
    }


def test_proxy_supports_http(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_TYPE", "http")
    monkeypatch.setenv("TG_PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("TG_PROXY_PORT", "8080")

    proxy = get_telegram_proxy()
    assert proxy["proxy_type"] == "http"
    assert proxy["addr"] == "127.0.0.1"
    assert proxy["port"] == 8080
    assert proxy["rdns"] is True


def test_proxy_rejects_invalid_type(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_TYPE", "vless")
    with pytest.raises(RuntimeError, match="TG_PROXY_TYPE"):
        get_telegram_proxy()


def test_proxy_rejects_invalid_port(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_PORT", "70000")
    with pytest.raises(RuntimeError, match="TG_PROXY_PORT"):
        get_telegram_proxy()
