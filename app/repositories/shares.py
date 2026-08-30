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
                    RETURNING token
                    """,
                    (resource_id, token),
                )
                return cursor.fetchone()["token"]

    def get_resource_id(self, token):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT resource_id FROM shares WHERE token=%s",
                    (token,),
                )
                row = cursor.fetchone()
                return row["resource_id"] if row else None
