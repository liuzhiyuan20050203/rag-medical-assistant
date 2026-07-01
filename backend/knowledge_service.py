import json
import re
from pathlib import Path
from datetime import datetime

from storage import load_json_data, save_json_data


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DISEASE_FILE = DATA_DIR / "diseases.json"
MEDICINE_FILE = DATA_DIR / "medicines.json"
UPLOAD_DIR = DATA_DIR / "uploads"

COMMON_SYMPTOMS = [
    "咳嗽", "流鼻涕", "鼻塞", "咽痛", "发热", "高热", "低热", "头痛", "头晕",
    "腹泻", "腹痛", "胃痛", "反酸", "烧心", "恶心", "呕吐", "皮肤瘙痒", "红疹",
    "皮疹", "过敏", "牙痛", "乏力", "胸痛", "呼吸困难", "喘不上气"
]


def load_json(file_path):
    """
    通用JSON读取方法
    """
    return load_json_data(file_path, list)


def save_json(file_path, data):
    """
    通用JSON保存方法
    """
    save_json_data(file_path, data)


def get_all_diseases():
    """
    获取全部常见病知识
    """
    return load_json(DISEASE_FILE)


def get_all_medicines():
    """
    获取全部药品知识
    """
    return load_json(MEDICINE_FILE)


def save_uploaded_source(file_name: str, content: str, doc_type: str):
    """
    保存管理员上传的原始文档，便于后续追溯。
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "_", file_name or "upload.txt")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    target = UPLOAD_DIR / f"{timestamp}_{doc_type}_{safe_name}"

    with open(target, "w", encoding="utf-8") as f:
        f.write(content or "")

    return str(target)


def append_diseases(records):
    """
    批量追加疾病知识。
    """
    diseases = get_all_diseases()
    diseases.extend(records)
    save_json(DISEASE_FILE, diseases)
    return records


def append_medicines(records):
    """
    批量追加药品知识。
    """
    medicines = get_all_medicines()
    medicines.extend(records)
    save_json(MEDICINE_FILE, medicines)
    return records


def trim_text(text: str, max_len: int = 180):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def first_title(file_name: str, content: str):
    lines = [line.strip(" #\t\r\n") for line in (content or "").splitlines() if line.strip()]
    if lines:
        return lines[0][:32]
    return Path(file_name or "管理员上传文档").stem[:32]


def extract_symptoms(content: str):
    symptoms = [item for item in COMMON_SYMPTOMS if item in (content or "")]
    return symptoms[:8] or ["待补充"]


def normalize_disease_record(item, fallback_name="管理员上传疾病知识"):
    """
    将上传的JSON对象规整为系统疾病知识格式。
    """
    symptoms = item.get("symptoms", [])
    if isinstance(symptoms, str):
        symptoms = [part.strip() for part in re.split(r"[、,，;\s]+", symptoms) if part.strip()]

    return {
        "name": item.get("name") or fallback_name,
        "category": item.get("category") or "上传知识",
        "symptoms": symptoms or ["待补充"],
        "description": item.get("description") or item.get("content") or "",
        "care_advice": item.get("care_advice") or item.get("care") or "由管理员上传的疾病知识文档生成，建议继续补充结构化护理建议。",
        "medicine_notice": item.get("medicine_notice") or item.get("notice") or "用药需结合药品说明书或医生、药师指导。",
        "warning": item.get("warning") or "如症状严重、持续加重或出现危险信号，应及时就医。",
        "source": item.get("source") or "管理员上传"
    }


def normalize_medicine_record(item, fallback_name="管理员上传药品说明书"):
    """
    将上传的JSON对象规整为系统药品知识格式。
    """
    return {
        "name": item.get("name") or fallback_name,
        "type": item.get("type") or item.get("category") or "上传说明书",
        "usage": item.get("usage") or item.get("description") or item.get("content") or "",
        "notice": item.get("notice") or "由管理员上传的药品说明书生成，请结合原说明书继续核对。",
        "contraindication": item.get("contraindication") or item.get("contraindications") or "请参考原药品说明书禁忌项。",
        "side_effect": item.get("side_effect") or item.get("adverse_reaction") or item.get("side_effects") or "请参考原药品说明书不良反应项。",
        "source": item.get("source") or "管理员上传"
    }


def extract_section(content: str, names, max_len=140):
    for name in names:
        index = (content or "").find(name)
        if index >= 0:
            return trim_text(content[index:index + max_len], max_len)
    return ""


def parse_disease_upload(file_name: str, content: str):
    """
    支持管理员上传JSON结构化疾病知识，或上传普通文本后自动生成一条疾病知识记录。
    """
    save_uploaded_source(file_name, content, "disease")
    fallback_name = first_title(file_name, content)

    try:
        parsed = json.loads(content)
        items = parsed if isinstance(parsed, list) else [parsed]
        records = [
            normalize_disease_record(item, fallback_name=fallback_name)
            for item in items
            if isinstance(item, dict)
        ]
        if records:
            return append_diseases(records)
    except json.JSONDecodeError:
        pass

    record = normalize_disease_record(
        {
            "name": fallback_name,
            "category": "上传文档",
            "symptoms": extract_symptoms(content),
            "description": trim_text(content, 220),
            "care_advice": extract_section(content, ["护理", "建议", "处理"]) or "由管理员上传的疾病知识文档生成，建议继续补充结构化护理建议。",
            "medicine_notice": extract_section(content, ["用药", "药物", "治疗"]) or "用药需结合药品说明书或医生、药师指导。",
            "warning": extract_section(content, ["就医", "警示", "危险"]) or "如症状严重、持续加重或出现危险信号，应及时就医。"
        },
        fallback_name=fallback_name
    )
    return append_diseases([record])


def parse_medicine_upload(file_name: str, content: str):
    """
    支持管理员上传JSON结构化药品知识，或上传普通说明书文本后自动生成一条药品知识记录。
    """
    save_uploaded_source(file_name, content, "medicine")
    fallback_name = first_title(file_name, content)

    try:
        parsed = json.loads(content)
        items = parsed if isinstance(parsed, list) else [parsed]
        records = [
            normalize_medicine_record(item, fallback_name=fallback_name)
            for item in items
            if isinstance(item, dict)
        ]
        if records:
            return append_medicines(records)
    except json.JSONDecodeError:
        pass

    record = normalize_medicine_record(
        {
            "name": fallback_name,
            "type": "上传说明书",
            "usage": extract_section(content, ["适应症", "功能主治", "用途"]) or trim_text(content, 180),
            "notice": extract_section(content, ["注意事项", "注意"]),
            "contraindication": extract_section(content, ["禁忌", "禁用"]),
            "side_effect": extract_section(content, ["不良反应", "副作用"])
        },
        fallback_name=fallback_name
    )
    return append_medicines([record])


def search_medicine(keyword: str):
    """
    根据药品名称或药品类别查询药品信息
    """
    medicines = get_all_medicines()
    result = []

    for item in medicines:
        name = item.get("name", "")
        medicine_type = item.get("type", "")

        if keyword in name or keyword in medicine_type:
            result.append(item)

    return result
