import json
import sys
from pathlib import Path
from datetime import datetime

from db import (
    DATA_DIR,
    ensure_normalized_schema,
    get_connection,
    json_loads,
    parse_time,
    replace_history_relations,
    table_exists,
    upsert_disease_record,
    upsert_medicine_record,
    upsert_warning_rule,
)
from auth_service import default_users


BASE_DIR = Path(__file__).resolve().parent

JSON_FILES = {
    "diseases": ("diseases.json", list),
    "medicines": ("medicines.json", list),
    "warning_rules": ("warning_rules.json", list),
    "history": ("history.json", list),
    "users": ("users.json", list),
    "sessions": ("sessions.json", dict),
    "search_log": ("search_log.json", list),
}


def read_json_file(file_name, default_factory):
    path = DATA_DIR / file_name
    if not path.exists():
        return default_factory()

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_app_json_payload(cursor, key, default_factory):
    if not table_exists(cursor, "app_json_store"):
        return default_factory()

    cursor.execute(
        "SELECT payload FROM app_json_store WHERE store_key = %s",
        (key,),
    )
    row = cursor.fetchone()
    if not row or not row.get("payload"):
        return default_factory()

    return json_loads(row["payload"], default_factory())


def payload_sources(cursor, key):
    file_name, default_factory = JSON_FILES[key]
    return [
        ("local_json", read_json_file(file_name, default_factory)),
        ("app_json_store", load_app_json_payload(cursor, key, default_factory)),
    ]


def seed_diseases(cursor):
    count = 0
    for _source, diseases in payload_sources(cursor, "diseases"):
        for item in diseases or []:
            if upsert_disease_record(cursor, item):
                count += 1
    return count


def seed_medicines(cursor):
    count = 0
    for _source, medicines in payload_sources(cursor, "medicines"):
        for item in medicines or []:
            if upsert_medicine_record(cursor, item):
                count += 1
    return count


def seed_warning_rules(cursor):
    count = 0
    for _source, rules in payload_sources(cursor, "warning_rules"):
        for item in rules or []:
            if upsert_warning_rule(cursor, item):
                count += 1
    return count


def seed_users(cursor):
    count = 0
    sources = payload_sources(cursor, "users")
    if not any(items for _source, items in sources):
        sources = [("default", default_users())]

    for _source, users in sources:
        for item in users or []:
            if not isinstance(item, dict):
                continue
            username = (item.get("username") or "").strip()
            password_hash = item.get("password_hash") or ""
            if not username or not password_hash:
                continue

            cursor.execute(
                """
                INSERT INTO users
                (username, password_hash, role, active, create_time, update_time)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    password_hash = VALUES(password_hash),
                    role = VALUES(role),
                    active = VALUES(active),
                    update_time = VALUES(update_time)
                """,
                (
                    username,
                    password_hash,
                    "admin" if item.get("role") == "admin" else "user",
                    1 if item.get("active", True) else 0,
                    parse_time(item.get("create_time")) or datetime.now(),
                    parse_time(item.get("update_time")) or datetime.now(),
                ),
            )
            count += 1
    return count


def seed_sessions(cursor):
    count = 0
    for _source, sessions in payload_sources(cursor, "sessions"):
        for token, session in (sessions or {}).items():
            username = (session.get("username") or "").strip()
            if not token or not username:
                continue
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if not user:
                continue

            cursor.execute(
                """
                INSERT INTO user_sessions (token, user_id, create_time)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    user_id = VALUES(user_id),
                    create_time = VALUES(create_time)
                """,
                (
                    token,
                    user["id"],
                    parse_time(session.get("create_time")) or datetime.now(),
                ),
            )
            count += 1
    return count


def search_log_exists(cursor, item):
    cursor.execute(
        """
        SELECT id
        FROM search_logs
        WHERE kind = %s
          AND keyword = %s
          AND create_time <=> %s
        LIMIT 1
        """,
        (
            item.get("kind", "") or "",
            item.get("keyword", "") or "",
            parse_time(item.get("create_time")),
        ),
    )
    return cursor.fetchone() is not None


def seed_search_logs(cursor):
    count = 0
    for _source, logs in payload_sources(cursor, "search_log"):
        for item in logs or []:
            if not isinstance(item, dict) or search_log_exists(cursor, item):
                continue
            cursor.execute(
                """
                INSERT INTO search_logs (kind, keyword, create_time)
                VALUES (%s, %s, %s)
                """,
                (
                    item.get("kind", "") or "",
                    item.get("keyword", "") or "",
                    parse_time(item.get("create_time")) or datetime.now(),
                ),
            )
            log_id = cursor.lastrowid
            for index, title in enumerate(item.get("matched_titles", []) or [], start=1):
                cursor.execute(
                    """
                    INSERT INTO search_log_matches (search_log_id, title, sort_order)
                    VALUES (%s, %s, %s)
                    """,
                    (log_id, str(title), index),
                )
            count += 1
    return count


def parse_warning(warning):
    if not isinstance(warning, dict):
        return 0, []

    matched = warning.get("matched", [])
    if isinstance(matched, str):
        matched = [matched]

    return 1 if warning.get("has_warning") else 0, matched


def parse_llm(llm):
    if not isinstance(llm, dict):
        return 0, "", ""

    used = llm.get("used")
    if used is None:
        used = llm.get("success", False)

    return 1 if used else 0, llm.get("provider", "") or "", llm.get("model", "") or ""


def history_exists(cursor, item):
    cursor.execute(
        """
        SELECT id
        FROM chat_history
        WHERE question = %s
          AND answer = %s
          AND create_time <=> %s
        LIMIT 1
        """,
        (
            item.get("question", "") or "",
            item.get("answer", "") or "",
            parse_time(item.get("create_time")),
        ),
    )
    return cursor.fetchone() is not None


def seed_history(cursor):
    inserted = 0
    skipped = 0
    for _source, history in payload_sources(cursor, "history"):
        for item in history or []:
            if not isinstance(item, dict) or not item.get("question"):
                continue

            if history_exists(cursor, item):
                skipped += 1
                continue

            has_warning, warning_keywords = parse_warning(item.get("warning"))
            llm_used, llm_provider, llm_model = parse_llm(item.get("llm"))
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
                    item.get("question", "") or "",
                    item.get("answer", "") or "",
                    has_warning,
                    llm_used,
                    llm_provider,
                    llm_model,
                    1 if item.get("is_error") else 0,
                    item.get("error_reason", "") or "",
                    item.get("satisfaction", "") or "",
                    item.get("rating", 0) or 0,
                    item.get("feedback_text", "") or "",
                    parse_time(item.get("create_time")) or datetime.now(),
                    parse_time(item.get("review_time")),
                ),
            )
            replace_history_relations(
                cursor,
                cursor.lastrowid,
                warning_keywords=warning_keywords,
                retrieved_docs=item.get("retrieved_docs", []),
                database_context=item.get("database_context", {
                    "diseases": [],
                    "medicines": [],
                    "has_matches": False,
                }),
            )
            inserted += 1

    return inserted, skipped


def run_extra_seeders(cursor):
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))

    import seed_expanded_knowledge
    import seed_knowledge_final_addon
    import seed_knowledge_comprehensive_stage

    for module in [
        seed_expanded_knowledge,
        seed_knowledge_final_addon,
        seed_knowledge_comprehensive_stage,
    ]:
        module.upsert_diseases(cursor)
        if hasattr(module, "upsert_medicines"):
            module.upsert_medicines(cursor)
        module.upsert_warning_rules(cursor)


def count_table(cursor, name):
    cursor.execute(f"SELECT COUNT(*) AS total FROM `{name}`")
    return cursor.fetchone()["total"]


def main():
    ensure_normalized_schema(force=True)

    with get_connection(autocommit=False) as conn:
        try:
            with conn.cursor() as cursor:
                users = seed_users(cursor)
                sessions = seed_sessions(cursor)
                diseases = seed_diseases(cursor)
                medicines = seed_medicines(cursor)
                warnings = seed_warning_rules(cursor)
                search_logs = seed_search_logs(cursor)
                history_inserted, history_skipped = seed_history(cursor)
                run_extra_seeders(cursor)

                counts = {
                    "users": count_table(cursor, "users"),
                    "user_sessions": count_table(cursor, "user_sessions"),
                    "disease_categories": count_table(cursor, "disease_categories"),
                    "diseases": count_table(cursor, "diseases"),
                    "disease_symptoms": count_table(cursor, "disease_symptoms"),
                    "medicine_types": count_table(cursor, "medicine_types"),
                    "medicines": count_table(cursor, "medicines"),
                    "warning_rules": count_table(cursor, "warning_rules"),
                    "chat_history": count_table(cursor, "chat_history"),
                    "search_logs": count_table(cursor, "search_logs"),
                }

            conn.commit()
        except Exception:
            conn.rollback()
            raise

    print("[完成] 规范化 MySQL 数据库结构和业务数据已补全")
    print(
        "[迁移] "
        f"users {users} 条，sessions {sessions} 条，"
        f"diseases {diseases} 条，medicines {medicines} 条，"
        f"warning_rules {warnings} 条，search_logs {search_logs} 条，"
        f"history 新增 {history_inserted} 条/跳过 {history_skipped} 条"
    )
    print("[统计] " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    if counts.get("chat_history"):
        print("[提示] 旧历史记录已拆分到 chat_history_* 关联表")
    print("[提示] 如后端已启动，请访问 /api/rag/init 或 /api/admin/vector/rebuild 重建 RAG 向量索引")
    if table_exists_in_current_db("app_json_store"):
        print("[提示] 检测到旧 app_json_store 表；确认数据无误后可手动备份并删除该旧表")


def table_exists_in_current_db(table_name):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            return table_exists(cursor, table_name)


if __name__ == "__main__":
    main()
