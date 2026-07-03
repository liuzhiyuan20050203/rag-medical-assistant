import re

from analytics_service import add_search_log
from history_service import add_history_record
from llm_service import generate_llm_answer
from rag_service import search_knowledge, build_simple_answer
from safety_check import check_warning


MEDICINE_INTENT_WORDS = {
    "药", "药品", "用药", "吃药", "服药", "吃什么药", "用什么药",
    "能不能吃", "可以吃吗", "怎么吃", "怎么用", "外用", "口服",
    "副作用", "不良反应", "禁忌", "说明书", "药效", "药物",
    "注意事项", "适用情况", "适应症", "禁忌人群",

    "布洛芬", "对乙酰氨基酚", "氯雷他定", "蒙脱石散", "奥美拉唑",
    "藿香正气", "阿莫西林", "头孢", "法莫替丁", "铝碳酸镁",
    "玻璃酸钠", "硝酸咪康唑", "克霉唑", "氢化可的松",
    "维生素B2", "聚维酮碘", "洛索洛芬钠"
}

VAGUE_WORDS = {
    "不舒服", "难受", "帮我看看", "怎么办", "有点难受", "身体不舒服",
    "不太舒服", "不舒服了", "感觉不对", "不对劲", "哪里都不舒服"
}

SYMPTOM_WORDS = {
    # 通用不适
    "疼", "痛", "痒", "肿", "麻", "乏力", "没精神", "难受",

    # 发热呼吸
    "发热", "发烧", "低烧", "高烧", "咳", "咳嗽", "干咳", "有痰",
    "胸闷", "胸痛", "气短", "喘", "喘不上气", "呼吸困难",

    # 鼻咽喉
    "鼻塞", "流鼻涕", "打喷嚏", "喉咙痛", "嗓子疼", "嗓子痛", "咽痛",
    "声音哑", "嗓子哑",

    # 胃肠道
    "胃疼", "胃痛", "胃不舒服", "胃胀", "反酸", "反酸水", "烧心",
    "胸口烧心", "胃里冒酸水", "胃里往上返酸", "腹痛", "肚子疼",
    "肚子痛", "腹泻", "拉肚子", "大便稀", "便秘", "恶心",
    "想吐", "呕吐", "吐了", "没胃口", "吃不下饭",

    # 皮肤
    "红疹", "皮疹", "起疹子", "皮肤红", "皮肤痒", "脱皮", "水泡",
    "瘙痒", "过敏",

    # 眼耳口腔
    "眼睛红", "眼睛干", "眼睛痒", "眼痛", "耳朵疼", "耳朵响",
    "耳鸣", "牙疼", "牙痛", "口腔溃疡", "嘴里烂了", "牙龈出血",

    # 神经肌肉
    "头晕", "头疼", "头痛", "心慌", "心悸", "手抖", "抽筋",
    "手麻", "腿抽筋", "关节疼", "腰疼", "肩膀疼", "脚后跟疼",

    # 出血和危险相关
    "出血", "便血", "黑便", "呕血", "咳血", "嘴歪", "说话不清楚"
}

# 用来增强危险症状识别。
# 因为 safety_check.py 目前是关键词直接匹配，如果用户说口语表达，可能不直接命中 warning_rules。
WARNING_PHRASE_EXPANSION = {
    "胸口疼还出汗": ["胸痛伴出汗", "剧烈胸痛", "胸痛"],
    "胸痛出汗": ["胸痛伴出汗", "剧烈胸痛"],
    "胸口痛到左手": ["胸痛放射左臂", "剧烈胸痛"],
    "胸痛到左胳膊": ["胸痛放射左臂", "剧烈胸痛"],
    "胸口疼到左胳膊": ["胸痛放射左臂", "剧烈胸痛"],
    "喘不上气": ["呼吸困难", "呼吸困难加重"],
    "大口喘不上气": ["呼吸困难", "呼吸困难加重"],
    "嘴唇发紫": ["口唇发紫", "呼吸困难"],
    "说话不清楚": ["言语不清", "口角歪斜"],
    "嘴歪": ["口角歪斜", "言语不清"],
    "一边没力气": ["肢体无力", "言语不清"],
    "突然剧烈头痛": ["突发剧烈头痛", "危险症状"],
    "吐了很多血": ["呕血", "大量呕血"],
    "咳了很多血": ["大量咯血", "咳血"],
    "大便黑": ["黑便", "消化道出血"],
    "血便很多": ["大量便血", "便血"],
    "小便很少": ["小便明显减少", "严重脱水"],
    "尿很少": ["小便明显减少", "严重脱水"],
    "小孩抽搐": ["高热惊厥", "抽搐"],
    "孩子抽搐": ["高热惊厥", "抽搐"],
    "孩子没精神": ["儿童精神萎靡", "儿童精神差"],
    "小孩没精神": ["儿童精神萎靡", "儿童精神差"],
    "怀孕出血": ["孕妇阴道出血", "孕妇不适"],
    "孕妇出血": ["孕妇阴道出血", "孕妇不适"],
    "怀孕肚子疼": ["孕期腹痛", "孕妇腹痛"],
    "孕妇肚子疼": ["孕期腹痛", "孕妇腹痛"],
    "被狗咬了": ["动物咬伤", "动物咬伤出血"],
    "被猫咬了": ["动物咬伤", "动物咬伤出血"],
    "眼睛受伤": ["眼外伤", "眼痛视力下降"],
    "伤口很深": ["深部伤口", "持续出血"]
}


def clean_text(text):
    return re.sub(r"\s+", "", str(text or "").strip())


def expand_warning_text(text):
    """
    将口语危险表达扩展为 warning_rules 中更可能存在的标准关键词。
    这样 check_warning() 不用大改，也能识别更多老年人口语表达。
    """
    text = clean_text(text)
    extra_terms = []

    for phrase, terms in WARNING_PHRASE_EXPANSION.items():
        if phrase in text:
            extra_terms.extend(terms)

    if extra_terms:
        return text + " " + " ".join(extra_terms)

    return text


def classify_intent(text, image_result=None):
    """
    第一版规则意图识别。
    后续可以升级为大模型分类，但现在规则版更稳定、可解释。
    """
    text = clean_text(text)

    if image_result:
        return "image_assisted_check"

    if any(word in text for word in MEDICINE_INTENT_WORDS):
        return "medicine_consult"

    if any(word in text for word in SYMPTOM_WORDS):
        return "symptom_check"

    return "unknown_or_insufficient"


def need_followup(text, intent):
    """
    判断是否需要追问。
    原则：
    - 危险症状不追问，直接提醒就医
    - 药品咨询不强制追问
    - 太短、太模糊的症状描述先追问
    """
    text = clean_text(text)

    if intent in {"medicine_consult", "image_assisted_check"}:
        return False

    if len(text) <= 4:
        return True

    if text in VAGUE_WORDS:
        return True

    if any(word == text for word in VAGUE_WORDS):
        return True

    has_symptom_word = any(word in text for word in SYMPTOM_WORDS)
    if not has_symptom_word:
        return True

    return False


def build_followup_questions(intent):
    if intent == "medicine_consult":
        return [
            "请补充药品名称。",
            "请说明你想了解的是适用情况、副作用、禁忌，还是能否与其他药同用。",
            "如果正在孕期、儿童用药、老人用药或有慢性病，请一并说明。"
        ]

    return [
        "请问主要是哪里不舒服？",
        "症状持续多久了？",
        "是否伴有发热、咳嗽、腹泻、呕吐、胸痛、呼吸困难或皮疹？",
        "症状是突然出现，还是逐渐加重？"
    ]


def build_followup_answer(intent):
    questions = build_followup_questions(intent)
    return (
        "你提供的信息还比较少，暂时不适合直接给出常见病方向判断。\n\n"
        "为了更准确地提供参考，请补充以下信息：\n"
        + "\n".join([f"{index}. {question}" for index, question in enumerate(questions, start=1)])
        + "\n\n本系统仅提供健康信息参考，不能替代医生诊断或药师指导。"
    )


def build_low_confidence_answer():
    return (
        "知识库中暂时没有检索到足够相关的信息。\n\n"
        "建议你换一种方式描述，例如说明具体部位、主要症状、持续时间、是否伴随发热、疼痛、皮疹、腹泻或呼吸不适。"
        "如果症状明显加重，或出现胸痛、呼吸困难、意识异常、持续高热、呕血、黑便等情况，应及时就医。\n\n"
        "本系统仅提供健康信息参考，不能替代医生诊断或药师指导。"
    )


def filter_medicine_docs_for_question(question, retrieved_docs):
    """
    药品咨询场景下，优先保留药品类文档。

    处理逻辑：
    1. 如果用户问题中直接包含某个药品标题，只保留精确命中的药品。
       例如：布洛芬有什么注意事项 -> 只保留 布洛芬
    2. 如果没有精确命中，则保留药品类文档。
    3. 如果过滤后为空，则保留原始检索结果中的前3条，避免完全无结果。
    """
    question = clean_text(question)

    medicine_docs = [
        doc for doc in retrieved_docs or []
        if doc.get("doc_type") == "medicine"
    ]

    exact_docs = [
        doc for doc in medicine_docs
        if doc.get("title") and doc.get("title") in question
    ]

    if exact_docs:
        return exact_docs[:3]

    if medicine_docs:
        return medicine_docs[:3]

    return (retrieved_docs or [])[:3]


def filter_normal_docs(retrieved_docs):
    """
    普通症状自查场景下，最多保留前3条结果。
    """
    return (retrieved_docs or [])[:3]


def doc_titles(retrieved_docs):
    return [
        doc.get("title", "")
        for doc in retrieved_docs or []
        if doc.get("title", "")
    ]


def run_health_agent(text, image_result=None, user_id=None):
    """
    HealthAgent 文本版智能调度入口。

    功能：
    1. 危险症状优先判断
    2. 意图识别
    3. 信息不足追问
    4. 调用 RAG 检索
    5. 调用大模型生成回答
    6. 保存 chat_history
    7. 写入 search_logs
    """
    question = str(text or "").strip()

    if not question:
        return {
            "success": False,
            "intent": "empty",
            "risk_level": "unknown",
            "need_followup": True,
            "question": question,
            "answer": "请输入你的症状描述或用药问题。",
            "warning": None,
            "retrieved_docs": [],
            "used_tools": [],
            "history_id": None,
            "llm": {
                "used": False,
                "provider": "",
                "model": "",
                "error": ""
            }
        }

    used_tools = []

    # 1. 危险症状优先判断
    warning_text = expand_warning_text(question)
    warning_result = check_warning(warning_text)
    used_tools.append("safety_check")

    if warning_result.get("has_warning"):
        intent = "emergency"
        risk_level = "high"
        answer = warning_result.get("message", "")

        add_search_log(
            kind="warning",
            keyword=question,
            matched_titles=warning_result.get("matched", []),
            user_id=user_id
        )

        add_search_log(
            kind="agent",
            keyword=question,
            matched_titles=[intent],
            user_id=user_id
        )

        record = add_history_record(
            question=question,
            answer=answer,
            warning=warning_result,
            retrieved_docs=[],
            llm={
                "success": False,
                "provider": "rule_agent",
                "model": "health-agent-v1"
            }
        )

        return {
            "success": True,
            "intent": intent,
            "risk_level": risk_level,
            "need_followup": False,
            "question": question,
            "answer": answer,
            "warning": warning_result,
            "retrieved_docs": [],
            "used_tools": used_tools,
            "history_id": record.get("id") if record else None,
            "llm": {
                "used": False,
                "provider": "rule_agent",
                "model": "health-agent-v1",
                "error": ""
            }
        }

    # 2. 意图识别
    intent = classify_intent(question, image_result=image_result)
    used_tools.append("intent_classifier")

    # 3. 信息不足先追问
    if need_followup(question, intent):
        answer = build_followup_answer(intent)

        add_search_log(
            kind="agent",
            keyword=question,
            matched_titles=[intent, "need_followup"],
            user_id=user_id
        )

        record = add_history_record(
            question=question,
            answer=answer,
            warning=warning_result,
            retrieved_docs=[],
            llm={
                "success": False,
                "provider": "rule_agent",
                "model": "health-agent-v1"
            }
        )

        return {
            "success": True,
            "intent": "unknown_or_insufficient",
            "risk_level": "unknown",
            "need_followup": True,
            "followup_questions": build_followup_questions(intent),
            "question": question,
            "answer": answer,
            "warning": warning_result,
            "retrieved_docs": [],
            "used_tools": used_tools,
            "history_id": record.get("id") if record else None,
            "llm": {
                "used": False,
                "provider": "rule_agent",
                "model": "health-agent-v1",
                "error": ""
            }
        }

    # 4. RAG 检索
    # 先多取几条，再根据意图做过滤。
    # 药品咨询场景尤其需要过滤，避免无关药品混入大模型上下文。
    raw_retrieved_docs = search_knowledge(question, top_k=6)
    used_tools.append("rag_search")

    if intent == "medicine_consult":
        retrieved_docs = filter_medicine_docs_for_question(question, raw_retrieved_docs)
    else:
        retrieved_docs = filter_normal_docs(raw_retrieved_docs)

    matched_titles = doc_titles(retrieved_docs)

    if intent == "medicine_consult":
        log_kind = "medicine"
    elif intent == "image_assisted_check":
        log_kind = "image"
    else:
        log_kind = "rag"

    add_search_log(
        kind=log_kind,
        keyword=question,
        matched_titles=matched_titles,
        user_id=user_id
    )

    add_search_log(
        kind="agent",
        keyword=question,
        matched_titles=[intent],
        user_id=user_id
    )

    # 5. 低命中处理
    if not retrieved_docs:
        answer = build_low_confidence_answer()

        record = add_history_record(
            question=question,
            answer=answer,
            warning=warning_result,
            retrieved_docs=[],
            llm={
                "success": False,
                "provider": "rule_agent",
                "model": "health-agent-v1"
            }
        )

        return {
            "success": True,
            "intent": intent,
            "risk_level": "low",
            "need_followup": False,
            "question": question,
            "answer": answer,
            "warning": warning_result,
            "retrieved_docs": [],
            "used_tools": used_tools,
            "history_id": record.get("id") if record else None,
            "llm": {
                "used": False,
                "provider": "rule_agent",
                "model": "health-agent-v1",
                "error": ""
            }
        }

    # 6. 大模型生成回答，失败则用本地模板兜底
    fallback_answer = build_simple_answer(question, retrieved_docs)
    llm_result = generate_llm_answer(question, retrieved_docs)
    used_tools.append("llm_answer")

    if llm_result.get("success"):
        answer = llm_result.get("answer", "")
    else:
        answer = fallback_answer

    # 7. 保存完整问答历史
    record = add_history_record(
        question=question,
        answer=answer,
        warning=warning_result,
        retrieved_docs=retrieved_docs,
        llm=llm_result
    )

    return {
        "success": True,
        "intent": intent,
        "risk_level": "low",
        "need_followup": False,
        "question": question,
        "answer": answer,
        "warning": warning_result,
        "retrieved_docs": retrieved_docs,
        "used_tools": used_tools,
        "history_id": record.get("id") if record else None,
        "llm": {
            "used": llm_result.get("success", False),
            "provider": llm_result.get("provider", ""),
            "model": llm_result.get("model", ""),
            "error": llm_result.get("error", "")
        }
    }