# 云服务器数据库部署说明

本项目默认使用 `backend/data/*.json` 保存数据。现在已经支持可选 MySQL 存储：

- 不配置 `DATABASE_URL`：继续使用本地 JSON 文件。
- 配置 `DATABASE_URL`：后端自动使用云服务器 MySQL，并在数据库里创建 `app_json_store` 表。

## 1. 在云服务器安装 MySQL

以下命令以 Ubuntu 为例：

```bash
sudo apt update
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
sudo mysql_secure_installation
```

## 2. 创建数据库和用户

登录 MySQL：

```bash
sudo mysql
```

执行：

```sql
CREATE DATABASE rag_medical CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'rag_user'@'localhost' IDENTIFIED BY '请换成强密码';
GRANT ALL PRIVILEGES ON rag_medical.* TO 'rag_user'@'localhost';
FLUSH PRIVILEGES;
```

如果后端和 MySQL 不在同一台服务器，把 `'localhost'` 改成后端服务器的内网 IP，并且只允许这个 IP 访问 3306 端口。

## 3. 配置后端环境变量

在云服务器的 `backend/.env` 写入：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

DATABASE_URL=mysql+pymysql://rag_user:请换成强密码@127.0.0.1:3306/rag_medical?charset=utf8mb4
MYSQL_JSON_TABLE=app_json_store
```

如果 MySQL 在另一台机器，把 `127.0.0.1` 改成 MySQL 服务器地址。

## 4. 安装 Python 依赖

```bash
cd backend
pip install -r requirements.txt
```

## 5. 迁移现有 JSON 数据

首次部署时运行一次：

```bash
python migrate_json_to_mysql.py
```

该脚本会把这些文件写入 MySQL：

- `diseases.json`
- `medicines.json`
- `warning_rules.json`
- `history.json`
- `users.json`
- `sessions.json`
- `search_log.json`

重复执行会覆盖 MySQL 里的同名数据块，所以正式上线后不要随手重复跑迁移脚本。

## 6. 启动并验证

启动后端：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

验证存储状态：

```bash
curl http://127.0.0.1:8000/api/storage/status
```

如果配置正确，会看到：

```json
{
  "mode": "mysql",
  "database_enabled": true,
  "connected": true
}
```

## 7. 安全建议

- 不要把 MySQL 3306 端口暴露给公网；优先让后端和数据库部署在同一台云服务器，使用 `127.0.0.1` 连接。
- 如果必须远程连接数据库，只在云厂商安全组和 MySQL 用户授权里放行后端服务器 IP。
- `.env` 里有数据库密码和 API Key，不要提交到 GitHub 或发给别人。
- 上线前请修改默认管理员密码 `admin/admin123`。
