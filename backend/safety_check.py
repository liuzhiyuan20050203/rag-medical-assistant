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


NEGATION_MARKERS = ("没有", "没出现", "无", "否认", "并未", "不是")
HYPOTHETICAL_MARKERS = ("如果", "假如", "倘若", "万一")
REFERENCE_MARKERS = ("文章", "说明书", "写着", "写了", "提到", "这句话", "什么意思")
HISTORY_MARKERS = ("上个月", "以前", "过去", "曾经", "有过", "已经就医", "已经缓解", "已缓解")
CURRENT_MARKERS = ("现在", "目前", "正在", "突然", "刚才", "今天")
RESOLVED_MARKERS = ("已经缓解", "已缓解", "缓解了", "已经好了", "目前没有不适", "现在没有不适")
RECURRENCE_MARKERS = ("又", "再次", "复发", "重新出现", "现在胸痛", "目前胸痛")
WARNING_SYNONYMS = {
    "言语不清": ("说话含糊", "说话不清楚", "讲话含糊", "说不清话"),
    "肢体无力": (
        "手抬不起来", "手也抬不起来", "胳膊抬不起来", "胳膊抬不动", "腿抬不起来", "手脚没力气",
        "一边手脚没力", "半边身子没劲", "单侧无力",
    ),
    "呼吸困难": ("呼吸很费劲", "呼吸不畅", "气不够用"),
    "意识模糊": ("叫不醒", "反应很慢", "神志不清"),
    "口角歪斜": ("嘴歪", "嘴角歪"),
}
IMMEDIATE_EMERGENCY_RULES = {
    "胸痛", "呼吸困难", "喘不上气", "意识模糊", "抽搐",
    "言语不清", "口角歪斜", "肢体无力", "突发剧烈头痛", "面唇肿胀",
}


def _readable_text(value):
    try:
        return value.encode("latin1").decode("gbk")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _context_for_match(question, rule):
    """Classify the local clause around a warning term without suppressing current emergencies."""
    question = _readable_text(question)
    rule = _readable_text(rule)
    start = question.find(rule)
    left = question[max(0, start - 18):start]
    clause_start = max(question.rfind(mark, 0, start) for mark in "，。！？；,.!?;")
    clause = question[clause_start + 1:start + len(rule) + 18]

    if any(marker in left[-8:] for marker in NEGATION_MARKERS):
        return "negated"
    if any(marker in clause for marker in HYPOTHETICAL_MARKERS):
        return "hypothetical"
    if any(marker in clause for marker in REFERENCE_MARKERS):
        return "reference"
    if any(marker in question for marker in RESOLVED_MARKERS) and not any(
        marker in question for marker in RECURRENCE_MARKERS
    ):
        return "historical"
    if any(marker in question for marker in HISTORY_MARKERS) and not any(
        marker in question for marker in CURRENT_MARKERS
    ):
        return "historical"
    return "current"


def check_warning(question: str):
    """
    检查用户输入中是否包含危险症状关键词。
    """
    question = question or ""
    rules = load_warning_rules()
    matched = []
    ignored = []
    evidence = []
    readable_question = _readable_text(question)

    for rule in rules:
        readable_rule = _readable_text(rule)
        candidates = (readable_rule, *WARNING_SYNONYMS.get(readable_rule, ()))
        for candidate in candidates:
            if not candidate or candidate not in readable_question:
                continue
            context = _context_for_match(readable_question, candidate)
            if context == "current":
                if rule not in matched:
                    matched.append(rule)
                evidence.append({"keyword": rule, "expression": candidate})
            else:
                ignored.append({"keyword": rule, "expression": candidate, "context": context})
            break

    if matched:
        immediate = any(_readable_text(rule) in IMMEDIATE_EMERGENCY_RULES for rule in matched)
        action_message = (
            "建议立即拨打急救电话120或尽快前往急诊就医，不要等待自行缓解。"
            if immediate
            else "建议你尽快就医或咨询专业医生。"
        )
        return {
            "has_warning": True,
            "matched": matched,
            "ignored": ignored,
            "evidence": evidence,
            "message": (
                "你描述的症状中包含可能存在较高风险的情况："
                + "、".join(matched)
                + "。" + action_message
                + "本系统仅提供健康信息参考，不能替代医生诊断。"
            )
        }

    return {
        "has_warning": False,
        "matched": [],
        "ignored": ignored,
        "evidence": evidence,
        "message": ""
    }
