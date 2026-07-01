import json
from pathlib import Path

from storage import load_json_data


BASE_DIR = Path(__file__).resolve().parent
RULE_FILE = BASE_DIR / "data" / "warning_rules.json"


def load_warning_rules():
    """
    读取危险症状规则库
    """
    return load_json_data(RULE_FILE, list)


def check_warning(question: str):
    """
    检查用户输入中是否包含危险症状关键词
    """
    rules = load_warning_rules()
    matched = []

    for rule in rules:
        if rule in question:
            matched.append(rule)

    if matched:
        return {
            "has_warning": True,
            "matched": matched,
            "message": (
                "你描述的症状中包含可能存在较高风险的情况："
                + "、".join(matched)
                + "。建议你及时就医或咨询专业医生。本系统仅提供健康信息参考，不能替代医生诊断。"
            )
        }

    return {
        "has_warning": False,
        "matched": [],
        "message": ""
    }
