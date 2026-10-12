import secrets

from database_pool import connection, transaction


class ShareRepository:
    def create(self, resource_id, expires_at=None):
        """Create or rotate the one global share link for a resource."""
        token = secrets.token_urlsafe(32)
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO shares(resource_id, token, expires_at)
                    VALUES(%s, %s, %s)
                    ON CONFLICT (resource_id) DO UPDATE
                    SET token=EXCLUDED.token,
                        created_at=EXTRACT(EPOCH FROM NOW())::BIGINT,
                        expires_at=EXCLUDED.expires_at
                    RETURNING id, resource_id, token, created_at, expires_at
                    """,
                    (resource_id, token, expires_at),
                )
                return cursor.fetchone()

    def list_for_resource(self, resource_id):
        return self.list_for_resources([resource_id]).get(resource_id, [])

    def list_for_resources(self, resource_ids):
        if not resource_ids:
            return {}
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, resource_id, token, created_at, expires_at
                    FROM shares
                    WHERE resource_id = ANY(%s)
                    """,
                    (list(resource_ids),),
                )
                rows = cursor.fetchall()
        result = {resource_id: [] for resource_id in resource_ids}
        for row in rows:
            result.setdefault(row["resource_id"], []).append(
                {
                    "id": row["id"],
                    "token": row["token"],
                    "url": f"/share/{row['token']}",
                    "created_at": row["created_at"],
                    "expires_at": row["expires_at"],
                }
            )
        return result

    def attach_to_resources(self, resources):
        if not resources:
            return
        shares_by_resource = self.list_for_resources(
            [resource["id"] for resource in resources]
        )
        for resource in resources:
            resource["shares"] = shares_by_resource.get(resource["id"], [])

    def delete(self, share_id):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM shares WHERE id=%s RETURNING id",
                    (share_id,),
                )
                return cursor.fetchone() is not None

    def get_resource_id(self, token):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT resource_id
                    FROM shares
                    WHERE token=%s
                      AND (expires_at IS NULL OR expires_at > EXTRACT(EPOCH FROM NOW())::BIGINT)
                    """,
                    (token,),
                )
                row = cursor.fetchone()
                return row["resource_id"] if row else None
