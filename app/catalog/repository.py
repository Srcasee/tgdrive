from database_pool import connection, transaction


_SHARE_SQL = """
COALESCE(
    (
        SELECT json_agg(
            json_build_object(
                'id', s.id,
                'token', s.token,
                'url', '/share/' || s.token,
                'created_at', s.created_at
            ) ORDER BY s.id DESC
        )
        FROM shares s
        WHERE s.resource_id = r.id
    ),
    '[]'::json
) AS shares
"""


class CatalogRepository:
    def list_resources(self, limit, offset, category_id=None):
        with connection() as conn:
            with conn.cursor() as cursor:
                where = "WHERE r.status='active' AND EXISTS (SELECT 1 FROM files f WHERE f.resource_id=r.id AND f.is_available=TRUE AND f.status='active')"
                params = []
                if category_id is not None:
                    where += " AND EXISTS (SELECT 1 FROM resource_categories rc WHERE rc.resource_id=r.id AND rc.category_id=%s)"
                    params.append(category_id)
                cursor.execute(f"SELECT COUNT(*) AS total FROM resources r {where}", params)
                total = cursor.fetchone()["total"]
                cursor.execute(f"""
                    SELECT r.id, r.content_hash, r.filename, r.size, r.mime_type,
                           COALESCE(array_agg(DISTINCT c.id) FILTER (WHERE c.id IS NOT NULL), '{{}}') AS category_ids,
                           COUNT(DISTINCT f.id) AS source_count,
                           {_SHARE_SQL}
                    FROM resources r
                    LEFT JOIN resource_categories rc ON rc.resource_id=r.id
                    LEFT JOIN categories c ON c.id=rc.category_id
                    LEFT JOIN files f ON f.resource_id=r.id AND f.is_available=TRUE AND f.status='active'
                    {where}
                    GROUP BY r.id
                    ORDER BY r.id DESC LIMIT %s OFFSET %s
                """, params + [limit, offset])
                return total, cursor.fetchall()

    def search_resources(self, query, limit=100, category_id=None):
        with connection() as conn:
            with conn.cursor() as cursor:
                where = "r.status='active' AND r.filename ILIKE %s AND EXISTS (SELECT 1 FROM files f WHERE f.resource_id=r.id AND f.is_available=TRUE AND f.status='active')"
                params = [f"%{query}%"]
                if category_id is not None:
                    where += " AND EXISTS (SELECT 1 FROM resource_categories rc WHERE rc.resource_id=r.id AND rc.category_id=%s)"
                    params.append(category_id)
                cursor.execute(f"""
                    SELECT r.id, r.content_hash, r.filename, r.size, r.mime_type,
                           COALESCE(array_agg(DISTINCT c.id) FILTER (WHERE c.id IS NOT NULL), '{{}}') AS category_ids,
                           COUNT(DISTINCT f.id) AS source_count,
                           {_SHARE_SQL}
                    FROM resources r
                    LEFT JOIN resource_categories rc ON rc.resource_id=r.id
                    LEFT JOIN categories c ON c.id=rc.category_id
                    LEFT JOIN files f ON f.resource_id=r.id AND f.is_available=TRUE AND f.status='active'
                    WHERE {where}
                    GROUP BY r.id
                    ORDER BY r.id DESC LIMIT %s
                """, params + [limit])
                return cursor.fetchall()

    def get_resource(self, resource_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT r.id, r.content_hash, r.filename, r.size, r.mime_type, r.status,
                           COALESCE(array_agg(DISTINCT c.id) FILTER (WHERE c.id IS NOT NULL), '{{}}') AS category_ids,
                           COUNT(DISTINCT f.id) FILTER (WHERE f.is_available=TRUE AND f.status='active') AS source_count,
                           {_SHARE_SQL}
                    FROM resources r
                    LEFT JOIN resource_categories rc ON rc.resource_id=r.id
                    LEFT JOIN categories c ON c.id=rc.category_id
                    LEFT JOIN files f ON f.resource_id=r.id
                    WHERE r.id=%s
                    GROUP BY r.id
                """, (resource_id,))
                return cursor.fetchone()

    def set_categories(self, resource_id, category_ids):
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM resources WHERE id=%s", (resource_id,))
                if not cursor.fetchone():
                    return None
                if category_ids:
                    cursor.execute("SELECT id FROM categories WHERE id = ANY(%s)", (category_ids,))
                    found = {row["id"] for row in cursor.fetchall()}
                    missing = set(category_ids) - found
                    if missing:
                        raise ValueError("category not found")
                cursor.execute("DELETE FROM resource_categories WHERE resource_id=%s", (resource_id,))
                if category_ids:
                    cursor.executemany(
                        "INSERT INTO resource_categories(resource_id, category_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
                        [(resource_id, category_id) for category_id in category_ids],
                    )
                cursor.execute("""
                    SELECT r.id, r.filename,
                           COALESCE(array_agg(DISTINCT c.id) FILTER (WHERE c.id IS NOT NULL), '{}') AS category_ids
                    FROM resources r
                    LEFT JOIN resource_categories rc ON rc.resource_id=r.id
                    LEFT JOIN categories c ON c.id=rc.category_id
                    WHERE r.id=%s GROUP BY r.id
                """, (resource_id,))
                return cursor.fetchone()
