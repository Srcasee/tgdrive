from database_pool import connection, transaction


_ACTIVE_SOURCE_EXISTS = """
EXISTS (
    SELECT 1 FROM files sf
    JOIN telegram_sources ts
      ON ts.account_id=sf.account_id
     AND ts.telegram_chat_id=sf.telegram_chat_id
     AND ts.enabled=TRUE
    WHERE sf.resource_id=r.id
      AND sf.is_available=TRUE
      AND sf.status='active'
)
"""

_RESOURCE_SOURCES_SQL = """
COALESCE(
    (
        SELECT json_agg(
            json_build_object(
                'file_id', sf.id,
                'account_id', sf.account_id,
                'account_name', a.name,
                'telegram_chat_id', sf.telegram_chat_id,
                'chat_name', sts.name,
                'message_id', sf.message_id,
                'topic_id', sf.topic_id,
                'filename', sf.filename,
                'size', sf.size,
                'mime_type', sf.mime_type,
                'upload_time', sf.upload_time
            )
            ORDER BY sf.account_id, sf.telegram_chat_id, sf.topic_id NULLS FIRST, sf.message_id
        )
        FROM files sf
        JOIN telegram_sources sts
          ON sts.account_id=sf.account_id
         AND sts.telegram_chat_id=sf.telegram_chat_id
         AND sts.enabled=TRUE
        LEFT JOIN accounts a ON a.id=sf.account_id
        WHERE sf.resource_id=r.id
          AND sf.is_available=TRUE
          AND sf.status='active'
    ),
    '[]'::json
) AS sources
"""

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

_SORT_COLUMNS = {
    "id": "r.id",
    "filename": "LOWER(r.filename)",
    "size": "r.size",
    "mime_type": "LOWER(r.mime_type)",
    "source_count": "COUNT(DISTINCT f.id)",
}


class CatalogRepository:
    def list_resources(self, limit, offset, category_id=None, sort="id", order="desc", account_id=None):
        with connection() as conn:
            with conn.cursor() as cursor:
                active_source_exists = _ACTIVE_SOURCE_EXISTS
                resource_sources_sql = _RESOURCE_SOURCES_SQL
                source_count_sql = "COUNT(DISTINCT f.id)"
                if account_id is not None:
                    scoped_condition = " AND sf.account_id=" + str(int(account_id))
                    active_source_exists = active_source_exists.replace("WHERE sf.resource_id=r.id", "WHERE sf.resource_id=r.id" + scoped_condition)
                    resource_sources_sql = resource_sources_sql.replace("WHERE sf.resource_id=r.id", "WHERE sf.resource_id=r.id" + scoped_condition)
                    source_count_sql = "COUNT(DISTINCT f.id) FILTER (WHERE f.account_id=" + str(int(account_id)) + " AND EXISTS (SELECT 1 FROM telegram_sources ts_count WHERE ts_count.account_id=f.account_id AND ts_count.telegram_chat_id=f.telegram_chat_id AND ts_count.enabled=TRUE))"
                where = f"WHERE r.status='active' AND {active_source_exists}"
                params = []
                if category_id is not None:
                    where += " AND EXISTS (SELECT 1 FROM resource_categories rc WHERE rc.resource_id=r.id AND rc.category_id=%s)"
                    params.append(category_id)
                cursor.execute(f"SELECT COUNT(*) AS total FROM resources r {where}", params)
                total = cursor.fetchone()["total"]
                sort_sql = source_count_sql if sort == "source_count" else _SORT_COLUMNS.get(sort, _SORT_COLUMNS["id"])
                direction = "ASC" if order == "asc" else "DESC"
                cursor.execute(f"""
                    SELECT r.id, r.content_hash, r.filename, r.size, r.mime_type,
                           COALESCE(array_agg(DISTINCT c.id) FILTER (WHERE c.id IS NOT NULL), '{{}}') AS category_ids,
                           {source_count_sql} AS source_count,
                           {resource_sources_sql},
                           {_SHARE_SQL}
                    FROM resources r
                    LEFT JOIN resource_categories rc ON rc.resource_id=r.id
                    LEFT JOIN categories c ON c.id=rc.category_id
                    LEFT JOIN files f ON f.resource_id=r.id AND f.is_available=TRUE AND f.status='active'
                    {where}
                    GROUP BY r.id
                    ORDER BY {sort_sql} {direction}, r.id DESC LIMIT %s OFFSET %s
                """, params + [limit, offset])
                return total, cursor.fetchall()

    def search_resources(self, query, limit=100, category_id=None, account_id=None):
        with connection() as conn:
            with conn.cursor() as cursor:
                active_source_exists = _ACTIVE_SOURCE_EXISTS
                resource_sources_sql = _RESOURCE_SOURCES_SQL
                source_count_sql = "COUNT(DISTINCT f.id)"
                if account_id is not None:
                    scoped_condition = " AND sf.account_id=" + str(int(account_id))
                    active_source_exists = active_source_exists.replace("WHERE sf.resource_id=r.id", "WHERE sf.resource_id=r.id" + scoped_condition)
                    resource_sources_sql = resource_sources_sql.replace("WHERE sf.resource_id=r.id", "WHERE sf.resource_id=r.id" + scoped_condition)
                    source_count_sql = "COUNT(DISTINCT f.id) FILTER (WHERE f.account_id=" + str(int(account_id)) + ")"
                where = f"r.status='active' AND r.filename ILIKE %s AND {active_source_exists}"
                params = [f"%{query}%"]
                if category_id is not None:
                    where += " AND EXISTS (SELECT 1 FROM resource_categories rc WHERE rc.resource_id=r.id AND rc.category_id=%s)"
                    params.append(category_id)
                cursor.execute(f"""
                    SELECT r.id, r.content_hash, r.filename, r.size, r.mime_type,
                           COALESCE(array_agg(DISTINCT c.id) FILTER (WHERE c.id IS NOT NULL), '{{}}') AS category_ids,
                           {source_count_sql} AS source_count,
                           {resource_sources_sql},
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
                           {_RESOURCE_SOURCES_SQL},
                           {_SHARE_SQL}
                    FROM resources r
                    LEFT JOIN resource_categories rc ON rc.resource_id=r.id
                    LEFT JOIN categories c ON c.id=rc.category_id
                    LEFT JOIN files f ON f.resource_id=r.id
                    WHERE r.id=%s
                    GROUP BY r.id
                """, (resource_id,))
                return cursor.fetchone()

    def deactivate_telegram_chats(self, account_id, chat_ids):
        """Make files/resources from removed Telegram chats unavailable."""
        if not chat_ids:
            return
        with transaction() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE files
                    SET is_available=FALSE, status='inactive', scan_status='idle'
                    WHERE account_id=%s AND telegram_chat_id = ANY(%s)
                    """,
                    (account_id, chat_ids),
                )
                cursor.execute(
                    """
                    UPDATE resources r
                    SET status='inactive', updated_at=EXTRACT(EPOCH FROM NOW())::BIGINT
                    WHERE EXISTS (
                        SELECT 1 FROM files f
                        WHERE f.resource_id=r.id
                          AND f.account_id=%s
                          AND f.telegram_chat_id = ANY(%s)
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM files f2
                        WHERE f2.resource_id=r.id
                          AND f2.is_available=TRUE
                          AND f2.status='active'
                    )
                    """,
                    (account_id, chat_ids),
                )

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
