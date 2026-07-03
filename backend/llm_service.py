import os
import requests
from dotenv import load_dotenv


load_dotenv()


def get_llm_config():
    """
    读取大模型配置
    """
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower()

    if provider == "deepseek":
        return {
            "provider": "deepseek",
            "api_key": os.getenv("DEEPSEEK_API_KEY", "").strip(),
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        }

    if provider == "qwen":
        return {
            "provider": "qwen",
            "api_key": os.getenv("DASHSCOPE_API_KEY", "").strip(),
            "base_url": os.getenv("QWEN_BASE_URL", "").rstrip("/"),
            "model": os.getenv("QWEN_MODEL", "qwen-plus")
        }

    return {
        "provider": provider,
        "api_key": "",
        "base_url": "",
        "model": ""
    }


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
        citation = doc.get("citation", "")
        source = doc.get("source") or {}
        source_label = source.get("label", "")
        if citation or source_label:
            content = f"来源：{citation or source_label}\n{content}"

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
    """
    将数据库精确/半精确命中记录整理成大模型可读的上下文。
    """
    if not database_context or not database_context.get("has_matches"):
        return "数据库中没有命中足够相关的结构化疾病或药品记录。"

    context_parts = []

    diseases = database_context.get("diseases", [])
    if diseases:
        context_parts.append("【数据库命中的疾病记录】")
        for index, item in enumerate(diseases, start=1):
            raw = item.get("raw") or {}
            context_parts.append(
                f"疾病{index}：{raw.get('name', item.get('title', ''))}\n"
                f"匹配依据：{'；'.join(item.get('matched_fields', []))}\n"
                f"类别：{raw.get('category', '')}\n"
                f"常见症状：{compact_context_value(raw.get('symptoms', []), 180)}\n"
                f"说明：{compact_context_value(raw.get('description', ''), 260)}\n"
                f"护理建议：{compact_context_value(raw.get('care_advice', ''), 220)}\n"
                f"用药注意：{compact_context_value(raw.get('medicine_notice', ''), 220)}\n"
                f"就医提醒：{compact_context_value(raw.get('warning', ''), 220)}"
            )

    medicines = database_context.get("medicines", [])
    if medicines:
        context_parts.append("【数据库命中的药品记录】")
        for index, item in enumerate(medicines, start=1):
            raw = item.get("raw") or {}
            context_parts.append(
                f"药品{index}：{raw.get('name', item.get('title', ''))}\n"
                f"匹配依据：{'；'.join(item.get('matched_fields', []))}\n"
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
    retrieved_context = build_retrieved_context(retrieved_docs)

    system_prompt = (
        "你是一个基于RAG知识库的常见病自查与用药指南辅助系统。"
        "你不是医生，不能进行确诊，不能替代医生诊断或药师指导。"
        "你的回答必须严格基于系统提供的数据库命中记录和知识库资料。"
        "数据库命中记录是结构化事实，应优先使用；RAG检索资料用于补充和交叉验证。"
        "如果数据库命中记录和RAG资料不一致，以数据库命中记录为准，并说明需要医生或药师复核。"
        "不允许扩展资料中没有出现的疾病、药品、剂量、治疗方案或具体病程时间。"
        "如果数据库和知识库资料都不足，请明确说明：当前资料中暂无足够信息，不要泛泛科普。"
        "不要推荐处方药，不要建议用户自行使用抗生素，不要给出具体用药剂量。"
        "只输出与命中记录直接相关的内容，不要罗列无关疾病或通用套话。"
        "回答必须简洁，不要写成长篇科普文章。"
        "回答要使用中文，语气谨慎、清晰、简洁，适合普通用户阅读。"
    )

    user_prompt = f"""
    用户问题：
    {question}

    以下是系统从数据库中匹配到的结构化记录：
    {database_context_text}

    以下是系统从知识库中检索到的相关资料：
    {retrieved_context}

    请你综合数据库命中记录和RAG知识库资料回答，不要加入资料中没有出现的内容。

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
    - 优先点名数据库命中的疾病或药品；未命中的内容不要写成确定建议
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
    config = get_llm_config()

    if not config["api_key"]:
        return {
            "success": False,
            "provider": config["provider"],
            "model": config["model"],
            "answer": "",
            "error": "未配置大模型API Key，已使用本地模板回答。"
        }

    if not config["base_url"]:
        return {
            "success": False,
            "provider": config["provider"],
            "model": config["model"],
            "answer": "",
            "error": "未配置大模型base_url，已使用本地模板回答。"
        }

    url = config["base_url"] + "/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}"
    }

    payload = {
        "model": config["model"],
        "messages": build_messages(question, retrieved_docs, database_context),
        "temperature": 0.1,
        "max_tokens": 1100,
        "stream": False
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "provider": config["provider"],
                "model": config["model"],
                "answer": "",
                "error": f"大模型接口调用失败，状态码：{response.status_code}，返回：{response.text}"
            }

        result = response.json()
        answer = result["choices"][0]["message"]["content"].strip()

        return {
            "success": True,
            "provider": config["provider"],
            "model": config["model"],
            "answer": answer,
            "error": ""
        }

    except Exception as e:
        return {
            "success": False,
            "provider": config["provider"],
            "model": config["model"],
            "answer": "",
            "error": f"大模型调用异常：{str(e)}"
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
        ],
        database_context=None
    )

    return result
