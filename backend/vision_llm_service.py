import json
import os
import re
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values, load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH, override=True)
load_dotenv(override=False)


def load_local_vision_env():
    if not ENV_PATH.exists():
        return {}

    return {
        key.lstrip("\ufeff"): value
        for key, value in dotenv_values(ENV_PATH).items()
        if key and key.lstrip("\ufeff").startswith("VISION_LLM_")
    }


def config_value(local_env: dict[str, str | None], name: str, default: str = ""):
    if name in local_env:
        return (local_env.get(name) or "").strip()
    return os.getenv(name, default).strip()


def get_vision_llm_config():
    """
    读取多模态LLM配置。
    默认按 OpenAI-compatible chat/completions 协议组织请求，
    可接入通义千问VL、智谱GLM-V、火山方舟、OpenRouter等兼容接口。
    """
    local_env = load_local_vision_env()
    provider = config_value(local_env, "VISION_LLM_PROVIDER", "custom") or "custom"
    base_url = config_value(local_env, "VISION_LLM_BASE_URL").rstrip("/")
    model = config_value(local_env, "VISION_LLM_MODEL")
    api_key = config_value(local_env, "VISION_LLM_API_KEY")

    if provider.lower() == "openai":
        base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        model = model or os.getenv("OPENAI_MODEL", "gpt-5.5")
        api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()

    return {
        "provider": provider,
        "base_url": base_url,
        "model": model,
        "api_key": api_key,
        "timeout": int(config_value(local_env, "VISION_LLM_TIMEOUT", "60") or "60"),
        "max_tokens": int(config_value(local_env, "VISION_LLM_MAX_TOKENS", "900") or "900"),
        "temperature": float(config_value(local_env, "VISION_LLM_TEMPERATURE", "0.1") or "0.1"),
        "image_detail": config_value(local_env, "VISION_LLM_IMAGE_DETAIL", "auto") or "auto"
    }


def vision_llm_available():
    config = get_vision_llm_config()
    return bool(config["base_url"] and config["model"] and config["api_key"])


def normalize_chat_completions_url(base_url: str):
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def safe_json_parse(text: str):
    text = clean_model_text(text)

    if not text:
        return None

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


def clean_model_text(text: str):
    text = (text or "").strip()
    if not text:
        return ""

    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

    markers = ["最终答案：", "最终回答：", "结论：", "回答："]
    for marker in markers:
        if marker in text:
            text = text.split(marker, 1)[1]
            break

    return text.strip()


def build_medical_vision_prompt(note: str = "", frame_count: int = 1):
    frame_text = "图片" if frame_count <= 1 else f"{frame_count}张视频关键帧"

    return (
        "你是一个医疗健康信息辅助系统的多模态识别模块。"
        "请观察用户提供的"
        + frame_text
        + "，只描述可见内容和画面质量，不要进行医学确诊，不要给出处方、剂量或治疗方案。"
        "如果图像可能涉及皮肤、咽喉、口腔、药品包装、说明书、伤口或排泄物，请谨慎描述可见线索，"
        "并提醒用户补充症状文字和及时就医的情况。"
        "\n\n用户补充说明："
        + (note or "无")
        + "\n\n请只返回JSON对象，字段如下："
        "{"
        "\"summary\":\"一句话概括\","
        "\"likely_scene\":\"可能场景\","
        "\"visible_findings\":[\"可见线索\"],"
        "\"quality_warnings\":[\"画质或拍摄问题\"],"
        "\"recommended_questions\":[\"建议继续追问的问题\"],"
        "\"safety_notice\":\"安全声明\""
        "}"
    )


def build_messages(image_data_urls: list[str], note: str):
    config = get_vision_llm_config()
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": build_medical_vision_prompt(note, frame_count=len(image_data_urls))
        }
    ]

    for image_data_url in image_data_urls:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": image_data_url,
                "detail": config["image_detail"]
            }
        })

    return [
        {
            "role": "system",
            "content": (
                "你负责医疗健康应用中的视觉信息辅助识别。"
                "你不能替代医生诊断或药师指导，不能根据图片直接下诊断。"
            )
        },
        {
            "role": "user",
            "content": content
        }
    ]


def disabled_result(reason: str):
    config = get_vision_llm_config()

    return {
        "used": False,
        "provider": config["provider"],
        "model": config["model"],
        "success": False,
        "analysis": None,
        "raw_text": "",
        "error": reason
    }


def analyze_images_with_vision_llm(image_data_urls: list[str], note: str = ""):
    """
    调用多模态LLM分析单图或多张视频关键帧。
    """
    config = get_vision_llm_config()

    if not image_data_urls:
        return disabled_result("未提供图片或关键帧。")

    if not vision_llm_available():
        return disabled_result("未配置多模态LLM，已仅返回本地视觉分析结果。")

    url = normalize_chat_completions_url(config["base_url"])
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}"
    }
    payload = {
        "model": config["model"],
        "messages": build_messages(image_data_urls, note),
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
        "stream": False
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=config["timeout"]
        )

        if response.status_code != 200:
            return disabled_result(
                f"多模态LLM接口调用失败，状态码：{response.status_code}"
            )

        result = response.json()
        answer = clean_model_text(result["choices"][0]["message"]["content"])
        parsed = safe_json_parse(answer)
        if not isinstance(parsed, dict):
            return {
                "used": True,
                "provider": config["provider"],
                "model": config["model"],
                "success": False,
                "analysis": None,
                "raw_text": answer[:800],
                "error": "多模态LLM未返回有效JSON识别结果。"
            }

        return {
            "used": True,
            "provider": config["provider"],
            "model": config["model"],
            "success": True,
            "analysis": parsed,
            "raw_text": answer[:800],
            "error": ""
        }
    except Exception as exc:
        return disabled_result(f"多模态LLM调用异常：{str(exc)}")
