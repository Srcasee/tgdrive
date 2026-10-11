from download.api import _resource_etag


def test_resource_etag_prefers_valid_sha256_digest():
    digest = "a" * 64
    assert _resource_etag({"id": 7, "size": 123, "content_hash": digest}) == f'"sha256:{digest}"'


def test_resource_etag_uses_resource_identity_without_hashing():
    assert _resource_etag({"id": 7, "size": 123, "content_hash": None}) == '"resource:7:123"'
    assert _resource_etag({"id": 7, "size": 123, "content_hash": "not-a-digest"}) == '"resource:7:123"'
    assert _resource_etag({"id": 7, "size": 123, "content_hash": "g" * 64}) == '"resource:7:123"'


def test_resource_etag_is_unavailable_without_stable_identity():
    assert _resource_etag({"content_hash": None}) is None
    assert _resource_etag({"id": 7, "content_hash": None}) is None
