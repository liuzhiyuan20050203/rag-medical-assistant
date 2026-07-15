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

CURRENT_GOOD_SCORE = 0.35
CURRENT_LOW_SCORE = 0.25
RECHECK_LIMIT = 12
ANALYTICS_HISTORY_LIMIT = 200
QUALITY_ACTIONS = {"rag_answer", "medicine_query", "image_assist", "agent_error", "unknown"}

SYMPTOM_ALIASES = {
    "腹痛": ("肚子疼", "肚子痛"),
    "腹泻": ("拉肚子",),
    "咽痛": ("喉咙痛", "嗓子疼", "嗓子痛"),
    "流涕": ("流鼻涕",),
    "呼吸困难": ("喘不上气", "呼吸不畅"),
}
NEGATION_MARKERS = ("没有", "没出现", "无", "否认", "并未", "不是")
HYPOTHETICAL_MARKERS = ("如果", "假如", "倘若", "万一")
HISTORY_MARKERS = ("上个月", "以前", "过去", "曾经", "有过", "之前")
REFERENCE_MARKERS = ("文章", "说明书", "写着", "写了", "提到", "这句话")
THIRD_PARTY_MARKERS = (
    "我爸", "我妈", "父亲", "母亲", "爸爸", "妈妈", "爷爷", "奶奶",
    "外公", "外婆", "家人", "孩子", "老人", "他", "她",
)
CURRENT_MARKERS = ("现在", "目前", "正在", "今天", "刚才", "突然", "又", "再次", "复发")

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
    "needs_review": "当前需人工复核",
    "improved": "当前召回已改善",
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

    if suggested_category in {"multimodal", "agent"}:
        return "needs_review"

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


def supports_knowledge_recheck(issue):
    """Only knowledge retrieval gaps can be evaluated by rerunning retrieval."""
    return issue.get("suggested_category") in {"disease", "medicine"}


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
        if action in QUALITY_ACTIONS and confidence < 0.6:
            low_confidence_counter[action] += 1
        if is_bad_feedback(record):
            bad_feedback_counter[action] += 1
        if action == "rag_answer" and not docs and not (record.get("warning") or {}).get("has_warning"):
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
        if get_action(record) == "rag_answer"
        and not (record.get("warning") or {}).get("has_warning")
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
        if issue.get("needs_review"):
            candidate_records.append((record, issue))

    for record, issue in candidate_records[:RECHECK_LIMIT]:
        question = record.get("question", "")
        existing_docs = record.get("retrieved_docs") or []
        recheck_applied = deep_recheck and supports_knowledge_recheck(issue)
        current_docs = current_search(question, top_k=3) if recheck_applied else existing_docs
        current_status = (
            current_issue_status(issue, record, current_docs)
            if deep_recheck
            else "historical_only"
        )
        previous_top_score = max_doc_score(existing_docs)
        current_top_score = max_doc_score(current_docs)
        previous_titles = {
            str(doc.get("title") or "").strip()
            for doc in existing_docs
            if str(doc.get("title") or "").strip()
        }
        current_titles = {
            str(doc.get("title") or "").strip()
            for doc in current_docs
            if str(doc.get("title") or "").strip()
        }
        if recheck_applied:
            rechecked += 1

        row = {
            **issue,
            "action_label": ACTION_LABELS.get(issue.get("action"), issue.get("action") or "未识别"),
            "status": current_status,
            "status_label": STATUS_LABELS.get(current_status, current_status),
            "recheck_applied": recheck_applied,
            "previous_top_score": round(previous_top_score, 3),
            "current_top_score": round(current_top_score, 3),
            "score_change": round(current_top_score - previous_top_score, 3),
            "previous_retrieved_count": len(existing_docs),
            "current_retrieved_count": len(current_docs),
            "retrieval_count_change": len(current_docs) - len(existing_docs),
            "previous_docs": summarize_docs(existing_docs),
            "current_docs": summarize_docs(current_docs),
            "added_titles": sorted(current_titles - previous_titles),
            "removed_titles": sorted(previous_titles - current_titles),
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


def record_scope_key(record):
    """Use a session when available and fall back to one legacy history record."""
    session_id = record.get("session_id")
    return f"session:{session_id}" if session_id else f"record:{record.get('id', id(record))}"


def build_symptom_terms(diseases):
    terms = {}
    for disease in diseases:
        for symptom in disease.get("symptoms", []):
            symptom = str(symptom or "").strip()
            if symptom:
                terms.setdefault(symptom, {symptom})

    for canonical, aliases in SYMPTOM_ALIASES.items():
        if canonical in terms:
            terms[canonical].update(aliases)
    return terms


def has_current_symptom_mention(question, term):
    """Accept an affirmed current mention and ignore negated or non-current contexts."""
    separators = "，。！？；,.!?;\n"
    offset = 0
    while True:
        start = question.find(term, offset)
        if start < 0:
            return False

        clause_start = max(question.rfind(mark, 0, start) for mark in separators)
        following = [question.find(mark, start + len(term)) for mark in separators]
        following = [position for position in following if position >= 0]
        clause_end = min(following) if following else len(question)
        clause = question[clause_start + 1:clause_end]
        local_start = start - clause_start - 1
        prefix = clause[:local_start]

        is_current = any(marker in prefix for marker in CURRENT_MARKERS)
        excluded = (
            any(marker in prefix[-8:] for marker in NEGATION_MARKERS)
            or any(marker in prefix for marker in HYPOTHETICAL_MARKERS)
            or any(marker in clause for marker in REFERENCE_MARKERS)
            or (any(marker in prefix for marker in HISTORY_MARKERS) and not is_current)
            or any(marker in prefix for marker in THIRD_PARTY_MARKERS)
        )
        if not excluded:
            return True
        offset = start + len(term)


def normalize_medicine_label(value):
    text = re.sub(r"\s+", "", str(value or "")).lower()
    for suffix in ("肠溶片", "缓释片", "分散片", "胶囊", "颗粒", "口服液", "片"):
        if text.endswith(suffix) and len(text) > len(suffix):
            return text[:-len(suffix)]
    return text


def medicine_topics_for_record(record):
    action = get_action(record)
    if action not in {"medicine_query", "image_assist"}:
        return set()

    medicine_titles = {
        str(doc.get("title", "")).strip()
        for doc in record.get("retrieved_docs") or []
        if doc.get("doc_type") == "medicine" and str(doc.get("title", "")).strip()
    }
    if not medicine_titles:
        return set()

    agent_meta = record.get("agent_meta") or {}
    topic = str(agent_meta.get("current_topic") or agent_meta.get("keyword") or "").strip()
    question = str(record.get("question", ""))
    target_text = topic or question
    normalized_target = normalize_medicine_label(target_text)
    matched = {
        title for title in medicine_titles
        if normalize_medicine_label(title) in normalized_target
        or normalized_target in normalize_medicine_label(title)
    }
    if matched:
        return matched

    # Legacy medicine records may not contain Agent metadata.
    return medicine_titles if action == "medicine_query" and len(medicine_titles) == 1 else set()


def build_demand_counters(history, diseases):
    symptom_counter = Counter()
    disease_counter = Counter()
    medicine_counter = Counter()
    symptom_terms = build_symptom_terms(diseases)
    seen_symptoms = set()
    seen_medicines = set()

    for record in history:
        scope = record_scope_key(record)
        question = str(record.get("question", ""))

        for canonical, variants in symptom_terms.items():
            key = (scope, canonical)
            if key not in seen_symptoms and any(
                has_current_symptom_mention(question, variant) for variant in variants
            ):
                symptom_counter[canonical] += 1
                seen_symptoms.add(key)

        disease_titles = {
            str(doc.get("title", "")).strip()
            for doc in record.get("retrieved_docs") or []
            if doc.get("doc_type") == "disease" and str(doc.get("title", "")).strip()
        }
        disease_counter.update(disease_titles)

        for title in medicine_topics_for_record(record):
            key = (scope, title)
            if key not in seen_medicines:
                medicine_counter[title] += 1
                seen_medicines.add(key)

    return symptom_counter, disease_counter, medicine_counter


def user_question_text(question):
    """Remove OCR and media-analysis text appended by the system."""
    text = str(question or "")
    for marker in ("。图片识别描述：", "。图片识别标签：", "\n图片识别描述：", "\n图片识别标签："):
        text = text.split(marker, 1)[0]
    if text.startswith(("图片识别描述：", "图片识别标签：")):
        return ""
    return text.strip()


def build_word_cloud(history, symptoms, medicines, warning_rules):
    keyword_counter = Counter()
    known_terms = set(symptoms) | {item.get("name", "") for item in medicines} | set(warning_rules)

    for item in history:
        question = user_question_text(item.get("question", ""))

        for term in known_terms:
            if term and term in question:
                keyword_counter[term] += 1

    return [
        {"text": text, "value": count}
        for text, count in keyword_counter.most_common(28)
    ]


def build_analytics(deep_recheck=False):
    history = get_history_list(limit=ANALYTICS_HISTORY_LIMIT)
    diseases = get_all_diseases()
    medicines = get_all_medicines()
    warning_rules = load_warning_rules()

    symptom_counter, disease_counter, medicine_counter = build_demand_counters(history, diseases)
    risk_counter = Counter({"高风险提醒": 0, "普通咨询": 0, "RAG无知识召回": 0})
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

        warning = item.get("warning") or {}
        retrieved_docs = item.get("retrieved_docs") or []

        if warning.get("has_warning"):
            risk_counter["高风险提醒"] += 1
        elif get_action(item) == "rag_answer" and not retrieved_docs:
            risk_counter["RAG无知识召回"] += 1
        else:
            risk_counter["普通咨询"] += 1

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

    error_count = sum(1 for item in history if item.get("is_error"))
    warning_count = sum(1 for item in history if (item.get("warning") or {}).get("has_warning"))
    feedback_count = sum(1 for item in history if item.get("rating") or item.get("satisfaction"))
    average_rating = round(rating_total / rating_count, 1) if rating_count else 0
    quality_diagnosis = build_quality_diagnosis(history, deep_recheck=deep_recheck)
    history_times = [str(item.get("create_time") or "") for item in history if item.get("create_time")]

    return {
        "scope": {
            "history_limit": ANALYTICS_HISTORY_LIMIT,
            "sample_count": len(history),
            "start_time": min(history_times) if history_times else "",
            "end_time": max(history_times) if history_times else "",
        },
        "overview": {
            "total_questions": len(history),
            "warning_count": warning_count,
            "knowledge_count": len(diseases) + len(medicines),
            "disease_count": len(diseases),
            "medicine_count": len(medicines),
            "medicine_search_count": sum(1 for item in history if get_action(item) == "medicine_query"),
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
