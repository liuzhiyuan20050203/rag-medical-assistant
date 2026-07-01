import json
import os
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")
load_dotenv()

_TABLE_READY = False


def is_database_enabled():
    return bool(os.getenv("DATABASE_URL", "").strip() or os.getenv("MYSQL_HOST", "").strip())


def _table_name():
    name = os.getenv("MYSQL_JSON_TABLE", "app_json_store").strip() or "app_json_store"
    if not re.match(r"^[A-Za-z0-9_]+$", name):
        raise ValueError("MYSQL_JSON_TABLE can only contain letters, numbers, and underscores")
    return name


def _database_config():
    url = os.getenv("DATABASE_URL", "").strip()

    if url:
        parsed = urlparse(url)
        if parsed.scheme not in {"mysql", "mysql+pymysql"}:
            raise ValueError("DATABASE_URL must use mysql:// or mysql+pymysql://")

        query = parse_qs(parsed.query)
        database = parsed.path.lstrip("/")
        if not database:
            raise ValueError("DATABASE_URL must include a database name")

        return {
            "host": parsed.hostname or "127.0.0.1",
            "port": parsed.port or 3306,
            "user": unquote(parsed.username or ""),
            "password": unquote(parsed.password or ""),
            "database": database,
            "charset": query.get("charset", ["utf8mb4"])[0],
        }

    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1").strip(),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "rag_user").strip(),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", os.getenv("MYSQL_DB", "rag_medical")).strip(),
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4").strip() or "utf8mb4",
    }


def _connect():
    import pymysql
    import pymysql.cursors

    config = _database_config()
    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset=config["charset"],
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )


def ensure_json_store():
    global _TABLE_READY

    if _TABLE_READY:
        return

    table = _table_name()
    sql = f"""
    CREATE TABLE IF NOT EXISTS `{table}` (
        `store_key` VARCHAR(80) NOT NULL PRIMARY KEY,
        `payload` LONGTEXT NOT NULL,
        `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """

    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)

    _TABLE_READY = True


def _decode_payload(payload):
    if payload is None:
        return None

    if isinstance(payload, (dict, list)):
        return payload

    return json.loads(payload)


def db_key_exists(key):
    ensure_json_store()
    table = _table_name()

    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT 1 FROM `{table}` WHERE `store_key` = %s LIMIT 1", (key,))
            return cursor.fetchone() is not None


def load_db_json(key, seed_data=None):
    ensure_json_store()
    table = _table_name()

    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT `payload` FROM `{table}` WHERE `store_key` = %s", (key,))
            row = cursor.fetchone()

    if row:
        return _decode_payload(row["payload"])

    if seed_data is None:
        return None

    data = seed_data() if callable(seed_data) else seed_data
    save_db_json(key, data)
    return data


def save_db_json(key, data):
    ensure_json_store()
    table = _table_name()
    payload = json.dumps(data, ensure_ascii=False)

    with _connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                INSERT INTO `{table}` (`store_key`, `payload`)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE `payload` = VALUES(`payload`)
                """,
                (key, payload),
            )


def _default_value(default_factory):
    if callable(default_factory):
        return default_factory()
    if default_factory is None:
        return []
    return default_factory


def _read_local_json(file_path, default_factory=None):
    path = Path(file_path)

    if not path.exists():
        return _default_value(default_factory)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _store_key(file_path):
    return Path(file_path).stem


def load_json_data(file_path, default_factory=None):
    if is_database_enabled():
        return load_db_json(
            _store_key(file_path),
            seed_data=lambda: _read_local_json(file_path, default_factory),
        )

    return _read_local_json(file_path, default_factory)


def save_json_data(file_path, data):
    if is_database_enabled():
        save_db_json(_store_key(file_path), data)
        return

    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def migrate_local_json_file(file_path, default_factory=None):
    data = _read_local_json(file_path, default_factory)
    save_db_json(_store_key(file_path), data)
    return _store_key(file_path), data


def get_storage_status():
    if not is_database_enabled():
        return {
            "mode": "json",
            "database_enabled": False,
            "message": "Using local JSON files in backend/data.",
        }

    config = _database_config()
    status = {
        "mode": "mysql",
        "database_enabled": True,
        "host": config["host"],
        "port": config["port"],
        "database": config["database"],
        "table": _table_name(),
        "connected": False,
    }

    try:
        ensure_json_store()
        status["connected"] = True
        status["message"] = "Connected to MySQL JSON store."
    except Exception as exc:
        status["error"] = str(exc)
        status["message"] = "Unable to connect to MySQL JSON store."

    return status
