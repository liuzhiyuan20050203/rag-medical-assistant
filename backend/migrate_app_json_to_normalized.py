import json
import os

import pymysql
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    """
    连接 MySQL 数据库
    """
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "rag_medical"),
        charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


def load_payload(cursor, store_key):
    """
    从 app_json_store 中读取指定 store_key 的 JSON 数据
    """
    cursor.execute(
        "SELECT payload FROM app_json_store WHERE store_key = %s",
        (store_key,)
    )
    row = cursor.fetchone()

    if not row:
        print(f"[跳过] app_json_store 中没有找到 {store_key}")
        return []

    payload = row.get("payload")

    if not payload:
        print(f"[跳过] {store_key} 的 payload 为空")
        return []

    try:
        return json.loads(payload)
    except json.JSONDecodeError as e:
        print(f"[错误] {store_key} JSON 解析失败：{e}")
        return []


def migrate_diseases(cursor):
    """
    迁移疾病知识库
    """
    diseases = load_payload(cursor, "diseases")

    count = 0

    for item in diseases:
        name = item.get("name", "").strip()
        if not name:
            continue

        symptoms = item.get("symptoms", "")
        if isinstance(symptoms, list):
            symptoms = "、".join(symptoms)

        cursor.execute(
            """
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
            """,
            (
                name,
                item.get("category", ""),
                symptoms,
                item.get("description", ""),
                item.get("care_advice", ""),
                item.get("medicine_notice", ""),
                item.get("warning", "")
            )
        )

        count += 1

    print(f"[完成] diseases 迁移 {count} 条")


def migrate_medicines(cursor):
    """
    迁移药品知识库
    """
    medicines = load_payload(cursor, "medicines")

    count = 0

    for item in medicines:
        name = item.get("name", "").strip()
        if not name:
            continue

        cursor.execute(
            """
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
            """,
            (
                name,
                item.get("type", ""),
                item.get("usage", item.get("usage_info", "")),
                item.get("notice", ""),
                item.get("contraindication", ""),
                item.get("side_effect", "")
            )
        )

        count += 1

    print(f"[完成] medicines 迁移 {count} 条")


def migrate_warning_rules(cursor):
    """
    迁移危险症状规则库
    warning_rules 可能是字符串列表，也可能是字典列表，这里两种都兼容。
    """
    rules = load_payload(cursor, "warning_rules")

    count = 0

    for item in rules:
        if isinstance(item, str):
            keyword = item.strip()
            risk_level = "high"
            advice = "该症状可能存在较高健康风险，建议及时就医。"
        elif isinstance(item, dict):
            keyword = item.get("keyword", "").strip()
            risk_level = item.get("risk_level", "high")
            advice = item.get("advice", "该症状可能存在较高健康风险，建议及时就医。")
        else:
            continue

        if not keyword:
            continue

        cursor.execute(
            """
            INSERT INTO warning_rules
            (keyword, risk_level, advice)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                risk_level = VALUES(risk_level),
                advice = VALUES(advice)
            """,
            (keyword, risk_level, advice)
        )

        count += 1

    print(f"[完成] warning_rules 迁移 {count} 条")


def main():
    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            migrate_diseases(cursor)
            migrate_medicines(cursor)
            migrate_warning_rules(cursor)

        conn.commit()
        print("[成功] app_json_store 数据已迁移到规范化业务表")

    except Exception as e:
        conn.rollback()
        print("[失败] 迁移过程中出现错误：", e)

    finally:
        conn.close()


if __name__ == "__main__":
    main()