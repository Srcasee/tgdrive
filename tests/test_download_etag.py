from download.api import _resource_etag


def test_resource_etag_uses_only_valid_sha256_digests():
    digest = "a" * 64
    assert _resource_etag({"content_hash": digest}) == f'"sha256:{digest}"'
    assert _resource_etag({"content_hash": None}) is None
    assert _resource_etag({"content_hash": "not-a-digest"}) is None
    assert _resource_etag({"content_hash": "g" * 64}) is None
