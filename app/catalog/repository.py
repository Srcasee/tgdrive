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
                'topic_name', sf.topic_name,
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
    def list_resources(self, limit, offset, sort="id", order="desc", account_id=None, chat_id=None, topic_id=None):
        with connection() as conn:
            with conn.cursor() as cursor:
                active_source_exists = _ACTIVE_SOURCE_EXISTS
                resource_sources_sql = _RESOURCE_SOURCES_SQL
                source_count_sql = "COUNT(DISTINCT f.id)"
                scoped_conditions = ""
                if account_id is not None: scoped_conditions += " AND sf.account_id=" + str(int(account_id))
                if chat_id is not None: scoped_conditions += " AND sf.telegram_chat_id=" + str(int(chat_id))
                if topic_id is not None: scoped_conditions += " AND sf.topic_id=" + str(int(topic_id))
                if scoped_conditions:
                    active_source_exists = active_source_exists.replace("WHERE sf.resource_id=r.id", "WHERE sf.resource_id=r.id" + scoped_conditions)
                    resource_sources_sql = resource_sources_sql.replace("WHERE sf.resource_id=r.id", "WHERE sf.resource_id=r.id" + scoped_conditions)
                    filters = []
                    if account_id is not None: filters.append("f.account_id=" + str(int(account_id)))
                    if chat_id is not None: filters.append("f.telegram_chat_id=" + str(int(chat_id)))
                    if topic_id is not None: filters.append("f.topic_id=" + str(int(topic_id)))
                    filters.append("EXISTS (SELECT 1 FROM telegram_sources ts_count WHERE ts_count.account_id=f.account_id AND ts_count.telegram_chat_id=f.telegram_chat_id AND ts_count.enabled=TRUE)")
                    source_count_sql = "COUNT(DISTINCT f.id) FILTER (WHERE " + " AND ".join(filters) + ")"
                where = f"WHERE r.status='active' AND {active_source_exists}"
                params = []
                cursor.execute(f"SELECT COUNT(*) AS total FROM resources r {where}", params)
                total = cursor.fetchone()["total"]
                sort_sql = source_count_sql if sort == "source_count" else _SORT_COLUMNS.get(sort, _SORT_COLUMNS["id"])
                direction = "ASC" if order == "asc" else "DESC"
                cursor.execute(f"""
                    SELECT r.id, r.content_hash, r.filename, r.size, r.mime_type,
                           {source_count_sql} AS source_count,
                           {resource_sources_sql},
                           {_SHARE_SQL}
                    FROM resources r
                    LEFT JOIN files f ON f.resource_id=r.id AND f.is_available=TRUE AND f.status='active'
                    {where}
                    GROUP BY r.id
                    ORDER BY {sort_sql} {direction}, r.id DESC LIMIT %s OFFSET %s
                """, params + [limit, offset])
                return total, cursor.fetchall()

    def search_resources(self, query, limit=100, account_id=None, chat_id=None, topic_id=None):
        with connection() as conn:
            with conn.cursor() as cursor:
                active_source_exists = _ACTIVE_SOURCE_EXISTS
                resource_sources_sql = _RESOURCE_SOURCES_SQL
                source_count_sql = "COUNT(DISTINCT f.id)"
                scoped_conditions = ""
                if account_id is not None: scoped_conditions += " AND sf.account_id=" + str(int(account_id))
                if chat_id is not None: scoped_conditions += " AND sf.telegram_chat_id=" + str(int(chat_id))
                if topic_id is not None: scoped_conditions += " AND sf.topic_id=" + str(int(topic_id))
                if scoped_conditions:
                    active_source_exists = active_source_exists.replace("WHERE sf.resource_id=r.id", "WHERE sf.resource_id=r.id" + scoped_conditions)
                    resource_sources_sql = resource_sources_sql.replace("WHERE sf.resource_id=r.id", "WHERE sf.resource_id=r.id" + scoped_conditions)
                    filters = []
                    if account_id is not None: filters.append("f.account_id=" + str(int(account_id)))
                    if chat_id is not None: filters.append("f.telegram_chat_id=" + str(int(chat_id)))
                    if topic_id is not None: filters.append("f.topic_id=" + str(int(topic_id)))
                    filters.append("EXISTS (SELECT 1 FROM telegram_sources ts_count WHERE ts_count.account_id=f.account_id AND ts_count.telegram_chat_id=f.telegram_chat_id AND ts_count.enabled=TRUE)")
                    source_count_sql = "COUNT(DISTINCT f.id) FILTER (WHERE " + " AND ".join(filters) + ")"
                where = f"r.status='active' AND r.filename ILIKE %s AND {active_source_exists}"
                params = [f"%{query}%"]
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

    def get_resource_tree(self):
        """Build the account -> group -> topic tree from active Telegram file sources."""
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT a.id AS account_id, COALESCE(a.name, '账号 ' || a.id::TEXT) AS account_name,
                           ts.telegram_chat_id AS chat_id,
                           COALESCE(ts.name, '群组 ' || ts.telegram_chat_id::TEXT) AS chat_name,
                           f.topic_id, MAX(f.topic_name) AS topic_name
                    FROM telegram_sources ts
                    JOIN accounts a ON a.id=ts.account_id
                    JOIN files f ON f.account_id=ts.account_id AND f.telegram_chat_id=ts.telegram_chat_id
                    JOIN resources r ON r.id=f.resource_id
                    WHERE ts.enabled=TRUE AND f.is_available=TRUE AND f.status='active' AND r.status='active'
                    GROUP BY a.id, a.name, ts.telegram_chat_id, ts.name, f.topic_id
                    ORDER BY a.id, ts.name, ts.telegram_chat_id, f.topic_id NULLS FIRST
                """)
                rows = cursor.fetchall()
        accounts = {}
        for row in rows:
            aid, cid, tid = row["account_id"], row["chat_id"], row["topic_id"]
            if aid not in accounts:
                accounts[aid] = {"key": f"account:{aid}", "title": row["account_name"], "account_id": aid, "children": [], "_groups": {}}
            account = accounts[aid]
            if cid not in account["_groups"]:
                group = {"key": f"group:{aid}:{cid}", "title": row["chat_name"], "account_id": aid, "chat_id": cid, "children": [], "_topics": set()}
                account["_groups"][cid] = group
                account["children"].append(group)
            group = account["_groups"][cid]
            if tid is not None and tid not in group["_topics"]:
                group["_topics"].add(tid)
                group["children"].append({"key": f"topic:{aid}:{cid}:{tid}", "title": row["topic_name"] or f"话题 {tid}", "account_id": aid, "chat_id": cid, "topic_id": tid, "isLeaf": True})
        result = list(accounts.values())
        for account in result:
            account.pop("_groups", None)
            for group in account["children"]:
                group.pop("_topics", None)
                if not group["children"]: group["isLeaf"] = True
        return result

    def get_resource(self, resource_id):
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT r.id, r.content_hash, r.filename, r.size, r.mime_type, r.status,
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

    # Manual resource categorization is disabled for now; keep the implementation for future reactivation.
    # def set_categories(self, resource_id, category_ids):
    #     with transaction() as conn:
    #         with conn.cursor() as cursor:
    #             cursor.execute("SELECT id FROM resources WHERE id=%s", (resource_id,))
    #             if not cursor.fetchone():
    #                 return None
    #             if category_ids:
    #                 cursor.execute("SELECT id FROM categories WHERE id = ANY(%s)", (category_ids,))
    #                 found = {row["id"] for row in cursor.fetchall()}
    #                 missing = set(category_ids) - found
    #                 if missing:
    #                     raise ValueError("category not found")
    #             cursor.execute("DELETE FROM resource_categories WHERE resource_id=%s", (resource_id,))
    #             if category_ids:
    #                 cursor.executemany(
    #                     "INSERT INTO resource_categories(resource_id, category_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
    #                     [(resource_id, category_id) for category_id in category_ids],
    #                 )
    #             cursor.execute("""
    #                 SELECT r.id, r.filename,
    #                        COALESCE(array_agg(DISTINCT c.id) FILTER (WHERE c.id IS NOT NULL), '{}') AS category_ids
    #                 FROM resources r
    #                 LEFT JOIN resource_categories rc ON rc.resource_id=r.id
    #                 LEFT JOIN categories c ON c.id=rc.category_id
    #                 WHERE r.id=%s GROUP BY r.id
    #             """, (resource_id,))
    #             return cursor.fetchone()
