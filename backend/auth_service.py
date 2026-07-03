import hashlib
import secrets
from datetime import datetime

from db import ensure_normalized_schema, get_connection, parse_time


PASSWORD_SALT = "rag-medical-assistant-demo"


def hash_password(password: str):
    return hashlib.sha256(f"{PASSWORD_SALT}:{password}".encode("utf-8")).hexdigest()


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_time(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


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


def public_user(user):
    return {
        "username": user.get("username", ""),
        "role": user.get("role", "user"),
        "active": bool(user.get("active", True)),
        "create_time": format_time(user.get("create_time")),
        "update_time": format_time(user.get("update_time"))
    }


def db_user(row):
    if not row:
        return None
    return {
        "id": row.get("id"),
        "username": row.get("username", ""),
        "password_hash": row.get("password_hash", ""),
        "role": row.get("role", "user"),
        "active": bool(row.get("active", True)),
        "create_time": format_time(row.get("create_time")),
        "update_time": format_time(row.get("update_time")),
    }


def normalize_role(role: str):
    return "admin" if role == "admin" else "user"


def ensure_default_admin():
    ensure_normalized_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM users")
            if cursor.fetchone()["total"]:
                return

            admin = default_users()[0]
            cursor.execute(
                """
                INSERT INTO users
                (username, password_hash, role, active, create_time, update_time)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    admin["username"],
                    admin["password_hash"],
                    admin["role"],
                    1 if admin["active"] else 0,
                    parse_time(admin["create_time"]),
                    parse_time(admin["update_time"]),
                ),
            )


def ensure_user_file():
    ensure_default_admin()


def ensure_session_file():
    ensure_normalized_schema()


def load_users():
    ensure_default_admin()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, password_hash, role, active, create_time, update_time
                FROM users
                ORDER BY id ASC
                """
            )
            return [db_user(row) for row in cursor.fetchall()]


def save_users(users):
    ensure_normalized_schema()
    with get_connection(autocommit=False) as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM user_sessions")
                cursor.execute("DELETE FROM users")
                for user in users or []:
                    username = (user.get("username") or "").strip()
                    if not username:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO users
                        (username, password_hash, role, active, create_time, update_time)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            username,
                            user.get("password_hash") or hash_password("admin123"),
                            normalize_role(user.get("role", "user")),
                            1 if user.get("active", True) else 0,
                            parse_time(user.get("create_time")) or datetime.now(),
                            parse_time(user.get("update_time")) or datetime.now(),
                        ),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def load_sessions():
    ensure_normalized_schema()
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.token, u.username, s.create_time
                FROM user_sessions s
                JOIN users u ON u.id = s.user_id
                ORDER BY s.create_time DESC
                """
            )
            return {
                row["token"]: {
                    "username": row["username"],
                    "create_time": format_time(row.get("create_time"))
                }
                for row in cursor.fetchall()
            }


def save_sessions(sessions):
    ensure_normalized_schema()
    with get_connection(autocommit=False) as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM user_sessions")
                for token, session in (sessions or {}).items():
                    username = (session.get("username") or "").strip()
                    if not token or not username:
                        continue
                    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                    row = cursor.fetchone()
                    if not row:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO user_sessions (token, user_id, create_time)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            user_id = VALUES(user_id),
                            create_time = VALUES(create_time)
                        """,
                        (
                            token,
                            row["id"],
                            parse_time(session.get("create_time")) or datetime.now(),
                        ),
                    )
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def find_user(username: str):
    ensure_default_admin()
    username = (username or "").strip()
    if not username:
        return None

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, password_hash, role, active, create_time, update_time
                FROM users
                WHERE username = %s
                LIMIT 1
                """,
                (username,),
            )
            return db_user(cursor.fetchone())


def admin_count(users):
    return sum(1 for user in users if user.get("role") == "admin" and user.get("active", True))


def register_user(username: str, password: str):
    return create_user(username, password, role="user", active=True, register_mode=True)


def authenticate_user(username: str, password: str):
    user = find_user(username)
    if not user or not user.get("active", True):
        return None

    if user.get("password_hash") != hash_password(password or ""):
        return None

    return public_user(user)


def create_session(username: str):
    user = find_user(username)
    if not user or not user.get("active", True):
        return None

    token = secrets.token_urlsafe(32)
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_sessions (token, user_id, create_time, last_seen_at)
                VALUES (%s, %s, %s, %s)
                """,
                (token, user["id"], datetime.now(), datetime.now()),
            )
    return token


def token_from_authorization(authorization: str):
    authorization = authorization or ""
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return authorization.strip()


def user_from_token(authorization: str):
    ensure_normalized_schema()
    token = token_from_authorization(authorization)
    if not token:
        return None

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    u.id, u.username, u.password_hash, u.role, u.active,
                    u.create_time, u.update_time
                FROM user_sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = %s
                LIMIT 1
                """,
                (token,),
            )
            user = db_user(cursor.fetchone())
            if user:
                cursor.execute(
                    "UPDATE user_sessions SET last_seen_at = %s WHERE token = %s",
                    (datetime.now(), token),
                )

    if not user or not user.get("active", True):
        return None

    return public_user(user)


def create_user(username: str, password: str, role: str = "user", active=True, register_mode=False):
    ensure_default_admin()
    username = (username or "").strip()
    password = password or ""

    if len(username) < 3 or len(password) < 6:
        return None, "用户名至少3位，密码至少6位。"

    if find_user(username):
        return None, "用户名已存在。"

    user = {
        "username": username,
        "password_hash": hash_password(password),
        "role": normalize_role(role),
        "active": bool(active),
        "create_time": now_text(),
        "update_time": now_text()
    }

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users
                (username, password_hash, role, active, create_time, update_time)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    user["username"],
                    user["password_hash"],
                    user["role"],
                    1 if user["active"] else 0,
                    parse_time(user["create_time"]),
                    parse_time(user["update_time"]),
                ),
            )
            user["id"] = cursor.lastrowid

    return public_user(user), "注册成功。" if register_mode else "用户创建成功。"


def update_user(username: str, fields: dict):
    ensure_default_admin()
    target = find_user(username)
    if not target:
        return None, "用户不存在。"

    next_role = normalize_role((fields or {}).get("role", target.get("role", "user")))
    next_active = bool((fields or {}).get("active", target.get("active", True)))

    if target.get("role") == "admin" and (next_role != "admin" or not next_active):
        simulated = []
        for user in load_users():
            copied = dict(user)
            if copied.get("username") == target.get("username"):
                copied["role"] = next_role
                copied["active"] = next_active
            simulated.append(copied)

        if admin_count(simulated) == 0:
            return None, "至少需要保留一个启用状态的管理员。"

    password_hash = target.get("password_hash")
    password = (fields or {}).get("password", "")
    if password:
        if len(password) < 6:
            return None, "新密码至少6位。"
        password_hash = hash_password(password)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET role = %s,
                    active = %s,
                    password_hash = %s,
                    update_time = %s
                WHERE username = %s
                """,
                (
                    next_role,
                    1 if next_active else 0,
                    password_hash,
                    datetime.now(),
                    target["username"],
                ),
            )

    return public_user(find_user(target["username"])), "用户更新成功。"


def delete_user(username: str, current_username: str = ""):
    ensure_default_admin()
    username = (username or "").strip()
    target = find_user(username)

    if not target:
        return False, "用户不存在。"

    if username == current_username:
        return False, "不能删除当前登录的管理员账号。"

    remaining = [user for user in load_users() if user.get("username") != username]
    if target.get("role") == "admin" and admin_count(remaining) == 0:
        return False, "至少需要保留一个启用状态的管理员。"

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))

    return True, "用户删除成功。"


def list_public_users():
    return [public_user(user) for user in load_users()]
