import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env", override=True)
load_dotenv()

_SCHEMA_READY = False


def is_database_enabled():
    return True


def database_config():
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1").strip() or "127.0.0.1",
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "rag_medical").strip() or "rag_medical",
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", os.getenv("MYSQL_DB", "rag_medical")).strip() or "rag_medical",
        "charset": os.getenv("MYSQL_CHARSET", "utf8mb4").strip() or "utf8mb4",
    }


def get_connection(autocommit=True):
    import pymysql
    import pymysql.cursors

    config = database_config()
    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset=config["charset"],
        autocommit=autocommit,
        cursorclass=pymysql.cursors.DictCursor,
    )


def table_exists(cursor, table_name):
    cursor.execute("SHOW TABLES LIKE %s", (table_name,))
    return cursor.fetchone() is not None


def column_exists(cursor, table_name, column_name):
    if not table_exists(cursor, table_name):
        return False
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}` LIKE %s", (column_name,))
    return cursor.fetchone() is not None


def add_column_if_missing(cursor, table_name, column_name, ddl):
    if not column_exists(cursor, table_name, column_name):
        cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN {ddl}")


def json_dumps(data):
    return json.dumps(data if data is not None else [], ensure_ascii=False)


def json_loads(text, default=None):
    if default is None:
        default = []
    if text is None or text == "":
        return default
    if isinstance(text, (list, dict)):
        return text
    try:
        return json.loads(text)
    except Exception:
        return default


def split_terms(value):
    if not value:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = re.split(r"[、,，;；\s]+", str(value))

    result = []
    seen = set()
    for item in raw_items:
        text = str(item).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def parse_time(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), pattern)
        except ValueError:
            pass
    return value


def create_schema(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `disease_categories` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` VARCHAR(120) NOT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_disease_categories_name` (`name`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `diseases` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` VARCHAR(120) NOT NULL,
            `category_id` INT NULL,
            `description` TEXT NULL,
            `care_advice` TEXT NULL,
            `medicine_notice` TEXT NULL,
            `warning` TEXT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_diseases_name` (`name`),
            KEY `idx_diseases_category_id` (`category_id`),
            CONSTRAINT `fk_diseases_category`
                FOREIGN KEY (`category_id`) REFERENCES `disease_categories` (`id`)
                ON DELETE SET NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `disease_symptoms` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `disease_id` INT NOT NULL,
            `symptom` VARCHAR(120) NOT NULL,
            `sort_order` INT NOT NULL DEFAULT 0,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_disease_symptoms` (`disease_id`, `symptom`),
            KEY `idx_disease_symptoms_symptom` (`symptom`),
            CONSTRAINT `fk_disease_symptoms_disease`
                FOREIGN KEY (`disease_id`) REFERENCES `diseases` (`id`)
                ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `medicine_types` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` VARCHAR(120) NOT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_medicine_types_name` (`name`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `medicines` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` VARCHAR(120) NOT NULL,
            `type_id` INT NULL,
            `usage_info` TEXT NULL,
            `notice` TEXT NULL,
            `contraindication` TEXT NULL,
            `side_effect` TEXT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_medicines_name` (`name`),
            KEY `idx_medicines_type_id` (`type_id`),
            CONSTRAINT `fk_medicines_type`
                FOREIGN KEY (`type_id`) REFERENCES `medicine_types` (`id`)
                ON DELETE SET NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `warning_rules` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `keyword` VARCHAR(120) NOT NULL,
            `risk_level` VARCHAR(30) NOT NULL DEFAULT 'high',
            `advice` TEXT NULL,
            `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_warning_rules_keyword` (`keyword`),
            KEY `idx_warning_rules_risk_level` (`risk_level`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `users` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `username` VARCHAR(80) NOT NULL,
            `password_hash` CHAR(64) NOT NULL,
            `role` VARCHAR(20) NOT NULL DEFAULT 'user',
            `active` TINYINT(1) NOT NULL DEFAULT 1,
            `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `update_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_users_username` (`username`),
            KEY `idx_users_role_active` (`role`, `active`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `user_sessions` (
            `token` VARCHAR(128) NOT NULL,
            `user_id` BIGINT NOT NULL,
            `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `last_seen_at` DATETIME NULL,
            PRIMARY KEY (`token`),
            KEY `idx_user_sessions_user_id` (`user_id`),
            CONSTRAINT `fk_user_sessions_user`
                FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
                ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `search_logs` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `kind` VARCHAR(40) NOT NULL,
            `keyword` VARCHAR(255) NOT NULL DEFAULT '',
            `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (`id`),
            KEY `idx_search_logs_kind_time` (`kind`, `create_time`)
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `search_log_matches` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `search_log_id` BIGINT NOT NULL,
            `title` VARCHAR(255) NOT NULL,
            `sort_order` INT NOT NULL DEFAULT 0,
            PRIMARY KEY (`id`),
            KEY `idx_search_log_matches_log` (`search_log_id`, `sort_order`),
            KEY `idx_search_log_matches_title` (`title`),
            CONSTRAINT `fk_search_log_matches_log`
                FOREIGN KEY (`search_log_id`) REFERENCES `search_logs` (`id`)
                ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `chat_history` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `user_id` BIGINT NULL,
            `question` TEXT NOT NULL,
            `answer` LONGTEXT NULL,
            `has_warning` TINYINT(1) NOT NULL DEFAULT 0,
            `llm_used` TINYINT(1) NOT NULL DEFAULT 0,
            `llm_provider` VARCHAR(80) NOT NULL DEFAULT '',
            `llm_model` VARCHAR(120) NOT NULL DEFAULT '',
            `is_error` TINYINT(1) NOT NULL DEFAULT 0,
            `error_reason` TEXT NULL,
            `satisfaction` VARCHAR(30) NOT NULL DEFAULT '',
            `rating` INT NOT NULL DEFAULT 0,
            `feedback_text` TEXT NULL,
            `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            `review_time` DATETIME NULL,
            PRIMARY KEY (`id`),
            KEY `idx_chat_history_create_time` (`create_time`),
            KEY `idx_chat_history_user_id` (`user_id`),
            CONSTRAINT `fk_chat_history_user`
                FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
                ON DELETE SET NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `chat_history_warning_matches` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `history_id` BIGINT NOT NULL,
            `warning_rule_id` INT NULL,
            `keyword` VARCHAR(120) NOT NULL,
            `sort_order` INT NOT NULL DEFAULT 0,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uk_chat_warning_keyword` (`history_id`, `keyword`),
            KEY `idx_chat_warning_rule` (`warning_rule_id`),
            CONSTRAINT `fk_chat_warning_history`
                FOREIGN KEY (`history_id`) REFERENCES `chat_history` (`id`)
                ON DELETE CASCADE,
            CONSTRAINT `fk_chat_warning_rule`
                FOREIGN KEY (`warning_rule_id`) REFERENCES `warning_rules` (`id`)
                ON DELETE SET NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `chat_history_retrieved_docs` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `history_id` BIGINT NOT NULL,
            `doc_type` VARCHAR(30) NOT NULL,
            `source_table` VARCHAR(80) NOT NULL DEFAULT '',
            `source_id` BIGINT NULL,
            `title` VARCHAR(255) NOT NULL DEFAULT '',
            `score` DOUBLE NULL,
            `content` LONGTEXT NULL,
            `sort_order` INT NOT NULL DEFAULT 0,
            PRIMARY KEY (`id`),
            KEY `idx_chat_retrieved_history` (`history_id`, `sort_order`),
            KEY `idx_chat_retrieved_source` (`source_table`, `source_id`),
            CONSTRAINT `fk_chat_retrieved_history`
                FOREIGN KEY (`history_id`) REFERENCES `chat_history` (`id`)
                ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `chat_history_contexts` (
            `history_id` BIGINT NOT NULL,
            `query_text` TEXT NULL,
            `expanded_query` TEXT NULL,
            `has_matches` TINYINT(1) NOT NULL DEFAULT 0,
            PRIMARY KEY (`history_id`),
            CONSTRAINT `fk_chat_context_history`
                FOREIGN KEY (`history_id`) REFERENCES `chat_history` (`id`)
                ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `chat_history_database_matches` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `history_id` BIGINT NOT NULL,
            `doc_type` VARCHAR(30) NOT NULL,
            `source_table` VARCHAR(80) NOT NULL DEFAULT '',
            `source_id` BIGINT NULL,
            `title` VARCHAR(255) NOT NULL DEFAULT '',
            `score` DOUBLE NULL,
            `sort_order` INT NOT NULL DEFAULT 0,
            PRIMARY KEY (`id`),
            KEY `idx_chat_db_matches_history` (`history_id`, `sort_order`),
            KEY `idx_chat_db_matches_source` (`source_table`, `source_id`),
            CONSTRAINT `fk_chat_db_matches_history`
                FOREIGN KEY (`history_id`) REFERENCES `chat_history` (`id`)
                ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS `chat_history_database_match_fields` (
            `id` BIGINT NOT NULL AUTO_INCREMENT,
            `match_id` BIGINT NOT NULL,
            `matched_field` VARCHAR(255) NOT NULL,
            `sort_order` INT NOT NULL DEFAULT 0,
            PRIMARY KEY (`id`),
            KEY `idx_chat_db_match_fields_match` (`match_id`, `sort_order`),
            CONSTRAINT `fk_chat_db_match_fields_match`
                FOREIGN KEY (`match_id`) REFERENCES `chat_history_database_matches` (`id`)
                ON DELETE CASCADE
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """
    )


def upgrade_legacy_schema(cursor):
    if table_exists(cursor, "diseases"):
        add_column_if_missing(cursor, "diseases", "category_id", "`category_id` INT NULL AFTER `name`")

    if table_exists(cursor, "medicines"):
        add_column_if_missing(cursor, "medicines", "type_id", "`type_id` INT NULL AFTER `name`")


def upsert_named_row(cursor, table_name, name):
    name = (name or "").strip()
    if not name:
        return None

    cursor.execute(
        f"""
        INSERT INTO `{table_name}` (`name`)
        VALUES (%s)
        ON DUPLICATE KEY UPDATE `name` = VALUES(`name`)
        """,
        (name,),
    )
    cursor.execute(f"SELECT `id` FROM `{table_name}` WHERE `name` = %s LIMIT 1", (name,))
    row = cursor.fetchone()
    return row["id"] if row else None


def replace_disease_symptoms(cursor, disease_id, symptoms):
    cursor.execute("DELETE FROM `disease_symptoms` WHERE `disease_id` = %s", (disease_id,))
    for index, symptom in enumerate(split_terms(symptoms), start=1):
        cursor.execute(
            """
            INSERT INTO `disease_symptoms` (`disease_id`, `symptom`, `sort_order`)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE `sort_order` = VALUES(`sort_order`)
            """,
            (disease_id, symptom, index),
        )


def upsert_disease_record(cursor, item):
    if not isinstance(item, dict):
        return None

    name = (item.get("name") or "").strip()
    if not name:
        return None

    category_id = upsert_named_row(cursor, "disease_categories", item.get("category", ""))
    cursor.execute(
        """
        INSERT INTO `diseases`
        (`name`, `category_id`, `description`, `care_advice`, `medicine_notice`, `warning`)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `category_id` = VALUES(`category_id`),
            `description` = VALUES(`description`),
            `care_advice` = VALUES(`care_advice`),
            `medicine_notice` = VALUES(`medicine_notice`),
            `warning` = VALUES(`warning`),
            `updated_at` = CURRENT_TIMESTAMP
        """,
        (
            name,
            category_id,
            item.get("description", "") or "",
            item.get("care_advice", "") or "",
            item.get("medicine_notice", "") or "",
            item.get("warning", "") or "",
        ),
    )
    cursor.execute("SELECT `id` FROM `diseases` WHERE `name` = %s LIMIT 1", (name,))
    row = cursor.fetchone()
    disease_id = row["id"] if row else None
    if disease_id:
        replace_disease_symptoms(cursor, disease_id, item.get("symptoms", []))
    return disease_id


def upsert_medicine_record(cursor, item):
    if not isinstance(item, dict):
        return None

    name = (item.get("name") or "").strip()
    if not name:
        return None

    medicine_type = item.get("type", item.get("category", "")) or ""
    type_id = upsert_named_row(cursor, "medicine_types", medicine_type)
    cursor.execute(
        """
        INSERT INTO `medicines`
        (`name`, `type_id`, `usage_info`, `notice`, `contraindication`, `side_effect`)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `type_id` = VALUES(`type_id`),
            `usage_info` = VALUES(`usage_info`),
            `notice` = VALUES(`notice`),
            `contraindication` = VALUES(`contraindication`),
            `side_effect` = VALUES(`side_effect`),
            `updated_at` = CURRENT_TIMESTAMP
        """,
        (
            name,
            type_id,
            item.get("usage", item.get("usage_info", "")) or "",
            item.get("notice", "") or "",
            item.get("contraindication", "") or "",
            item.get("side_effect", "") or "",
        ),
    )
    cursor.execute("SELECT `id` FROM `medicines` WHERE `name` = %s LIMIT 1", (name,))
    row = cursor.fetchone()
    return row["id"] if row else None


def upsert_warning_rule(cursor, item):
    if isinstance(item, str):
        keyword = item.strip()
        risk_level = "high"
        advice = "该症状可能存在较高健康风险，建议及时就医。"
    elif isinstance(item, dict):
        keyword = (item.get("keyword") or "").strip()
        risk_level = item.get("risk_level", "high") or "high"
        advice = item.get("advice", "") or "该症状可能存在较高健康风险，建议及时就医。"
    else:
        return None

    if not keyword:
        return None

    cursor.execute(
        """
        INSERT INTO `warning_rules` (`keyword`, `risk_level`, `advice`)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `risk_level` = VALUES(`risk_level`),
            `advice` = VALUES(`advice`),
            `updated_at` = CURRENT_TIMESTAMP
        """,
        (keyword, risk_level, advice),
    )
    cursor.execute("SELECT `id` FROM `warning_rules` WHERE `keyword` = %s LIMIT 1", (keyword,))
    row = cursor.fetchone()
    return row["id"] if row else None


def migrate_legacy_knowledge_columns(cursor):
    if table_exists(cursor, "diseases") and column_exists(cursor, "diseases", "category"):
        has_symptoms = column_exists(cursor, "diseases", "symptoms")
        fields = "`id`, `category`, `category_id`"
        if has_symptoms:
            fields += ", `symptoms`"

        cursor.execute(f"SELECT {fields} FROM `diseases`")
        for row in cursor.fetchall():
            category_id = row.get("category_id")
            if not category_id and row.get("category"):
                category_id = upsert_named_row(cursor, "disease_categories", row.get("category"))
                cursor.execute(
                    "UPDATE `diseases` SET `category_id` = %s WHERE `id` = %s",
                    (category_id, row["id"]),
                )

            if has_symptoms and row.get("symptoms"):
                cursor.execute(
                    "SELECT 1 FROM `disease_symptoms` WHERE `disease_id` = %s LIMIT 1",
                    (row["id"],),
                )
                if cursor.fetchone() is None:
                    replace_disease_symptoms(cursor, row["id"], row.get("symptoms"))

    if table_exists(cursor, "medicines") and column_exists(cursor, "medicines", "type"):
        cursor.execute("SELECT `id`, `type`, `type_id` FROM `medicines`")
        for row in cursor.fetchall():
            if not row.get("type_id") and row.get("type"):
                type_id = upsert_named_row(cursor, "medicine_types", row.get("type"))
                cursor.execute(
                    "UPDATE `medicines` SET `type_id` = %s WHERE `id` = %s",
                    (type_id, row["id"]),
                )


def source_from_doc(doc):
    source = doc.get("source") or {}
    raw = doc.get("raw") or {}
    doc_type = doc.get("doc_type", "")
    source_table = source.get("table", "")
    if not source_table and doc_type == "disease":
        source_table = "diseases"
    if not source_table and doc_type == "medicine":
        source_table = "medicines"

    source_id = source.get("record_id") or raw.get("id") or doc.get("record_id")
    try:
        source_id = int(source_id) if source_id not in (None, "") else None
    except (TypeError, ValueError):
        source_id = None

    return source_table, source_id


def insert_warning_matches(cursor, history_id, keywords):
    for index, keyword in enumerate(split_terms(keywords), start=1):
        cursor.execute("SELECT `id` FROM `warning_rules` WHERE `keyword` = %s", (keyword,))
        row = cursor.fetchone()
        cursor.execute(
            """
            INSERT INTO `chat_history_warning_matches`
            (`history_id`, `warning_rule_id`, `keyword`, `sort_order`)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                `warning_rule_id` = VALUES(`warning_rule_id`),
                `sort_order` = VALUES(`sort_order`)
            """,
            (history_id, row["id"] if row else None, keyword, index),
        )


def insert_retrieved_docs(cursor, history_id, docs):
    for index, doc in enumerate(docs or [], start=1):
        if not isinstance(doc, dict):
            continue
        source_table, source_id = source_from_doc(doc)
        cursor.execute(
            """
            INSERT INTO `chat_history_retrieved_docs`
            (`history_id`, `doc_type`, `source_table`, `source_id`, `title`,
             `score`, `content`, `sort_order`)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                history_id,
                doc.get("doc_type", "") or "",
                source_table or "",
                source_id,
                doc.get("title", "") or "",
                doc.get("score"),
                doc.get("content", "") or "",
                index,
            ),
        )


def insert_database_context(cursor, history_id, database_context):
    context = database_context or {}
    cursor.execute(
        """
        INSERT INTO `chat_history_contexts`
        (`history_id`, `query_text`, `expanded_query`, `has_matches`)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            `query_text` = VALUES(`query_text`),
            `expanded_query` = VALUES(`expanded_query`),
            `has_matches` = VALUES(`has_matches`)
        """,
        (
            history_id,
            context.get("query", "") or "",
            context.get("expanded_query", "") or "",
            1 if context.get("has_matches") else 0,
        ),
    )

    ordered_matches = []
    for item in context.get("diseases", []) or []:
        ordered_matches.append(item)
    for item in context.get("medicines", []) or []:
        ordered_matches.append(item)

    for index, item in enumerate(ordered_matches, start=1):
        if not isinstance(item, dict):
            continue
        raw = item.get("raw") or {}
        doc_type = item.get("doc_type", "") or ""
        source_table = "diseases" if doc_type == "disease" else "medicines" if doc_type == "medicine" else ""
        source_id = raw.get("id") or item.get("record_id")
        try:
            source_id = int(source_id) if source_id not in (None, "") else None
        except (TypeError, ValueError):
            source_id = None

        cursor.execute(
            """
            INSERT INTO `chat_history_database_matches`
            (`history_id`, `doc_type`, `source_table`, `source_id`, `title`,
             `score`, `sort_order`)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                history_id,
                doc_type,
                source_table,
                source_id,
                item.get("title", "") or "",
                item.get("score"),
                index,
            ),
        )
        match_id = cursor.lastrowid
        for field_index, field in enumerate(item.get("matched_fields", []) or [], start=1):
            cursor.execute(
                """
                INSERT INTO `chat_history_database_match_fields`
                (`match_id`, `matched_field`, `sort_order`)
                VALUES (%s, %s, %s)
                """,
                (match_id, str(field), field_index),
            )


def replace_history_relations(cursor, history_id, warning_keywords=None, retrieved_docs=None, database_context=None):
    cursor.execute("DELETE FROM `chat_history_warning_matches` WHERE `history_id` = %s", (history_id,))
    cursor.execute("DELETE FROM `chat_history_retrieved_docs` WHERE `history_id` = %s", (history_id,))
    cursor.execute("DELETE FROM `chat_history_contexts` WHERE `history_id` = %s", (history_id,))
    cursor.execute("DELETE FROM `chat_history_database_matches` WHERE `history_id` = %s", (history_id,))

    insert_warning_matches(cursor, history_id, warning_keywords or [])
    insert_retrieved_docs(cursor, history_id, retrieved_docs or [])
    insert_database_context(cursor, history_id, database_context or {})


def migrate_legacy_history_columns(cursor):
    if not table_exists(cursor, "chat_history"):
        return

    has_warning_keywords = column_exists(cursor, "chat_history", "warning_keywords")
    has_retrieved_docs = column_exists(cursor, "chat_history", "retrieved_docs")
    has_database_context = column_exists(cursor, "chat_history", "database_context")

    if not any([has_warning_keywords, has_retrieved_docs, has_database_context]):
        return

    fields = ["`id`"]
    if has_warning_keywords:
        fields.append("`warning_keywords`")
    if has_retrieved_docs:
        fields.append("`retrieved_docs`")
    if has_database_context:
        fields.append("`database_context`")

    cursor.execute(f"SELECT {', '.join(fields)} FROM `chat_history`")
    for row in cursor.fetchall():
        history_id = row["id"]

        cursor.execute(
            "SELECT 1 FROM `chat_history_retrieved_docs` WHERE `history_id` = %s LIMIT 1",
            (history_id,),
        )
        retrieved_ready = cursor.fetchone() is not None

        cursor.execute(
            "SELECT 1 FROM `chat_history_contexts` WHERE `history_id` = %s LIMIT 1",
            (history_id,),
        )
        context_ready = cursor.fetchone() is not None

        cursor.execute(
            "SELECT 1 FROM `chat_history_warning_matches` WHERE `history_id` = %s LIMIT 1",
            (history_id,),
        )
        warning_ready = cursor.fetchone() is not None

        if not warning_ready and has_warning_keywords:
            insert_warning_matches(cursor, history_id, json_loads(row.get("warning_keywords"), []))

        if not retrieved_ready and has_retrieved_docs:
            insert_retrieved_docs(cursor, history_id, json_loads(row.get("retrieved_docs"), []))

        if not context_ready and has_database_context:
            insert_database_context(
                cursor,
                history_id,
                json_loads(row.get("database_context"), {
                    "diseases": [],
                    "medicines": [],
                    "has_matches": False,
                }),
            )


def ensure_normalized_schema(force=False):
    global _SCHEMA_READY

    if _SCHEMA_READY and not force:
        return

    with get_connection(autocommit=False) as conn:
        try:
            with conn.cursor() as cursor:
                create_schema(cursor)
                upgrade_legacy_schema(cursor)
                migrate_legacy_knowledge_columns(cursor)
                migrate_legacy_history_columns(cursor)
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    _SCHEMA_READY = True


def get_storage_status():
    config = database_config()
    status = {
        "mode": "mysql_normalized",
        "database_enabled": True,
        "host": config["host"],
        "port": config["port"],
        "database": config["database"],
        "connected": False,
        "tables": [
            "users",
            "user_sessions",
            "disease_categories",
            "diseases",
            "disease_symptoms",
            "medicine_types",
            "medicines",
            "warning_rules",
            "chat_history",
            "chat_history_warning_matches",
            "chat_history_retrieved_docs",
            "chat_history_contexts",
            "chat_history_database_matches",
            "search_logs",
            "search_log_matches",
        ],
    }

    try:
        ensure_normalized_schema()
        status["connected"] = True
        status["message"] = "Connected to normalized MySQL tables."
    except Exception as exc:
        status["error"] = str(exc)
        status["message"] = "Unable to connect to normalized MySQL tables."

    return status
