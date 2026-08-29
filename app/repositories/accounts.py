from database import get_connection


class AccountRepository:
    def list_all(self):
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, name, username, session, enabled
                    FROM accounts
                    ORDER BY id
                    """
                )
                return cursor.fetchall()

    def get_id_by_session(self, session):
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM accounts WHERE session=%s",
                    (session,),
                )
                row = cursor.fetchone()
                return row["id"] if row else None

    def get_session(self, account_id):
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT session FROM accounts WHERE id=%s AND enabled=TRUE",
                    (account_id,),
                )
                row = cursor.fetchone()
                return row["session"] if row else None

    def upsert_session(self, session, name=None):
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO accounts(name, session, enabled)
                    VALUES(%s, %s, TRUE)
                    ON CONFLICT (session) DO UPDATE
                    SET name=COALESCE(accounts.name, EXCLUDED.name)
                    RETURNING id
                    """,
                    (name or session, session),
                )
                account_id = cursor.fetchone()["id"]
            conn.commit()
            return account_id
