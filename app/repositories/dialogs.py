from database_pool import connection, transaction


class DialogRepository:
    def replace_for_account(self, account_id, dialogs):
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
                        ON CONFLICT (account_id, telegram_chat_id) DO UPDATE SET
                            name=EXCLUDED.name,
                            username=EXCLUDED.username,
                            entity_type=EXCLUDED.entity_type,
                            is_group=EXCLUDED.is_group,
                            is_channel=EXCLUDED.is_channel,
                            updated_at=EXCLUDED.updated_at
                        """,
                        (
                            account_id,
                            dialog["id"],
                            dialog["name"],
                            dialog.get("username"),
                            dialog.get("entity_type", "unknown"),
                            dialog.get("is_group", False),
                            dialog.get("is_channel", False),
                        ),
                    )

    def list_for_account(self, account_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, telegram_chat_id AS id, name, username,
                           entity_type, is_group, is_channel, updated_at
                    FROM telegram_dialogs
                    WHERE account_id=%s
                    ORDER BY name NULLS LAST, telegram_chat_id
                    """,
                    (account_id,),
                )
                return cursor.fetchall()
