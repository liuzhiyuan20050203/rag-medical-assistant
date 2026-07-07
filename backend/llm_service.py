import json
import os
import re
import requests
from textwrap import dedent
from dotenv import load_dotenv


load_dotenv()


def get_llm_config():
    """
    读取大模型配置
    """
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower()
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()

    if provider == "deepseek" and not deepseek_key and os.getenv("VISION_LLM_API_KEY", "").strip():
        provider = "qwen"

    if provider == "deepseek":
        return {
            "provider": "deepseek",
            "api_key": deepseek_key,
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        }

    if provider == "qwen":
        return {
            "provider": "qwen",
            "api_key": (
                os.getenv("DASHSCOPE_API_KEY", "")
                or os.getenv("QWEN_API_KEY", "")
                or os.getenv("VISION_LLM_API_KEY", "")
            ).strip(),
            "base_url": (
                os.getenv("QWEN_BASE_URL", "")
                or os.getenv("VISION_LLM_BASE_URL", "")
                or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ).rstrip("/"),
            "model": os.getenv("QWEN_MODEL", "qwen-plus")
        }

    return {
        "provider": provider,
        "api_key": "",
        "base_url": "",
        "model": ""
    }


def normalize_chat_url(base_url):
    if base_url.endswith("/chat/completions"):
        return base_url
    return base_url.rstrip("/") + "/chat/completions"


def call_chat_completion(messages, temperature=0.1, max_tokens=1100):
    config = get_llm_config()

    if not config["api_key"]:
        return {
            "success": False,
            "provider": config["provider"],
            "model": config["model"],
            "content": "",
            "error": "未配置大模型API Key，已使用本地规则或模板回答。"
        }

    if not config["base_url"]:
        return {
            "success": False,
            "provider": config["provider"],
            "model": config["model"],
            "content": "",
            "error": "未配置大模型base_url，已使用本地规则或模板回答。"
        }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}"
    }
    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }

    try:
        response = requests.post(
            normalize_chat_url(config["base_url"]),
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "provider": config["provider"],
                "model": config["model"],
                "content": "",
                "error": f"大模型接口调用失败，状态码：{response.status_code}，返回：{response.text}"
            }

        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        return {
            "success": True,
            "provider": config["provider"],
            "model": config["model"],
            "content": content,
            "error": ""
        }
    except Exception as e:
        return {
            "success": False,
            "provider": config["provider"],
            "model": config["model"],
            "content": "",
            "error": f"大模型调用异常：{str(e)}"
        }


def parse_json_object(text):
    text = (text or "").strip()
    if not text:
        return None

    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).replace("```", "")
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

    return None


def build_retrieved_context(retrieved_docs):
    """
    将RAG检索结果整理成大模型可读的上下文
    """
    if not retrieved_docs:
        return "知识库中没有检索到足够相关的资料。"

    context_parts = []

    for index, doc in enumerate(retrieved_docs, start=1):
        title = doc.get("title", "")
        doc_type_value = doc.get("doc_type", "")
        content = doc.get("content", "")

        if doc_type_value == "disease":
            doc_type = "常见病"
        elif doc_type_value == "medicine":
            doc_type = "药品"
        else:
            doc_type = "资料"

        context_parts.append(
            f"资料{index}：\n"
            f"标题：{title}\n"
            f"类型：{doc_type}\n"
            f"内容：{content}\n"
        )

    return "\n".join(context_parts)


def compact_context_value(value, limit=260):
    if isinstance(value, list):
        value = "、".join(str(item) for item in value if item)

    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def build_database_context(database_context):
    if not database_context or not database_context.get("has_matches"):
        return ""

    context_parts = []

    for index, item in enumerate(database_context.get("diseases", []), start=1):
        raw = item.get("raw") or {}
        context_parts.append(
            f"数据库疾病{index}：{raw.get('name', item.get('title', ''))}\n"
            f"类别：{raw.get('category', '')}\n"
            f"常见症状：{compact_context_value(raw.get('symptoms', []), 180)}\n"
            f"说明：{compact_context_value(raw.get('description', ''), 260)}\n"
            f"护理建议：{compact_context_value(raw.get('care_advice', ''), 220)}\n"
            f"用药注意：{compact_context_value(raw.get('medicine_notice', ''), 220)}\n"
            f"就医提醒：{compact_context_value(raw.get('warning', ''), 220)}"
        )

    for index, item in enumerate(database_context.get("medicines", []), start=1):
        raw = item.get("raw") or {}
        context_parts.append(
            f"数据库药品{index}：{raw.get('name', item.get('title', ''))}\n"
            f"类别：{raw.get('type', '')}\n"
            f"适用情况：{compact_context_value(raw.get('usage', ''), 220)}\n"
            f"注意事项：{compact_context_value(raw.get('notice', ''), 240)}\n"
            f"禁忌人群：{compact_context_value(raw.get('contraindication', ''), 220)}\n"
            f"不良反应：{compact_context_value(raw.get('side_effect', ''), 220)}"
        )

    return "\n\n".join(context_parts)


def build_messages(question, retrieved_docs, database_context=None):
    """
    构造大模型Prompt
    """
    database_context_text = build_database_context(database_context)
    context = build_retrieved_context(retrieved_docs)
    if database_context_text:
        context = f"{database_context_text}\n\n{context}"

    system_prompt = (
        "你是一个基于RAG知识库的常见病自查与用药指南辅助系统。"
        "你不是医生，不能进行确诊，不能替代医生诊断或药师指导。"
        "你的回答必须严格基于系统提供的知识库资料，"
        "不允许扩展资料中没有出现的疾病、药品、剂量、治疗方案或具体病程时间。"
        "如果知识库资料不足，请明确说明：知识库中暂无足够信息。"
        "不要推荐处方药，不要建议用户自行使用抗生素，不要给出具体用药剂量。"
        "回答必须简洁，不要写成长篇科普文章。"
        "回答要使用中文，语气谨慎、清晰、简洁，适合普通用户阅读。"
    )

    user_prompt = f"""
    用户问题：
    {question}

    以下是系统从知识库中检索到的相关资料：
    {context}

    请你只根据以上知识库资料回答，不要加入资料中没有出现的内容。

    请按照以下结构生成回答：

    1. 症状初步分析
    2. 可能相关的常见病方向
    3. 日常护理建议
    4. 用药注意事项
    5. 就医提醒
    6. 安全声明

    回答要求：
    - 不要以“好的”“希望您早日康复”等寒暄语开头或结尾
    - 不要直接确诊
    - 不要编造知识库中没有的疾病、药品、治疗方法、病程时间
    - 不要给出具体处方和剂量
    - 不要自行加入知识库之外的时间判断，例如“3天”“5天”“一周”等，除非资料中明确出现
    - 每个部分控制在1到2句话
    - 总字数控制在400到650字之间
    - 第6点安全声明必须完整写完
    - 安全声明中不要写“您不是医生”，应写“本系统不能替代医生诊断或药师指导”
    - 语言要简洁、清楚、谨慎
    """

    return [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_prompt
        }
    ]


def generate_llm_answer(question, retrieved_docs, database_context=None):
    """
    调用大模型生成回答
    """
    result = call_chat_completion(
        build_messages(question, retrieved_docs, database_context),
        temperature=0.1,
        max_tokens=1100,
    )
    return {
        "success": result["success"],
        "provider": result["provider"],
        "model": result["model"],
        "answer": result.get("content", ""),
        "error": result["error"],
    }


def build_agent_planner_messages(normalized):
    history_lines = []
    for item in normalized.get("history", [])[-6:]:
        history_lines.append(f"{item.get('role', 'user')}：{item.get('content', '')}")

    system_prompt = (
        "你是医疗健康RAG系统的Agent规划器，只负责判断意图和选择工具，不直接给医学结论。"
        "必须输出JSON对象，不要输出Markdown。"
        "危险症状由系统规则优先处理；如果用户描述明显需要急诊，也可标记danger_alert。"
        "图片识别只是视觉线索，不能根据图片直接确诊。"
        "药盒、说明书、OTC、胶囊、片剂等优先medicine_query；皮肤、红疹、湿疹、伤口、咽喉等症状图片优先rag_answer或ask_followup。"
    )
    user_prompt = f"""
    最近对话：
    {chr(10).join(history_lines) or "无"}

    当前输入类型：{normalized.get("input_type")}
    用户文字：{normalized.get("text") or "无"}
    图片识别描述：{normalized.get("image_summary") or "无"}
    图片识别标签：{"、".join(normalized.get("image_tags", [])) or "无"}
    合并后的问题：{normalized.get("question") or "无"}

    可选action只能是：ask_followup、medicine_query、rag_answer。

    请输出JSON：
    {{
      "action": "ask_followup|medicine_query|rag_answer",
      "intent": "followup|medicine_query|symptom_query|symptom_image|general_health",
      "confidence": 0.0到1.0,
      "reason": "一句话说明为什么这样选",
      "search_query": "用于检索知识库或药品库的关键词",
      "followup_questions": ["最多3个需要追问的问题"],
      "current_topic": "当前会话主题，如布洛芬、皮肤红疹、咳嗽等"
    }}
    """

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def generate_agent_plan(normalized):
    result = call_chat_completion(
        build_agent_planner_messages(normalized),
        temperature=0.0,
        max_tokens=600,
    )
    plan = parse_json_object(result.get("content", "")) if result.get("success") else None

    if not isinstance(plan, dict):
        return {
            "success": False,
            "provider": result["provider"],
            "model": result["model"],
            "plan": None,
            "error": result["error"] or "Agent Planner 未返回有效JSON。",
            "raw_text": result.get("content", ""),
        }

    action = plan.get("action")
    if action not in {"ask_followup", "medicine_query", "rag_answer"}:
        plan["action"] = "rag_answer"

    try:
        confidence = float(plan.get("confidence", 0.65))
    except (TypeError, ValueError):
        confidence = 0.65
    plan["confidence"] = max(0.0, min(confidence, 1.0))

    if not isinstance(plan.get("followup_questions"), list):
        plan["followup_questions"] = []

    return {
        "success": True,
        "provider": result["provider"],
        "model": result["model"],
        "plan": plan,
        "error": "",
        "raw_text": result.get("content", ""),
    }


def build_agent_answer_messages(question, retrieved_docs, answer_type, history=None):
    context = build_retrieved_context(retrieved_docs)
    history_text = "\n".join(
        f"{item.get('role', 'user')}：{item.get('content', '')}"
        for item in (history or [])[-6:]
    )

    type_instruction = {
        "medicine": (
            "用户在问药品信息。请基于药品知识库资料回答药品用途、注意事项、禁忌和不良反应。"
            "不要给具体剂量，不要替代医生或药师指导。"
        ),
        "symptom_image": (
            "用户提供了症状相关图片。请说明只能根据图片识别结果和知识库资料做健康信息提示，不能确诊。"
            "优先结合皮肤/症状线索、危险信号、日常护理和就医提醒回答。"
        ),
        "symptom": (
            "用户在问症状或常见病方向。请基于知识库资料做初步分析、护理建议和就医提醒。"
        ),
    }.get(answer_type, "请基于知识库资料回答用户问题。")

    system_prompt = (
        "你是一个基于RAG知识库的医疗健康AI助手。"
        "你不能确诊，不能替代医生诊断或药师指导。"
        "必须以知识库资料为主要依据；资料不足时要明确说明需要补充信息或线下就医。"
        "不要补充知识库没有出现的具体药品、成分名、剂量、疗程、治疗方案或检查项目。"
        "回答要自然、简洁、人性化，面向普通用户。不要使用emoji或夸张符号。"
    )
    user_prompt = f"""
    最近对话：
    {history_text or "无"}

    用户当前问题：
    {question}

    任务类型：
    {type_instruction}

    知识库资料：
    {context}

    回答要求：
    - 中文回答
    - 不要直接确诊
    - 不要编造知识库之外的药品、成分名、剂量、疗程、治疗方案或检查项目
    - 如果涉及图片，强调图片只能提供可见线索
    - 普通用户能看懂，语气自然
    - 不要使用emoji、对勾、警示图标等装饰符号
    - 控制在300到600字
    - 结尾保留安全提醒
    """

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def generate_agent_answer(question, retrieved_docs, answer_type="symptom", history=None):
    result = call_chat_completion(
        build_agent_answer_messages(question, retrieved_docs, answer_type, history=history),
        temperature=0.2,
        max_tokens=1100,
    )

    return {
        "success": result["success"],
        "provider": result["provider"],
        "model": result["model"],
        "answer": result.get("content", ""),
        "error": result["error"],
    }


def test_llm_connection():
    """
    测试大模型连接是否正常
    """
    result = generate_llm_answer(
        question="请回复：大模型连接成功。",
        retrieved_docs=[
            {
                "title": "测试资料",
                "doc_type": "test",
                "content": "这是一次大模型连接测试。"
            }
        ]
    )

    return result
