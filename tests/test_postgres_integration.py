import os

import psycopg
import pytest

from database import init_database
from database_pool import close_pool, open_pool
from repositories.accounts import AccountRepository
from repositories.files import FileRepository
from repositories.resources import ResourceRepository
from repositories.sources import SourceRepository
from catalog.repository import CatalogRepository


DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL is required for PostgreSQL integration tests"
)


@pytest.fixture(scope="module", autouse=True)
def postgres_pool():
    open_pool()
    try:
        yield
    finally:
        close_pool()


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS shares, resource_categories, files, resources, telegram_sources, categories, accounts, schema_migrations CASCADE")
    conn.commit()


def test_schema_and_repositories_are_transactional():
    with psycopg.connect(DATABASE_URL) as conn:
        _reset_schema(conn)

    init_database()
    accounts = AccountRepository()
    files = FileRepository()
    resources = ResourceRepository()
    sources = SourceRepository()
    catalog = CatalogRepository()

    account_id = accounts.upsert_session("integration-session", "Integration")
    sources.add(account_id, 10001, "Integration source")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO resources(identity_key, content_hash, filename, size, mime_type) VALUES(%s,%s,%s,%s,%s) RETURNING id",
                ("sha256:" + "a" * 64, "a" * 64, "one.bin", 123, "application/octet-stream"),
            )
            resource_id = cur.fetchone()[0]
            cur.execute("INSERT INTO categories(name) VALUES('Docs') RETURNING id")
            category_id = cur.fetchone()[0]
        conn.commit()

    files.upsert_indexed_message(
        filename="one.bin", size=123, mime_type="application/octet-stream",
        chat_id=10001, message_id=7, upload_time=1700000000,
        account_id=account_id, resource_id=resource_id, content_hash="a" * 64,
    )
    files.upsert_indexed_message(
        filename="one-renamed.bin", size=456, mime_type="application/octet-stream",
        chat_id=10001, message_id=7, upload_time=1700000001,
        account_id=account_id, resource_id=resource_id, content_hash="a" * 64,
    )

    assigned = catalog.set_categories(resource_id, [category_id])
    assert assigned["category_ids"] == [category_id]
    assert catalog.get_resource(resource_id)["source_count"] == 1

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM accounts")
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) FROM telegram_sources")
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) FROM files")
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT filename, size, resource_id, content_hash, status, scan_status, is_available FROM files")
            assert cur.fetchone() == ("one-renamed.bin", 456, resource_id, "a" * 64, "active", "indexed", True)

    provisional_id = resources.get_or_create(
        filename="same-metadata.bin",
        size=10,
        mime_type="application/octet-stream",
    )
    files.upsert_indexed_message(
        filename="same-metadata.bin", size=10, mime_type="application/octet-stream",
        chat_id=10001, message_id=8, upload_time=1700000002,
        account_id=account_id, resource_id=provisional_id, content_hash=None,
    )
    verified_id = resources.verify_file(2, "b" * 64)
    assert verified_id != provisional_id
    assert resources.get(provisional_id)["content_hash"] is None
    assert resources.get(verified_id)["content_hash"] == "b" * 64

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT resource_id, content_hash FROM files WHERE id=2")
            assert cur.fetchone() == (verified_id, "b" * 64)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM accounts WHERE id=%s", (account_id,))
        conn.commit()

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT resource_id, account_id, filename FROM files WHERE id=1")
            assert cur.fetchone() == (resource_id, None, "one-renamed.bin")
            cur.execute("SELECT COUNT(*) FROM resources WHERE id=%s", (resource_id,))
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) FROM resource_categories WHERE resource_id=%s", (resource_id,))
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) FROM telegram_sources s LEFT JOIN accounts a ON a.id=s.account_id WHERE a.id IS NULL")
            assert cur.fetchone()[0] == 0

    files.upsert_indexed_message(
        filename="no-hash.bin", size=1, mime_type="application/octet-stream",
        chat_id=10001, message_id=9, upload_time=1700000003,
        account_id=None, resource_id=resource_id, content_hash=None,
    )
