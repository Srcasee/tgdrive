import pytest

from telegram.proxy_config import get_telegram_proxy


def test_proxy_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("TG_PROXY_ENABLED", raising=False)
    assert get_telegram_proxy() is None


def test_proxy_returns_telethon_mapping_when_enabled(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_TYPE", "socks5")
    monkeypatch.setenv("TG_PROXY_HOST", "proxy")
    monkeypatch.setenv("TG_PROXY_PORT", "1080")
    monkeypatch.setenv("TG_PROXY_USERNAME", "")
    monkeypatch.setenv("TG_PROXY_PASSWORD", "")

    assert get_telegram_proxy() == {
        "proxy_type": "socks5",
        "addr": "proxy",
        "port": 1080,
        "rdns": True,
        "username": None,
        "password": None,
    }


def test_proxy_rejects_invalid_port(monkeypatch):
    monkeypatch.setenv("TG_PROXY_ENABLED", "true")
    monkeypatch.setenv("TG_PROXY_TYPE", "socks5")
    monkeypatch.setenv("TG_PROXY_HOST", "proxy")
    monkeypatch.setenv("TG_PROXY_PORT", "70000")

    with pytest.raises(RuntimeError, match="TG_PROXY_PORT must be between"):
        get_telegram_proxy()
