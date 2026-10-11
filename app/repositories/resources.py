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
        identity_key = build_index_identity_key(filename, size, mime_type)
        digest = content_hash.lower() if content_hash else None
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO resources(identity_key, content_hash, filename, size, mime_type)
                    VALUES(%s,%s,%s,%s,%s)
                    ON CONFLICT (identity_key) DO UPDATE
                    SET filename=EXCLUDED.filename,
                        size=EXCLUDED.size,
                        mime_type=EXCLUDED.mime_type,
                        updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT
                    RETURNING id
                    """,
                    (identity_key, digest, filename, size, mime_type),
                )
                return cursor.fetchone()["id"]

    def get(self, resource_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, identity_key, content_hash, filename, size, mime_type,
                           status,
                           EXISTS (
                               SELECT 1 FROM files f
                               WHERE f.resource_id = resources.id
                                 AND f.is_available = TRUE
                                 AND f.status = 'active'
                           ) AS is_available,
                           created_at, updated_at
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

    def verify_file(self, file_id, content_hash):
        """Record a source's digest without changing metadata-based resource identity."""
        digest = content_hash.lower()
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT resource_id FROM files WHERE id=%s FOR UPDATE", (file_id,)
                )
                file_row = cursor.fetchone()
                if file_row is None:
                    raise ValueError("file not found")
                resource_id = file_row["resource_id"]

                cursor.execute(
                    "SELECT content_hash FROM resources WHERE id=%s FOR UPDATE", (resource_id,)
                )
                current = cursor.fetchone()
                if current is None:
                    raise ValueError("resource not found")

                cursor.execute("UPDATE files SET content_hash=%s WHERE id=%s", (digest, file_id))
                if current["content_hash"] == digest:
                    return resource_id

                # Metadata identity is authoritative. Multiple sources can share a
                # Resource even if their digest observations differ; in that case
                # the Resource-level digest is ambiguous and must not be asserted.
                cursor.execute(
                    "SELECT id FROM resources WHERE content_hash=%s AND id<>%s",
                    (digest, resource_id),
                )
                digest_owner = cursor.fetchone()
                if current["content_hash"] is not None and current["content_hash"] != digest:
                    cursor.execute(
                        "UPDATE resources SET content_hash=NULL, updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT WHERE id=%s",
                        (resource_id,),
                    )
                elif digest_owner:
                    cursor.execute(
                        "UPDATE resources SET content_hash=NULL, updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT WHERE id=%s",
                        (resource_id,),
                    )
                else:
                    cursor.execute(
                        "UPDATE resources SET content_hash=%s, updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT WHERE id=%s",
                        (digest, resource_id),
                    )
                return resource_id
