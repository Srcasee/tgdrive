import os

os.environ["AUTH_SECRET"] = "integration-secret"
os.environ["AUTH_TOKEN_TTL"] = "3600"
os.environ["AUTH_COOKIE_SECURE"] = "false"

from fastapi.testclient import TestClient

from auth.security import hash_password
from catalog.service import CatalogService
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

    def record_login(self, user_id, login_at, login_ip):
        user = next((u for u in self.users.values() if u["id"] == user_id), None)
        if user:
            user["last_login_at"] = login_at
            user["last_login_ip"] = login_ip


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

    def assign_resource(self, resource_id, category_id):
        return {"resource_id": resource_id, "category_id": category_id}


class FakeResources:
    def __init__(self):
        self.available = {
            1: {
                "id": 1,
                "filename": "video.mp4",
                "size": 100,
                "mime_type": "video/mp4",
                "status": "active",
                "is_available": True,
                "shares": [],
            },
        }

    def _rows(self):
        return list(self.available.values())

    def list_resources(self, limit, offset, category_id=None, sort="id", order="desc", account_id=None, chat_id=None, topic_id=None):
        rows = self._rows()[offset:offset + limit]
        return len(self.available), rows

    def search_resources(self, query, limit=100, category_id=None, account_id=None, chat_id=None, topic_id=None):
        return [x for x in self._rows() if query.lower() in x["filename"].lower()][:limit]

    def get_resource(self, resource_id):
        return self.available.get(resource_id)

    def set_categories(self, resource_id, category_ids):
        resource = self.available.get(resource_id)
        if not resource:
            return None
        resource["category_ids"] = list(category_ids)
        return resource

    def get(self, resource_id):
        return self.available.get(resource_id)

    def get_download_info(self, resource_id):
        return self.available.get(resource_id)

    def get_stream_info(self, resource_id):
        return self.available.get(resource_id)

    def get_head_info(self, resource_id):
        return self.available.get(resource_id)


class FakeShares:
    def __init__(self):
        self.tokens = {}
        self.next_id = 1

    def create(self, resource_id, expires_at=None):
        existing = next((item for item in self.tokens.values() if item["resource_id"] == resource_id), None)
        for token, item in list(self.tokens.items()):
            if item["resource_id"] == resource_id:
                del self.tokens[token]
        share = {"id": existing["id"] if existing else self.next_id, "token": f"test-share-token-{self.next_id}", "created_at": 100, "expires_at": expires_at}
        self.next_id += 1
        self.tokens[share["token"]] = {"id": share["id"], "resource_id": resource_id, "expires_at": expires_at}
        return share

    def list_for_resource(self, resource_id):
        return [
            {"id": item["id"], "resource_id": item["resource_id"], "token": token, "created_at": 0}
            for token, item in self.tokens.items()
            if item["resource_id"] == resource_id
        ]

    def delete(self, share_id):
        for token, item in list(self.tokens.items()):
            if item["id"] == share_id:
                del self.tokens[token]
                return True
        return False

    def get_resource_id(self, token):
        item = self.tokens.get(token)
        if not item:
            return None
        if item.get("expires_at") is not None and item["expires_at"] <= 200:
            return None
        return item["resource_id"]


async def _noop_startup():
    return None


async def _noop_shutdown():
    return None


def make_client(monkeypatch):
    users = FakeUsers()
    categories = FakeCategories()
    resources = FakeResources()
    shares = FakeShares()
    monkeypatch.setattr("auth.api.user_repository", users)
    monkeypatch.setattr("auth.dependencies.user_repository", users)
    monkeypatch.setattr("admin.api.category_repository", categories)
    monkeypatch.setattr("admin.api.share_repository", shares)
    monkeypatch.setattr("catalog.api.service", CatalogService(resources))
    monkeypatch.setattr("download.api.resource_repository", resources)
    monkeypatch.setattr("share.api.share_repository", shares)

    app = create_app()
    lifecycle = ApplicationLifecycle()
    lifecycle.startup = _noop_startup
    lifecycle.shutdown = _noop_shutdown
    app.state.lifecycle = lifecycle

    return TestClient(app), resources, shares


def test_legacy_web_entry_points_redirect_to_admin_frontend(monkeypatch):
    client, _, _ = make_client(monkeypatch)

    for path in ("/", "/web"):
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/admin/"


def test_auth_and_authorization(monkeypatch):
    client, _, _ = make_client(monkeypatch)
    assert client.get("/auth/me").status_code == 401

    response = client.post("/auth/login", json={"username": "user", "password": "user-pass"})
    assert response.status_code == 200
    assert response.json()["role"] == "user"
    assert client.get("/auth/me").status_code == 200
    assert client.get("/api/admin/categories").status_code == 403

    response = client.post("/auth/login", json={"username": "admin", "password": "admin-pass"})
    assert response.status_code == 200
    assert client.get("/api/admin/categories").status_code == 200


def test_auth_me_refreshes_session_cookie(monkeypatch):
    client, _, _ = make_client(monkeypatch)
    login = client.post("/auth/login", json={"username": "admin", "password": "admin-pass"})
    assert login.status_code == 200

    refreshed = client.get("/auth/me")
    assert refreshed.status_code == 200
    assert "tgdrive_session=" in refreshed.headers["set-cookie"]
    assert "Max-Age=3600" in refreshed.headers["set-cookie"]
    assert "HttpOnly" in refreshed.headers["set-cookie"]
    assert "Path=/" in refreshed.headers["set-cookie"]


def test_manual_category_mutations_are_disabled(monkeypatch):
    client, _, _ = make_client(monkeypatch)
    client.post("/auth/login", json={"username": "admin", "password": "admin-pass"})

    # Previous CRUD expectations are intentionally retained as comments because manual
    # category management is disabled.
    # created = client.post("/api/admin/categories", json={"name": "Movies"})
    # assert created.status_code == 200
    # category_id = created.json()["id"]
    # assert client.put(f"/api/admin/categories/{category_id}", json={"name": "Films"}).status_code == 200
    # assert client.delete(f"/api/admin/categories/{category_id}").status_code == 200

    assert client.get("/api/admin/categories").status_code == 200
    assert client.post("/api/admin/categories", json={"name": "Movies"}).status_code == 405
    assert client.put("/api/admin/categories/1", json={"name": "Films"}).status_code == 404
    assert client.delete("/api/admin/categories/1").status_code == 404
    assert client.put("/api/admin/resources/1/categories", json={"category_ids": [1]}).status_code == 404


def test_protected_catalog_and_delivery_apis(monkeypatch):
    client, _, _ = make_client(monkeypatch)
    assert client.get("/catalog").status_code == 401
    assert client.get("/catalog/search?q=video").status_code == 401
    assert client.get("/resources/1/download").status_code == 401
    assert client.get("/resources/1/stream").status_code == 401

    client.post("/auth/login", json={"username": "user", "password": "user-pass"})
    assert client.get("/catalog").status_code == 200
    assert client.get("/catalog/search?q=video").status_code == 200
    assert client.get("/resources/999/download").status_code == 404
    assert client.get("/resources/999/stream").status_code == 404


def test_unavailable_resource_is_not_downloadable_or_streamable(monkeypatch):
    client, resources, _ = make_client(monkeypatch)
    client.post("/auth/login", json={"username": "user", "password": "user-pass"})
    resources.available[1]["is_available"] = False
    assert client.get("/resources/1/download").status_code == 404
    assert client.get("/resources/1/stream").status_code == 404


def test_share_link_creation_and_admin_revoke(monkeypatch):
    client, resources, shares = make_client(monkeypatch)
    assert client.post("/resources/1/share").status_code == 401

    client.post("/auth/login", json={"username": "user", "password": "user-pass"})
    response = client.post("/resources/1/share")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == 1
    assert payload["url"] == "http://testserver/share/test-share-token-1"
    assert payload["resource_id"] == 1
    assert payload["expires_at"] is None

    token = "test-share-token-1"
    assert client.get("/share/unknown-token").status_code == 404
    assert shares.get_resource_id(token) == 1
    landing = client.get(f"/share/{token}")
    assert landing.status_code == 200
    assert "video.mp4" in landing.text
    assert "100 字节" in landing.text
    assert f"/share/{token}/download" in landing.text
    assert client.get("/share/unknown-token/download").status_code == 404
    second = client.post("/resources/1/share")
    assert second.status_code == 200
    assert second.json()["id"] == payload["id"]
    assert second.json()["url"] != payload["url"]
    assert shares.get_resource_id(token) is None
    token = second.json()["url"].rsplit("/", 1)[-1]
    assert shares.get_resource_id(token) == 1

    catalog = client.get("/catalog").json()
    assert catalog["data"]["items"][0]["shares"] == []

    assert client.delete("/api/admin/shares/1").status_code == 403

    client.post("/auth/login", json={"username": "admin", "password": "admin-pass"})
    assert client.delete("/api/admin/shares/1").status_code == 200
    assert client.delete("/api/admin/shares/1").status_code == 404
    assert shares.get_resource_id(token) is None


def test_share_expiration_validation_and_public_expiry(monkeypatch):
    client, _, shares = make_client(monkeypatch)
    client.post("/auth/login", json={"username": "user", "password": "user-pass"})

    assert client.post(
        "/resources/1/share",
        json={"expires_at": "2000-01-01T00:00:00Z"},
    ).status_code == 400
    assert client.post(
        "/resources/1/share",
        json={"expires_at": "2099-01-01T00:00:00"},
    ).status_code == 400

    response = client.post(
        "/resources/1/share",
        json={"expires_at": "2099-01-01T00:00:00Z"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["expires_at"] is not None
    token = payload["url"].rsplit("/", 1)[-1]
    assert shares.get_resource_id(token) == 1

    shares.tokens[token]["expires_at"] = 100
    assert client.get(f"/share/{token}").status_code == 404
    assert client.get(f"/share/{token}/download").status_code == 404


def test_download_range_returns_only_requested_bytes(monkeypatch):
    client, resources, _ = make_client(monkeypatch)

    class FakeSelector:
        async def stream_resource(self, resource_id, offset=0, on_source=None, expected_hash=None, expected_bytes=None):
            if on_source:
                on_source({"id": 1})
            yield bytes((i % 256 for i in range(offset, min(offset + 10, 100))))

    class FakeDownloadService:
        def start(self, resource_id, created_by=None):
            return None

        def stream(self, chunks, record_id, expected_bytes, on_digest=None, hash_content=False):
            return chunks

    monkeypatch.setattr("download.api.source_selector", FakeSelector())
    monkeypatch.setattr("download.api.download_service", FakeDownloadService())
    monkeypatch.setattr("download.api.resource_repository", resources)

    client.post("/auth/login", json={"username": "user", "password": "user-pass"})
    response = client.get("/resources/1/download", headers={"Range": "bytes=10-19"})

    assert response.status_code == 206
    assert response.headers["content-range"] == "bytes 10-19/100"
    assert response.headers["content-length"] == "10"
    assert response.content == bytes(range(10, 20))


def test_download_unsatisfiable_range_returns_416(monkeypatch):
    client, _, _ = make_client(monkeypatch)
    client.post("/auth/login", json={"username": "user", "password": "user-pass"})

    response = client.get("/resources/1/download", headers={"Range": "bytes=100-110"})

    assert response.status_code == 416
    assert response.headers["content-range"] == "bytes */100"


def test_download_records_are_paginated_and_bulk_deletable(monkeypatch):
    client, _, _ = make_client(monkeypatch)

    class FakeDownloads:
        def __init__(self):
            self.deleted = []

        def list_by_status(self, status, page=1, size=50):
            return {
                "items": [{
                    "id": 7,
                    "filename": "video.mp4",
                    "status": status,
                    "started_at": 1700000000,
                    "completed_at": 1700000010 if status != "active" else None,
                }],
                "total": 1,
                "page": page,
                "size": size,
            }

        def bulk_delete(self, ids):
            self.deleted.extend(ids)
            return len(ids)

    downloads = FakeDownloads()
    monkeypatch.setattr("admin.api.download_service", downloads)

    assert client.get("/api/admin/downloads").status_code == 401
    client.post("/auth/login", json={"username": "admin", "password": "admin-pass"})

    response = client.get("/api/admin/downloads?status=failed&page=2&size=50")
    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "failed"
    assert response.json()["page"] == 2
    assert response.json()["size"] == 50
    assert client.get("/api/admin/downloads?status=unknown").status_code == 400
    assert client.post("/api/admin/downloads/bulk-delete", json={"ids": [7, 7, 8]}).json() == {
        "status": "ok",
        "deleted": 2,
    }
    assert sorted(downloads.deleted) == [7, 8]
    assert client.delete("/api/admin/downloads/7").status_code == 404
