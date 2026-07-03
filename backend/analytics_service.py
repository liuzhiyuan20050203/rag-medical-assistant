import re
from collections import Counter
from datetime import datetime

from db import ensure_normalized_schema, get_connection, parse_time
from history_service import get_history_list
from knowledge_service import get_all_diseases, get_all_medicines
from safety_check import load_warning_rules


STOP_WORDS = {
    "我", "我的", "一下", "怎么办", "怎么", "什么", "可以", "没有", "还有",
    "感觉", "请问", "是不是", "需要", "这个", "那个", "而且", "一直", "有点"
}


def ensure_search_log():
    ensure_normalized_schema()


def load_search_logs():
    ensure_normalized_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, kind, keyword, create_time
                FROM search_logs
                ORDER BY create_time DESC, id DESC
                LIMIT 200
                """
            )
            logs = cursor.fetchall()

            if not logs:
                return []

            log_ids = [row["id"] for row in logs]
            placeholders = ", ".join(["%s"] * len(log_ids))
            cursor.execute(
                f"""
                SELECT search_log_id, title
                FROM search_log_matches
                WHERE search_log_id IN ({placeholders})
                ORDER BY search_log_id ASC, sort_order ASC, id ASC
                """,
                log_ids,
            )
            match_rows = cursor.fetchall()

    matches_by_log = {}
    for row in match_rows:
        matches_by_log.setdefault(row["search_log_id"], []).append(row["title"])

    return [
        {
            "kind": row.get("kind", ""),
            "keyword": row.get("keyword", ""),
            "matched_titles": matches_by_log.get(row["id"], []),
            "create_time": parse_date_time(row.get("create_time")),
        }
        for row in logs
    ]


def save_search_logs(logs):
    ensure_normalized_schema()
    with get_connection(autocommit=False) as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM search_logs")
                for item in logs or []:
                    insert_search_log(cursor, item)
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def parse_date_time(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value or "")


def insert_search_log(cursor, item):
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


def add_search_log(kind: str, keyword: str, matched_titles=None):
    ensure_normalized_schema()
    with get_connection(autocommit=False) as conn:
        try:
            with conn.cursor() as cursor:
                insert_search_log(
                    cursor,
                    {
                        "kind": kind,
                        "keyword": keyword,
                        "matched_titles": matched_titles or [],
                        "create_time": datetime.now(),
                    },
                )
                cursor.execute(
                    """
                    DELETE FROM search_logs
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT id
                            FROM search_logs
                            ORDER BY create_time DESC, id DESC
                            LIMIT 200
                        ) recent_logs
                    )
                    """
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def top_items(counter: Counter, limit=10, key_name="name", value_name="count"):
    return [
        {key_name: name, value_name: count}
        for name, count in counter.most_common(limit)
        if name and count > 0
    ]


def parse_date(value: str):
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").strftime("%m-%d")
    except (TypeError, ValueError):
        return "未知"


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
    history = get_history_list()
    diseases = get_all_diseases()
    medicines = get_all_medicines()
    warning_rules = load_warning_rules()
    search_logs = load_search_logs()

    symptom_counter = Counter()
    disease_counter = Counter()
    medicine_counter = Counter()
    risk_counter = Counter({"高风险提醒": 0, "普通咨询": 0, "信息不足": 0})
    satisfaction_counter = Counter({"5星": 0, "4星": 0, "3星": 0, "2星": 0, "1星": 0, "未评价": 0})
    daily_counter = Counter()
    rating_total = 0
    rating_count = 0

    disease_symptoms = []
    for disease in diseases:
        disease_symptoms.extend(disease.get("symptoms", []))

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
        if log.get("kind") == "medicine":
            for title in log.get("matched_titles", []):
                medicine_counter[title] += 1
            if not log.get("matched_titles") and log.get("keyword"):
                medicine_counter[log.get("keyword")] += 1

    error_count = sum(1 for item in history if item.get("is_error"))
    warning_count = sum(1 for item in history if (item.get("warning") or {}).get("has_warning"))
    feedback_count = sum(1 for item in history if item.get("rating") or item.get("satisfaction"))
    average_rating = round(rating_total / rating_count, 1) if rating_count else 0

    return {
        "overview": {
            "total_questions": len(history),
            "warning_count": warning_count,
            "knowledge_count": len(diseases) + len(medicines),
            "disease_count": len(diseases),
            "medicine_count": len(medicines),
            "medicine_search_count": len([log for log in search_logs if log.get("kind") == "medicine"]),
            "error_count": error_count,
            "feedback_count": feedback_count,
            "average_rating": average_rating
        },
        "symptom_stats": top_items(symptom_counter, limit=12),
        "disease_stats": top_items(disease_counter, limit=10),
        "medicine_stats": top_items(medicine_counter, limit=10),
        "risk_distribution": top_items(risk_counter, limit=6),
        "word_cloud": build_word_cloud(history, disease_symptoms, medicines, warning_rules),
        "satisfaction": top_items(satisfaction_counter, limit=4),
        "daily_questions": [
            {"date": date, "count": count}
            for date, count in sorted(daily_counter.items())
        ]
    }
