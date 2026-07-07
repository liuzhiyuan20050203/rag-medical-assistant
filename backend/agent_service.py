import os
import re

from analytics_service import add_search_log
from history_service import add_history_record
from knowledge_service import get_all_medicines, search_medicine
from llm_service import generate_agent_answer, generate_agent_plan, generate_llm_answer
from rag_service import build_simple_answer, search_knowledge
from safety_check import check_warning


INPUT_TYPES = {"text", "voice", "image", "mixed"}
MEDICINE_INTENTS = [
    "药",
    "用药",
    "吃什么",
    "能不能吃",
    "说明书",
    "禁忌",
    "不良反应",
    "副作用",
    "剂量",
    "使用",
    "怎么用",
    "怎么使用",
    "如何使用",
]
MEDICINE_CONTEXT_WORDS = [
    "药名",
    "药品名称",
    "药品",
    "药盒",
    "说明书",
    "胶囊",
    "片剂",
    "颗粒",
    "口服液",
    "OTC",
]
MEDICINE_NAME_HINTS = [
    "片",
    "胶囊",
    "颗粒",
    "口服液",
    "散",
    "丸",
    "膏",
    "滴眼液",
    "喷雾",
    "贴",
    "头孢",
    "西林",
    "霉素",
    "沙星",
    "硝唑",
    "拉唑",
    "替丁",
    "地平",
    "他汀",
    "洛芬",
]
COMMON_MEDICAL_PRODUCTS = [
    "健胃消食片",
    "创可贴",
    "碘伏",
    "酒精棉片",
    "退热贴",
    "感冒灵",
    "连花清瘟",
    "板蓝根",
    "云南白药",
    "红霉素软膏",
    "莫匹罗星软膏",
    "开塞露",
    "蒙脱石散",
    "口服补液盐",
]
SYMPTOM_INTENTS = [
    "疼",
    "痛",
    "咳",
    "发烧",
    "发热",
    "流鼻涕",
    "腹泻",
    "拉肚子",
    "恶心",
    "呕吐",
    "头晕",
    "皮疹",
    "湿疹",
    "瘙痒",
    "红疹",
    "红斑",
    "过敏",
    "怎么办",
]
IMAGE_SYMPTOM_WORDS = [
    "皮肤",
    "红疹",
    "皮疹",
    "湿疹",
    "瘙痒",
    "发红",
    "红斑",
    "丘疹",
    "水疱",
    "脱屑",
    "伤口",
    "肿胀",
    "咽喉",
    "口腔",
    "舌头",
    "眼睛",
]
SYMPTOM_IMAGE_QUESTIONS = [
    "什么症状",
    "什么病",
    "严重吗",
    "怎么办",
    "怎么处理",
    "怎么回事",
    "是不是",
    "看一下",
    "看看",
]
CONTEXT_REFERENCES = [
    "这个药",
    "这种药",
    "该药",
    "它",
    "这个",
    "刚才那个",
    "上面那个",
]
VAGUE_QUESTIONS = {
    "不舒服",
    "我不舒服",
    "难受",
    "我难受",
    "怎么办",
    "帮我看看",
    "看看这个",
    "这个严重吗",
}

ACTION_META = {
    "empty_input": {
        "intent": "unknown",
        "confidence": 0.0,
        "summary": "等待用户补充可分析的输入。",
    },
    "danger_alert": {
        "intent": "danger_alert",
        "confidence": 0.95,
        "summary": "命中危险症状规则，优先给出就医提醒。",
    },
    "ask_followup": {
        "intent": "followup",
        "confidence": 0.72,
        "summary": "当前信息不足，先追问关键症状细节。",
    },
    "medicine_query": {
        "intent": "medicine_query",
        "confidence": 0.86,
        "summary": "识别为药品相关问题，调用药品知识库。",
    },
    "image_assist": {
        "intent": "image_assist",
        "confidence": 0.78,
        "summary": "图片识别结果已转换为文本线索并参与判断。",
    },
    "rag_answer": {
        "intent": "symptom_query",
        "confidence": 0.82,
        "summary": "识别为健康症状问题，调用 RAG 知识库生成回答。",
    },
}


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def env_flag(name, default=False):
    value = os.getenv(name, "")
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_tags(tags):
    if not tags:
        return []

    if isinstance(tags, str):
        return [
            item.strip()
            for item in re.split(r"[，,、;；\s]+", tags)
            if item.strip()
        ]

    if isinstance(tags, list):
        return [
            clean_text(item)
            for item in tags
            if clean_text(item)
        ]

    return []


def normalize_history(history):
    if not isinstance(history, list):
        return []

    normalized = []
    for item in history[-6:]:
        if isinstance(item, dict):
            role = clean_text(item.get("role", "user")) or "user"
            content = clean_text(item.get("content", ""))
            current_topic = clean_text(item.get("current_topic", ""))
            docs = item.get("docs") if isinstance(item.get("docs"), list) else []
        else:
            role = "user"
            content = clean_text(item)
            current_topic = ""
            docs = []

        normalized_docs = [
            {
                "title": clean_text(doc.get("title", "")),
                "doc_type": clean_text(doc.get("doc_type", "")),
            }
            for doc in docs
            if isinstance(doc, dict) and clean_text(doc.get("title", ""))
        ]

        if content or current_topic or normalized_docs:
            normalized.append({
                "role": role,
                "content": content,
                "current_topic": current_topic,
                "docs": normalized_docs,
            })

    return normalized


def build_history_text(history):
    return "。".join(
        item["content"]
        for item in history
        if item.get("content")
    )


def find_context_medicine_keyword(history):
    """
    根据结构化上下文继承“这个药”的指代对象。
    只看 current_topic 和上一轮参考文档标题，避免从回答正文里误抓其它药名。
    """
    for item in reversed(history or []):
        candidates = []
        current_topic = clean_text(item.get("current_topic", ""))
        if current_topic:
            candidates.append(current_topic)

        for doc in item.get("docs", []):
            if doc.get("doc_type") == "medicine" and doc.get("title"):
                candidates.append(doc["title"])

        for candidate in candidates:
            if search_medicine(candidate):
                return candidate

    return ""


def normalize_input(data):
    text = clean_text(
        data.get("text")
        or data.get("question")
        or data.get("transcript")
        or ""
    )
    input_type = clean_text(data.get("input_type") or "text").lower()
    if input_type not in INPUT_TYPES:
        input_type = "text"

    image_summary = clean_text(
        data.get("image_summary")
        or data.get("image_description")
        or data.get("image_text")
        or ""
    )
    image_tags = normalize_tags(data.get("image_tags") or data.get("tags"))
    image_result = data.get("image_result") if isinstance(data.get("image_result"), dict) else {}
    history = normalize_history(data.get("history"))

    image_parts = []
    if image_summary:
        image_parts.append(f"图片识别描述：{image_summary}")
    if image_tags:
        image_parts.append("图片识别标签：" + "、".join(image_tags))

    question_parts = []
    if text:
        question_parts.append(text)
    question_parts.extend(image_parts)

    question = "。".join(question_parts).strip("。")

    return {
        "user_id": data.get("user_id"),
        "text": text,
        "input_type": input_type,
        "image_summary": image_summary,
        "image_tags": image_tags,
        "image_result": image_result,
        "history": history,
        "question": question,
    }


def has_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def image_looks_like_symptom(normalized):
    image_text = "。".join([
        normalized.get("image_summary", ""),
        "、".join(normalized.get("image_tags", [])),
    ])
    return has_any(image_text, IMAGE_SYMPTOM_WORDS)


def asks_about_symptom_image(normalized):
    text = normalized.get("text", "")
    if not text:
        return False

    return has_any(text, SYMPTOM_IMAGE_QUESTIONS) and image_looks_like_symptom(normalized)


def find_medicine_keyword(normalized):
    question = normalized["question"]
    history_text = build_history_text(normalized.get("history", []))
    search_space = "。".join([question, history_text])
    candidates = []

    for medicine in get_all_medicines():
        name = clean_text(medicine.get("name", ""))
        if name and name in question:
            return name

    for name in COMMON_MEDICAL_PRODUCTS:
        if name in question:
            return name

    text = normalized.get("text", "").strip()
    if 2 <= len(text) <= 30 and not has_any(text, SYMPTOM_INTENTS):
        if search_medicine(text):
            return text

    if has_any(question, CONTEXT_REFERENCES):
        context_keyword = find_context_medicine_keyword(normalized.get("history", []))
        if context_keyword:
            return context_keyword

        for medicine in get_all_medicines():
            name = clean_text(medicine.get("name", ""))
            if name and name in history_text:
                return name

    candidates.extend(normalized.get("image_tags", []))

    for tag in candidates:
        result = search_medicine(tag)
        if result:
            return tag

    match = re.search(
        r"(?:药名|药品名称|药品|药盒|说明书|识别为药品|可能是药品|这个药)[：:\s]*([\u4e00-\u9fffA-Za-z0-9\-]{2,20})",
        search_space,
    )
    if match:
        return match.group(1)

    return ""


def infer_health_product_keyword(normalized):
    keyword = find_medicine_keyword(normalized)
    if keyword:
        return keyword

    question = normalized["question"]
    match = re.search(
        r"([\u4e00-\u9fffA-Za-z0-9\-]{2,20})(?:怎么用|怎么使用|如何使用|有什么用|有什么注意|注意事项|说明书)",
        question,
    )
    if match:
        return match.group(1)

    text = normalized.get("text", "")
    if 2 <= len(text) <= 12 and not has_any(text, SYMPTOM_INTENTS):
        return text

    return ""


def looks_like_standalone_medicine_name(keyword):
    keyword = clean_text(keyword)

    if not (2 <= len(keyword) <= 30):
        return False

    if has_any(keyword, SYMPTOM_INTENTS + IMAGE_SYMPTOM_WORDS):
        return False

    return has_any(keyword, MEDICINE_NAME_HINTS)


def is_medicine_query(normalized):
    text = normalized["text"]
    question = normalized["question"]

    if asks_about_symptom_image(normalized):
        return False

    if find_medicine_keyword(normalized):
        return True

    product_keyword = infer_health_product_keyword(normalized)
    if product_keyword and search_medicine(product_keyword):
        return True

    if product_keyword and looks_like_standalone_medicine_name(product_keyword):
        return True

    if product_keyword and has_any(question, MEDICINE_INTENTS + MEDICINE_CONTEXT_WORDS):
        return True

    if has_any(text, MEDICINE_INTENTS):
        return True

    return has_any(question, MEDICINE_INTENTS) and has_any(question, MEDICINE_CONTEXT_WORDS)


def is_information_insufficient(normalized):
    question = normalized["question"]
    text = normalized["text"]

    if normalized["input_type"] == "image" and (normalized["image_summary"] or normalized["image_tags"]):
        return False

    if is_medicine_query(normalized):
        return False

    if text in VAGUE_QUESTIONS:
        return True

    has_symptom = has_any(question, SYMPTOM_INTENTS)
    if has_symptom or image_looks_like_symptom(normalized):
        return False

    if len(question) < 8:
        return True

    return True


def build_followup_questions(normalized):
    question = normalized["question"]

    if is_medicine_query(normalized):
        return [
            "请补充药品名称，或上传更清晰的药盒、说明书识别结果。",
            "你想了解的是适用情况、禁忌人群，还是不良反应？",
            "是否有过敏史、基础疾病，或正在使用其他药物？",
        ]

    questions = [
        "主要不舒服的部位和症状是什么？",
        "症状大概持续多久了，是否正在加重？",
        "有没有胸痛、呼吸困难、高热不退、意识模糊等危险表现？",
    ]

    if "咳" in question or "喉" in question:
        questions = [
            "咳嗽大概持续多久了？是否有痰、发热或咽痛？",
            "有没有胸痛、呼吸困难、咳血等危险表现？",
            "是否有基础疾病，或近期接触过感冒、流感患者？",
        ]
    elif "腹" in question or "肚" in question or "拉" in question:
        questions = [
            "腹痛或腹泻持续多久了？每天大概几次？",
            "有没有呕血、黑便、严重腹痛、明显脱水或持续高热？",
            "近期是否吃过不洁食物，或正在服用其他药物？",
        ]
    elif "皮" in question or "疹" in question or "痒" in question:
        questions = [
            "皮疹出现多久了？范围是否扩大，是否伴随明显瘙痒或疼痛？",
            "有没有面唇肿胀、呼吸困难、发热等危险表现？",
            "近期是否接触新食物、药物、护肤品或过敏原？",
        ]

    return questions


def build_trace(action, used_tools, reason, intent=None, confidence=None):
    meta = ACTION_META.get(action, {})
    intent = intent or meta.get("intent", "unknown")
    confidence = meta.get("confidence", 0.0) if confidence is None else confidence

    return {
        "action": action,
        "intent": intent,
        "confidence": confidence,
        "summary": meta.get("summary", reason),
        "used_tools": used_tools,
        "reason": reason,
        "steps": [
            {
                "name": tool,
                "status": "used",
            }
            for tool in used_tools
        ],
    }


def finalize_agent_response(response):
    action = response.get("action", "unknown")
    meta = ACTION_META.get(action, {})
    intent = response.get("intent") or meta.get("intent", "unknown")
    confidence = response.get("confidence")
    trace = response.get("agent_trace") or {}

    if confidence is None:
        confidence = trace.get("confidence", meta.get("confidence", 0.0))

    response["intent"] = intent
    response["confidence"] = confidence

    trace.setdefault("action", action)
    trace.setdefault("intent", intent)
    trace.setdefault("confidence", confidence)
    trace.setdefault("summary", meta.get("summary", trace.get("reason", "")))
    trace.setdefault("used_tools", [])
    trace.setdefault(
        "steps",
        [
            {
                "name": tool,
                "status": "used",
            }
            for tool in trace.get("used_tools", [])
        ],
    )
    response["agent_trace"] = trace

    return response


def build_medicine_answer(keyword, medicines):
    if not medicines:
        return (
            f"暂未在药品知识库中查询到“{keyword}”的明确记录。\n\n"
            "建议核对药品名称或上传更清晰的药盒、说明书识别结果。"
            "不要仅凭图片或简称自行判断药品用途，也不要自行调整用药剂量。\n\n"
            "本系统仅提供健康信息参考，不能替代医生诊断或药师指导。"
        )

    lines = [f"已在药品知识库中查询到与“{keyword}”相关的信息："]
    for index, item in enumerate(medicines[:3], start=1):
        lines.extend([
            "",
            f"{index}. {item.get('name', '')}",
            f"药品类别：{item.get('type', '')}",
            f"适用情况：{item.get('usage', '')}",
            f"注意事项：{item.get('notice', '')}",
            f"禁忌人群：{item.get('contraindication', '')}",
            f"不良反应：{item.get('side_effect', '')}",
        ])

    lines.append("")
    lines.append("安全提示：请按药品说明书或医生、药师指导使用，不要自行叠加同类药物或调整剂量。本系统仅提供健康信息参考，不能替代医生诊断或药师指导。")
    return "\n".join(lines)


def docs_from_medicines(medicines):
    docs = []
    for item in medicines[:3]:
        content = (
            f"药品名称：{item.get('name', '')}\n"
            f"药品类别：{item.get('type', '')}\n"
            f"适用情况：{item.get('usage', '')}\n"
            f"注意事项：{item.get('notice', '')}\n"
            f"禁忌人群：{item.get('contraindication', '')}\n"
            f"不良反应：{item.get('side_effect', '')}"
        )
        docs.append({
            "title": item.get("name", ""),
            "doc_type": "medicine",
            "score": 1.0,
            "content": content,
            "raw": item,
        })
    return docs


def run_rag_answer(question):
    retrieved_docs = search_knowledge(question, top_k=3)
    fallback_answer = build_simple_answer(question, retrieved_docs)
    llm_result = generate_llm_answer(question, retrieved_docs)
    answer = llm_result["answer"] if llm_result.get("success") else fallback_answer

    return answer, retrieved_docs, llm_result


def should_skip_final_llm(normalized):
    if env_flag("AGENT_FAST_MODE", False):
        return True

    if normalized.get("image_summary") and env_flag("AGENT_FAST_IMAGE_MODE", False):
        return True

    return False


def max_doc_score(retrieved_docs):
    scores = [
        float(doc.get("score", 0) or 0)
        for doc in (retrieved_docs or [])
    ]
    return max(scores) if scores else 0.0


def medicine_confidence(keyword, medicines):
    if medicines:
        exact_match = any(clean_text(item.get("name", "")) == keyword for item in medicines)
        return 0.94 if exact_match else 0.82

    if keyword:
        return 0.46

    return 0.25


def rag_confidence(retrieved_docs, has_image=False):
    score = max_doc_score(retrieved_docs)
    if score >= 0.45:
        return 0.88
    if score >= 0.25:
        return 0.72 if not has_image else 0.76
    if score > 0:
        return 0.55
    return 0.32


def low_confidence_notice(action, confidence):
    if confidence >= 0.6:
        return ""

    if action == "medicine_query":
        return (
            "\n\n补充说明：当前知识库没有查到足够明确的药品记录，"
            "回答仅能作为一般健康信息参考。建议核对药品包装、说明书，或咨询医生、药师。"
        )

    return (
        "\n\n补充说明：当前知识库匹配度较低，回答可能不够完整。"
        "建议补充更具体的症状、持续时间、部位和图片信息，必要时及时就医。"
        )


def clamp_score(value):
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    return round(max(0.0, min(score, 1.0)), 2)


def reliability_level(score):
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "medium"
    if score >= 0.4:
        return "low"
    return "insufficient"


def reliability_label(level):
    return {
        "high": "资料匹配充分",
        "medium": "资料匹配一般",
        "low": "依据偏弱",
        "insufficient": "依据不足",
    }.get(level, "待评估")


def reliability_message(level, is_danger=False):
    if is_danger:
        return "已命中危险信号规则，请优先关注安全提醒，必要时及时就医。"
    return {
        "high": "已找到较明确的知识库依据，但医疗建议仍需结合个人情况判断。",
        "medium": "已找到部分参考依据，建议补充年龄、症状持续时间、用药史等信息以提高判断质量。",
        "low": "当前问题或知识库匹配不够充分，回答只能作为一般健康信息参考。",
        "insufficient": "当前依据不足，不建议仅凭本次回答做医疗或用药决定。",
    }.get(level, "本次回答仅供健康信息参考。")


def text_terms(text):
    text = clean_text(text).lower()
    terms = set(re.findall(r"[\u4e00-\u9fff]{2,}|[a-z0-9]{2,}", text))
    for index in range(max(len(text) - 1, 0)):
        pair = text[index:index + 2]
        if re.fullmatch(r"[\u4e00-\u9fff]{2}", pair):
            terms.add(pair)
    return {item for item in terms if item not in {"这个", "那个", "什么", "怎么", "是否", "可以", "建议"}}


def overlap_score(left, right):
    left_terms = text_terms(left)
    if not left_terms:
        return 0.0
    right_terms = text_terms(right)
    if not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms)


def docs_text(retrieved_docs):
    return "\n".join(
        clean_text(doc.get("content", "")) + " " + clean_text(doc.get("title", ""))
        for doc in (retrieved_docs or [])
        if isinstance(doc, dict)
    )


def retrieval_reliability(retrieved_docs, action):
    if action == "danger_alert":
        return 0.95
    if action == "ask_followup":
        return 0.45
    if action == "medicine_query" and retrieved_docs:
        return 0.95
    score = max_doc_score(retrieved_docs)
    if score >= 0.45:
        return 0.9
    if score >= 0.25:
        return 0.72
    if score > 0:
        return 0.48
    return 0.18


def faithfulness_reliability(answer, retrieved_docs, action):
    if action == "danger_alert":
        return 0.9
    if action == "ask_followup":
        return 0.65
    if not retrieved_docs:
        return 0.35
    support = overlap_score(answer, docs_text(retrieved_docs))
    if any(doc.get("doc_type") == "medicine" for doc in retrieved_docs):
        return max(0.65, min(0.95, 0.6 + support * 0.35))
    return min(0.92, 0.42 + support * 0.58)


def relevance_reliability(question, answer, plan, retrieved_docs):
    topic = clean_text((plan or {}).get("current_topic", ""))
    if topic and topic in answer:
        return 0.9
    doc_titles = " ".join(clean_text(doc.get("title", "")) for doc in (retrieved_docs or []))
    if topic and topic and topic not in doc_titles and doc_titles:
        return 0.45
    score = overlap_score(question, answer)
    return min(0.92, max(0.35, 0.45 + score * 0.5))


def input_completeness_reliability(normalized, action):
    text = normalized.get("text") or normalized.get("question", "")
    score = 0.25
    if len(text) >= 6:
        score += 0.15
    if len(text) >= 18:
        score += 0.15
    if normalized.get("image_summary"):
        score += 0.15
    if normalized.get("image_tags"):
        score += 0.1
    if has_any(text, ["多久", "天", "小时", "发热", "疼", "痛", "痒", "年龄", "用药", "禁忌", "剂量"]):
        score += 0.15
    if action == "medicine_query" and find_medicine_keyword(normalized):
        score += 0.2
    if action == "ask_followup":
        score = min(score, 0.45)
    return score


def consistency_reliability(answer, plan, retrieved_docs):
    topic = clean_text((plan or {}).get("current_topic", ""))
    if not topic:
        return 0.75
    doc_titles = " ".join(clean_text(doc.get("title", "")) for doc in (retrieved_docs or []))
    if doc_titles and topic not in doc_titles and not any(title in topic for title in doc_titles.split()):
        return 0.45
    if topic in answer:
        return 0.88
    return 0.68


def source_authority_reliability(retrieved_docs, action):
    if action == "danger_alert":
        return 0.9
    if not retrieved_docs:
        return 0.3
    if any(doc.get("doc_type") == "medicine" for doc in retrieved_docs):
        return 0.92
    if any(doc.get("doc_type") in {"disease", "warning_rule"} for doc in retrieved_docs):
        return 0.82
    return 0.65


def build_reliability_report(action, normalized, answer, retrieved_docs=None, plan=None, warning=None):
    retrieved_docs = retrieved_docs or []
    warning = warning or {}
    components = {
        "knowledge_match": clamp_score(retrieval_reliability(retrieved_docs, action)),
        "faithfulness": clamp_score(faithfulness_reliability(answer, retrieved_docs, action)),
        "answer_relevance": clamp_score(relevance_reliability(normalized.get("question", ""), answer, plan, retrieved_docs)),
        "input_completeness": clamp_score(input_completeness_reliability(normalized, action)),
        "consistency": clamp_score(consistency_reliability(answer, plan, retrieved_docs)),
        "source_authority": clamp_score(source_authority_reliability(retrieved_docs, action)),
    }
    weights = {
        "knowledge_match": 0.30,
        "faithfulness": 0.25,
        "answer_relevance": 0.15,
        "input_completeness": 0.10,
        "consistency": 0.10,
        "source_authority": 0.10,
    }
    final_score = clamp_score(sum(components[key] * weight for key, weight in weights.items()))
    level = reliability_level(final_score)
    safety_level = "high" if warning.get("has_warning") else ("medium" if action in {"image_assist", "rag_answer"} else "low")
    return {
        "final_score": final_score,
        "level": level,
        "label": reliability_label(level),
        "message": reliability_message(level, is_danger=bool(warning.get("has_warning"))),
        "safety_level": safety_level,
        "components": components,
        "weights": weights,
        "method": "本地综合评分：RAG检索匹配、回答支撑度、问题相关度、输入完整度、多轮一致性和来源权威度加权得到；不是模型概率。",
    }


def apply_reliability(response, normalized, answer, retrieved_docs=None, plan=None, warning=None):
    reliability = build_reliability_report(
        response.get("action", "unknown"),
        normalized,
        answer,
        retrieved_docs=retrieved_docs,
        plan=plan,
        warning=warning,
    )
    response["reliability"] = reliability
    response["confidence"] = reliability["final_score"]
    trace = response.get("agent_trace") or {}
    trace["reliability"] = reliability
    trace["confidence"] = reliability["final_score"]
    response["agent_trace"] = trace
    return response


def rule_based_plan(normalized):
    if asks_about_symptom_image(normalized):
        return {
            "action": "rag_answer",
            "intent": "symptom_image",
            "confidence": 0.82,
            "reason": "规则识别为症状图片咨询，先基于RAG给出可见线索和就医建议。",
            "search_query": normalized["question"],
            "followup_questions": build_followup_questions(normalized),
            "current_topic": "症状图片",
        }

    if is_information_insufficient(normalized):
        return {
            "action": "ask_followup",
            "intent": "followup",
            "confidence": 0.72,
            "reason": "规则判断当前信息不足，需要先追问。",
            "search_query": normalized["question"],
            "followup_questions": build_followup_questions(normalized),
            "current_topic": "",
        }

    if is_medicine_query(normalized):
        keyword = infer_health_product_keyword(normalized) or normalized["text"] or normalized["question"]
        return {
            "action": "medicine_query",
            "intent": "medicine_query",
            "confidence": 0.86,
            "reason": "规则识别为药品相关问题。",
            "search_query": keyword,
            "followup_questions": [],
            "current_topic": keyword,
        }

    return {
        "action": "rag_answer",
        "intent": "symptom_image" if normalized["image_summary"] else "symptom_query",
        "confidence": 0.82,
        "reason": "规则识别为症状或健康问题，进入RAG问答。",
        "search_query": normalized["question"],
        "followup_questions": [],
        "current_topic": "",
    }


def can_skip_llm_planner(normalized):
    if is_information_insufficient(normalized):
        return True

    if asks_about_symptom_image(normalized):
        return True

    if find_medicine_keyword(normalized):
        return True

    text = normalized.get("text", "")
    if normalized.get("image_summary") and text:
        return True

    return False


def get_agent_plan(normalized):
    if can_skip_llm_planner(normalized):
        plan = rule_based_plan(normalized)
        plan["_source"] = "rule_planner_fast_path"
        plan["_llm"] = {
            "used": False,
            "provider": "",
            "model": "",
            "error": "命中确定性规则，跳过大模型Planner以提升响应速度。",
        }
        return plan

    llm_plan = generate_agent_plan(normalized)
    if llm_plan.get("success") and llm_plan.get("plan"):
        plan = llm_plan["plan"]
        if asks_about_symptom_image(normalized) and plan.get("action") in {"medicine_query", "ask_followup"}:
            plan["action"] = "rag_answer"
            plan["intent"] = "symptom_image"
            plan["reason"] = f"{plan.get('reason', '')}；规则校正：当前是症状图片咨询，应先基于RAG给出可见线索和就医建议，再提出追问。".strip("；")
            plan["search_query"] = normalized["question"]
            plan["confidence"] = min(float(plan.get("confidence", 0.7)), 0.82)
        plan["_source"] = "llm_planner"
        plan["_llm"] = {
            "used": True,
            "provider": llm_plan.get("provider", ""),
            "model": llm_plan.get("model", ""),
            "error": "",
        }
        return plan

    plan = rule_based_plan(normalized)
    plan["_source"] = "rule_planner"
    plan["_llm"] = {
        "used": False,
        "provider": llm_plan.get("provider", ""),
        "model": llm_plan.get("model", ""),
        "error": llm_plan.get("error", ""),
    }
    return plan


def build_agent_trace_from_plan(action, used_tools, plan, fallback_reason):
    source = plan.get("_source", "rule_planner")
    reason = plan.get("reason") or fallback_reason
    summary = (
        "大模型Planner完成意图判断，Agent按规划调用工具。"
        if source == "llm_planner"
        else ACTION_META.get(action, {}).get("summary", fallback_reason)
    )
    trace = build_trace(
        action,
        used_tools,
        reason,
        intent=plan.get("intent"),
        confidence=plan.get("confidence"),
    )
    trace["summary"] = summary
    trace["planner"] = {
        "source": source,
        "reason": reason,
        "search_query": plan.get("search_query", ""),
        "current_topic": plan.get("current_topic", ""),
        "llm": plan.get("_llm", {}),
    }
    return trace


def build_history_agent_meta(action, used_tools, plan=None, retrieved_docs=None, extra=None):
    plan = plan or {}
    meta = ACTION_META.get(action, {})

    return {
        "action": action,
        "intent": plan.get("intent") or meta.get("intent", "unknown"),
        "confidence": plan.get("confidence", meta.get("confidence", 0.0)),
        "reason": plan.get("reason", ""),
        "planner_source": plan.get("_source", ""),
        "search_query": plan.get("search_query", ""),
        "current_topic": plan.get("current_topic", ""),
        "used_tools": used_tools,
        "retrieved_count": len(retrieved_docs or []),
        "top_score": max_doc_score(retrieved_docs or []),
        **(extra or {}),
    }


def run_agent(data):
    normalized = normalize_input(data or {})
    question = normalized["question"]
    user_id = normalized.get("user_id")
    used_tools = ["normalize_input"]

    if not question:
        answer = "请先输入症状描述、语音转文字结果，或上传图片识别结果。"
        response = {
            "success": False,
            "action": "empty_input",
            "need_followup": True,
            "is_danger": False,
            "question": "",
            "answer": answer,
            "followup_questions": ["请描述主要症状，或提供药品/图片识别结果。"],
            "warning": None,
            "retrieved_docs": [],
            "history_id": None,
            "llm": None,
            "normalized_input": normalized,
            "agent_trace": build_trace("empty_input", used_tools, "没有可用于判断的文本、语音或图片识别内容。"),
        }
        return finalize_agent_response(apply_reliability(response, normalized, answer, retrieved_docs=[]))

    warning_result = check_warning(question)
    used_tools.append("warning_check")

    if warning_result.get("has_warning"):
        answer = warning_result.get("message", "")
        reliability = build_reliability_report(
            "danger_alert",
            normalized,
            answer,
            retrieved_docs=[],
            warning=warning_result,
        )
        record = add_history_record(
            question=question,
            answer=answer,
            warning=warning_result,
            retrieved_docs=[],
            llm=None,
            user_id=user_id,
            agent_meta=build_history_agent_meta(
                "danger_alert",
                used_tools,
                retrieved_docs=[],
                extra={
                    "reason": "命中危险症状规则，优先提醒及时就医。",
                    "reliability": reliability,
                },
            ),
        )

        response = {
            "success": True,
            "action": "danger_alert",
            "need_followup": False,
            "is_danger": True,
            "question": question,
            "answer": answer,
            "followup_questions": [],
            "warning": warning_result,
            "retrieved_docs": [],
            "history_id": record.get("id") if record else None,
            "llm": None,
            "normalized_input": normalized,
            "agent_trace": build_trace("danger_alert", used_tools, "命中危险症状规则，优先提醒及时就医。"),
        }
        return finalize_agent_response(apply_reliability(
            response,
            normalized,
            answer,
            retrieved_docs=[],
            warning=warning_result,
        ))

    plan = get_agent_plan(normalized)
    used_tools.append(plan.get("_source", "rule_planner"))
    planned_action = plan.get("action", "rag_answer")

    if planned_action == "ask_followup":
        followup_questions = plan.get("followup_questions") or build_followup_questions(normalized)
        answer = "为了更准确地判断下一步是否需要调用知识库，请先补充以下信息：\n" + "\n".join(
            f"{index}. {item}"
            for index, item in enumerate(followup_questions, start=1)
        )

        response = {
            "success": True,
            "action": "ask_followup",
            "need_followup": True,
            "is_danger": False,
            "question": question,
            "answer": answer,
            "followup_questions": followup_questions,
            "warning": warning_result,
            "retrieved_docs": [],
            "history_id": None,
            "llm": plan.get("_llm"),
            "normalized_input": normalized,
            "agent_trace": build_agent_trace_from_plan(
                "ask_followup",
                used_tools,
                plan,
                "输入信息不足，Agent 选择先追问而不是直接生成结论。",
            ),
        }
        return finalize_agent_response(apply_reliability(
            response,
            normalized,
            answer,
            retrieved_docs=[],
            plan=plan,
            warning=warning_result,
        ))

    if planned_action == "medicine_query":
        keyword = (
            infer_health_product_keyword(normalized)
            or clean_text(plan.get("search_query", ""))
            or normalized["text"]
            or normalized["question"]
        )
        medicines = search_medicine(keyword)
        used_tools.append("medicine_search")
        add_search_log("medicine", keyword, [item.get("name", "") for item in medicines])
        retrieved_docs = docs_from_medicines(medicines)
        plan["confidence"] = medicine_confidence(keyword, medicines)
        if not medicines:
            plan["reason"] = f"识别到可能的药品或医疗用品“{keyword}”，但药品知识库未命中明确记录。"
        fallback_answer = build_medicine_answer(keyword, medicines)
        answer_llm = {
            "success": False,
            "provider": "",
            "model": "",
            "answer": "",
            "error": "极速模式已跳过最终大模型回答。",
        }
        if not should_skip_final_llm(normalized):
            answer_llm = generate_agent_answer(
                question,
                retrieved_docs,
                answer_type="medicine",
                history=normalized.get("history", []),
            )
        if answer_llm.get("success"):
            used_tools.append("llm_answer")
            answer = answer_llm["answer"]
        else:
            used_tools.append("local_fallback")
            answer = fallback_answer
        answer += low_confidence_notice("medicine_query", plan["confidence"])
        action = "image_assist" if normalized["input_type"] == "image" else "medicine_query"
        reason = "图片识别结果包含药品信息，Agent 调用药品知识库。" if action == "image_assist" else "识别为药品查询，Agent 调用药品知识库。"
        reliability = build_reliability_report(
            action,
            normalized,
            answer,
            retrieved_docs=retrieved_docs,
            plan=plan,
            warning=warning_result,
        )
        plan["confidence"] = reliability["final_score"]

        record = add_history_record(
            question=question,
            answer=answer,
            warning=warning_result,
            retrieved_docs=retrieved_docs,
            llm=answer_llm if answer_llm.get("success") else plan.get("_llm"),
            user_id=user_id,
            agent_meta=build_history_agent_meta(
                action,
                used_tools,
                plan=plan,
                retrieved_docs=retrieved_docs,
                extra={
                    "keyword": keyword,
                    "llm_used": answer_llm.get("success", False),
                    "reliability": reliability,
                },
            ),
        )

        response = {
            "success": True,
            "action": action,
            "need_followup": False,
            "is_danger": False,
            "question": question,
            "answer": answer,
            "followup_questions": [],
            "warning": warning_result,
            "retrieved_docs": retrieved_docs,
            "history_id": record.get("id") if record else None,
            "llm": {
                "used": answer_llm.get("success", False),
                "provider": answer_llm.get("provider", plan.get("_llm", {}).get("provider", "")),
                "model": answer_llm.get("model", plan.get("_llm", {}).get("model", "")),
                "error": answer_llm.get("error", plan.get("_llm", {}).get("error", "")),
                "planner_used": plan.get("_llm", {}).get("used", False),
            },
            "normalized_input": normalized,
            "agent_trace": build_agent_trace_from_plan(action, used_tools, plan, reason),
        }
        return finalize_agent_response(apply_reliability(
            response,
            normalized,
            answer,
            retrieved_docs=retrieved_docs,
            plan=plan,
            warning=warning_result,
        ))

    used_tools.append("rag_search")
    search_query = clean_text(plan.get("search_query", "")) or question
    retrieved_docs = search_knowledge(search_query, top_k=3)
    plan["confidence"] = rag_confidence(retrieved_docs, has_image=bool(normalized["image_summary"]))
    if plan["confidence"] < 0.6:
        plan["reason"] = f"{plan.get('reason', '')}；知识库检索匹配度较低。".strip("；")
    fallback_answer = build_simple_answer(question, retrieved_docs)
    answer_type = "symptom_image" if normalized["image_summary"] else "symptom"
    llm_result = {
        "success": False,
        "provider": "",
        "model": "",
        "answer": "",
        "error": "极速模式已跳过最终大模型回答。",
    }
    if not should_skip_final_llm(normalized):
        llm_result = generate_agent_answer(
            question,
            retrieved_docs,
            answer_type=answer_type,
            history=normalized.get("history", []),
        )
    if llm_result.get("success"):
        used_tools.append("llm_answer")
        answer = llm_result["answer"]
    else:
        used_tools.append("local_fallback")
        answer = fallback_answer
    answer += low_confidence_notice(action="rag_answer", confidence=plan["confidence"])
    action = "image_assist" if normalized["input_type"] == "image" else "rag_answer"
    reason = "图片识别结果被转成文本后进入 RAG 问答。" if action == "image_assist" else "识别为症状或健康问题，Agent 调用 RAG 知识库。"
    reliability = build_reliability_report(
        action,
        normalized,
        answer,
        retrieved_docs=retrieved_docs,
        plan=plan,
        warning=warning_result,
    )
    plan["confidence"] = reliability["final_score"]

    record = add_history_record(
        question=question,
        answer=answer,
        warning=warning_result,
        retrieved_docs=retrieved_docs,
        llm=llm_result if llm_result.get("success") else plan.get("_llm"),
        user_id=user_id,
        agent_meta=build_history_agent_meta(
            action,
            used_tools,
            plan=plan,
            retrieved_docs=retrieved_docs,
            extra={
                "answer_type": answer_type,
                "llm_used": llm_result.get("success", False),
                "reliability": reliability,
            },
        ),
    )

    response = {
        "success": True,
        "action": action,
        "need_followup": False,
        "is_danger": False,
        "question": question,
        "answer": answer,
        "followup_questions": [],
        "warning": warning_result,
        "retrieved_docs": retrieved_docs,
        "history_id": record.get("id") if record else None,
        "llm": {
            "used": llm_result.get("success", False),
            "provider": llm_result.get("provider", ""),
            "model": llm_result.get("model", ""),
            "error": llm_result.get("error", ""),
            "planner_used": plan.get("_llm", {}).get("used", False),
        },
        "normalized_input": normalized,
        "agent_trace": build_agent_trace_from_plan(action, used_tools, plan, reason),
    }
    return finalize_agent_response(apply_reliability(
        response,
        normalized,
        answer,
        retrieved_docs=retrieved_docs,
        plan=plan,
        warning=warning_result,
    ))
