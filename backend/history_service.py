from datetime import datetime

from db import (
    ensure_normalized_schema,
    get_connection,
    parse_time,
    replace_history_relations,
    split_terms,
)


def default_database_context():
    return {
        "diseases": [],
        "medicines": [],
        "has_matches": False
    }


def format_time(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def parse_warning_info(warning):
    if not warning:
        return 0, []

    if isinstance(warning, dict):
        has_warning = 1 if warning.get("has_warning") else 0
        matched = warning.get("matched", [])
        return has_warning, split_terms(matched)

    return 0, []


def parse_llm_info(llm):
    if not llm:
        return 0, "", ""

    if isinstance(llm, dict):
        used = llm.get("used")
        if used is None:
            used = llm.get("success", False)

        return (
            1 if used else 0,
            llm.get("provider", "") or "",
            llm.get("model", "") or ""
        )

    return 0, "", ""


def source_raw_from_db(cursor, source_table, source_id):
    if not source_table or not source_id:
        return {}

    if source_table == "diseases":
        cursor.execute(
            """
            SELECT
                d.id,
                d.name,
                COALESCE(c.name, '') AS category,
                d.description,
                d.care_advice,
                d.medicine_notice,
                d.warning
            FROM diseases d
            LEFT JOIN disease_categories c ON c.id = d.category_id
            WHERE d.id = %s
            LIMIT 1
            """,
            (source_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {}

        cursor.execute(
            """
            SELECT symptom
            FROM disease_symptoms
            WHERE disease_id = %s
            ORDER BY sort_order ASC, id ASC
            """,
            (source_id,),
        )
        row["symptoms"] = [item["symptom"] for item in cursor.fetchall()]
        return row

    if source_table == "medicines":
        cursor.execute(
            """
            SELECT
                m.id,
                m.name,
                COALESCE(t.name, '') AS type,
                m.usage_info AS `usage`,
                m.notice,
                m.contraindication,
                m.side_effect
            FROM medicines m
            LEFT JOIN medicine_types t ON t.id = m.type_id
            WHERE m.id = %s
            LIMIT 1
            """,
            (source_id,),
        )
        return cursor.fetchone() or {}

    return {}


def load_warning_keywords(cursor, history_id):
    cursor.execute(
        """
        SELECT keyword
        FROM chat_history_warning_matches
        WHERE history_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        (history_id,),
    )
    return [row["keyword"] for row in cursor.fetchall()]


def load_retrieved_docs(cursor, history_id):
    cursor.execute(
        """
        SELECT doc_type, source_table, source_id, title, score, content
        FROM chat_history_retrieved_docs
        WHERE history_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        (history_id,),
    )
    docs = []
    for row in cursor.fetchall():
        doc = {
            "title": row.get("title", ""),
            "doc_type": row.get("doc_type", ""),
            "score": row.get("score"),
            "content": row.get("content", "") or "",
        }
        raw = source_raw_from_db(cursor, row.get("source_table"), row.get("source_id"))
        if raw:
            doc["raw"] = raw
        docs.append(doc)
    return docs


def load_database_context(cursor, history_id):
    cursor.execute(
        """
        SELECT query_text, expanded_query, has_matches
        FROM chat_history_contexts
        WHERE history_id = %s
        LIMIT 1
        """,
        (history_id,),
    )
    row = cursor.fetchone()
    if not row:
        return default_database_context()

    context = {
        "query": row.get("query_text", "") or "",
        "expanded_query": row.get("expanded_query", "") or "",
        "diseases": [],
        "medicines": [],
        "has_matches": bool(row.get("has_matches")),
    }

    cursor.execute(
        """
        SELECT id, doc_type, source_table, source_id, title, score
        FROM chat_history_database_matches
        WHERE history_id = %s
        ORDER BY sort_order ASC, id ASC
        """,
        (history_id,),
    )
    matches = cursor.fetchall()

    for match in matches:
        cursor.execute(
            """
            SELECT matched_field
            FROM chat_history_database_match_fields
            WHERE match_id = %s
            ORDER BY sort_order ASC, id ASC
            """,
            (match["id"],),
        )
        result = {
            "doc_type": match.get("doc_type", ""),
            "title": match.get("title", ""),
            "score": match.get("score"),
            "matched_fields": [item["matched_field"] for item in cursor.fetchall()],
            "raw": source_raw_from_db(cursor, match.get("source_table"), match.get("source_id")),
        }

        if result["doc_type"] == "disease":
            context["diseases"].append(result)
        elif result["doc_type"] == "medicine":
            context["medicines"].append(result)

    context["has_matches"] = context["has_matches"] or bool(context["diseases"] or context["medicines"])
    return context


def row_to_record(cursor, row):
    warning_keywords = load_warning_keywords(cursor, row.get("id"))
    retrieved_docs = load_retrieved_docs(cursor, row.get("id"))
    database_context = load_database_context(cursor, row.get("id"))

    return {
        "id": row.get("id"),
        "user_id": row.get("user_id"),
        "question": row.get("question", ""),
        "answer": row.get("answer", ""),
        "warning": {
            "has_warning": bool(row.get("has_warning")),
            "matched": warning_keywords,
            "message": (
                "你描述的症状中包含可能存在较高风险的情况："
                + "、".join(warning_keywords)
                + "。建议你及时就医或咨询专业医生。本系统仅提供健康信息参考，不能替代医生诊断。"
                if row.get("has_warning") and warning_keywords
                else ""
            )
        },
        "retrieved_docs": retrieved_docs,
        "database_context": database_context,
        "llm": {
            "used": bool(row.get("llm_used")),
            "provider": row.get("llm_provider", "") or "",
            "model": row.get("llm_model", "") or "",
            "error": ""
        },
        "is_error": bool(row.get("is_error")),
        "error_reason": row.get("error_reason", "") or "",
        "satisfaction": row.get("satisfaction", "") or "",
        "rating": row.get("rating", 0) or 0,
        "feedback_text": row.get("feedback_text", "") or "",
        "create_time": format_time(row.get("create_time")),
        "review_time": format_time(row.get("review_time"))
    }


def ensure_history_file():
    ensure_normalized_schema()
    return True


def load_history():
    return get_history_list()


def save_history(history_list):
    ensure_normalized_schema()
    with get_connection(autocommit=False) as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM chat_history")

                for item in reversed(history_list or []):
                    warning = item.get("warning") or {}
                    has_warning, warning_keywords = parse_warning_info(warning)
                    llm_used, llm_provider, llm_model = parse_llm_info(item.get("llm"))

                    cursor.execute(
                        """
                        INSERT INTO chat_history
                        (
                            question, answer, has_warning,
                            llm_used, llm_provider, llm_model,
                            is_error, error_reason, satisfaction, rating,
                            feedback_text, create_time, review_time
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            item.get("question", ""),
                            item.get("answer", ""),
                            has_warning,
                            llm_used,
                            llm_provider,
                            llm_model,
                            1 if item.get("is_error") else 0,
                            item.get("error_reason", ""),
                            item.get("satisfaction", ""),
                            item.get("rating", 0),
                            item.get("feedback_text", ""),
                            parse_time(item.get("create_time")) or datetime.now(),
                            parse_time(item.get("review_time")),
                        )
                    )
                    replace_history_relations(
                        cursor,
                        cursor.lastrowid,
                        warning_keywords=warning_keywords,
                        retrieved_docs=item.get("retrieved_docs", []),
                        database_context=item.get("database_context", default_database_context()),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def next_history_id(history_list):
    if not history_list:
        return 1
    return max(item.get("id", 0) for item in history_list) + 1


def add_history_record(
    question,
    answer,
    warning=None,
    retrieved_docs=None,
    llm=None,
    database_context=None
):
    has_warning, warning_keywords = parse_warning_info(warning)
    llm_used, llm_provider, llm_model = parse_llm_info(llm)
    ensure_normalized_schema()

    with get_connection(autocommit=False) as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO chat_history
                    (
                        question,
                        answer,
                        has_warning,
                        llm_used,
                        llm_provider,
                        llm_model,
                        is_error,
                        error_reason,
                        satisfaction,
                        rating,
                        feedback_text
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, 0, '', '', 0, '')
                    """,
                    (
                        question,
                        answer,
                        has_warning,
                        llm_used,
                        llm_provider,
                        llm_model
                    )
                )
                record_id = cursor.lastrowid
                replace_history_relations(
                    cursor,
                    record_id,
                    warning_keywords=warning_keywords,
                    retrieved_docs=retrieved_docs or [],
                    database_context=database_context or default_database_context(),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    return get_history_by_id(record_id)


def get_history_by_id(record_id: int):
    ensure_normalized_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM chat_history
                WHERE id = %s
                LIMIT 1
                """,
                (record_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return row_to_record(cursor, row)


def get_history_list():
    ensure_normalized_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM chat_history
                ORDER BY create_time DESC, id DESC
                LIMIT 50
                """
            )
            rows = cursor.fetchall()
            return [row_to_record(cursor, row) for row in rows]


def clear_history_records():
    ensure_normalized_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM chat_history")

    return True


def update_history_record(record_id: int, fields: dict):
    ensure_normalized_schema()
    allowed_fields = {
        "is_error",
        "error_reason",
        "satisfaction",
        "rating",
        "feedback_text"
    }

    update_fields = {}
    for key, value in (fields or {}).items():
        if key in allowed_fields:
            update_fields[key] = value

    if not update_fields:
        return get_history_by_id(record_id)

    update_fields["review_time"] = datetime.now()
    set_clause = ", ".join([f"`{key}` = %s" for key in update_fields.keys()])
    values = list(update_fields.values())
    values.append(record_id)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE chat_history
                SET {set_clause}
                WHERE id = %s
                """,
                values,
            )

    return get_history_by_id(record_id)


def mark_history_error(record_id: int, reason: str = ""):
    return update_history_record(
        record_id,
        {
            "is_error": True,
            "error_reason": reason or "管理员标记为错误回答",
            "satisfaction": "不满意",
            "rating": 1
        }
    )


def rating_to_satisfaction(rating: int):
    if rating >= 4:
        return "满意"
    if rating == 3:
        return "一般"
    if rating in {1, 2}:
        return "不满意"
    return ""


def set_history_feedback(record_id: int, rating: int, feedback_text: str = ""):
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return None

    if rating < 1 or rating > 5:
        return None

    return update_history_record(
        record_id,
        {
            "rating": rating,
            "feedback_text": (feedback_text or "").strip(),
            "satisfaction": rating_to_satisfaction(rating),
            "is_error": rating <= 2
        }
    )


def set_history_satisfaction(record_id: int, satisfaction: str):
    rating_map = {
        "满意": 5,
        "一般": 3,
        "不满意": 1
    }

    rating = rating_map.get(satisfaction)

    if not rating:
        return None

    return update_history_record(
        record_id,
        {
            "rating": rating,
            "satisfaction": satisfaction,
            "is_error": satisfaction == "不满意"
        }
    )
