import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import pymysql
from dotenv import load_dotenv

from history_service import get_history_list
from knowledge_service import get_all_diseases, get_all_medicines
from safety_check import load_warning_rules


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)


STOP_WORDS = {
    "我", "我的", "一下", "怎么办", "怎么", "什么", "可以", "没有", "还有",
    "感觉", "请问", "是不是", "需要", "这个", "那个", "而且", "一直", "有点"
}


def get_connection():
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


def normalize_matched_titles(matched_titles):
    """
    把命中的标题统一转成字符串存入 search_logs.matched_title。
    例如：
    ["布洛芬", "对乙酰氨基酚"] -> "布洛芬、对乙酰氨基酚"
    """
    if matched_titles is None:
        return ""

    if isinstance(matched_titles, list):
        text = "、".join([str(item).strip() for item in matched_titles if str(item).strip()])
    else:
        text = str(matched_titles).strip()

    # matched_title 通常是 varchar，避免内容过长导致写入失败
    return text[:250]


def infer_matched_type(kind):
    """
    根据日志类型推断命中类型。
    后续 Agent、图片识别接入后可以继续扩展。
    """
    kind = (kind or "").strip()

    if kind == "medicine":
        return "medicine"

    if kind == "symptom":
        return "disease"

    if kind == "rag":
        return "knowledge"

    if kind == "warning":
        return "warning"

    if kind == "agent":
        return "agent"

    if kind == "image":
        return "image"

    return "unknown"


def add_search_log(kind: str, keyword: str, matched_titles=None, user_id=None):
    """
    新增搜索/检索日志。

    说明：
    - 老年用户免登录时 user_id 可以为 None
    - 药品查询、RAG 检索、Agent 判断、图片识别后面都可以复用这个函数
    """
    kind = (kind or "").strip()
    keyword = (keyword or "").strip()
    matched_title = normalize_matched_titles(matched_titles)
    matched_type = infer_matched_type(kind)

    if not kind and not keyword:
        return None

    sql = """
        INSERT INTO search_logs
        (user_id, kind, keyword, matched_title, matched_type)
        VALUES (%s, %s, %s, %s, %s)
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    user_id,
                    kind,
                    keyword,
                    matched_title,
                    matched_type
                )
            )
            log_id = cursor.lastrowid

    return {
        "id": log_id,
        "user_id": user_id,
        "kind": kind,
        "keyword": keyword,
        "matched_title": matched_title,
        "matched_titles": split_matched_titles(matched_title),
        "matched_type": matched_type
    }


def split_matched_titles(matched_title):
    """
    把数据库中的 matched_title 字符串转回列表，兼容原来的统计代码。
    """
    if not matched_title:
        return []

    return [
        item.strip()
        for item in str(matched_title).split("、")
        if item.strip()
    ]


def load_search_logs(limit: int = 500):
    """
    从 MySQL 读取最近的搜索日志。
    """
    sql = """
        SELECT
            id,
            user_id,
            kind,
            keyword,
            matched_title,
            matched_type,
            create_time
        FROM search_logs
        ORDER BY create_time DESC
        LIMIT %s
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (limit,))
            rows = cursor.fetchall()

    logs = []

    for row in rows:
        matched_title = row.get("matched_title") or ""

        logs.append({
            "id": row.get("id"),
            "user_id": row.get("user_id"),
            "kind": row.get("kind") or "",
            "keyword": row.get("keyword") or "",
            "matched_title": matched_title,
            "matched_titles": split_matched_titles(matched_title),
            "matched_type": row.get("matched_type") or "",
            "create_time": row.get("create_time")
        })

    return logs


def top_items(counter: Counter, limit=10, key_name="name", value_name="count"):
    return [
        {key_name: name, value_name: count}
        for name, count in counter.most_common(limit)
        if name and count > 0
    ]


def parse_date(value):
    """
    兼容字符串时间和 datetime 时间。
    """
    if isinstance(value, datetime):
        return value.strftime("%m-%d")

    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S").strftime("%m-%d")
    except (TypeError, ValueError):
        return "未知"


def normalize_symptoms(symptoms):
    """
    兼容 symptoms 是 list 或字符串。
    """
    if symptoms is None:
        return []

    if isinstance(symptoms, list):
        return [str(item).strip() for item in symptoms if str(item).strip()]

    if isinstance(symptoms, str):
        return [
            item.strip()
            for item in re.split(r"[，,、;；\s]+", symptoms)
            if item.strip()
        ]

    return []


def build_word_cloud(history, symptoms, medicines, warning_rules):
    keyword_counter = Counter()
    known_terms = set(symptoms) | {item.get("name", "") for item in medicines} | set(warning_rules)

    for item in history:
        question = item.get("question", "")

        for term in known_terms:
            if term and term in question:
                keyword_counter[term] += 2

        parts = re.split(r"[，。；、！？?,.!;:\s\n\r\t]+", question)
        for part in parts:
            part = re.sub(r"^(我|我的|有点|一直|而且)", "", part).strip()
            if 2 <= len(part) <= 8 and part not in STOP_WORDS:
                keyword_counter[part] += 1

    return [
        {"text": text, "value": count}
        for text, count in keyword_counter.most_common(28)
    ]


def build_analytics():
    """
    构建数据分析结果。

    数据来源：
    - chat_history：完整问答记录
    - search_logs：药品查询、RAG检索、Agent行为等匿名日志
    - diseases / medicines / warning_rules：知识库基础数据
    """
    history = get_history_list()
    diseases = get_all_diseases()
    medicines = get_all_medicines()
    warning_rules = load_warning_rules()
    search_logs = load_search_logs()

    symptom_counter = Counter()
    disease_counter = Counter()
    medicine_counter = Counter()
    search_keyword_counter = Counter()
    risk_counter = Counter({"高风险提醒": 0, "普通咨询": 0, "信息不足": 0})
    satisfaction_counter = Counter({"5星": 0, "4星": 0, "3星": 0, "2星": 0, "1星": 0, "未评价": 0})
    daily_counter = Counter()
    search_daily_counter = Counter()

    rating_total = 0
    rating_count = 0

    disease_symptoms = []
    for disease in diseases:
        disease_symptoms.extend(normalize_symptoms(disease.get("symptoms", [])))

    for item in history:
        question = item.get("question", "")
        daily_counter[parse_date(item.get("create_time"))] += 1

        for symptom in disease_symptoms:
            if symptom and symptom in question:
                symptom_counter[symptom] += 1

        warning = item.get("warning") or {}
        retrieved_docs = item.get("retrieved_docs") or []

        if warning.get("has_warning"):
            risk_counter["高风险提醒"] += 1
        elif retrieved_docs:
            risk_counter["普通咨询"] += 1
        else:
            risk_counter["信息不足"] += 1

        for doc in retrieved_docs:
            if doc.get("doc_type") == "disease":
                disease_counter[doc.get("title", "")] += 1
            elif doc.get("doc_type") == "medicine":
                medicine_counter[doc.get("title", "")] += 1

        rating = item.get("rating") or 0
        if not rating and item.get("satisfaction"):
            rating = {"满意": 5, "一般": 3, "不满意": 1}.get(item.get("satisfaction"), 0)

        try:
            rating = int(rating)
        except (TypeError, ValueError):
            rating = 0

        if 1 <= rating <= 5:
            satisfaction_counter[f"{rating}星"] += 1
            rating_total += rating
            rating_count += 1
        else:
            satisfaction_counter["未评价"] += 1

    for log in search_logs:
        kind = log.get("kind")
        keyword = log.get("keyword", "")
        matched_titles = log.get("matched_titles", [])
        create_time = log.get("create_time")

        search_daily_counter[parse_date(create_time)] += 1

        if keyword:
            search_keyword_counter[keyword] += 1

        if kind == "medicine":
            if matched_titles:
                for title in matched_titles:
                    medicine_counter[title] += 1
            elif keyword:
                medicine_counter[keyword] += 1

        elif kind in {"symptom", "rag"}:
            if matched_titles:
                for title in matched_titles:
                    disease_counter[title] += 1

        elif kind == "warning":
            risk_counter["高风险提醒"] += 1

    error_count = sum(1 for item in history if item.get("is_error"))
    warning_count = sum(1 for item in history if (item.get("warning") or {}).get("has_warning"))
    feedback_count = sum(1 for item in history if item.get("rating") or item.get("satisfaction"))
    average_rating = round(rating_total / rating_count, 1) if rating_count else 0

    medicine_search_count = len([log for log in search_logs if log.get("kind") == "medicine"])
    symptom_search_count = len([log for log in search_logs if log.get("kind") in {"symptom", "rag"}])
    agent_log_count = len([log for log in search_logs if log.get("kind") == "agent"])
    image_log_count = len([log for log in search_logs if log.get("kind") == "image"])

    return {
        "overview": {
            "total_questions": len(history),
            "warning_count": warning_count,
            "knowledge_count": len(diseases) + len(medicines),
            "disease_count": len(diseases),
            "medicine_count": len(medicines),
            "search_log_count": len(search_logs),
            "medicine_search_count": medicine_search_count,
            "symptom_search_count": symptom_search_count,
            "agent_log_count": agent_log_count,
            "image_log_count": image_log_count,
            "error_count": error_count,
            "feedback_count": feedback_count,
            "average_rating": average_rating
        },
        "symptom_stats": top_items(symptom_counter, limit=12),
        "disease_stats": top_items(disease_counter, limit=10),
        "medicine_stats": top_items(medicine_counter, limit=10),
        "search_keyword_stats": top_items(search_keyword_counter, limit=10),
        "risk_distribution": top_items(risk_counter, limit=6),
        "word_cloud": build_word_cloud(history, disease_symptoms, medicines, warning_rules),
        "satisfaction": top_items(satisfaction_counter, limit=6),
        "daily_questions": [
            {"date": date, "count": count}
            for date, count in sorted(daily_counter.items())
        ],
        "daily_searches": [
            {"date": date, "count": count}
            for date, count in sorted(search_daily_counter.items())
        ]
    }