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

    def list_by_status(self, status, page=1, size=50):
        if status not in {"active", "completed", "failed"}:
            raise ValueError("unsupported download status")
        offset = (page - 1) * size
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM download_records WHERE status=%s", (status,))
                total = cursor.fetchone()["total"]
                cursor.execute(
                    """
                    SELECT id, filename, status, started_at, completed_at
                    FROM download_records
                    WHERE status=%s
                    ORDER BY started_at DESC, id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (status, size, offset),
                )
                items = cursor.fetchall()
        return {"items": items, "total": total, "page": page, "size": size}

    def bulk_delete(self, record_ids):
        if not record_ids:
            return 0
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM download_records WHERE id = ANY(%s) RETURNING id",
                    (record_ids,),
                )
                deleted = len(cursor.fetchall())
            conn.commit()
        return deleted

    def cleanup_older_than(self, days=30):
        cutoff = int(time.time()) - days * 24 * 60 * 60
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM download_records WHERE COALESCE(completed_at, started_at) < %s",
                    (cutoff,),
                )
                deleted = cursor.rowcount
            conn.commit()
        return deleted
