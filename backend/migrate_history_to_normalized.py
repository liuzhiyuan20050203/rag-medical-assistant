import json
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def get_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "rag_medical"),
        charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


def json_dumps(data):
    return json.dumps(data if data is not None else [], ensure_ascii=False)


def load_old_history(cursor):
    cursor.execute(
        "SELECT payload FROM app_json_store WHERE store_key = %s",
        ("history",)
    )
    row = cursor.fetchone()

    if not row or not row.get("payload"):
        return []

    try:
        return json.loads(row["payload"])
    except Exception as e:
        print("history JSON 解析失败：", e)
        return []


def parse_warning(warning):
    if not isinstance(warning, dict):
        return 0, []

    has_warning = 1 if warning.get("has_warning") else 0
    matched = warning.get("matched", [])

    if isinstance(matched, str):
        matched = [matched]

    return has_warning, matched


def parse_llm(item):
    llm = item.get("llm") or {}

    if not isinstance(llm, dict):
        return 0, "", ""

    return (
        1 if llm.get("used") else 0,
        llm.get("provider", "") or "",
        llm.get("model", "") or ""
    )


def main():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            old_history = load_old_history(cursor)

            if not old_history:
                print("[提示] app_json_store 中没有旧历史记录")
                return

            count = 0

            for item in old_history:
                question = item.get("question", "")
                answer = item.get("answer", "")

                if not question:
                    continue

                has_warning, warning_keywords = parse_warning(item.get("warning"))
                llm_used, llm_provider, llm_model = parse_llm(item)

                cursor.execute(
                    """
                    INSERT INTO chat_history
                    (
                        question,
                        answer,
                        has_warning,
                        warning_keywords,
                        retrieved_docs,
                        llm_used,
                        llm_provider,
                        llm_model,
                        is_error,
                        error_reason,
                        satisfaction,
                        rating,
                        feedback_text,
                        create_time,
                        review_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        question,
                        answer,
                        has_warning,
                        json_dumps(warning_keywords),
                        json_dumps(item.get("retrieved_docs", [])),
                        llm_used,
                        llm_provider,
                        llm_model,
                        1 if item.get("is_error") else 0,
                        item.get("error_reason", "") or "",
                        item.get("satisfaction", "") or "",
                        item.get("rating", 0) or 0,
                        item.get("feedback_text", "") or "",
                        item.get("create_time") or None,
                        item.get("review_time") or None
                    )
                )

                count += 1

        conn.commit()
        print(f"[成功] 旧历史记录已迁移 {count} 条到 chat_history 表")

    except Exception as e:
        conn.rollback()
        print("[失败] 迁移历史记录时出错：", e)

    finally:
        conn.close()


if __name__ == "__main__":
    main()