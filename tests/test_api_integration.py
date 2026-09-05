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

    def list_resources(self, limit, offset, category_id=None, sort="id", order="desc"):
        rows = self._rows()[offset:offset + limit]
        return len(self.available), rows

    def search_resources(self, query, limit=100, category_id=None):
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

    def create(self, resource_id):
        share = {"id": self.next_id, "token": f"test-share-token-{self.next_id}"}
        self.next_id += 1
        self.tokens[share["token"]] = {"id": share["id"], "resource_id": resource_id}
        return share

    def list_for_resource(self, resource_id):
