from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from config import settings


@contextmanager
def get_connection():
    conn = psycopg.connect(settings.DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT
                )
                """
            )
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
            applied = {row["version"] for row in cursor.fetchall()}

            if 1 not in applied:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS accounts (
                        id BIGSERIAL PRIMARY KEY,
                        name TEXT,
                        username TEXT,
                        session TEXT UNIQUE,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE
                    );

                    CREATE TABLE IF NOT EXISTS telegram_sources (
                        id BIGSERIAL PRIMARY KEY,
                        account_id BIGINT REFERENCES accounts(id) ON DELETE CASCADE,
                        name TEXT,
                        telegram_chat_id BIGINT,
                        last_message_id BIGINT NOT NULL DEFAULT 0,
                        last_scan_time BIGINT,
                        scan_interval INTEGER NOT NULL DEFAULT 600,
                        sync_mode TEXT NOT NULL DEFAULT 'incremental',
                        scan_status TEXT NOT NULL DEFAULT 'idle',
                        enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        updated_at BIGINT
                    );

                    CREATE TABLE IF NOT EXISTS categories (
                        id BIGSERIAL PRIMARY KEY,
                        name TEXT UNIQUE
                    );

                    CREATE TABLE IF NOT EXISTS files (
                        id BIGSERIAL PRIMARY KEY,
                        filename TEXT NOT NULL,
                        size BIGINT NOT NULL DEFAULT 0,
                        mime_type TEXT,
                        telegram_chat_id BIGINT NOT NULL,
                        message_id BIGINT NOT NULL,
                        topic_id BIGINT,
                        telegram_file_id TEXT,
                        upload_time BIGINT,
                        category_id BIGINT REFERENCES categories(id) ON DELETE SET NULL,
                        created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
                        last_message_id BIGINT NOT NULL DEFAULT 0,
                        account_id BIGINT REFERENCES accounts(id) ON DELETE CASCADE,
                        status TEXT NOT NULL DEFAULT 'active',
                        is_available BOOLEAN NOT NULL DEFAULT TRUE,
                        scan_status TEXT NOT NULL DEFAULT 'idle'
                    );

                    CREATE TABLE IF NOT EXISTS shares (
                        id BIGSERIAL PRIMARY KEY,
                        file_id BIGINT REFERENCES files(id) ON DELETE CASCADE,
                        token TEXT UNIQUE,
                        created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT
                    );

                    CREATE UNIQUE INDEX IF NOT EXISTS idx_file_unique
                        ON files(account_id, telegram_chat_id, message_id);
                    CREATE INDEX IF NOT EXISTS idx_files_account ON files(account_id);
                    CREATE INDEX IF NOT EXISTS idx_files_available ON files(is_available);
                    CREATE INDEX IF NOT EXISTS idx_sources_account ON telegram_sources(account_id);
                    CREATE INDEX IF NOT EXISTS idx_sources_chat ON telegram_sources(telegram_chat_id);
                    CREATE INDEX IF NOT EXISTS idx_files_filename ON files(filename);
                    """
                )
                cursor.execute("INSERT INTO schema_migrations(version) VALUES (1)")

            if 2 not in applied:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGSERIAL PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
                        enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT
                    );
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_source_unique
                        ON telegram_sources(account_id, telegram_chat_id);
                    """
                )
                cursor.execute("INSERT INTO schema_migrations(version) VALUES (2)")

            conn.commit()
            print("[DB] PostgreSQL database initialized", flush=True)
