import os

import psycopg
import pytest

from database import init_database
from database_pool import close_pool, open_pool
from repositories.accounts import AccountRepository
from repositories.files import FileRepository
from repositories.sources import SourceRepository


DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL is required for PostgreSQL integration tests"
)


@pytest.fixture(scope="module", autouse=True)
def postgres_pool():
    """Keep the shared PostgreSQL pool alive for the whole integration module."""
    open_pool()
    try:
        yield
    finally:
        close_pool()


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            "DROP TABLE IF EXISTS shares, files, resources, telegram_sources, categories, accounts, schema_migrations CASCADE"
        )
    conn.commit()


def test_schema_and_repositories_are_transactional():
    with psycopg.connect(DATABASE_URL) as conn:
        _reset_schema(conn)

    init_database()
    accounts = AccountRepository()
    files = FileRepository()
    sources = SourceRepository()

    account_id = accounts.upsert_session("integration-session", "Integration")
    sources.add(account_id, 10001, "Integration source")

    resource_id = 123
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO resources(identity_key, filename, size, mime_type) VALUES(%s,%s,%s,%s) RETURNING id",
                ("integration-resource", "one.bin", 123, "application/octet-stream"),
            )
            resource_id = cur.fetchone()[0]
        conn.commit()

    files.upsert_verified_message(
        filename="one.bin", size=123, mime_type="application/octet-stream",
        chat_id=10001, message_id=7, upload_time=1700000000,
        account_id=account_id, resource_id=resource_id,
    )
    files.upsert_verified_message(
        filename="one-renamed.bin", size=456, mime_type="application/octet-stream",
        chat_id=10001, message_id=7, upload_time=1700000001,
        account_id=account_id, resource_id=resource_id,
    )

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM accounts")
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) FROM telegram_sources")
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) FROM files")
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT filename, size, resource_id, status, scan_status, is_available FROM files")
            assert cur.fetchone() == ("one-renamed.bin", 456, resource_id, "active", "verified", True)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM accounts WHERE id=%s", (account_id,))
        conn.commit()

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT resource_id, account_id, filename FROM files")
            assert cur.fetchone() == (resource_id, None, "one-renamed.bin")
            cur.execute("SELECT COUNT(*) FROM resources WHERE id=%s", (resource_id,))
            assert cur.fetchone()[0] == 1
            cur.execute(
                "SELECT COUNT(*) FROM telegram_sources s LEFT JOIN accounts a ON a.id=s.account_id WHERE a.id IS NULL"
            )
            assert cur.fetchone()[0] == 0

    with pytest.raises(ValueError, match="filename is required"):
        files.upsert_verified_message(
            filename=None, size=1, mime_type="application/octet-stream",
            chat_id=10001, message_id=8, upload_time=1700000002,
            account_id=account_id, resource_id=resource_id,
        )

    with pytest.raises(ValueError, match="filename is required"):
        files.upsert_verified_message(
            filename="", size=1, mime_type="application/octet-stream",
            chat_id=10001, message_id=9, upload_time=1700000003,
            account_id=account_id, resource_id=resource_id,
        )

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM files WHERE message_id IN (8, 9)")
            assert cur.fetchone()[0] == 0
