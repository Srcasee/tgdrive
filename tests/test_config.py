import asyncio
import importlib


def test_config_import_allows_missing_telegram_credentials(monkeypatch):
    monkeypatch.setenv("TG_API_ID", "")
    monkeypatch.setenv("TG_API_HASH", "")

    import config

    config = importlib.reload(config)
    assert config.settings.TG_API_ID is None
    assert config.settings.TG_API_HASH is None


def test_telegram_credentials_are_validated_on_use(monkeypatch):
    monkeypatch.setenv("TG_API_ID", "")
    monkeypatch.setenv("TG_API_HASH", "")

    import config

    config = importlib.reload(config)
    try:
        config.validate_telegram_credentials()
    except RuntimeError as exc:
        assert "TG_API_ID" in str(exc)
        assert "TG_API_HASH" in str(exc)
    else:
        raise AssertionError("missing Telegram credentials were accepted")


def test_core_app_imports_without_telegram_credentials(monkeypatch):
    monkeypatch.setenv("TG_API_ID", "")
    monkeypatch.setenv("TG_API_HASH", "")

    from core.app import create_app

    app = create_app()
    assert app.title == "tgdrive"


def test_core_startup_skips_telegram_when_not_configured(monkeypatch):
    monkeypatch.setenv("TG_API_ID", "")
    monkeypatch.setenv("TG_API_HASH", "")
    monkeypatch.setenv("AUTH_SECRET", "test-secret")

    import config
    import core.lifecycle as lifecycle_module

    importlib.reload(config)
    lifecycle = lifecycle_module.ApplicationLifecycle()
    events = []
    monkeypatch.setattr(lifecycle_module, "open_pool", lambda: events.append("open"))
    monkeypatch.setattr(lifecycle_module, "initialize", lambda: events.append("init"))
    monkeypatch.setattr(lifecycle, "_bootstrap_admin", lambda: events.append("admin"))
    monkeypatch.setattr(lifecycle_module, "close_pool", lambda: events.append("close"))

    asyncio.run(lifecycle.startup())

    assert events == ["open", "init", "admin"]
    assert lifecycle.telegram_enabled is False

    asyncio.run(lifecycle.shutdown())
    assert events[-1] == "close"
