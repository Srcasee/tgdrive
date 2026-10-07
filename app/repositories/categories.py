from database_pool import connection, transaction


class CategoryRepository:
    def list_all(self):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name FROM categories ORDER BY name")
                return cursor.fetchall()

    def get(self, category_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, name FROM categories WHERE id=%s", (category_id,))
                return cursor.fetchone()

    def create(self, name):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO categories(name) VALUES(%s) RETURNING id, name",
                    (name.strip(),),
                )
                return cursor.fetchone()

    def update(self, category_id, name):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE categories SET name=%s WHERE id=%s RETURNING id, name",
                    (name.strip(), category_id),
                )
                return cursor.fetchone()

    def delete(self, category_id):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM categories WHERE id=%s RETURNING id", (category_id,))
                return cursor.fetchone()
