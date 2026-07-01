import os
import requests
from textwrap import dedent
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


def build_messages(question, retrieved_docs):
    """
    构造大模型Prompt
    """
    context = build_retrieved_context(retrieved_docs)

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


def generate_llm_answer(question, retrieved_docs):
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
        "messages": build_messages(question, retrieved_docs),
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
        ]
    )

    return result