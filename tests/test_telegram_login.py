import asyncio
import sys
from types import SimpleNamespace

import telegram.login as login


class FakeClient:
    def __init__(self, session, api_id, api_hash, proxy=None):
        self.session = session
        self.api_id = api_id
        self.api_hash = api_hash
        self.proxy = proxy
        self.disconnected = False

    async def start(self, phone):
        self.phone = phone

    async def get_me(self):
        return SimpleNamespace(username="test-user", first_name="Test")

    async def disconnect(self):
        self.disconnected = True


class FakePlugin:
    def get_proxy(self, account):
        return {"proxy_type": "socks5", "addr": "proxy", "port": 1080}


class FakeRuntime:
    def get_capability(self, capability):
        assert capability == "telegram.proxy"
        return FakePlugin()


class FakeAccounts:
    def __init__(self):
        self.calls = []

    def upsert_session(self, account, display_name):
        self.calls.append((account, display_name))
        return 1


def test_login_initializes_and_closes_database_pool(monkeypatch, tmp_path):
    events = []
    accounts = FakeAccounts()

    monkeypatch.setenv("TG_API_ID", "123")
    monkeypatch.setenv("TG_API_HASH", "hash")
    monkeypatch.setenv("TG_PHONE", "+10000000000")
    monkeypatch.setenv("TG_SESSION_DIR", str(tmp_path))
    monkeypatch.setenv("TG_ACCOUNT_NAME", "named-account")
    monkeypatch.setattr(sys, "argv", ["login.py"])
    monkeypatch.setattr(login, "open_pool", lambda: events.append("open"))
    monkeypatch.setattr(login, "initialize", lambda: events.append("initialize"))
    monkeypatch.setattr(login, "close_pool", lambda: events.append("close"))
    monkeypatch.setattr(login, "PluginRuntime", FakeRuntime)
    monkeypatch.setattr(login, "TelegramClient", FakeClient)
    monkeypatch.setattr(login, "AccountRepository", lambda: accounts)

    asyncio.run(login.main())

    assert events == ["open", "initialize", "close"]
    assert accounts.calls == [("named-account", "test-user")]
