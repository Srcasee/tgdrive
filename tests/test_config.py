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
