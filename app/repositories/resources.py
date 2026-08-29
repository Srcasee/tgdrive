from database_pool import connection, transaction


def build_index_identity_key(filename, size, mime_type):
    return f"index:{filename.strip().casefold()}|{int(size or 0)}|{mime_type or ''}"


def build_content_identity_key(content_hash):
    if not isinstance(content_hash, str) or len(content_hash) != 64:
        raise ValueError("content_hash must be a SHA-256 hex digest")
    try:
        int(content_hash, 16)
    except ValueError as exc:
        raise ValueError("content_hash must be a SHA-256 hex digest") from exc
    return f"sha256:{content_hash.lower()}"


class ResourceRepository:
    def get_or_create(self, *, filename, size, mime_type, content_hash=None):
        if content_hash:
            identity_key = build_content_identity_key(content_hash)
            with transaction() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO resources(identity_key, content_hash, filename, size, mime_type)
                        VALUES(%s,%s,%s,%s,%s)
                        ON CONFLICT (content_hash) DO UPDATE
                        SET filename=EXCLUDED.filename,
                            size=EXCLUDED.size,
                            mime_type=EXCLUDED.mime_type,
                            updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT
                        RETURNING id
                        """,
                        (identity_key, content_hash.lower(), filename, size, mime_type),
                    )
                    return cursor.fetchone()["id"]

        identity_key = build_index_identity_key(filename, size, mime_type)
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO resources(identity_key, filename, size, mime_type)
                    VALUES(%s,%s,%s,%s)
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
                    SELECT id, identity_key, content_hash, filename, size, mime_type,
                           status, created_at, updated_at
                    FROM resources WHERE id=%s
                    """,
                    (resource_id,),
                )
                return cursor.fetchone()

    def get_by_content_hash(self, content_hash):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, identity_key, content_hash, filename, size, mime_type, status
                    FROM resources WHERE content_hash=%s
                    """,
                    (content_hash.lower(),),
                )
                return cursor.fetchone()

    def verify(self, resource_id, content_hash):
        identity_key = build_content_identity_key(content_hash)
        digest = content_hash.lower()
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, content_hash FROM resources WHERE id=%s FOR UPDATE", (resource_id,))
                current = cursor.fetchone()
                if current is None:
                    raise ValueError("resource not found")
                if current["content_hash"] == digest:
                    return resource_id

                cursor.execute("SELECT id FROM resources WHERE content_hash=%s FOR UPDATE", (digest,))
                target = cursor.fetchone()
                if target and target["id"] != resource_id:
                    target_id = target["id"]
                    cursor.execute(
                        "INSERT INTO resource_categories(resource_id, category_id) SELECT %s, category_id FROM resource_categories WHERE resource_id=%s ON CONFLICT DO NOTHING",
                        (target_id, resource_id),
                    )
                    cursor.execute("UPDATE files SET resource_id=%s WHERE resource_id=%s", (target_id, resource_id))
                    cursor.execute("DELETE FROM resource_categories WHERE resource_id=%s", (resource_id,))
                    cursor.execute("DELETE FROM resources WHERE id=%s", (resource_id,))
                    return target_id

                cursor.execute(
                    "UPDATE resources SET identity_key=%s, content_hash=%s, updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT WHERE id=%s",
                    (identity_key, digest, resource_id),
                )
                cursor.execute("UPDATE files SET content_hash=%s WHERE resource_id=%s", (digest, resource_id))
                return resource_id
