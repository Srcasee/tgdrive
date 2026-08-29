#!/usr/bin/env python3
"""Migrate an existing tgdrive SQLite database into PostgreSQL.

Usage:
    SQLITE_PATH=/data/files.db \
    DATABASE_URL=postgresql://tgdrive:tgdrive@localhost:5432/tgdrive \
    python scripts/migrate_sqlite_to_postgres.py

The target schema must already exist. The script is intentionally one-way and
preserves the existing integer epoch timestamps used by the application.
"""

import os
import sqlite3

import psycopg


SQLITE_PATH = os.getenv("SQLITE_PATH", "/data/files.db")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://tgdrive:tgdrive@localhost:5432/tgdrive",
)


TABLES = (
    "accounts",
    "categories",
    "telegram_sources",
    "files",
    "shares",
)


def migrate():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    pg_conn = psycopg.connect(DATABASE_URL)

    try:
        with pg_conn.cursor() as pg:
            for table in TABLES:
                rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
                if not rows:
                    continue

                columns = rows[0].keys()
                quoted_columns = ", ".join(columns)
                placeholders = ", ".join(["%s"] * len(columns))

                for row in rows:
                    values = [row[column] for column in columns]
                    if table == "accounts":
                        pg.execute(
                            f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders}) "
                            "ON CONFLICT (id) DO UPDATE SET "
                            "name=EXCLUDED.name, username=EXCLUDED.username, "
                            "session=EXCLUDED.session, enabled=EXCLUDED.enabled",
                            values,
                        )
                    elif table == "categories":
                        pg.execute(
                            f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders}) "
                            "ON CONFLICT (id) DO NOTHING",
                            values,
                        )
                    elif table == "telegram_sources":
                        pg.execute(
                            f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders}) "
                            "ON CONFLICT (id) DO UPDATE SET "
                            "account_id=EXCLUDED.account_id, name=EXCLUDED.name, "
                            "telegram_chat_id=EXCLUDED.telegram_chat_id, "
                            "last_message_id=EXCLUDED.last_message_id, "
                            "last_scan_time=EXCLUDED.last_scan_time, "
                            "scan_interval=EXCLUDED.scan_interval, "
                            "sync_mode=EXCLUDED.sync_mode, scan_status=EXCLUDED.scan_status, "
                            "enabled=EXCLUDED.enabled, updated_at=EXCLUDED.updated_at",
                            values,
                        )
                    elif table == "files":
                        pg.execute(
                            f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders}) "
                            "ON CONFLICT (id) DO UPDATE SET "
                            "filename=EXCLUDED.filename, size=EXCLUDED.size, "
                            "mime_type=EXCLUDED.mime_type, telegram_chat_id=EXCLUDED.telegram_chat_id, "
                            "message_id=EXCLUDED.message_id, topic_id=EXCLUDED.topic_id, "
                            "telegram_file_id=EXCLUDED.telegram_file_id, upload_time=EXCLUDED.upload_time, "
                            "category_id=EXCLUDED.category_id, created_at=EXCLUDED.created_at, "
                            "last_message_id=EXCLUDED.last_message_id, account_id=EXCLUDED.account_id, "
                            "status=EXCLUDED.status, is_available=EXCLUDED.is_available, "
                            "scan_status=EXCLUDED.scan_status",
                            values,
                        )
                    elif table == "shares":
                        pg.execute(
                            f"INSERT INTO {table} ({quoted_columns}) VALUES ({placeholders}) "
                            "ON CONFLICT (id) DO NOTHING",
                            values,
                        )

            # Keep BIGSERIAL sequences ahead of imported IDs.
            for table in TABLES:
                if table == "schema_migrations":
                    continue
                pg.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
                )

        pg_conn.commit()
        print("[DB] SQLite migration completed", flush=True)
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    migrate()
