from database_pool import connection, transaction


class FileRepository:
    def get_by_telegram_location(self, account_id, chat_id, message_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, content_hash, resource_id, filename, size, mime_type FROM files WHERE account_id=%s AND telegram_chat_id=%s AND message_id=%s",
                    (account_id, chat_id, message_id),
                )
                return cursor.fetchone()

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

    def upsert_indexed_message(self, *, filename, size, mime_type, chat_id, message_id, upload_time, account_id, resource_id, content_hash=None):
        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("filename is required for indexed files")
        if resource_id is None:
            raise ValueError("resource_id is required for indexed files")
        if content_hash is not None and (not isinstance(content_hash, str) or len(content_hash) != 64):
            raise ValueError("content_hash must be a SHA-256 hex digest when provided")
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO files
                    (filename, size, mime_type, telegram_chat_id, message_id,
                     upload_time, account_id, resource_id, content_hash, status, scan_status, is_available)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'active','indexed',TRUE)
                    ON CONFLICT (account_id, telegram_chat_id, message_id)
                    DO UPDATE SET resource_id=EXCLUDED.resource_id,
                        content_hash=COALESCE(EXCLUDED.content_hash, files.content_hash),
                        filename=EXCLUDED.filename, size=EXCLUDED.size,
                        mime_type=EXCLUDED.mime_type, upload_time=EXCLUDED.upload_time,
                        status='active', scan_status='indexed', is_available=TRUE
                """, (filename, size, mime_type, chat_id, message_id, upload_time, account_id, resource_id, content_hash.lower() if content_hash else None))

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
                cursor.execute("UPDATE files SET scan_status='indexed', is_available=TRUE WHERE account_id=%s AND telegram_chat_id=%s AND scan_status='checking'", (account_id, chat_id))
