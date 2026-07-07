import json
import os
import re
from pathlib import Path
from datetime import datetime

import pymysql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"

load_dotenv(BASE_DIR / ".env")


COMMON_SYMPTOMS = [
    "咳嗽", "流鼻涕", "鼻塞", "咽痛", "发热", "高热", "低热", "头痛", "头晕",
    "腹泻", "腹痛", "胃痛", "反酸", "烧心", "恶心", "呕吐", "皮肤瘙痒", "红疹",
    "皮疹", "过敏", "牙痛", "乏力", "胸痛", "呼吸困难", "喘不上气"
]


def get_connection():
    """
    获取 MySQL 数据库连接
    """
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "rag_medical"),
        charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


def split_symptoms(symptoms):
    """
    将数据库中的症状字符串转换为列表，兼容前端和 RAG 模块。
    """
    if not symptoms:
        return []

    if isinstance(symptoms, list):
        return symptoms

    return [
        item.strip()
        for item in re.split(r"[、,，;；\s]+", str(symptoms))
        if item.strip()
    ]


def join_symptoms(symptoms):
    """
    将症状列表转换为数据库存储字符串。
    """
    if not symptoms:
        return ""

    if isinstance(symptoms, list):
        return "、".join([str(item).strip() for item in symptoms if str(item).strip()])

    return str(symptoms).strip()


def get_all_diseases():
    """
    获取全部常见病知识：从规范化 MySQL diseases 表读取。
    """
    sql = """
        SELECT
            id,
            name,
            category,
            symptoms,
            description,
            care_advice,
            medicine_notice,
            warning
        FROM diseases
        ORDER BY id ASC
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row.get("id"),
            "name": row.get("name", ""),
            "category": row.get("category", ""),
            "symptoms": split_symptoms(row.get("symptoms", "")),
            "description": row.get("description", ""),
            "care_advice": row.get("care_advice", ""),
            "medicine_notice": row.get("medicine_notice", ""),
            "warning": row.get("warning", "")
        })

    return result


def get_all_medicines():
    """
    获取全部药品知识：从规范化 MySQL medicines 表读取。
    """
    sql = """
        SELECT
            id,
            name,
            type,
            usage_info,
            notice,
            contraindication,
            side_effect
        FROM medicines
        ORDER BY id ASC
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row.get("id"),
            "name": row.get("name", ""),
            "type": row.get("type", ""),
            "usage": row.get("usage_info", ""),
            "notice": row.get("notice", ""),
            "contraindication": row.get("contraindication", ""),
            "side_effect": row.get("side_effect", "")
        })

    return result


def search_medicine(keyword: str):
    """
    根据药品名称、药品类别或适用情况查询药品信息。
    """
    keyword = (keyword or "").strip()

    if not keyword:
        return []

    sql = """
        SELECT
            id,
            name,
            type,
            usage_info,
            notice,
            contraindication,
            side_effect
        FROM medicines
        WHERE name LIKE %s
           OR type LIKE %s
           OR usage_info LIKE %s
        ORDER BY id ASC
    """

    like_keyword = f"%{keyword}%"

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (like_keyword, like_keyword, like_keyword))
            rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row.get("id"),
            "name": row.get("name", ""),
            "type": row.get("type", ""),
            "usage": row.get("usage_info", ""),
            "notice": row.get("notice", ""),
            "contraindication": row.get("contraindication", ""),
            "side_effect": row.get("side_effect", "")
        })

    return result


def search_disease(keyword: str):
    """
    根据疾病名称、分类、症状或描述查询疾病知识。
    """
    keyword = (keyword or "").strip()

    if not keyword:
        return []

    sql = """
        SELECT
            id,
            name,
            category,
            symptoms,
            description,
            care_advice,
            medicine_notice,
            warning
        FROM diseases
        WHERE name LIKE %s
           OR category LIKE %s
           OR symptoms LIKE %s
           OR description LIKE %s
        ORDER BY id ASC
        LIMIT 50
    """

    like_keyword = f"%{keyword}%"

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (like_keyword, like_keyword, like_keyword, like_keyword))
            rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "id": row.get("id"),
            "name": row.get("name", ""),
            "category": row.get("category", ""),
            "symptoms": split_symptoms(row.get("symptoms", "")),
            "description": row.get("description", ""),
            "care_advice": row.get("care_advice", ""),
            "medicine_notice": row.get("medicine_notice", ""),
            "warning": row.get("warning", "")
        })

    return result


def search_knowledge_items(kind: str, keyword: str):
    """
    管理员删除前的关键词搜索入口。
    """
    if kind == "disease":
        return search_disease(keyword)

    if kind == "medicine":
        return search_medicine(keyword)

    raise ValueError("知识库类型不正确，只能是 disease 或 medicine")


def get_knowledge_item_by_id(kind: str, item_id: int):
    if kind == "disease":
        sql = """
            SELECT
                id,
                name,
                category,
                symptoms,
                description,
                care_advice,
                medicine_notice,
                warning
            FROM diseases
            WHERE id = %s
            LIMIT 1
        """
    elif kind == "medicine":
        sql = """
            SELECT
                id,
                name,
                type,
                usage_info,
                notice,
                contraindication,
                side_effect
            FROM medicines
            WHERE id = %s
            LIMIT 1
        """
    else:
        raise ValueError("知识库类型不正确，只能是 disease 或 medicine")

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (item_id,))
            row = cursor.fetchone()

    if not row:
        return None

    if kind == "disease":
        return {
            "id": row.get("id"),
            "name": row.get("name", ""),
            "category": row.get("category", ""),
            "symptoms": split_symptoms(row.get("symptoms", "")),
            "description": row.get("description", ""),
            "care_advice": row.get("care_advice", ""),
            "medicine_notice": row.get("medicine_notice", ""),
            "warning": row.get("warning", "")
        }

    return {
        "id": row.get("id"),
        "name": row.get("name", ""),
        "type": row.get("type", ""),
        "usage": row.get("usage_info", ""),
        "notice": row.get("notice", ""),
        "contraindication": row.get("contraindication", ""),
        "side_effect": row.get("side_effect", "")
    }


def delete_knowledge_item(kind: str, item_id: int):
    """
    删除本地 MySQL 中的疾病或药品知识。删除后需要重建 RAG 向量索引。
    """
    try:
        item_id = int(item_id)
    except (TypeError, ValueError):
        raise ValueError("知识记录 ID 不正确")

    if item_id <= 0:
        raise ValueError("知识记录 ID 不正确")

    if kind not in {"disease", "medicine"}:
        raise ValueError("知识库类型不正确，只能是 disease 或 medicine")

    existing = get_knowledge_item_by_id(kind, item_id)
    if not existing:
        return None

    table = "diseases" if kind == "disease" else "medicines"

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"DELETE FROM {table} WHERE id = %s", (item_id,))

    return existing


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


def normalize_duplicate_name(name: str):
    """
    用于发现近似重复名称，比如“健胃消食片（成人装）”和“健胃消食片”。
    """
    text = str(name or "").lower()
    text = re.sub(r"[（(].*?[）)]", "", text)
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    for token in ["成人装", "儿童装", "胶囊", "片剂", "颗粒", "口服液", "说明书"]:
        text = text.replace(token, "")
    return text


def get_existing_names(table: str):
    if table not in {"diseases", "medicines"}:
        return []

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT id, name FROM {table} ORDER BY id ASC")
            return cursor.fetchall()


def build_duplicate_info(record, existing_rows):
    name = record.get("name", "").strip()
    normalized_name = normalize_duplicate_name(name)
    exact = None
    similar = []

    for row in existing_rows:
        existing_name = row.get("name", "")
        existing_normalized = normalize_duplicate_name(existing_name)

        if existing_name == name:
            exact = {
                "id": row.get("id"),
                "name": existing_name,
            }
            continue

        if (
            normalized_name
            and existing_normalized
            and (
                normalized_name == existing_normalized
                or normalized_name in existing_normalized
                or existing_normalized in normalized_name
            )
        ):
            similar.append({
                "id": row.get("id"),
                "name": existing_name,
            })

    return {
        "exact": exact,
        "similar": similar[:5],
    }


def summarize_upload_results(items):
    summary = {
        "total": len(items),
        "created": 0,
        "updated": 0,
        "similar": 0,
    }

    for item in items:
        status = item.get("status")
        if status == "created":
            summary["created"] += 1
        elif status == "updated":
            summary["updated"] += 1

        if item.get("similar_duplicates"):
            summary["similar"] += 1

    return summary


def append_diseases(records):
    """
    批量追加疾病知识：写入 MySQL diseases 表。
    """
    saved_records = []
    existing_rows = get_existing_names("diseases")

    sql = """
        INSERT INTO diseases
        (name, category, symptoms, description, care_advice, medicine_notice, warning)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            category = VALUES(category),
            symptoms = VALUES(symptoms),
            description = VALUES(description),
            care_advice = VALUES(care_advice),
            medicine_notice = VALUES(medicine_notice),
            warning = VALUES(warning),
            updated_at = CURRENT_TIMESTAMP
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for item in records:
                record = normalize_disease_record(item)
                symptoms_text = join_symptoms(record.get("symptoms", []))
                duplicate_info = build_duplicate_info(record, existing_rows)
                record["status"] = "updated" if duplicate_info["exact"] else "created"
                record["duplicate_of"] = duplicate_info["exact"]
                record["similar_duplicates"] = duplicate_info["similar"]

                cursor.execute(
                    sql,
                    (
                        record.get("name", ""),
                        record.get("category", ""),
                        symptoms_text,
                        record.get("description", ""),
                        record.get("care_advice", ""),
                        record.get("medicine_notice", ""),
                        record.get("warning", "")
                    )
                )

                saved_records.append(record)
                if record["status"] == "created":
                    existing_rows.append({
                        "id": cursor.lastrowid,
                        "name": record.get("name", ""),
                    })

    return saved_records


def append_medicines(records):
    """
    批量追加药品知识：写入 MySQL medicines 表。
    """
    saved_records = []
    existing_rows = get_existing_names("medicines")

    sql = """
        INSERT INTO medicines
        (name, type, usage_info, notice, contraindication, side_effect)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            type = VALUES(type),
            usage_info = VALUES(usage_info),
            notice = VALUES(notice),
            contraindication = VALUES(contraindication),
            side_effect = VALUES(side_effect),
            updated_at = CURRENT_TIMESTAMP
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for item in records:
                record = normalize_medicine_record(item)
                duplicate_info = build_duplicate_info(record, existing_rows)
                record["status"] = "updated" if duplicate_info["exact"] else "created"
                record["duplicate_of"] = duplicate_info["exact"]
                record["similar_duplicates"] = duplicate_info["similar"]

                cursor.execute(
                    sql,
                    (
                        record.get("name", ""),
                        record.get("type", ""),
                        record.get("usage", ""),
                        record.get("notice", ""),
                        record.get("contraindication", ""),
                        record.get("side_effect", "")
                    )
                )

                saved_records.append(record)
                if record["status"] == "created":
                    existing_rows.append({
                        "id": cursor.lastrowid,
                        "name": record.get("name", ""),
                    })

    return saved_records


def trim_text(text: str, max_len: int = 180):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def stringify_value(value):
    """
    将说明书中的列表/对象字段转换成适合写入 MySQL text 字段的中文文本。
    """
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, list):
        return "；".join(
            stringify_value(item)
            for item in value
            if stringify_value(item)
        )

    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            item_text = stringify_value(item)
            if item_text:
                parts.append(f"{key}：{item_text}")
        return "；".join(parts)

    return str(value).strip()


def first_present(item, keys):
    for key in keys:
        value = item.get(key)
        text = stringify_value(value)
        if text:
            return text
    return ""


def combine_sections(item, sections):
    parts = []

    for label, keys in sections:
        text = first_present(item, keys)
        if text:
            parts.append(f"{label}：{text}")

    return "\n".join(parts)


def first_title(file_name: str, content: str):
    lines = [line.strip(" #\t\r\n") for line in (content or "").splitlines() if line.strip()]
    for line in lines:
        if line not in {"{", "}", "[", "]"} and not line.startswith(("\"", "'")):
            return line[:32]
    return Path(file_name or "管理员上传文档").stem[:32]


def extract_symptoms(content: str):
    symptoms = [item for item in COMMON_SYMPTOMS if item in (content or "")]
    return symptoms[:8] or ["待补充"]


def normalize_disease_record(item, fallback_name="管理员上传疾病知识"):
    """
    将上传的 JSON 对象规整为系统疾病知识格式。
    """
    symptoms = item.get("symptoms", [])
    if isinstance(symptoms, str):
        symptoms = [
            part.strip()
            for part in re.split(r"[、,，;\s]+", symptoms)
            if part.strip()
        ]

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
    将上传的 JSON 对象规整为系统药品知识格式。
    """
    name = first_present(item, ["name", "通用名称", "药品名称", "商品名称", "名称"]) or fallback_name
    medicine_type = first_present(item, ["type", "category", "药品类别", "类别", "剂型"]) or "上传说明书"
    usage = (
        first_present(item, ["usage", "usage_info", "description", "content"])
        or combine_sections(
            item,
            [
                ("功能主治", ["功能主治", "适应症", "主治", "用途"]),
                ("用法用量", ["用法用量", "用法", "用量"]),
                ("药理作用", ["药理作用"]),
            ],
        )
    )
    notice = (
        first_present(item, ["notice"])
        or combine_sections(
            item,
            [
                ("注意事项", ["注意事项", "注意"]),
                ("药物相互作用", ["药物相互作用", "相互作用"]),
                ("贮藏", ["贮藏", "储存"]),
                ("规格", ["规格", "包装规格"]),
                ("批准文号", ["批准文号"]),
                ("生产企业", ["生产企业", "厂家", "企业"]),
            ],
        )
    )
    contraindication = first_present(
        item,
        ["contraindication", "contraindications", "禁忌", "禁用", "禁忌症"],
    )
    side_effect = first_present(
        item,
        ["side_effect", "adverse_reaction", "side_effects", "不良反应", "副作用"],
    )

    return {
        "name": name,
        "type": medicine_type,
        "usage": usage,
        "notice": notice or "由管理员上传的药品说明书生成，请结合原说明书继续核对。",
        "contraindication": contraindication or "请参考原药品说明书禁忌项。",
        "side_effect": side_effect or "请参考原药品说明书不良反应项。",
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
    支持管理员上传 JSON 结构化疾病知识，或上传普通文本后自动生成一条疾病知识记录。
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
    支持管理员上传 JSON 结构化药品知识，或上传普通说明书文本后自动生成一条药品知识记录。
    """
    save_uploaded_source(file_name, content, "medicine")
    fallback_name = first_title(file_name, content)

    stripped_content = (content or "").strip()

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
    except json.JSONDecodeError as exc:
        if stripped_content.startswith(("{", "[")):
            raise ValueError(f"药品 JSON 格式不合法：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}")

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
