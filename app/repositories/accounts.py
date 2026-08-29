from database import get_connection


class AccountRepository:
    def list_all(self):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, username, session, enabled
                FROM accounts
                ORDER BY id
                """
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_id_by_session(self, session):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM accounts WHERE session=?",
                (session,),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def get_session(self, account_id):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT session FROM accounts WHERE id=? AND enabled=1",
                (account_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def upsert_session(self, session, name=None):
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM accounts WHERE session=?",
                (session,),
            )
            row = cursor.fetchone()
            if row:
                return row[0]
            cursor.execute(
                """
                INSERT INTO accounts(name, session, enabled)
                VALUES(?, ?, 1)
                """,
                (name or session, session),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
