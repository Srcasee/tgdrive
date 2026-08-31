from database_pool import connection, transaction


class DialogRepository:
    def ensure_table(self):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS telegram_dialogs (
                        id BIGSERIAL PRIMARY KEY,
                        account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                        telegram_chat_id BIGINT NOT NULL,
                        name TEXT,
                        username TEXT,
                        entity_type TEXT NOT NULL DEFAULT 'unknown',
                        is_group BOOLEAN NOT NULL DEFAULT FALSE,
                        is_channel BOOLEAN NOT NULL DEFAULT FALSE,
                        updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT,
                        UNIQUE (account_id, telegram_chat_id)
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_telegram_dialogs_account ON telegram_dialogs(account_id)")

    def replace_for_account(self, account_id, dialogs):
        self.ensure_table()
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM telegram_dialogs WHERE account_id=%s", (account_id,))
                for dialog in dialogs:
                    cursor.execute(
                        """
                        INSERT INTO telegram_dialogs
                            (account_id, telegram_chat_id, name, username, entity_type,
                             is_group, is_channel, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s,
                                EXTRACT(EPOCH FROM NOW())::BIGINT)
                        """,
                        (
                            account_id,
                            dialog["id"],
                            dialog.get("name"),
                            dialog.get("username"),
                            dialog.get("entity_type", "unknown"),
                            dialog.get("is_group", False),
                            dialog.get("is_channel", False),
                        ),
                    )

    def list_for_account(self, account_id):
        self.ensure_table()
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT telegram_chat_id AS id, name, username,
                           entity_type, is_group, is_channel, updated_at
                    FROM telegram_dialogs
                    WHERE account_id=%s
                    ORDER BY name NULLS LAST, telegram_chat_id
                    """,
                    (account_id,),
                )
                return cursor.fetchall()
