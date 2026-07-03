-- Navicat 本地 MySQL 初始化脚本
-- 1. 在 Navicat 中用 root 或其他管理员账号连接本机 MySQL。
-- 2. 将 <LOCAL_DB_PASSWORD> 替换为 backend/.env 中的 MYSQL_PASSWORD。
-- 3. 执行本脚本后，在 backend 目录运行：python complete_mysql_database.py

CREATE DATABASE IF NOT EXISTS `rag_medical`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'rag_medical'@'localhost'
  IDENTIFIED BY '<LOCAL_DB_PASSWORD>';
ALTER USER 'rag_medical'@'localhost'
  IDENTIFIED BY '<LOCAL_DB_PASSWORD>';
GRANT ALL PRIVILEGES ON `rag_medical`.* TO 'rag_medical'@'localhost';

CREATE USER IF NOT EXISTS 'rag_medical'@'127.0.0.1'
  IDENTIFIED BY '<LOCAL_DB_PASSWORD>';
ALTER USER 'rag_medical'@'127.0.0.1'
  IDENTIFIED BY '<LOCAL_DB_PASSWORD>';
GRANT ALL PRIVILEGES ON `rag_medical`.* TO 'rag_medical'@'127.0.0.1';

USE `rag_medical`;

CREATE TABLE IF NOT EXISTS `disease_categories` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_disease_categories_name` (`name`)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `diseases` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `category_id` INT NULL,
  `description` TEXT NULL,
  `care_advice` TEXT NULL,
  `medicine_notice` TEXT NULL,
  `warning` TEXT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_diseases_name` (`name`),
  KEY `idx_diseases_category_id` (`category_id`),
  CONSTRAINT `fk_diseases_category`
    FOREIGN KEY (`category_id`) REFERENCES `disease_categories` (`id`)
    ON DELETE SET NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `medicine_types` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_medicine_types_name` (`name`)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `medicines` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `type_id` INT NULL,
  `usage_info` TEXT NULL,
  `notice` TEXT NULL,
  `contraindication` TEXT NULL,
  `side_effect` TEXT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_medicines_name` (`name`),
  KEY `idx_medicines_type_id` (`type_id`),
  CONSTRAINT `fk_medicines_type`
    FOREIGN KEY (`type_id`) REFERENCES `medicine_types` (`id`)
    ON DELETE SET NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `warning_rules` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `keyword` VARCHAR(120) NOT NULL,
  `risk_level` VARCHAR(30) NOT NULL DEFAULT 'high',
  `advice` TEXT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_warning_rules_keyword` (`keyword`),
  KEY `idx_warning_rules_risk_level` (`risk_level`)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `search_logs` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `kind` VARCHAR(40) NOT NULL,
  `keyword` VARCHAR(255) NOT NULL DEFAULT '',
  `create_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_search_logs_kind_time` (`kind`, `create_time`)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `chat_history_contexts` (
  `history_id` BIGINT NOT NULL,
  `query_text` TEXT NULL,
  `expanded_query` TEXT NULL,
  `has_matches` TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`history_id`),
  CONSTRAINT `fk_chat_context_history`
    FOREIGN KEY (`history_id`) REFERENCES `chat_history` (`id`)
    ON DELETE CASCADE
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

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
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

FLUSH PRIVILEGES;
