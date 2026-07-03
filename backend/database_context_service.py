import re

from knowledge_service import get_all_diseases, get_all_medicines


QUESTION_ALIASES = {
    "发烧": ["发热", "高热", "低热"],
    "喉咙痛": ["咽痛", "咽部不适", "咽炎"],
    "嗓子痛": ["咽痛", "咽部不适", "咽炎"],
    "嗓子疼": ["咽痛", "咽部不适", "咽炎"],
    "咽喉痛": ["咽痛", "咽部不适", "咽炎"],
    "流鼻水": ["流鼻涕", "鼻塞", "普通感冒"],
    "鼻子堵": ["鼻塞", "普通感冒"],
    "拉肚子": ["腹泻", "腹痛", "大便次数增多"],
    "肚子疼": ["腹痛", "胃痛", "上腹痛"],
    "肚子痛": ["腹痛", "胃痛", "上腹痛"],
    "胃不舒服": ["胃痛", "上腹不适", "反酸", "烧心"],
    "皮肤痒": ["皮肤瘙痒", "过敏", "皮肤过敏"],
    "起红疹": ["红疹", "皮疹", "皮肤过敏"],
    "起疹子": ["红疹", "皮疹", "皮肤过敏"],
    "头疼": ["头痛", "头晕"],
    "牙疼": ["牙痛", "牙龈肿痛"],
}

NEGATION_WORDS = ["没有", "无", "未", "不", "否认", "没"]


def compact_text(value, limit=180):
    if isinstance(value, list):
        value = "、".join(str(item) for item in value if item)

    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def has_positive_term(text: str, term: str):
    if not text or not term:
        return False

    start = text.find(term)

    while start >= 0:
        prefix = text[max(0, start - 6):start]
        if not any(word in prefix for word in NEGATION_WORDS):
            return True
        start = text.find(term, start + len(term))

    return False


def expand_question_text(question: str):
    expanded = question or ""

    for keyword, aliases in QUESTION_ALIASES.items():
        if has_positive_term(question, keyword):
            expanded += " " + " ".join(aliases)

        for alias in aliases:
            if has_positive_term(question, alias):
                expanded += " " + keyword

    return expanded


def collect_medical_terms(diseases, medicines):
    terms = set()

    for item in diseases:
        for field in ["name", "category"]:
            value = item.get(field, "")
            if len(value) >= 2:
                terms.add(value)

        for symptom in item.get("symptoms", []):
            if len(symptom) >= 2:
                terms.add(symptom)

    for item in medicines:
        for field in ["name", "type"]:
            value = item.get(field, "")
            if len(value) >= 2:
                terms.add(value)

    for keyword, aliases in QUESTION_ALIASES.items():
        terms.add(keyword)
        terms.update(aliases)

    return sorted(terms, key=len, reverse=True)


def matched_terms(query_text: str, field_text: str, terms, limit=6):
    hits = []

    for term in terms:
        if term in field_text and has_positive_term(query_text, term):
            hits.append(term)

        if len(hits) >= limit:
            break

    return hits


def add_match(matches, field, values):
    values = [value for value in values if value]
    if values:
        matches.append(f"{field}：{'、'.join(values)}")


def score_disease(item, query_text, terms):
    score = 0
    matches = []

    name = item.get("name", "")
    category = item.get("category", "")
    symptoms = item.get("symptoms", [])
    description = item.get("description", "")

    if has_positive_term(query_text, name):
        score += 12
        add_match(matches, "疾病名称", [name])

    if has_positive_term(query_text, category):
        score += 2
        add_match(matches, "疾病类别", [category])

    symptom_hits = [
        symptom for symptom in symptoms
        if has_positive_term(query_text, symptom)
    ]
    if symptom_hits:
        score += min(len(symptom_hits) * 5, 25)
        add_match(matches, "症状", symptom_hits[:6])

    desc_hits = matched_terms(query_text, description, terms, limit=3)
    if desc_hits:
        score += len(desc_hits) * 2
        add_match(matches, "描述", desc_hits)

    care_hits = matched_terms(query_text, item.get("care_advice", ""), terms, limit=2)
    if care_hits:
        score += len(care_hits)
        add_match(matches, "护理建议", care_hits)

    return score, matches


def score_medicine(item, query_text, terms):
    score = 0
    primary_score = 0
    matches = []

    name = item.get("name", "")
    medicine_type = item.get("type", "")
    usage = item.get("usage", "")
    notice = item.get("notice", "")
    contraindication = item.get("contraindication", "")
    side_effect = item.get("side_effect", "")

    if has_positive_term(query_text, name):
        primary_score += 14
        add_match(matches, "药品名称", [name])

    if has_positive_term(query_text, medicine_type):
        primary_score += 4
        add_match(matches, "药品类别", [medicine_type])

    usage_hits = matched_terms(query_text, usage, terms, limit=5)
    if usage_hits:
        primary_score += len(usage_hits) * 4
        add_match(matches, "适用情况", usage_hits)

    notice_hits = matched_terms(query_text, notice, terms, limit=3)
    if notice_hits:
        primary_score += len(notice_hits) * 2
        add_match(matches, "注意事项", notice_hits)

    score += primary_score

    risk_hits = matched_terms(
        query_text,
        f"{contraindication} {side_effect}",
        terms,
        limit=3
    )
    if primary_score > 0 and risk_hits:
        score += len(risk_hits)
        add_match(matches, "禁忌/不良反应", risk_hits)

    if primary_score <= 0:
        return 0, []

    return score, matches


def disease_result(item, score, matches):
    return {
        "doc_type": "disease",
        "title": item.get("name", ""),
        "score": score,
        "matched_fields": matches,
        "raw": item
    }


def medicine_result(item, score, matches):
    return {
        "doc_type": "medicine",
        "title": item.get("name", ""),
        "score": score,
        "matched_fields": matches,
        "raw": item
    }


def search_database_context(question: str, disease_limit=3, medicine_limit=3):
    """
    从结构化疾病/药品数据中做精确和半精确匹配。
    该层会自动走 storage.py：配置 MySQL 时读数据库，未配置时读本地 JSON。
    """
    diseases = get_all_diseases()
    medicines = get_all_medicines()
    query_text = expand_question_text(question or "")
    terms = collect_medical_terms(diseases, medicines)

    disease_matches = []
    for item in diseases:
        score, matches = score_disease(item, query_text, terms)
        if score > 0:
            disease_matches.append(disease_result(item, score, matches))

    medicine_matches = []
    for item in medicines:
        score, matches = score_medicine(item, query_text, terms)
        if score > 0:
            medicine_matches.append(medicine_result(item, score, matches))

    disease_matches.sort(key=lambda item: item["score"], reverse=True)
    medicine_matches.sort(key=lambda item: item["score"], reverse=True)

    return {
        "query": compact_text(question, 240),
        "expanded_query": compact_text(query_text, 320),
        "diseases": disease_matches[:disease_limit],
        "medicines": medicine_matches[:medicine_limit],
        "has_matches": bool(disease_matches or medicine_matches)
    }
