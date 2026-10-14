from database_pool import connection, transaction


class UserRepository:
    def get_by_username(self, username):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT u.id, u.username, u.password_hash, u.role, u.enabled, COALESCE(r.status, 1) AS role_enabled FROM users u LEFT JOIN roles r ON r.code=u.role WHERE u.username=%s",
                    (username,),
                )
                return cursor.fetchone()

    def get_credentials_by_id(self, user_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username, password_hash, role, enabled, last_login_at, last_login_ip, avatar_url FROM users WHERE id=%s",
                    (user_id,),
                )
                return cursor.fetchone()

    def get_by_id(self, user_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT u.id, u.username, u.role, u.enabled, u.last_login_at, u.last_login_ip, u.avatar_url, COALESCE(r.status, 1) AS role_enabled FROM users u LEFT JOIN roles r ON r.code=u.role WHERE u.id=%s",
                    (user_id,),
                )
                return cursor.fetchone()

    def record_login(self, user_id, login_at, login_ip):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET last_login_at=%s, last_login_ip=%s WHERE id=%s",
                    (login_at, login_ip, user_id),
                )

    def update_credentials(self, user_id, username, password_hash=None):
        with transaction() as conn:
            with conn.cursor() as cursor:
                if password_hash:
                    cursor.execute(
                        "UPDATE users SET username=%s, password_hash=%s WHERE id=%s RETURNING id, username, role, enabled, last_login_at, last_login_ip, avatar_url",
                        (username, password_hash, user_id),
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET username=%s WHERE id=%s RETURNING id, username, role, enabled, last_login_at, last_login_ip, avatar_url",
                        (username, user_id),
                    )
                return cursor.fetchone()


    def update_avatar(self, user_id, avatar_url):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET avatar_url=%s WHERE id=%s RETURNING id, username, role, enabled, last_login_at, last_login_ip, avatar_url",
                    (avatar_url, user_id),
                )
                return cursor.fetchone()

    def create(self, username, password_hash, role="user"):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users(username, password_hash, role, enabled)
                    VALUES(%s, %s, %s, TRUE)
                    RETURNING id, username, role, enabled
                    """,
                    (username, password_hash, role),
                )
                return cursor.fetchone()

    def ensure_admin(self, username, password_hash):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users(username, password_hash, role, enabled)
                    VALUES(%s, %s, 'admin', TRUE)
                    ON CONFLICT (username) DO NOTHING
                    RETURNING id
                    """,
                    (username, password_hash),
                )
                return cursor.fetchone()
