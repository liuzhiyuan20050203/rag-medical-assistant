# MySQL 规范化表部署说明

本项目运行时统一使用规范化 MySQL 表保存业务数据。`backend/data/*.json` 仍保留为初始化种子数据，首次部署或补齐数据时由 `complete_mysql_database.py` 导入。

## 1. 创建 MySQL 数据库

宝塔面板推荐配置：

```text
数据库名：rag_medical
用户名：rag_medical
密码：使用强密码
访问权限：本地服务器
字符集：utf8mb4
```

如果用命令行：

```bash
sudo mysql
```

```sql
CREATE DATABASE rag_medical CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'rag_medical'@'localhost' IDENTIFIED BY '请换成强密码';
GRANT ALL PRIVILEGES ON rag_medical.* TO 'rag_medical'@'localhost';
FLUSH PRIVILEGES;
```

本地 Navicat 也可以直接执行 [backend/navicat_local_mysql_setup.sql](backend/navicat_local_mysql_setup.sql)。

## 2. 配置后端环境变量

在 `backend/.env` 写入本地 Navicat MySQL 配置：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=rag_medical
MYSQL_PASSWORD=数据库密码
MYSQL_DATABASE=rag_medical
MYSQL_CHARSET=utf8mb4
RAG_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
RAG_RERANK_MODEL=lexical
RAG_RERANK_ENABLED=true
RAG_CHUNK_MAX_CHARS=360
RAG_CHUNK_OVERLAP=80
```

项目现在只读取 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE` 这些本地 MySQL 分项配置，不再使用云端数据库连接串。

## 3. 安装依赖

```bash
cd /www/wwwroot/rag-medical-assistant/backend
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 4. 初始化规范表和种子数据

首次部署执行：

```bash
python complete_mysql_database.py
```

脚本会创建并补齐这些核心表：

```text
users
user_sessions
disease_categories
diseases
disease_symptoms
medicine_types
medicines
warning_rules
search_logs
search_log_matches
chat_history
chat_history_warning_matches
chat_history_retrieved_docs
chat_history_contexts
chat_history_database_matches
chat_history_database_match_fields
```

如果数据库里已经存在旧版 `app_json_store`，脚本会读取旧 JSON 块并迁移到规范表；确认数据无误后，可以自行备份并删除旧表。

## 5. 启动并验证

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

验证：

```bash
curl http://127.0.0.1:8000/api/storage/status
```

正常会看到：

```json
{
  "mode": "mysql_normalized",
  "database_enabled": true,
  "connected": true
}
```

初始化或补充知识库后，建议重建 RAG 向量索引：

```bash
curl http://127.0.0.1:8000/api/rag/init
```

## 6. 安全建议

- `.env` 包含数据库密码和 API Key，不要提交到 GitHub。
- 上线前请修改默认管理员密码 `admin/admin123`。
- 不要开放 MySQL `3306` 到公网；后端和 MySQL 同机时使用 `127.0.0.1`。
- 如果必须远程访问数据库，只允许后端服务器 IP 访问。
