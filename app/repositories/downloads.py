import time

from database import get_connection


class DownloadRepository:
    def create(self, resource, created_by=None):
        now = int(time.time())
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO download_records
                        (resource_id, filename, size, status, started_at, bytes_transferred, created_by)
                    VALUES (%s, %s, %s, 'active', %s, 0, %s)
                    RETURNING id
                    """,
                    (resource["id"], resource["filename"], resource["size"], now, created_by),
                )
                row = cursor.fetchone()
            conn.commit()
        return row["id"]

    def complete(self, record_id, bytes_transferred):
        now = int(time.time())
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE download_records SET status='completed', completed_at=%s, bytes_transferred=%s WHERE id=%s AND status='active'", (now, bytes_transferred, record_id))
            conn.commit()

    def fail(self, record_id, bytes_transferred, error):
        now = int(time.time())
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE download_records SET status='failed', completed_at=%s, bytes_transferred=%s, error=%s WHERE id=%s AND status='active'", (now, bytes_transferred, error[:2000], record_id))
            conn.commit()

    def delete(self, record_id):
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM download_records WHERE id=%s RETURNING id", (record_id,))
                row = cursor.fetchone()
            conn.commit()
        return row is not None

    def list_active(self, limit=100): return self._list("WHERE status = 'active'", limit)
    def list_history(self, limit=100): return self._list("WHERE status IN ('completed', 'failed')", limit)

    def _list(self, where, limit):
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT id, resource_id, filename, size, status, started_at,
                           completed_at, bytes_transferred, error, created_by
                    FROM download_records {where}
                    ORDER BY started_at DESC, id DESC LIMIT %s
                """, (limit,))
                return cursor.fetchall()
