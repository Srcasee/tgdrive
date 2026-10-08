import telegram.client as telegram_client


class FakePluginRuntime:
    def get_capability(self, capability):
        return None


class FakeTelegramClient:
    def __init__(self, session, api_id, api_hash, proxy=None):
        self.session = session
        self.proxy = proxy
        self.connected = False

    def is_connected(self):
        return self.connected

    async def disconnect(self):
        self.connected = False


def test_client_refresh_only_loads_enabled_sessions(monkeypatch, tmp_path):
    (tmp_path / "enabled.session").touch()
    (tmp_path / "disabled.session").touch()

    monkeypatch.setattr(telegram_client.settings, "TG_SESSION_DIR", str(tmp_path))
    monkeypatch.setattr(telegram_client.settings, "TG_API_ID", 1)
    monkeypatch.setattr(telegram_client.settings, "TG_API_HASH", "hash")
    monkeypatch.setattr(telegram_client, "validate_telegram_credentials", lambda: None)
    monkeypatch.setattr(telegram_client, "plugin_runtime", FakePluginRuntime())
    monkeypatch.setattr(telegram_client, "TelegramClient", FakeTelegramClient)
    telegram_client.clients.clear()

    clients = telegram_client.refresh_clients(["enabled"])

    assert set(clients) == {"enabled"}
    assert telegram_client.get_clients() is clients
