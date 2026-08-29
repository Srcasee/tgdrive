#!/usr/bin/env python3
"""Migrate an existing tgdrive SQLite database into PostgreSQL.

Usage:
    SQLITE_PATH=/data/files.db \
    DATABASE_URL=postgresql://tgdrive:tgdrive@localhost:5432/tgdrive \
    python scripts/migrate_sqlite_to_postgres.py

The target schema must already exist. The migration is one-way and preserves
existing integer IDs and epoch timestamps used by the application.
"""

import os
import sqlite3

import psycopg


SQLITE_PATH = os.getenv("SQLITE_PATH", "/data/files.db")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://tgdrive:tgdrive@localhost:5432/tgdrive",
)


# Explicit target mappings are intentional: the PostgreSQL schema contains
# fields that older SQLite databases don't have. Missing values are filled by
# migration defaults instead of blindly copying SQLite column lists.
TABLE_COLUMNS = {
    "accounts": (
        "id",
        "name",
        "username",
        "session",
        "enabled",
    ),
    "categories": (
        "id",
        "name",
    ),
    "telegram_sources": (
        "id",
        "account_id",
        "name",
        "telegram_chat_id",
        "last_message_id",
        "last_scan_time",
        "scan_interval",
        "sync_mode",
        "scan_status",
        "enabled",
        "updated_at",
    ),
    "files": (
        "id",
        "filename",
        "size",
        "mime_type",
        "telegram_chat_id",
        "message_id",
        "topic_id",
        "telegram_file_id",
        "upload_time",
        "category_id",
        "created_at",
        "last_message_id",
        "account_id",
        "status",
        "is_available",
        "scan_status",
    ),
    "shares": (
        "id",
        "file_id",
        "token",
        "created_at",
    ),
}

BOOLEAN_COLUMNS = {
    "accounts": {"enabled"},
    "telegram_sources": {"enabled"},
    "files": {"is_available"},
}

DEFAULTS = {
    "accounts": {"enabled": True},
    "telegram_sources": {
        "account_id": None,
        "enabled": True,
        "updated_at": None,
    },
}

UPDATE_COLUMNS = {
    "accounts": "name=EXCLUDED.name, username=EXCLUDED.username, session=EXCLUDED.session, enabled=EXCLUDED.enabled",
    "categories": None,
    "telegram_sources": (
        "account_id=EXCLUDED.account_id, name=EXCLUDED.name, "
        "telegram_chat_id=EXCLUDED.telegram_chat_id, "
        "last_message_id=EXCLUDED.last_message_id, last_scan_time=EXCLUDED.last_scan_time, "
        "scan_interval=EXCLUDED.scan_interval, sync_mode=EXCLUDED.sync_mode, "
        "scan_status=EXCLUDED.scan_status, enabled=EXCLUDED.enabled, "
        "updated_at=EXCLUDED.updated_at"
    ),
    "files": (
        "filename=EXCLUDED.filename, size=EXCLUDED.size, mime_type=EXCLUDED.mime_type, "
        "telegram_chat_id=EXCLUDED.telegram_chat_id, message_id=EXCLUDED.message_id, "
        "topic_id=EXCLUDED.topic_id, telegram_file_id=EXCLUDED.telegram_file_id, "
        "upload_time=EXCLUDED.upload_time, category_id=EXCLUDED.category_id, "
        "created_at=EXCLUDED.created_at, last_message_id=EXCLUDED.last_message_id, "
        "account_id=EXCLUDED.account_id, status=EXCLUDED.status, "
        "is_available=EXCLUDED.is_available, scan_status=EXCLUDED.scan_status"
    ),
    "shares": None,
}


def _sqlite_columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _value(table, column, row, sqlite_columns):
    if column in sqlite_columns:
        value = row[column]
    else:
        value = DEFAULTS.get(table, {}).get(column)

    if column in BOOLEAN_COLUMNS.get(table, set()) and value is not None:
        return bool(value)
    return value


def migrate():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg.connect(DATABASE_URL)

    try:
        with pg_conn.transaction():
            with pg_conn.cursor() as pg:
                for table, columns in TABLE_COLUMNS.items():
                    sqlite_columns = _sqlite_columns(sqlite_conn, table)
                    select_columns = [column for column in columns if column in sqlite_columns]
                    if "id" not in select_columns:
                        raise RuntimeError(f"SQLite table {table!r} has no id column")

                    rows = sqlite_conn.execute(
                        f"SELECT {', '.join(select_columns)} FROM {table}"
                    ).fetchall()
                    if not rows:
                        continue

                    quoted_columns = ", ".join(columns)
                    placeholders = ", ".join(["%s"] * len(columns))
                    update = UPDATE_COLUMNS[table]
                    conflict = "DO NOTHING" if update is None else f"DO UPDATE SET {update}"
                    query = (
                        f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders}) "
                        f"ON CONFLICT (id) {conflict}"
                    )

                    for row in rows:
                        values = [
                            _value(table, column, row, sqlite_columns)
                            for column in columns
                        ]
                        pg.execute(query, values)

                # Keep BIGSERIAL sequences ahead of imported IDs.
                for table in TABLE_COLUMNS:
                    pg.execute(
                        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
                    )

        print("[DB] SQLite migration completed", flush=True)
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    migrate()
