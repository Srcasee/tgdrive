from database import get_connection


class FileRepository:
    def list_available(self, limit, offset):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM files WHERE is_available=1")
            total = cursor.fetchone()[0]
            cursor.execute(
                """
                SELECT id, filename, size, mime_type,
                       telegram_chat_id, message_id
                FROM files
                WHERE is_available=1
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            return total, [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def search(self, query, limit=100):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, filename, size, mime_type,
                       telegram_chat_id, message_id
                FROM files
                WHERE filename LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (f"%{query}%", limit),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_download_info(self, file_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT filename, telegram_chat_id, message_id, size,
                       mime_type, account_id, is_available
                FROM files WHERE id=?
                """,
                (file_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_stream_info(self, file_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT telegram_chat_id, message_id, filename,
                       mime_type, size, account_id
                FROM files WHERE id=?
                """,
                (file_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_head_info(self, file_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT size, mime_type FROM files WHERE id=?",
                (file_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def mark_verified(self, account_id, chat_id, message_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE files
                SET status='active', scan_status='verified', is_available=1
                WHERE account_id=? AND telegram_chat_id=? AND message_id=?
                """,
                (account_id, chat_id, message_id),
            )
            conn.commit()
        finally:
            conn.close()

    def upsert_message(self, *, filename, size, mime_type, chat_id,
                       message_id, upload_time, account_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO files
                (filename, size, mime_type, telegram_chat_id, message_id,
                 upload_time, account_id)
                VALUES(?,?,?,?,?,?,?)
                """,
                (filename, size, mime_type, chat_id, message_id,
                 upload_time, account_id),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_checking(self, account_id, chat_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE files
                SET scan_status='checking', is_available=0
                WHERE account_id=? AND telegram_chat_id=?
                """,
                (account_id, chat_id),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_unverified_deleted(self, account_id, chat_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE files
                SET status='deleted', is_available=0
                WHERE account_id=? AND telegram_chat_id=?
                  AND scan_status='checking'
                """,
                (account_id, chat_id),
            )
            conn.commit()
        finally:
            conn.close()
