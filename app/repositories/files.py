from database_pool import connection, transaction


class FileRepository:
    def list_available(self, limit, offset):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM files WHERE is_available=TRUE")
                total = cursor.fetchone()["total"]
                cursor.execute("""
                    SELECT id, resource_id, filename, size, mime_type, telegram_chat_id,
                           message_id, category_id
                    FROM files WHERE is_available=TRUE
                    ORDER BY id DESC LIMIT %s OFFSET %s
                """, (limit, offset))
                return total, cursor.fetchall()

    def search(self, query, limit=100):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, resource_id, filename, size, mime_type, telegram_chat_id,
                           message_id, category_id
                    FROM files
                    WHERE filename ILIKE %s AND is_available=TRUE
                    ORDER BY id DESC LIMIT %s
                """, (f"%{query}%", limit))
                return cursor.fetchall()

    def get_download_info(self, file_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, resource_id, filename, telegram_chat_id, message_id, size,
                           mime_type, account_id, is_available
                    FROM files WHERE id=%s
                """, (file_id,))
                return cursor.fetchone()

    def list_resource_sources(self, resource_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, resource_id, filename, size, mime_type, telegram_chat_id,
                           message_id, account_id, is_available, status
                    FROM files
                    WHERE resource_id=%s AND is_available=TRUE AND status='active'
                      AND account_id IS NOT NULL
                    ORDER BY id ASC
                """, (resource_id,))
                return cursor.fetchall()

    def get_stream_info(self, file_id):
        return self.get_download_info(file_id)

    def get_head_info(self, file_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT size, mime_type, is_available FROM files WHERE id=%s", (file_id,))
                return cursor.fetchone()

    def upsert_verified_message(self, *, filename, size, mime_type, chat_id, message_id, upload_time, account_id, resource_id):
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("filename is required for indexed files")
        if resource_id is None:
            raise ValueError("resource_id is required for indexed files")
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO files
                    (filename, size, mime_type, telegram_chat_id, message_id,
                     upload_time, account_id, resource_id, status, scan_status, is_available)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'active','verified',TRUE)
                    ON CONFLICT (account_id, telegram_chat_id, message_id)
                    DO UPDATE SET resource_id=EXCLUDED.resource_id,
                        filename=EXCLUDED.filename, size=EXCLUDED.size,
                        mime_type=EXCLUDED.mime_type, upload_time=EXCLUDED.upload_time,
                        status='active', scan_status='verified', is_available=TRUE
                """, (filename, size, mime_type, chat_id, message_id, upload_time, account_id, resource_id))

    def mark_checking(self, account_id, chat_id):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE files SET scan_status='checking', is_available=FALSE WHERE account_id=%s AND telegram_chat_id=%s", (account_id, chat_id))

    def mark_unverified_deleted(self, account_id, chat_id):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE files SET status='deleted', is_available=FALSE WHERE account_id=%s AND telegram_chat_id=%s AND scan_status='checking'", (account_id, chat_id))

    def reset_checking(self, account_id, chat_id):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE files SET scan_status='verified', is_available=TRUE WHERE account_id=%s AND telegram_chat_id=%s AND scan_status='checking'", (account_id, chat_id))
