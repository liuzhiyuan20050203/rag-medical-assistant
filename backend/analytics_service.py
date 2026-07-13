import json
import re
from collections import Counter
from pathlib import Path
from datetime import datetime

from history_service import (
    classify_review_issue,
    get_history_list,
    infer_history_confidence,
    max_doc_score,
)
from knowledge_service import get_all_diseases, get_all_medicines
from safety_check import load_warning_rules
from storage import is_database_enabled, load_json_data, save_json_data


BASE_DIR = Path(__file__).resolve().parent
SEARCH_LOG_FILE = BASE_DIR / "data" / "search_log.json"

STOP_WORDS = {
    "我", "我的", "一下", "怎么办", "怎么", "什么", "可以", "没有", "还有",
    "感觉", "请问", "是不是", "需要", "这个", "那个", "而且", "一直", "有点"
}

CURRENT_GOOD_SCORE = 0.35
CURRENT_LOW_SCORE = 0.25
RECHECK_LIMIT = 12

ACTION_LABELS = {
    "rag_answer": "RAG症状问答",
    "medicine_query": "药品知识库查询",
    "image_assist": "图片/视频辅助",
    "danger_alert": "危险症状提醒",
    "ask_followup": "追问补充信息",
    "empty_input": "等待有效输入",
    "agent_error": "Agent异常",
    "unknown": "未识别",
}

STATUS_LABELS = {
    "unresolved": "当前仍待改进",
    "needs_review": "当前需复核",
    "improved": "当前已改善",
    "historical_only": "历史待复核",
}


def ensure_search_log():
    if is_database_enabled():
        load_json_data(SEARCH_LOG_FILE, list)
        return

    if not SEARCH_LOG_FILE.exists():
        with open(SEARCH_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_search_logs():
    if is_database_enabled():
        return load_json_data(SEARCH_LOG_FILE, list)

    ensure_search_log()
    with open(SEARCH_LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_search_logs(logs):
    if is_database_enabled():
        save_json_data(SEARCH_LOG_FILE, logs)
        return

    with open(SEARCH_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def add_search_log(kind: str, keyword: str, matched_titles=None):
    logs = load_search_logs()
    logs.insert(0, {
        "kind": kind,
        "keyword": keyword,
        "matched_titles": matched_titles or [],
        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_search_logs(logs[:200])


def top_items(counter: Counter, limit=10, key_name="name", value_name="count"):
    return [
        {key_name: name, value_name: count}
        for name, count in counter.most_common(limit)
        if name and count > 0
    ]


def safe_int(value, default=0):
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def get_action(record):
    agent_meta = record.get("agent_meta") or {}
    action = agent_meta.get("action")
    if action:
        return action
    if (record.get("warning") or {}).get("has_warning"):
        return "danger_alert"
    answer = record.get("answer", "")
    if "药品知识库" in answer:
        return "medicine_query"
    return "rag_answer"


def is_bad_feedback(record):
    rating = safe_int(record.get("rating"))
    return bool(record.get("is_error")) or rating in {1, 2}


def summarize_docs(docs, limit=3):
    return [
        {
            "title": doc.get("title", ""),
            "doc_type": doc.get("doc_type", ""),
            "score": round(safe_float(doc.get("score")), 3),
        }
        for doc in (docs or [])[:limit]
    ]


def current_search(question, top_k=3):
    if not (question or "").strip():
        return []
    try:
        from rag_service import search_knowledge
        return search_knowledge(question, top_k=top_k)
    except Exception:
        return []


def current_issue_status(issue, record, current_docs):
    if (record.get("warning") or {}).get("has_warning"):
        return "historical_only"

    current_score = max_doc_score(current_docs)
    has_current_docs = bool(current_docs)
    issue_type = issue.get("issue_type", "")
    suggested_category = issue.get("suggested_category", "")
    has_current_medicine = any(doc.get("doc_type") == "medicine" for doc in current_docs or [])

    if is_bad_feedback(record):
        return "needs_review" if has_current_docs else "unresolved"

    if suggested_category == "medicine" or "药品" in issue_type:
        if has_current_medicine and current_score >= CURRENT_LOW_SCORE:
            return "improved"
        return "unresolved"

    if current_score >= CURRENT_GOOD_SCORE:
        return "improved"
    if has_current_docs and current_score >= CURRENT_LOW_SCORE:
        return "needs_review"
    return "unresolved"


def build_action_distribution(history):
    action_counter = Counter()
    confidence_sum = Counter()
    low_confidence_counter = Counter()
    bad_feedback_counter = Counter()
    no_retrieval_counter = Counter()

    for record in history:
        action = get_action(record)
        confidence = infer_history_confidence(record)
        docs = record.get("retrieved_docs") or []

        action_counter[action] += 1
        confidence_sum[action] += confidence
        if confidence < 0.6:
            low_confidence_counter[action] += 1
        if is_bad_feedback(record):
            bad_feedback_counter[action] += 1
        if not docs and not (record.get("warning") or {}).get("has_warning"):
            no_retrieval_counter[action] += 1

    return [
        {
            "action": action,
            "label": ACTION_LABELS.get(action, action or "未识别"),
            "count": count,
            "average_confidence": round(confidence_sum[action] / count, 2) if count else 0,
            "low_confidence_count": low_confidence_counter[action],
            "bad_feedback_count": bad_feedback_counter[action],
            "no_retrieval_count": no_retrieval_counter[action],
        }
        for action, count in action_counter.most_common()
    ]


def build_rag_quality(history):
    scored_records = [
        record for record in history
        if not (record.get("warning") or {}).get("has_warning")
    ]
    top_scores = [max_doc_score(record.get("retrieved_docs") or []) for record in scored_records]
    retrieved_counts = [len(record.get("retrieved_docs") or []) for record in scored_records]
    no_retrieval_count = sum(1 for count in retrieved_counts if count == 0)
    low_score_count = sum(1 for score in top_scores if 0 < score < CURRENT_GOOD_SCORE)

    return {
        "total_cases": len(scored_records),
        "average_top_score": round(sum(top_scores) / len(top_scores), 3) if top_scores else 0,
        "average_retrieved_count": round(sum(retrieved_counts) / len(retrieved_counts), 2) if retrieved_counts else 0,
        "no_retrieval_count": no_retrieval_count,
        "low_score_count": low_score_count,
    }


def build_quality_diagnosis(history, deep_recheck=False):
    issue_rows = []
    issue_counter = Counter()
    issue_examples = {}
    issue_fix = {}
    rechecked = 0

    candidate_records = []
    for record in history:
        issue = classify_review_issue(record)
        docs = record.get("retrieved_docs") or []
        confidence = infer_history_confidence(record)
        top_score = max_doc_score(docs)
        if (
            issue.get("needs_review")
            or confidence < 0.6
            or (not docs and not (record.get("warning") or {}).get("has_warning"))
            or (0 < top_score < CURRENT_GOOD_SCORE)
        ):
            candidate_records.append((record, issue))

    for record, issue in candidate_records[:RECHECK_LIMIT]:
        question = record.get("question", "")
        existing_docs = record.get("retrieved_docs") or []
        current_docs = current_search(question, top_k=3) if deep_recheck else existing_docs
        current_status = (
            current_issue_status(issue, record, current_docs)
            if deep_recheck
            else "historical_only"
        )
        current_top_score = max_doc_score(current_docs)
        rechecked += 1

        row = {
            **issue,
            "action_label": ACTION_LABELS.get(issue.get("action"), issue.get("action") or "未识别"),
            "status": current_status,
            "status_label": STATUS_LABELS.get(current_status, current_status),
            "current_top_score": round(current_top_score, 3),
            "current_retrieved_count": len(current_docs),
            "current_docs": summarize_docs(current_docs),
        }
        issue_rows.append(row)

        should_count_gap = (
            current_status in {"unresolved", "needs_review"}
            if deep_recheck
            else bool(issue.get("needs_review"))
        )
        if should_count_gap:
            key = (issue.get("keyword") or "待补充条目", issue.get("issue_type") or "待复核")
            issue_counter[key] += 1
            issue_fix[key] = issue.get("suggested_fix", "")
            issue_examples.setdefault(key, [])
            if len(issue_examples[key]) < 3:
                issue_examples[key].append(question)

    if deep_recheck:
        unresolved_rows = [item for item in issue_rows if item.get("status") in {"unresolved", "needs_review"}]
        improved_rows = [item for item in issue_rows if item.get("status") == "improved"]
    else:
        unresolved_rows = [item for item in issue_rows if item.get("needs_review")]
        improved_rows = []
    low_confidence_rows = [
        item for item in issue_rows
        if safe_float(item.get("confidence")) < 0.6 and item.get("status") != "improved"
    ]
    medicine_gap_rows = [
        item for item in unresolved_rows
        if item.get("suggested_category") == "medicine" or "药品" in item.get("issue_type", "")
    ]

    knowledge_gaps = [
        {
            "keyword": keyword,
            "gap_type": issue_type,
            "count": count,
            "examples": issue_examples.get((keyword, issue_type), []),
            "suggested_action": issue_fix.get((keyword, issue_type), ""),
        }
        for (keyword, issue_type), count in issue_counter.most_common(12)
    ]

    return {
        "analysis_mode": "current_recheck" if deep_recheck else "historical_snapshot",
        "quality_overview": {
            "rechecked_count": rechecked,
            "review_count": len(issue_rows),
            "current_unresolved_count": len(unresolved_rows),
            "improved_count": len(improved_rows),
            "low_confidence_count": len(low_confidence_rows),
            "medicine_gap_count": len(medicine_gap_rows),
        },
        "knowledge_gaps": knowledge_gaps,
        "review_suggestions": unresolved_rows[:10],
        "improved_cases": improved_rows[:10],
        "low_confidence_cases": low_confidence_rows[:8],
        "medicine_gap_stats": medicine_gap_rows[:8],
    }


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


def build_analytics(deep_recheck=False):
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
    quality_diagnosis = build_quality_diagnosis(history, deep_recheck=deep_recheck)

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
        ],
        "action_distribution": build_action_distribution(history),
        "rag_quality": build_rag_quality(history),
        **quality_diagnosis,
    }
