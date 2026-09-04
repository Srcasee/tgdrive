from database_pool import connection, transaction


class AccountRepository:
    def list_all(self):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, name, username, enabled
                    FROM accounts
                    ORDER BY id
                    """
                )
                return cursor.fetchall()

    def get(self, account_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, name, username, session, enabled FROM accounts WHERE id=%s",
                    (account_id,),
                )
                return cursor.fetchone()

    def list_enabled_sessions(self):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, session FROM accounts WHERE enabled=TRUE ORDER BY id"
                )
                return cursor.fetchall()

    def get_id_by_session(self, session):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM accounts WHERE session=%s",
                    (session,),
                )
                row = cursor.fetchone()
                return row["id"] if row else None

    def get_session(self, account_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT session FROM accounts WHERE id=%s AND enabled=TRUE",
                    (account_id,),
                )
                row = cursor.fetchone()
                return row["session"] if row else None

    def exists(self, account_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM accounts WHERE id=%s", (account_id,))
                return cursor.fetchone() is not None

    def set_enabled(self, account_id, enabled):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE accounts SET enabled=%s WHERE id=%s RETURNING id",
                    (enabled, account_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("account not found")
                return row["id"]

    def upsert_session(self, session, name=None):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO accounts(name, session, enabled)
                    VALUES(%s, %s, TRUE)
                    ON CONFLICT (session) DO UPDATE
                    SET name=COALESCE(accounts.name, EXCLUDED.name),
                        enabled=TRUE
                    RETURNING id
                    """,
                    (name or session, session),
                )
                return cursor.fetchone()["id"]
