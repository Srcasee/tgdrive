from database_pool import connection, transaction


class SourceRepository:
    def list_enabled_for_account(self, account_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, telegram_chat_id, name, scan_interval,
                           last_message_id, last_scan_time, sync_mode, scan_status
                    FROM telegram_sources
                    WHERE account_id=%s AND enabled=TRUE
                    """,
                    (account_id,),
                )
                return cursor.fetchall()

    def list_all_enabled(self):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT s.id, s.account_id, s.telegram_chat_id, s.name,
                           s.scan_interval, s.last_message_id, s.last_scan_time,
                           s.sync_mode, s.scan_status, s.enabled,
                           a.name AS account_name
                    FROM telegram_sources s
                    LEFT JOIN accounts a ON a.id=s.account_id
                    WHERE s.enabled=TRUE
                    ORDER BY a.name NULLS LAST, s.name NULLS LAST, s.id
                    """
                )
                return cursor.fetchall()

    def get(self, source_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, account_id, telegram_chat_id, name, enabled FROM telegram_sources WHERE id=%s",
                    (source_id,))
                return cursor.fetchone()

    def get_for_chat(self, account_id, telegram_chat_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, account_id, telegram_chat_id, name, enabled FROM telegram_sources WHERE account_id=%s AND telegram_chat_id=%s",
                    (account_id, telegram_chat_id))
                return cursor.fetchone()

    def set_enabled(self, source_id, enabled):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE telegram_sources
                    SET enabled=%s, scan_status='idle', updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT
                    WHERE id=%s
                    RETURNING id, account_id, telegram_chat_id, name, enabled
                    """,
                    (enabled, source_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("source not found")
                return row

    def disable_all_for_account(self, account_id):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE telegram_sources
                    SET enabled=FALSE, scan_status='idle', updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT
                    WHERE account_id=%s AND enabled=TRUE
                    RETURNING id, telegram_chat_id
                    """,
                    (account_id,),
                )
                return cursor.fetchall()

    def delete(self, source_id):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT account_id, telegram_chat_id FROM telegram_sources WHERE id=%s", (source_id,))
                row = cursor.fetchone()
                if row is None:
                    return None
                cursor.execute("DELETE FROM telegram_sources WHERE id=%s", (source_id,))
                return row

    def ensure_enabled(self, account_id, chat_id, name):
        existing = self.get_for_chat(account_id, chat_id)
        if existing is not None:
            return self.set_enabled(existing["id"], True)
        return {"id": self.add(account_id, chat_id, name), "account_id": account_id, "telegram_chat_id": chat_id, "name": name, "enabled": True}

    def remove_missing_dialogs(self, account_id, dialog_ids):
        """Disable sources whose chat is no longer present in Telegram dialogs."""
        with transaction() as conn:
            with conn.cursor() as cursor:
                if dialog_ids:
                    cursor.execute(
                        """
                        UPDATE telegram_sources
                        SET enabled=FALSE, scan_status='idle', updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT
                        WHERE account_id=%s AND enabled=TRUE
                          AND telegram_chat_id <> ALL(%s)
                        RETURNING telegram_chat_id
                        """,
                        (account_id, dialog_ids),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE telegram_sources
                        SET enabled=FALSE, scan_status='idle', updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT
                        WHERE account_id=%s AND enabled=TRUE
                        RETURNING telegram_chat_id
                        """,
                        (account_id,),
                    )
                return [row["telegram_chat_id"] for row in cursor.fetchall()]

    def mark_scanning(self, source_id):
        self._update_status(source_id, "scanning")

    def mark_success(self, source_id, last_message_id):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE telegram_sources
                    SET last_message_id=%s, last_scan_time=EXTRACT(EPOCH FROM NOW())::BIGINT,
                        scan_status='success', updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT
                    WHERE id=%s
                    """,
                    (last_message_id, source_id),
                )

    def mark_failed(self, source_id):
        self._update_status(source_id, "failed")

    def add(self, account_id, chat_id, name):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO telegram_sources
                    (account_id, telegram_chat_id, name, enabled)
                    VALUES (%s, %s, %s, TRUE)
                    RETURNING id
                    """,
                    (account_id, chat_id, name),
                )
                return cursor.fetchone()["id"]

    @staticmethod
    def _update_status(source_id, status):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE telegram_sources
                    SET scan_status=%s, updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT
                    WHERE id=%s
                    """,
                    (status, source_id),
                )
