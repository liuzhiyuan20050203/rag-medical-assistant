import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


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


def load_warning_rules():
    """
    读取危险症状规则库：从规范化 MySQL warning_rules 表读取。
    为了兼容原来的逻辑，这里返回关键词字符串列表。
    """
    sql = """
        SELECT keyword
        FROM warning_rules
        ORDER BY id ASC
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

    return [
        row.get("keyword", "").strip()
        for row in rows
        if row.get("keyword", "").strip()
    ]


def check_warning(question: str):
    """
    检查用户输入中是否包含危险症状关键词。
    """
    question = question or ""
    rules = load_warning_rules()
    matched = []

    for rule in rules:
        if rule and rule in question:
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