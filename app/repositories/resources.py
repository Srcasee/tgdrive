import hashlib

from database_pool import connection, transaction


def build_identity_key(filename, size, mime_type):
    normalized = f"{filename.strip().casefold()}|{int(size or 0)}|{mime_type or ''}"
    return hashlib.md5(normalized.encode("utf-8"), usedforsecurity=False).hexdigest()


class ResourceRepository:
    def get_or_create(self, *, filename, size, mime_type):
        identity_key = build_identity_key(filename, size, mime_type)
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO resources(identity_key, filename, size, mime_type)
                    VALUES(%s, %s, %s, %s)
                    ON CONFLICT (identity_key) DO UPDATE
                    SET filename=EXCLUDED.filename,
                        size=EXCLUDED.size,
                        mime_type=EXCLUDED.mime_type,
                        updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT
                    RETURNING id
                    """,
                    (identity_key, filename, size, mime_type),
                )
                return cursor.fetchone()["id"]

    def get(self, resource_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, identity_key, filename, size, mime_type, status,
                           created_at, updated_at
                    FROM resources
                    WHERE id=%s
                    """,
                    (resource_id,),
                )
                return cursor.fetchone()
