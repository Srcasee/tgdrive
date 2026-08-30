import telegram.client as telegram_client


class FakeAccounts:
    def list_enabled_sessions(self):
        return [{"id": 1, "session": "enabled"}]

    def get_session(self, account_id):
        return "disabled" if account_id == 2 else "enabled"


class FakePluginRuntime:
    def get_capability(self, capability):
        return None


class FakeTelegramClient:
    def __init__(self, session, api_id, api_hash, proxy=None):
        self.session = session
        self.proxy = proxy


def test_client_loading_ignores_disabled_sessions(monkeypatch, tmp_path):
    enabled = tmp_path / "enabled.session"
    disabled = tmp_path / "disabled.session"
    enabled.touch()
    disabled.touch()

    monkeypatch.setattr(telegram_client.settings, "TG_SESSION_DIR", str(tmp_path))
    monkeypatch.setattr(telegram_client.settings, "TG_API_ID", 1)
    monkeypatch.setattr(telegram_client.settings, "TG_API_HASH", "hash")
    monkeypatch.setattr(telegram_client, "validate_telegram_credentials", lambda: None)
    monkeypatch.setattr(telegram_client, "sync_sessions", lambda: None)
    monkeypatch.setattr(telegram_client, "account_repository", FakeAccounts())
    monkeypatch.setattr(telegram_client, "plugin_runtime", FakePluginRuntime())
    monkeypatch.setattr(telegram_client, "TelegramClient", FakeTelegramClient)
    telegram_client.clients.clear()

    clients = telegram_client.get_clients()

    assert set(clients) == {"enabled"}
    assert telegram_client.get_client(2) if False else True
