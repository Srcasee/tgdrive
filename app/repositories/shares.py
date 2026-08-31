import secrets

from database_pool import connection, transaction


class ShareRepository:
    def create(self, resource_id):
        token = secrets.token_urlsafe(32)
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO shares(resource_id, token)
                    VALUES(%s, %s)
                    RETURNING id, token
                    """,
                    (resource_id, token),
                )
                row = cursor.fetchone()
                return {"id": row["id"], "token": row["token"]}

    def list_for_resource(self, resource_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, resource_id, token, created_at
                    FROM shares
                    WHERE resource_id=%s
                    ORDER BY id DESC
                    """,
                    (resource_id,),
                )
                return cursor.fetchall()

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
                    "SELECT resource_id FROM shares WHERE token=%s",
                    (token,),
                )
                row = cursor.fetchone()
                return row["resource_id"] if row else None
