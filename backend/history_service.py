import json
import os
from pathlib import Path
from datetime import datetime

import pymysql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

_DATABASE_CONTEXT_COLUMN_READY = False


def get_connection():
    """
    获取 MySQL 数据库连接。
    """
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "rag_medical"),
        charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def json_dumps(data):
    """
    将 Python 对象安全转换为 JSON 字符串。
    """
    return json.dumps(data if data is not None else [], ensure_ascii=False)


def json_loads(text, default=None):
    """
    将 JSON 字符串安全转换为 Python 对象。
    """
    if default is None:
        default = []

    if not text:
        return default

    try:
        return json.loads(text)
    except Exception:
        return default


def default_database_context():
    return {
        "diseases": [],
        "medicines": [],
        "has_matches": False
    }


def format_time(value):
    """
    格式化时间，兼容前端原来的 create_time 字符串格式。
    """
    if not value:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    return str(value)


def parse_warning_info(warning):
    """
    从 warning 结果中提取是否危险和命中的关键词。
    """
    if not warning:
        return 0, []

    if isinstance(warning, dict):
        has_warning = 1 if warning.get("has_warning") else 0
        matched = warning.get("matched", [])
        if isinstance(matched, str):
            matched = [matched]
        return has_warning, matched

    return 0, []


def parse_llm_info(llm):
    """
    从 llm 结果中提取大模型使用情况。
    """
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


def ensure_database_context_column():
    """
    兼容已有 chat_history 表：缺少 database_context 列时自动补上。
    """
    global _DATABASE_CONTEXT_COLUMN_READY

    if _DATABASE_CONTEXT_COLUMN_READY:
        return

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM chat_history LIKE 'database_context'")
            if not cursor.fetchone():
                cursor.execute(
                    """
                    ALTER TABLE chat_history
                    ADD COLUMN database_context LONGTEXT NULL AFTER retrieved_docs
                    """
                )

    _DATABASE_CONTEXT_COLUMN_READY = True


def row_to_record(row):
    """
    将数据库行转换成前端原来使用的历史记录格式。
    """
    warning_keywords = json_loads(row.get("warning_keywords"), [])
    retrieved_docs = json_loads(row.get("retrieved_docs"), [])
    database_context = json_loads(row.get("database_context"), default_database_context())

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
    """
    兼容旧代码：当前已改为 MySQL，不再需要创建 history.json。
    """
    return True


def load_history():
    """
    兼容旧代码：读取历史记录。
    """
    return get_history_list()


def save_history(history_list):
    """
    兼容旧代码：用传入列表覆盖 chat_history。
    一般情况下不建议主动调用，清空历史请使用 clear_history_records。
    """
    ensure_database_context_column()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM chat_history")

            for item in reversed(history_list or []):
                warning = item.get("warning") or {}
                has_warning, warning_keywords = parse_warning_info(warning)

                cursor.execute(
                    """
                    INSERT INTO chat_history
                    (
                        question, answer, has_warning, warning_keywords,
                        retrieved_docs, database_context,
                        llm_used, llm_provider, llm_model,
                        is_error, error_reason, satisfaction, rating,
                        feedback_text, create_time, review_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        item.get("question", ""),
                        item.get("answer", ""),
                        has_warning,
                        json_dumps(warning_keywords),
                        json_dumps(item.get("retrieved_docs", [])),
                        json_dumps(item.get("database_context", default_database_context())),
                        1 if item.get("llm", {}).get("used") else 0,
                        item.get("llm", {}).get("provider", ""),
                        item.get("llm", {}).get("model", ""),
                        1 if item.get("is_error") else 0,
                        item.get("error_reason", ""),
                        item.get("satisfaction", ""),
                        item.get("rating", 0),
                        item.get("feedback_text", ""),
                        item.get("create_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        item.get("review_time") or None
                    )
                )


def next_history_id(history_list):
    """
    兼容旧代码：MySQL 使用 AUTO_INCREMENT，不再手动生成 ID。
    """
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
    """
    新增一条问答历史记录，写入 MySQL chat_history 表。
    """
    has_warning, warning_keywords = parse_warning_info(warning)
    llm_used, llm_provider, llm_model = parse_llm_info(llm)
    ensure_database_context_column()

    sql = """
        INSERT INTO chat_history
        (
            question,
            answer,
            has_warning,
            warning_keywords,
            retrieved_docs,
            database_context,
            llm_used,
            llm_provider,
            llm_model,
            is_error,
            error_reason,
            satisfaction,
            rating,
            feedback_text
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, '', '', 0, '')
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    question,
                    answer,
                    has_warning,
                    json_dumps(warning_keywords),
                    json_dumps(retrieved_docs or []),
                    json_dumps(database_context or default_database_context()),
                    llm_used,
                    llm_provider,
                    llm_model
                )
            )
            record_id = cursor.lastrowid

    return get_history_by_id(record_id)


def get_history_by_id(record_id: int):
    """
    根据 ID 获取单条历史记录。
    """
    sql = """
        SELECT *
        FROM chat_history
        WHERE id = %s
        LIMIT 1
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (record_id,))
            row = cursor.fetchone()

    if not row:
        return None

    return row_to_record(row)


def get_history_list():
    """
    获取全部历史记录，默认返回最近 50 条。
    """
    sql = """
        SELECT *
        FROM chat_history
        ORDER BY create_time DESC, id DESC
        LIMIT 50
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

    return [row_to_record(row) for row in rows]


def clear_history_records():
    """
    清空历史记录。
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM chat_history")

    return True


def update_history_record(record_id: int, fields: dict):
    """
    更新指定历史记录的审核或反馈字段。
    """
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

    update_fields["review_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    set_clause = ", ".join([f"{key} = %s" for key in update_fields.keys()])
    values = list(update_fields.values())
    values.append(record_id)

    sql = f"""
        UPDATE chat_history
        SET {set_clause}
        WHERE id = %s
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, values)

    return get_history_by_id(record_id)


def mark_history_error(record_id: int, reason: str = ""):
    """
    标记错误回答，供管理员后台和满意度统计使用。
    """
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
    """
    将评分转换为满意度文字。
    """
    if rating >= 4:
        return "满意"
    if rating == 3:
        return "一般"
    if rating in {1, 2}:
        return "不满意"
    return ""


def set_history_feedback(record_id: int, rating: int, feedback_text: str = ""):
    """
    设置用户星级评分和详细评价。
    """
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
    """
    兼容旧版三档满意度反馈。
    """
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
