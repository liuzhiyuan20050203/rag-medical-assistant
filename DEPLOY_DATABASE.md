# 云服务器 MySQL 部署说明

本项目默认可以继续使用 `backend/data/*.json` 保存数据；生产或云端部署时推荐启用 MySQL。

- 不配置 `DATABASE_URL` 且不配置 `MYSQL_HOST`：使用本地 JSON 文件。
- 配置 `DATABASE_URL` 或 `MYSQL_HOST`：后端自动使用 MySQL，并创建 `app_json_store` 表。

当前项目的 MySQL 存储方式是“JSON 数据块存储”：每个原始 JSON 文件会写入 `app_json_store` 的一行，例如 `diseases`、`medicines`、`history`。

## 1. 宝塔面板创建 MySQL 数据库

在宝塔面板中进入：

```text
数据库 -> MySQL -> 添加数据库
```

推荐填写：

```text
数据库名：rag_medical
用户名：rag_medical
密码：使用强密码
访问权限：本地服务器
字符集：utf8mb4
```

如果后端和 MySQL 部署在同一台宝塔服务器上，数据库权限保持“本地服务器”即可，不要开放 MySQL 3306 到公网。

## 2. Ubuntu 命令行创建数据库

如果不用宝塔，也可以手动安装 MySQL：

```bash
sudo apt update
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
sudo mysql_secure_installation
```

登录 MySQL：

```bash
sudo mysql
```

执行：

```sql
CREATE DATABASE rag_medical CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'rag_medical'@'localhost' IDENTIFIED BY '请换成强密码';
GRANT ALL PRIVILEGES ON rag_medical.* TO 'rag_medical'@'localhost';
FLUSH PRIVILEGES;
```

## 3. 配置后端环境变量

在云服务器的 `backend/.env` 写入：

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

DATABASE_URL=
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=rag_medical
MYSQL_PASSWORD=宝塔数据库密码
MYSQL_DATABASE=rag_medical
MYSQL_CHARSET=utf8mb4
MYSQL_JSON_TABLE=app_json_store
```

也可以使用 `DATABASE_URL`：

```env
DATABASE_URL=mysql+pymysql://rag_medical:请换成强密码@127.0.0.1:3306/rag_medical?charset=utf8mb4
MYSQL_JSON_TABLE=app_json_store
```

如果密码里有 `@`、`#`、`:`、`/` 等特殊字符，推荐使用 `MYSQL_HOST`、`MYSQL_USER`、`MYSQL_PASSWORD` 这种分项写法。

## 4. 安装 Python 依赖

建议使用 Python 3.10 或 3.11。

```bash
cd /www/wwwroot/rag-medical-assistant/backend
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

宝塔 Python 项目管理器安装的 Python 可能不在 PATH 中，可以先查找：

```bash
find /www/server -type f -name "python3.11" 2>/dev/null
```

然后使用完整路径创建虚拟环境。

## 5. 迁移现有 JSON 数据

首次部署时运行一次：

```bash
cd /www/wwwroot/rag-medical-assistant/backend
source venv/bin/activate
python migrate_json_to_mysql.py
```

脚本会写入这些数据块：

- `diseases`
- `medicines`
- `warning_rules`
- `history`
- `users`
- `sessions`
- `search_log`

注意：重复执行会覆盖 MySQL 中同名数据块，正式上线后不要随意重复运行迁移脚本。

## 6. 启动并验证

启动后端：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

验证存储状态：

```bash
curl http://127.0.0.1:8000/api/storage/status
```

配置正确时会看到：

```json
{
  "mode": "mysql",
  "database_enabled": true,
  "connected": true
}
```

## 7. 宝塔/阿里云端口建议

如果只是演示，可以放行后端端口：

```text
8000/TCP
```

需要同时在宝塔“安全”和阿里云 ECS 安全组里放行。

正式部署更推荐使用 Nginx 反向代理：

```text
公网 80/443 -> Nginx -> 127.0.0.1:8000
```

无论哪种方式，都不建议开放：

```text
3306/TCP
```

## 8. 安全建议

- `.env` 包含数据库密码和 API Key，不要提交到 GitHub。
- 本仓库只提交 `backend/.env.example`，真实 `backend/.env` 已被 `.gitignore` 排除。
- 上线前请修改默认管理员密码 `admin/admin123`。
- 如果数据库必须远程访问，只允许后端服务器 IP 访问 3306，不要使用 `0.0.0.0/0`。
