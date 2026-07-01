import hashlib
import json
import secrets
from pathlib import Path
from datetime import datetime

from storage import is_database_enabled, load_json_data, save_json_data


BASE_DIR = Path(__file__).resolve().parent
USER_FILE = BASE_DIR / "data" / "users.json"
SESSION_FILE = BASE_DIR / "data" / "sessions.json"
PASSWORD_SALT = "rag-medical-assistant-demo"


def hash_password(password: str):
    return hashlib.sha256(f"{PASSWORD_SALT}:{password}".encode("utf-8")).hexdigest()


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def default_users():
    return [
        {
            "username": "admin",
            "password_hash": hash_password("admin123"),
            "role": "admin",
            "active": True,
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
    return {
        "username": user.get("username", ""),
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

    target["update_time"] = now_text()
    save_users(users)
    return public_user(target), "用户更新成功。"


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
