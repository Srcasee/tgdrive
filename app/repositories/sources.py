from database import get_connection


class SourceRepository:
    def list_enabled_for_account(self, account_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, telegram_chat_id, name, scan_interval,
                       last_message_id, last_scan_time, sync_mode, scan_status
                FROM telegram_sources
                WHERE account_id=? AND enabled=1
                """,
                (account_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def mark_scanning(self, source_id):
        self._update_status(source_id, "scanning")

    def mark_success(self, source_id, last_message_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE telegram_sources
                SET last_message_id=?, last_scan_time=strftime('%s','now'),
                    scan_status='success', updated_at=strftime('%s','now')
                WHERE id=?
                """,
                (last_message_id, source_id),
            )
            conn.commit()
        finally:
            conn.close()

    def add(self, account_id, chat_id, name):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO telegram_sources
                (account_id, telegram_chat_id, name, enabled)
                VALUES (?, ?, ?, 1)
                """,
                (account_id, chat_id, name),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def _update_status(source_id, status):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE telegram_sources
                SET scan_status=?, updated_at=strftime('%s','now')
                WHERE id=?
                """,
                (status, source_id),
            )
            conn.commit()
        finally:
            conn.close()
