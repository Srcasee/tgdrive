import os

os.environ["AUTH_SECRET"] = "integration-secret"
os.environ["AUTH_TOKEN_TTL"] = "3600"
os.environ["AUTH_COOKIE_SECURE"] = "false"

from fastapi.testclient import TestClient

from auth.security import hash_password
from core.app import create_app
from core.lifecycle import ApplicationLifecycle


class FakeUsers:
    def __init__(self):
        self.users = {
            "user": {"id": 1, "username": "user", "password_hash": hash_password("user-pass"), "role": "user", "enabled": True},
            "admin": {"id": 2, "username": "admin", "password_hash": hash_password("admin-pass"), "role": "admin", "enabled": True},
        }

    def get_by_username(self, username):
        return self.users.get(username)

    def get_by_id(self, user_id):
        return next((u for u in self.users.values() if u["id"] == user_id), None)


class FakeCategories:
    def __init__(self):
        self.items = []
        self.next_id = 1

    def list_all(self):
        return list(self.items)

    def get(self, category_id):
        return next((x for x in self.items if x["id"] == category_id), None)

    def create(self, name):
        item = {"id": self.next_id, "name": name.strip()}
        self.next_id += 1
        self.items.append(item)
        return item

    def update(self, category_id, name):
        item = self.get(category_id)
        if item:
            item["name"] = name.strip()
        return item

    def delete(self, category_id):
        item = self.get(category_id)
        if item:
            self.items.remove(item)
        return item

    def assign_file(self, file_id, category_id):
        return {"id": file_id, "category_id": category_id}


class FakeFiles:
    def __init__(self):
        self.available = {
            1: {"id": 1, "filename": "video.mp4", "size": 100, "mime_type": "video/mp4", "is_available": True}
        }

    def list_available(self, limit, offset):
        rows = list(self.available.values())[offset:offset + limit]
        return len(self.available), rows

    def search(self, query, limit=100):
        return [x for x in self.available.values() if query.lower() in x["filename"].lower()]

    def get_download_info(self, file_id):
        return self.available.get(file_id)

    def get_stream_info(self, file_id):
        return self.available.get(file_id)

    def get_head_info(self, file_id):
        return self.available.get(file_id)


async def _noop_startup():
    return None


async def _noop_shutdown():
    return None


def make_client(monkeypatch):
    users = FakeUsers()
    categories = FakeCategories()
    files = FakeFiles()
    monkeypatch.setattr("auth.api.user_repository", users)
    monkeypatch.setattr("auth.dependencies.user_repository", users)
    monkeypatch.setattr("admin.api.category_repository", categories)
    monkeypatch.setattr("files.api.file_repository", files)

    app = create_app()
    lifecycle = ApplicationLifecycle()
    lifecycle.startup = _noop_startup
    lifecycle.shutdown = _noop_shutdown
    app.state.lifecycle = lifecycle

    return TestClient(app), files


def test_auth_and_authorization(monkeypatch):
    client, _ = make_client(monkeypatch)
    assert client.get("/auth/me").status_code == 401

    response = client.post("/auth/login", json={"username": "user", "password": "user-pass"})
    assert response.status_code == 200
    assert response.json()["role"] == "user"
    assert client.get("/auth/me").status_code == 200
    assert client.get("/api/admin/categories").status_code == 403

    response = client.post("/auth/login", json={"username": "admin", "password": "admin-pass"})
    assert response.status_code == 200
    assert client.get("/api/admin/categories").status_code == 200


def test_category_admin_crud(monkeypatch):
    client, _ = make_client(monkeypatch)
    client.post("/auth/login", json={"username": "admin", "password": "admin-pass"})

    created = client.post("/api/admin/categories", json={"name": "Movies"})
    assert created.status_code == 200
    category_id = created.json()["id"]
    assert client.get("/api/admin/categories").json()[0]["name"] == "Movies"
    assert client.put(f"/api/admin/categories/{category_id}", json={"name": "Films"}).status_code == 200
    assert client.delete(f"/api/admin/categories/{category_id}").status_code == 200


def test_protected_file_apis(monkeypatch):
    client, _ = make_client(monkeypatch)
    assert client.get("/files").status_code == 401
    assert client.get("/files/search?q=video").status_code == 401
    assert client.get("/files/1/download").status_code == 401
    assert client.get("/files/1/stream").status_code == 401

    client.post("/auth/login", json={"username": "user", "password": "user-pass"})
    assert client.get("/files").status_code == 200
    assert client.get("/files/search?q=video").status_code == 200
    assert client.get("/files/999/download").status_code == 404
    assert client.get("/files/999/stream").status_code == 404


def test_unavailable_file_is_not_downloadable_or_streamable(monkeypatch):
    client, files = make_client(monkeypatch)
    client.post("/auth/login", json={"username": "user", "password": "user-pass"})
    files.available[1]["is_available"] = False
    assert client.get("/files/1/download").status_code == 404
    assert client.get("/files/1/stream").status_code == 404
