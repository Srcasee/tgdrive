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
        resource_dialogs = [dialog for dialog in dialogs if dialog.get("is_channel", False)]
        current_ids = {dialog["id"] for dialog in resource_dialogs}
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT telegram_chat_id FROM telegram_dialogs WHERE account_id=%s", (account_id,))
                previous_ids = {row["telegram_chat_id"] for row in cursor.fetchall()}
                removed_ids = sorted(previous_ids - current_ids)
                cursor.execute("DELETE FROM telegram_dialogs WHERE account_id=%s", (account_id,))
                for dialog in resource_dialogs:
                    cursor.execute(
                        """
                        INSERT INTO telegram_dialogs
                            (account_id, telegram_chat_id, name, username, entity_type,
                             is_group, is_channel, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, EXTRACT(EPOCH FROM NOW())::BIGINT)
                        """,
                        (account_id, dialog["id"], dialog.get("name"), dialog.get("username"),
                         dialog.get("entity_type", "channel"), False, True),
                    )
        return removed_ids

    def list_for_account(self, account_id):
        self.ensure_table()
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT d.telegram_chat_id AS id, d.name, d.username,
                           d.entity_type, d.is_group, d.is_channel, d.updated_at,
                           COALESCE(s.enabled, FALSE) AS source_enabled,
                           s.id AS source_id,
                           s.scan_status
                    FROM telegram_dialogs d
                    LEFT JOIN telegram_sources s
                      ON s.account_id=d.account_id AND s.telegram_chat_id=d.telegram_chat_id
                    WHERE d.account_id=%s AND d.is_channel=TRUE
                    ORDER BY d.name NULLS LAST, d.telegram_chat_id
                    """,
                    (account_id,),
                )
                return cursor.fetchall()

    def delete(self, account_id, telegram_chat_id):
        self.ensure_table()
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM telegram_dialogs WHERE account_id=%s AND telegram_chat_id=%s", (account_id, telegram_chat_id))
                return cursor.rowcount > 0

    def delete_all_for_account(self, account_id):
        self.ensure_table()
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM telegram_dialogs WHERE account_id=%s", (account_id,))
                return cursor.rowcount
