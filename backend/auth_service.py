import hashlib
import json
import os
import secrets
from pathlib import Path
from datetime import datetime

import pymysql
from dotenv import load_dotenv

from storage import is_database_enabled, load_json_data, save_json_data


BASE_DIR = Path(__file__).resolve().parent
USER_FILE = BASE_DIR / "data" / "users.json"
SESSION_FILE = BASE_DIR / "data" / "sessions.json"
PASSWORD_SALT = "rag-medical-assistant-demo"
PROFILE_DEFAULTS = {
    "display_name": "",
    "real_name": "",
    "email": "",
    "phone": "",
    "gender": "",
    "birthday": "",
    "bio": "",
    "avatar": "",
}
PROFILE_TEXT_LIMITS = {
    "display_name": 30,
    "real_name": 30,
    "email": 80,
    "phone": 30,
    "gender": 20,
    "birthday": 30,
    "bio": 200,
}
AVATAR_MAX_LENGTH = 420_000

load_dotenv(BASE_DIR / ".env", override=True)


def hash_password(password: str):
    return hashlib.sha256(f"{PASSWORD_SALT}:{password}".encode("utf-8")).hexdigest()


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_connection():
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


def ensure_user_identity(user):
    """
    将兼容 JSON 存储里的登录用户同步到规范 users 表，返回稳定 user_id。
    """
    username = (user or {}).get("username", "").strip()
    if not username or not is_database_enabled():
        return None

    password_hash = (user or {}).get("password_hash") or hash_password(secrets.token_urlsafe(12))
    role = normalize_role((user or {}).get("role", "user"))

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    password_hash = VALUES(password_hash),
                    role = VALUES(role),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (username, password_hash, role)
            )
            cursor.execute("SELECT id FROM users WHERE username = %s LIMIT 1", (username,))
            row = cursor.fetchone()

    return row.get("id") if row else None


def default_users():
    return [
        {
            "username": "admin",
            "password_hash": hash_password("admin123"),
            "role": "admin",
            "active": True,
            "display_name": "管理员",
            "real_name": "",
            "email": "",
            "phone": "",
            "gender": "",
            "birthday": "",
            "bio": "",
            "avatar": "",
            "create_time": now_text(),
            "update_time": now_text()
        }
    ]


def ensure_user_file():
    if is_database_enabled():
        load_json_data(USER_FILE, default_users)
        return

    if USER_FILE.exists():
        return

    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(default_users(), f, ensure_ascii=False, indent=2)


def ensure_session_file():
    if is_database_enabled():
        load_json_data(SESSION_FILE, dict)
        return

    if SESSION_FILE.exists():
        return

    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)


def load_users():
    if is_database_enabled():
        users = load_json_data(USER_FILE, default_users)
    else:
        ensure_user_file()
        with open(USER_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)

    changed = False
    for user in users:
        if "role" not in user:
            user["role"] = "user"
            changed = True
        if "active" not in user:
            user["active"] = True
            changed = True
        if "update_time" not in user:
            user["update_time"] = user.get("create_time", now_text())
            changed = True
        for key, default_value in PROFILE_DEFAULTS.items():
            if key not in user:
                user[key] = user.get("username", "") if key == "display_name" else default_value
                changed = True

    if changed:
        save_users(users)

    return users


def save_users(users):
    if is_database_enabled():
        save_json_data(USER_FILE, users)
        return

    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def load_sessions():
    if is_database_enabled():
        return load_json_data(SESSION_FILE, dict)

    ensure_session_file()
    with open(SESSION_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_sessions(sessions):
    if is_database_enabled():
        save_json_data(SESSION_FILE, sessions)
        return

    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def public_user(user):
    user_id = ensure_user_identity(user)

    return {
        "id": user_id,
        "username": user.get("username", ""),
        "display_name": user.get("display_name") or user.get("username", ""),
        "real_name": user.get("real_name", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "gender": user.get("gender", ""),
        "birthday": user.get("birthday", ""),
        "bio": user.get("bio", ""),
        "avatar": user.get("avatar", ""),
        "role": user.get("role", "user"),
        "active": user.get("active", True),
        "create_time": user.get("create_time", ""),
        "update_time": user.get("update_time", "")
    }


def normalize_role(role: str):
    return "admin" if role == "admin" else "user"


def find_user(username: str):
    username = (username or "").strip()
    for user in load_users():
        if user.get("username") == username:
            return user
    return None


def admin_count(users):
    return sum(1 for user in users if user.get("role") == "admin" and user.get("active", True))


def register_user(username: str, password: str):
    username = (username or "").strip()
    password = password or ""

    if len(username) < 3 or len(password) < 6:
        return None, "用户名至少3位，密码至少6位。"

    users = load_users()
    if any(item.get("username") == username for item in users):
        return None, "用户名已存在。"

    user = {
        "username": username,
        "password_hash": hash_password(password),
        "role": "user",
        "active": True,
        "display_name": username,
        "real_name": "",
        "email": "",
        "phone": "",
        "gender": "",
        "birthday": "",
        "bio": "",
        "avatar": "",
        "create_time": now_text(),
        "update_time": now_text()
    }
    users.append(user)
    save_users(users)
    return public_user(user), "注册成功。"


def authenticate_user(username: str, password: str):
    users = load_users()
    password_hash = hash_password(password or "")

    for user in users:
        if user.get("username") == (username or "").strip() and user.get("password_hash") == password_hash:
            if not user.get("active", True):
                return None
            return public_user(user)

    return None


def create_session(username: str):
    user = find_user(username)
    if not user or not user.get("active", True):
        return None

    token = secrets.token_urlsafe(32)
    sessions = load_sessions()
    sessions[token] = {
        "username": username,
        "create_time": now_text()
    }
    save_sessions(sessions)
    return token


def token_from_authorization(authorization: str):
    authorization = authorization or ""
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return authorization.strip()


def user_from_token(authorization: str):
    token = token_from_authorization(authorization)
    if not token:
        return None

    sessions = load_sessions()
    session = sessions.get(token)
    if not session:
        return None

    user = find_user(session.get("username", ""))
    if not user or not user.get("active", True):
        return None

    return public_user(user)


def create_user(username: str, password: str, role: str = "user", active=True):
    username = (username or "").strip()
    password = password or ""

    if len(username) < 3 or len(password) < 6:
        return None, "用户名至少3位，密码至少6位。"

    users = load_users()
    if any(item.get("username") == username for item in users):
        return None, "用户名已存在。"

    user = {
        "username": username,
        "password_hash": hash_password(password),
        "role": normalize_role(role),
        "active": bool(active),
        "display_name": username,
        "real_name": "",
        "email": "",
        "phone": "",
        "gender": "",
        "birthday": "",
        "bio": "",
        "avatar": "",
        "create_time": now_text(),
        "update_time": now_text()
    }
    users.append(user)
    save_users(users)
    return public_user(user), "用户创建成功。"


def update_user(username: str, fields: dict):
    users = load_users()
    target = None

    for user in users:
        if user.get("username") == (username or "").strip():
            target = user
            break

    if not target:
        return None, "用户不存在。"

    next_role = normalize_role(fields.get("role", target.get("role", "user")))
    next_active = fields.get("active", target.get("active", True))
    next_active = bool(next_active)

    if target.get("role") == "admin" and (next_role != "admin" or not next_active):
        simulated = []
        for user in users:
            copied = dict(user)
            if copied.get("username") == target.get("username"):
                copied["role"] = next_role
                copied["active"] = next_active
            simulated.append(copied)

        if admin_count(simulated) == 0:
            return None, "至少需要保留一个启用状态的管理员。"

    target["role"] = next_role
    target["active"] = next_active

    password = fields.get("password", "")
    if password:
        if len(password) < 6:
            return None, "新密码至少6位。"
        target["password_hash"] = hash_password(password)

    for key in PROFILE_DEFAULTS:
        if key in fields:
            target[key] = clean_profile_text(key, fields.get(key, ""))

    target["update_time"] = now_text()
    save_users(users)
    return public_user(target), "用户更新成功。"


def clean_profile_text(key: str, value):
    text = str(value or "").strip()
    limit = PROFILE_TEXT_LIMITS.get(key)

    if limit:
        return text[:limit]

    return text


def clean_avatar(value):
    avatar = str(value or "").strip()

    if not avatar:
        return ""

    if len(avatar) > AVATAR_MAX_LENGTH:
        raise ValueError("头像图片过大，请选择更小的图片。")

    if avatar.startswith("data:image/") or avatar.startswith("http://") or avatar.startswith("https://"):
        return avatar

    raise ValueError("头像格式不支持，请上传图片文件。")


def sync_session_username(old_username: str, new_username: str):
    if old_username == new_username:
        return

    sessions = load_sessions()
    changed = False

    for session in sessions.values():
        if session.get("username") == old_username:
            session["username"] = new_username
            changed = True

    if changed:
        save_sessions(sessions)


def sync_normalized_username(old_username: str, new_username: str):
    if old_username == new_username or not is_database_enabled():
        return

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE users
                    SET username = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE username = %s
                    """,
                    (new_username, old_username)
                )
    except Exception:
        return


def update_current_profile(current_username: str, fields: dict):
    users = load_users()
    target = None
    old_username = (current_username or "").strip()

    for user in users:
        if user.get("username") == old_username:
            target = user
            break

    if not target:
        return None, "用户不存在。"

    next_username = str(fields.get("username", target.get("username", "")) or "").strip()
    if len(next_username) < 3:
        return None, "用户名至少3位。"

    if next_username != old_username and any(item.get("username") == next_username for item in users):
        return None, "用户名已存在。"

    try:
        next_avatar = clean_avatar(fields.get("avatar", target.get("avatar", "")))
    except ValueError as exc:
        return None, str(exc)

    target["username"] = next_username
    target["display_name"] = clean_profile_text("display_name", fields.get("display_name", target.get("display_name") or next_username)) or next_username
    target["real_name"] = clean_profile_text("real_name", fields.get("real_name", target.get("real_name", "")))
    target["email"] = clean_profile_text("email", fields.get("email", target.get("email", "")))
    target["phone"] = clean_profile_text("phone", fields.get("phone", target.get("phone", "")))
    target["gender"] = clean_profile_text("gender", fields.get("gender", target.get("gender", "")))
    target["birthday"] = clean_profile_text("birthday", fields.get("birthday", target.get("birthday", "")))
    target["bio"] = clean_profile_text("bio", fields.get("bio", target.get("bio", "")))
    target["avatar"] = next_avatar
    target["update_time"] = now_text()

    save_users(users)
    sync_session_username(old_username, next_username)
    sync_normalized_username(old_username, next_username)
    return public_user(target), "个人资料已保存。"


def change_current_password(current_username: str, old_password: str, new_password: str):
    users = load_users()
    target = None

    for user in users:
        if user.get("username") == (current_username or "").strip():
            target = user
            break

    if not target:
        return None, "用户不存在。"

    if target.get("password_hash") != hash_password(old_password or ""):
        return None, "当前密码不正确。"

    if len(new_password or "") < 6:
        return None, "新密码至少6位。"

    target["password_hash"] = hash_password(new_password)
    target["update_time"] = now_text()
    save_users(users)
    return public_user(target), "密码已修改。"


def delete_user(username: str, current_username: str = ""):
    username = (username or "").strip()
    users = load_users()
    target = None

    for user in users:
        if user.get("username") == username:
            target = user
            break

    if not target:
        return False, "用户不存在。"

    if username == current_username:
        return False, "不能删除当前登录的管理员账号。"

    remaining = [user for user in users if user.get("username") != username]
    if target.get("role") == "admin" and admin_count(remaining) == 0:
        return False, "至少需要保留一个启用状态的管理员。"

    save_users(remaining)

    sessions = load_sessions()
    sessions = {
        token: session
        for token, session in sessions.items()
        if session.get("username") != username
    }
    save_sessions(sessions)

    return True, "用户删除成功。"


def list_public_users():
    return [public_user(user) for user in load_users()]
