import os
import sqlite3
from pathlib import Path

import psycopg
import pytest

from database import init_database
from repositories.accounts import AccountRepository
from repositories.files import FileRepository
from repositories.sources import SourceRepository


DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL is required for PostgreSQL integration tests"
)


def _reset_schema(conn):
    with conn.cursor() as cur:
        cur.execute(
            "DROP TABLE IF EXISTS shares, files, telegram_sources, categories, accounts, schema_migrations CASCADE"
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
    source_id = sources.add(account_id, 10001, "Integration source")

    files.upsert_verified_message(
        filename="one.bin",
        size=123,
        mime_type="application/octet-stream",
        chat_id=10001,
        message_id=7,
        upload_time=1700000000,
        account_id=account_id,
    )
    files.upsert_verified_message(
        filename="one-renamed.bin",
        size=456,
        mime_type="application/octet-stream",
        chat_id=10001,
        message_id=7,
        upload_time=1700000001,
        account_id=account_id,
    )

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM accounts")
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) AS n FROM telegram_sources")
            assert cur.fetchone()[0] == 1
            cur.execute("SELECT COUNT(*) AS n FROM files")
            assert cur.fetchone()[0] == 1
            cur.execute(
                "SELECT filename, size, status, scan_status, is_available FROM files"
            )
            assert cur.fetchone() == (
                "one-renamed.bin",
                456,
                "active",
                "verified",
                True,
            )
            cur.execute(
                """
                SELECT COUNT(*)
                FROM files f
                LEFT JOIN accounts a ON a.id = f.account_id
                WHERE a.id IS NULL
                """
            )
            assert cur.fetchone()[0] == 0
            cur.execute(
                """
                SELECT COUNT(*)
                FROM telegram_sources s
                LEFT JOIN accounts a ON a.id = s.account_id
                WHERE a.id IS NULL
                """
            )
            assert cur.fetchone()[0] == 0

    # The repository transaction must roll back a failed statement.
    with pytest.raises(Exception):
        files.upsert_verified_message(
            filename=None,
            size=1,
            mime_type="application/octet-stream",
            chat_id=10001,
            message_id=8,
            upload_time=1700000002,
            account_id=account_id,
        )

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM files WHERE message_id=8")
            assert cur.fetchone()[0] == 0


def test_sqlite_to_postgres_migration(tmp_path: Path, monkeypatch):
    sqlite_path = tmp_path / "files.db"
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.executescript(
        """
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            session TEXT UNIQUE,
            enabled INTEGER DEFAULT 1
        );
        CREATE TABLE telegram_sources (
            id INTEGER PRIMARY KEY,
            name TEXT,
            telegram_chat_id INTEGER,
            last_message_id INTEGER DEFAULT 0,
            last_scan_time INTEGER,
            scan_interval INTEGER DEFAULT 600,
            sync_mode TEXT DEFAULT 'incremental',
            scan_status TEXT DEFAULT 'idle'
        );
        CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT UNIQUE);
        CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            filename TEXT,
            size INTEGER DEFAULT 0,
            mime_type TEXT,
            telegram_chat_id INTEGER,
            message_id INTEGER,
            topic_id INTEGER,
            telegram_file_id TEXT,
            upload_time INTEGER,
            category_id INTEGER,
            created_at INTEGER,
            last_message_id INTEGER DEFAULT 0,
            account_id INTEGER,
            status TEXT DEFAULT 'active',
            is_available INTEGER DEFAULT 1,
            scan_status TEXT DEFAULT 'idle'
        );
        CREATE TABLE shares (
            id INTEGER PRIMARY KEY,
            file_id INTEGER,
            token TEXT UNIQUE,
            created_at INTEGER
        );
        """
    )
    sqlite_conn.executemany(
        "INSERT INTO accounts VALUES (?, ?, ?, ?, ?)",
        [(10, "A", "user", "session-a", 1)],
    )
    sqlite_conn.executemany(
        "INSERT INTO telegram_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(20, "Source", 10001, 9, 1700000000, 600, "incremental", "success")],
    )
    sqlite_conn.executemany(
        "INSERT INTO categories VALUES (?, ?)", [(30, "docs")],
    )
    sqlite_conn.executemany(
        "INSERT INTO files VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(40, "a.pdf", 99, "application/pdf", 10001, 9, None, "tg-file", 1700000000, 30, 1700000000, 9, 10, "active", 1, "verified")],
    )
    sqlite_conn.executemany(
        "INSERT INTO shares VALUES (?, ?, ?, ?)", [(50, 40, "token-a", 1700000000)],
    )
    sqlite_conn.commit()
    sqlite_conn.close()

    with psycopg.connect(DATABASE_URL) as conn:
        _reset_schema(conn)
    init_database()

    monkeypatch.setenv("SQLITE_PATH", str(sqlite_path))
    from scripts.migrate_sqlite_to_postgres import migrate

    migrate()

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            for table, expected in (
                ("accounts", 1),
                ("telegram_sources", 1),
                ("categories", 1),
                ("files", 1),
                ("shares", 1),
            ):
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                assert cur.fetchone()[0] == expected

            cur.execute("SELECT id, filename, account_id FROM files WHERE id=40")
            assert cur.fetchone() == (40, "a.pdf", 10)
            cur.execute("SELECT id FROM shares WHERE id=50 AND file_id=40")
            assert cur.fetchone() == (50,)
            cur.execute(
                "SELECT last_value FROM files_id_seq"
            )
            assert cur.fetchone()[0] >= 40
