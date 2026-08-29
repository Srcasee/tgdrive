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
