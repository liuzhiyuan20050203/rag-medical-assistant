import json
from pathlib import Path
from datetime import datetime

from storage import is_database_enabled, load_json_data, save_json_data


BASE_DIR = Path(__file__).resolve().parent
HISTORY_FILE = BASE_DIR / "data" / "history.json"


def ensure_history_file():
    """
    确保历史记录文件存在
    """
    if is_database_enabled():
        load_json_data(HISTORY_FILE, list)
        return

    if not HISTORY_FILE.exists():
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)


def load_history():
    """
    读取历史记录
    """
    if is_database_enabled():
        return load_json_data(HISTORY_FILE, list)

    ensure_history_file()

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history_list):
    """
    保存历史记录
    """
    if is_database_enabled():
        save_json_data(HISTORY_FILE, history_list)
        return

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=2)


def next_history_id(history_list):
    if not history_list:
        return 1
    return max(item.get("id", 0) for item in history_list) + 1


def add_history_record(question, answer, warning=None, retrieved_docs=None):
    """
    新增一条问答历史记录
    """
    history_list = load_history()

    record = {
        "id": next_history_id(history_list),
        "question": question,
        "answer": answer,
        "warning": warning,
        "retrieved_docs": retrieved_docs or [],
        "is_error": False,
        "error_reason": "",
        "satisfaction": "",
        "rating": 0,
        "feedback_text": "",
        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    history_list.insert(0, record)

    # 最多保存最近50条，避免文件过大
    history_list = history_list[:50]

    save_history(history_list)

    return record


def get_history_list():
    """
    获取全部历史记录
    """
    return load_history()


def clear_history_records():
    """
    清空历史记录
    """
    save_history([])
    return True


def update_history_record(record_id: int, fields: dict):
    """
    更新指定历史记录的审核或反馈字段。
    """
    history_list = load_history()

    for item in history_list:
        if item.get("id") == record_id:
            item.update(fields)
            item["review_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_history(history_list)
            return item

    return None


def mark_history_error(record_id: int, reason: str = ""):
    """
    标记错误回答，供管理员后台和满意度统计使用。
    """
    return update_history_record(
        record_id,
        {
            "is_error": True,
            "error_reason": reason or "管理员标记为错误回答",
            "satisfaction": "不满意",
            "rating": 1
        }
    )


def rating_to_satisfaction(rating: int):
    if rating >= 4:
        return "满意"
    if rating == 3:
        return "一般"
    if rating in {1, 2}:
        return "不满意"
    return ""


def set_history_feedback(record_id: int, rating: int, feedback_text: str = ""):
    """
    设置用户星级评分和详细评价。
    """
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return None

    if rating < 1 or rating > 5:
        return None

    return update_history_record(
        record_id,
        {
            "rating": rating,
            "feedback_text": (feedback_text or "").strip(),
            "satisfaction": rating_to_satisfaction(rating),
            "is_error": rating <= 2
        }
    )


def set_history_satisfaction(record_id: int, satisfaction: str):
    """
    兼容旧版三档满意度反馈。
    """
    rating_map = {
        "满意": 5,
        "一般": 3,
        "不满意": 1
    }
    rating = rating_map.get(satisfaction)

    if not rating:
        return None

    return update_history_record(
        record_id,
        {
            "rating": rating,
            "satisfaction": satisfaction,
            "is_error": satisfaction == "不满意"
        }
    )
