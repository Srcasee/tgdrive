from contextlib import contextmanager

import auth.repository as auth_repository_module
from auth.repository import UserRepository


class FakeCursor:
    def __init__(self, responses, statements):
        self.responses = iter(responses)
        self.statements = statements

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, params=None):
        self.statements.append((query, params))

    def fetchone(self):
        return next(self.responses)


class FakeConnection:
    def __init__(self, responses, statements):
        self._cursor = FakeCursor(responses, statements)

    def cursor(self):
        return self._cursor


def _patch_transaction(monkeypatch, responses):
    statements = []
    conn = FakeConnection(responses, statements)

    @contextmanager
    def fake_transaction():
        yield conn

    monkeypatch.setattr(auth_repository_module, "transaction", fake_transaction)
    return statements


def test_bootstrap_does_not_recreate_admin_after_username_change(monkeypatch):
    statements = _patch_transaction(
        monkeypatch,
        [{"id": 12, "username": "renamed-admin"}],
    )

    result = UserRepository().ensure_admin("admin", "unused-hash")

    assert result == {
        "id": 12,
        "username": "renamed-admin",
        "created": False,
    }
    assert not any("INSERT INTO users" in query for query, _ in statements)


def test_bootstrap_creates_admin_when_no_admin_exists(monkeypatch):
    statements = _patch_transaction(
        monkeypatch,
        [None, {"id": 42, "username": "admin"}],
    )

    result = UserRepository().ensure_admin("admin", "password-hash")

    assert result == {"id": 42, "username": "admin", "created": True}
    assert any("INSERT INTO users" in query for query, _ in statements)


def test_bootstrap_does_not_promote_existing_non_admin_username(monkeypatch):
    statements = _patch_transaction(
        monkeypatch,
        [None, None, {"id": 8, "username": "admin"}],
    )

    result = UserRepository().ensure_admin("admin", "password-hash")

    assert result == {
        "id": 8,
        "username": "admin",
        "created": False,
        "username_conflict": True,
    }
    assert any("INSERT INTO users" in query for query, _ in statements)
