-- Navicat 本地 MySQL 初始化脚本
-- 使用方式：
-- 1. 在 Navicat 中用 root 或其他管理员账号连接本机 MySQL。
-- 2. 打开“查询”，把 <LOCAL_DB_PASSWORD> 替换为 backend/.env 中的 MYSQL_PASSWORD。
-- 3. 执行本脚本。

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

CREATE TABLE IF NOT EXISTS `app_json_store` (
  `store_key` VARCHAR(80) NOT NULL PRIMARY KEY,
  `payload` LONGTEXT NOT NULL,
  `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

FLUSH PRIVILEGES;
