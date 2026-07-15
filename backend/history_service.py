import json
import os
from pathlib import Path
from datetime import datetime

import pymysql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

_DATABASE_CONTEXT_COLUMN_READY = False
_REVIEW_COLUMNS_READY = False


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


def split_agent_meta(retrieved_docs):
    """
    从历史检索文档中拆出 Agent 调度元信息。
    元信息只给管理员审核使用，不作为普通 RAG 文档展示。
    """
    visible_docs = []
    agent_meta = {}

    for doc in retrieved_docs or []:
        if isinstance(doc, dict) and doc.get("doc_type") == "_agent_meta":
            agent_meta = doc.get("meta") or doc.get("raw") or {}
        else:
            visible_docs.append(doc)

    return visible_docs, agent_meta


def with_agent_meta(retrieved_docs, agent_meta=None):
    """
    将 Agent 调度信息轻量保存进 retrieved_docs JSON，避免为了审核功能改表结构。
    """
    docs, _old_meta = split_agent_meta(retrieved_docs or [])

    if agent_meta:
        docs.append({
            "title": "Agent 调度信息",
            "doc_type": "_agent_meta",
            "score": 0,
            "content": "",
            "meta": agent_meta,
        })

    return docs


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
    Keep older local chat_history tables compatible with database-backed RAG.
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


def ensure_history_review_columns():
    """
    给旧版 chat_history 表补齐审核工单状态字段。
    """
    global _REVIEW_COLUMNS_READY

    if _REVIEW_COLUMNS_READY:
        return

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM chat_history LIKE 'review_status'")
            review_status_column = cursor.fetchone()
            if not review_status_column:
                cursor.execute(
                    """
                    ALTER TABLE chat_history
                    ADD COLUMN review_status VARCHAR(30) NOT NULL DEFAULT 'auto' AFTER feedback_text
                    """
                )
            elif review_status_column.get("Default") != "auto":
                cursor.execute(
                    """
                    ALTER TABLE chat_history
                    MODIFY COLUMN review_status VARCHAR(30) NOT NULL DEFAULT 'auto'
                    """
                )

            cursor.execute("SHOW COLUMNS FROM chat_history LIKE 'review_note'")
            if not cursor.fetchone():
                cursor.execute(
                    """
                    ALTER TABLE chat_history
                    ADD COLUMN review_note LONGTEXT NULL AFTER review_status
                    """
                )

            cursor.execute("SHOW COLUMNS FROM chat_history LIKE 'review_retest'")
            if not cursor.fetchone():
                cursor.execute(
                    """
                    ALTER TABLE chat_history
                    ADD COLUMN review_retest LONGTEXT NULL AFTER review_note
                    """
                )

            # Older versions defaulted every row to pending. Rows without an
            # actual review action must return to automatic classification.
            cursor.execute(
                """
                UPDATE chat_history
                SET review_status = 'auto'
                WHERE review_status = 'pending'
                  AND (review_note IS NULL OR review_note = '')
                """
            )

    _REVIEW_COLUMNS_READY = True


def row_to_record(row):
    """
    将数据库行转换成前端原来使用的历史记录格式。
    """
    warning_keywords = json_loads(row.get("warning_keywords"), [])
    retrieved_docs = json_loads(row.get("retrieved_docs"), [])
    visible_docs, agent_meta = split_agent_meta(retrieved_docs)
    database_context = json_loads(row.get("database_context"), default_database_context())

    return {
        "id": row.get("id"),
        "session_id": row.get("session_id"),
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
        "retrieved_docs": visible_docs,
        "database_context": database_context,
        "agent_meta": agent_meta,
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
        "review_status": row.get("review_status", "") or "auto",
        "review_note": row.get("review_note", "") or "",
        "review_retest": json_loads(row.get("review_retest"), None),
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
    ensure_history_review_columns()

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
                        feedback_text, review_status, review_note,
                        create_time, review_time
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        item.get("review_status", "auto"),
                        item.get("review_note", ""),
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
    database_context=None,
    agent_meta=None,
    user_id=None
):
    """
    新增一条问答历史记录，写入 MySQL chat_history 表。
    """
    has_warning, warning_keywords = parse_warning_info(warning)
    llm_used, llm_provider, llm_model = parse_llm_info(llm)
    ensure_database_context_column()
    ensure_history_review_columns()

    sql = """
        INSERT INTO chat_history
        (
            user_id,
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
            feedback_text,
            review_status,
            review_note
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, '', '', 0, '', 'auto', '')
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    user_id,
                    question,
                    answer,
                    has_warning,
                    json_dumps(warning_keywords),
                    json_dumps(with_agent_meta(retrieved_docs or [], agent_meta)),
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
    ensure_history_review_columns()

    sql = """
        SELECT
            chat_history.*,
            (
                SELECT ar.session_id
                FROM agent_runs ar
                WHERE ar.history_id = chat_history.id
                ORDER BY ar.id DESC
                LIMIT 1
            ) AS session_id
        FROM chat_history
        WHERE chat_history.id = %s
        LIMIT 1
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (record_id,))
            row = cursor.fetchone()

    if not row:
        return None

    return row_to_record(row)


def get_history_list(limit: int = 50, user_id=None):
    """
    获取全部历史记录，默认返回最近 50 条。
    """
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 200))
    ensure_history_review_columns()

    params = []
    where_clause = ""

    if user_id is not None:
        where_clause = "WHERE user_id = %s"
        params.append(user_id)

    sql = f"""
        SELECT
            chat_history.*,
            (
                SELECT ar.session_id
                FROM agent_runs ar
                WHERE ar.history_id = chat_history.id
                ORDER BY ar.id DESC
                LIMIT 1
            ) AS session_id
        FROM chat_history
        {where_clause}
        ORDER BY chat_history.create_time DESC, chat_history.id DESC
        LIMIT %s
    """
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

    return [row_to_record(row) for row in rows]


def max_doc_score(retrieved_docs):
    scores = []
    for doc in retrieved_docs or []:
        try:
            scores.append(float(doc.get("score", 0) or 0))
        except (TypeError, ValueError, AttributeError):
            continue

    return max(scores) if scores else 0.0


def infer_history_confidence(record):
    agent_meta = record.get("agent_meta") or {}
    confidence = agent_meta.get("confidence")

    try:
        if confidence is not None:
            return round(float(confidence), 2)
    except (TypeError, ValueError):
        pass

    if (record.get("warning") or {}).get("has_warning"):
        return 0.95

    answer = record.get("answer", "")
    if "暂未在药品知识库" in answer or "知识库匹配度较低" in answer:
        return 0.46

    score = max_doc_score(record.get("retrieved_docs") or [])
    if score >= 0.45:
        return 0.88
    if score >= 0.25:
        return 0.72
    if score > 0:
        return 0.55

    return 0.35


def infer_issue_keyword(record):
    question = record.get("question", "")
    answer = record.get("answer", "")

    for text in (answer, question):
        if "“" in text and "”" in text:
            start = text.find("“") + 1
            end = text.find("”", start)
            if end > start:
                return text[start:end].strip()

    cleaned = question.replace("图片识别描述：", " ").replace("图片识别标签：", " ")
    cleaned = cleaned.replace("怎么使用", " ").replace("怎么用", " ").replace("是什么", " ")
    cleaned = cleaned.replace("这是什么症状", " ").replace("怎么办", " ")
    cleaned = cleaned.replace("。", " ").replace("，", " ").strip()
    return cleaned[:24] or "待补充条目"


def classify_review_issue(record):
    agent_meta = record.get("agent_meta") or {}
    retrieved_docs = record.get("retrieved_docs") or []
    answer = record.get("answer", "")
    question = record.get("question", "")
    feedback_text = str(record.get("feedback_text") or "").strip()
    rating = int(record.get("rating") or 0)
    confidence = infer_history_confidence(record)
    action = agent_meta.get("action") or ("medicine_query" if "药品知识库" in answer else "rag_answer")
    intent = agent_meta.get("intent") or ""
    top_score = max_doc_score(retrieved_docs)
    is_bad_feedback = bool(record.get("is_error")) or rating in {1, 2}
    has_warning = bool((record.get("warning") or {}).get("has_warning"))
    reviewable_actions = {"rag_answer", "medicine_query", "image_assist", "agent_error", "unknown"}
    retrieval_actions = {"rag_answer", "medicine_query", "image_assist"}
    low_confidence = action in reviewable_actions and confidence < 0.6
    no_docs = action in retrieval_actions and not retrieved_docs and not has_warning
    explicit_knowledge_gap = (
        "暂未在药品知识库" in answer
        or "知识库匹配度较低" in answer
    )
    image_related = action == "image_assist" or any(
        word in question for word in ["图片识别", "图像", "照片"]
    )
    medicine_related = action in {"medicine_query", "image_assist"} and (
        "药" in question or "药品知识库" in answer or "说明书" in question
    )

    if medicine_related and (no_docs or "暂未在药品知识库" in answer):
        issue_type = "药品库缺失"
        suggested_category = "medicine"
        suggested_fix = "补充或校对药品说明书字段：适用情况、注意事项、禁忌人群、不良反应。"
    elif image_related and (is_bad_feedback or low_confidence):
        issue_type = "图片识别待复核"
        suggested_category = "multimodal"
        suggested_fix = "复核图片识别结果是否提取到了关键可见信息，再决定是否补充疾病知识。"
    elif is_bad_feedback:
        issue_type = "用户差评"
        suggested_category = "agent"
        suggested_fix = "检查 Agent 意图判断、检索结果和回答措辞，必要时补知识库或调整规则。"
    elif action == "agent_error":
        issue_type = "Agent处理异常"
        suggested_category = "agent"
        suggested_fix = "检查 Agent 调度日志和异常信息，修复后使用原问题重新测试。"
    elif medicine_related and low_confidence:
        issue_type = "药品回答低置信"
        suggested_category = "medicine"
        suggested_fix = "核对药品匹配、说明书依据和回答措辞，并使用原问题重新测试。"
    elif low_confidence or no_docs or explicit_knowledge_gap:
        issue_type = "RAG低命中"
        suggested_category = "disease"
        suggested_fix = "补充疾病/症状知识：常见表现、家庭护理、用药注意和需要就医的危险信号。"
    else:
        issue_type = "待人工复核"
        suggested_category = "agent"
        suggested_fix = "该记录有反馈或审核价值，建议管理员快速复核回答质量。"

    needs_review = (
        is_bad_feedback
        or low_confidence
        or no_docs
        or bool(feedback_text)
        or action == "agent_error"
        or explicit_knowledge_gap
    )
    stored_review_status = record.get("review_status") or "auto"
    if stored_review_status == "auto":
        review_status = "pending" if needs_review else "not_required"
    else:
        review_status = stored_review_status
        needs_review = review_status == "pending"

    return {
        "record_id": record.get("id"),
        "question": question,
        "answer": answer,
        "create_time": record.get("create_time", ""),
        "rating": rating,
        "feedback_text": feedback_text,
        "is_error": bool(record.get("is_error")),
        "error_reason": record.get("error_reason", ""),
        "action": action,
        "intent": intent,
        "confidence": confidence,
        "top_score": round(top_score, 3),
        "retrieved_count": len(retrieved_docs),
        "issue_type": issue_type,
        "suggested_category": suggested_category,
        "suggested_fix": suggested_fix,
        "keyword": infer_issue_keyword(record),
        "needs_review": needs_review,
        "review_status": review_status,
        "review_note": record.get("review_note", ""),
        "review_retest": record.get("review_retest"),
        "review_time": record.get("review_time", ""),
        "agent_meta": agent_meta,
    }


def get_review_issue_list(limit: int = 100, only_need_review: bool = False):
    """
    给管理员后台使用的“待补充知识库/错误样本”列表。
    """
    issues = [
        classify_review_issue(record)
        for record in get_history_list(limit=limit)
    ]

    # Normal high-confidence answers are not review tickets. Keep manually
    # processed/ignored tickets so the admin can audit completed work.
    issues = [item for item in issues if item.get("review_status") != "not_required"]

    if only_need_review:
        issues = [item for item in issues if item.get("needs_review")]

    issues.sort(
        key=lambda item: (
            not item.get("needs_review"),
            item.get("confidence", 1),
            -int(item.get("record_id") or 0),
        )
    )
    return issues


def clear_history_records(user_id=None):
    """
    清空历史记录。
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            if user_id is None:
                cursor.execute("DELETE FROM chat_history")
            else:
                cursor.execute("DELETE FROM chat_history WHERE user_id = %s", (user_id,))

    return True


def update_history_record(record_id: int, fields: dict, user_id=None):
    """
    更新指定历史记录的审核或反馈字段。
    """
    allowed_fields = {
        "is_error",
        "error_reason",
        "satisfaction",
        "rating",
        "feedback_text",
        "review_status",
        "review_note",
        "review_retest"
    }

    update_fields = {}
    for key, value in (fields or {}).items():
        if key in allowed_fields:
            update_fields[key] = value

    if not update_fields:
        return get_history_by_id(record_id)

    ensure_history_review_columns()
    update_fields["review_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    set_clause = ", ".join([f"{key} = %s" for key in update_fields.keys()])
    values = list(update_fields.values())
    values.append(record_id)

    user_clause = ""
    if user_id is not None:
        user_clause = "AND user_id = %s"
        values.append(user_id)

    sql = f"""
        UPDATE chat_history
        SET {set_clause}
        WHERE id = %s {user_clause}
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, values)

    record = get_history_by_id(record_id)
    if user_id is not None and record and record.get("user_id") != user_id:
        return None
    return record


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


def set_review_ticket_status(record_id: int, status: str, note: str = ""):
    """
    设置管理员审核工单状态。
    status: pending / processed / ignored
    """
    status = (status or "").strip()
    note = (note or "").strip()
    if status not in {"pending", "processed", "ignored"}:
        return None
    if status in {"processed", "ignored"} and not note:
        return None

    return update_history_record(
        record_id,
        {
            "review_status": status,
            "review_note": note,
        }
    )


def set_review_retest_result(record_id: int, retest: dict):
    """
    保存审核工单的最新复测摘要，不覆盖原始问答。
    """
    if not isinstance(retest, dict):
        return None

    return update_history_record(
        record_id,
        {
            "review_retest": json_dumps(retest),
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


def set_history_feedback(record_id: int, rating: int, feedback_text: str = "", user_id=None):
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
        },
        user_id=user_id
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
