from database_pool import connection, transaction


class UserRepository:
    def get_by_username(self, username):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT u.id, u.username, u.password_hash, u.role, u.enabled, u.totp_secret, u.totp_enabled, COALESCE(r.status, 1) AS role_enabled FROM users u LEFT JOIN roles r ON r.code=u.role WHERE u.username=%s",
                    (username,),
                )
                return cursor.fetchone()

    def get_credentials_by_id(self, user_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, username, password_hash, role, enabled, last_login_at, last_login_ip, avatar_url, totp_secret, totp_enabled FROM users WHERE id=%s",
                    (user_id,),
                )
                return cursor.fetchone()

    def get_by_id(self, user_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT u.id, u.username, u.role, u.enabled, u.last_login_at, u.last_login_ip, u.avatar_url, u.totp_enabled, COALESCE(r.status, 1) AS role_enabled FROM users u LEFT JOIN roles r ON r.code=u.role WHERE u.id=%s",
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

    def update_totp_secret(self, user_id, secret):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET totp_secret=%s, totp_enabled=FALSE WHERE id=%s RETURNING id",
                    (secret, user_id),
                )
                return cursor.fetchone()

    def set_totp_enabled(self, user_id, enabled):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET totp_enabled=%s, totp_secret=CASE WHEN %s THEN totp_secret ELSE NULL END WHERE id=%s RETURNING id",
                    (enabled, enabled, user_id),
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
                # Serialize bootstrap attempts so two starting instances cannot
                # create separate bootstrap administrators at the same time.
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", (724063901,))

                # Bootstrap is only for an empty administrator table. In
                # particular, renaming an existing admin must not recreate the
                # old ADMIN_USERNAME on the next restart.
                cursor.execute(
                    "SELECT id, username FROM users WHERE role='admin' ORDER BY id LIMIT 1"
                )
                existing_admin = cursor.fetchone()
                if existing_admin:
                    return {
                        "id": existing_admin["id"],
                        "username": existing_admin["username"],
                        "created": False,
                    }

                cursor.execute(
                    """
                    INSERT INTO users(username, password_hash, role, enabled)
                    VALUES(%s, %s, 'admin', TRUE)
                    ON CONFLICT (username) DO NOTHING
                    RETURNING id, username
                    """,
                    (username, password_hash),
                )
                created = cursor.fetchone()
                if created:
                    return {
                        "id": created["id"],
                        "username": created["username"],
                        "created": True,
                    }

                # Never silently promote an existing non-admin account just
                # because its username matches the configured bootstrap name.
                cursor.execute(
                    "SELECT id, username FROM users WHERE username=%s",
                    (username,),
                )
                conflicting_user = cursor.fetchone()
                if conflicting_user:
                    return {
                        "id": conflicting_user["id"],
                        "username": conflicting_user["username"],
                        "created": False,
                        "username_conflict": True,
                    }
                return None
