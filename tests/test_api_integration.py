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
