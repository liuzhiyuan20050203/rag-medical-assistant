# 多模态常见病症自查与安全用药咨询 Agent

## 一、项目简介

本项目是一个面向普通用户的多模态常见病症自查与安全用药咨询 Agent。系统支持文字、语音、图片和视频输入，优先检查危险症状，再根据 Agent 意图调用药品查询或混合 RAG，并生成带有安全边界的健康信息回答。

系统采用前后端分离架构，前端使用 Vue 3，后端使用 FastAPI。正式运行数据存储在 MySQL 规范化业务表中，`backend/data/*.json` 主要保留为迁移、测试和兼容数据。RAG 检索模块使用 FAISS，回答生成通过 OpenAI-compatible 接口调用已配置的大模型；模型不可用时自动回退到本地安全模板。

正式能力不包括疾病确诊、处方开具、个体化精确剂量和化验单指标解读，也不能替代医生、药师或正规医疗服务。未登录咨询可能以匿名方式用于系统统计和质量改进，不与个人账号绑定；请勿输入姓名、手机号、身份证号等身份信息。

---

## 二、项目技术栈

| 模块      | 技术                 |
| ------- | ------------------ |
| 前端框架    | Vue 3              |
| 前端路由    | Vue Router         |
| 后端框架    | FastAPI            |
| 后端运行服务器 | Uvicorn            |
| 编程语言    | Python、JavaScript  |
| 向量检索    | FAISS              |
| 向量计算    | NumPy              |
| 大模型     | OpenAI-compatible API |
| 多模态识别  | OpenAI-compatible 视觉模型接口 / 本地视觉统计 |
| 数据存储    | MySQL / JSON 测试与迁移数据 |
| 接口调用    | Fetch API、Requests |
| 配置管理    | python-dotenv、Vite 环境变量 |

---

## 三、系统功能

### 1. 症状自查

用户可以输入自然语言症状描述，例如：

```text
我咳嗽、流鼻涕、喉咙痛，怎么办？
```

系统处理流程如下：

```text
用户输入症状
↓
危险症状规则检测
↓
FAISS 检索常见病知识库
↓
已配置的大模型基于检索资料生成回答
↓
前端展示系统回答和RAG检索结果
```

系统回答包括：

* 症状初步分析
* 可能相关的常见病方向
* 日常护理建议
* 用药注意事项
* 就医提醒
* 安全声明

---

### 2. 用药查询

用户可以输入药品名称或药品类别，例如：

```text
布洛芬
氯雷他定
蒙脱石散
```

系统会返回药品的基本信息，包括：

* 药品名称
* 药品类别
* 适用情况
* 注意事项
* 禁忌人群
* 不良反应

---

### 3. 危险症状提醒

系统内置危险症状规则库，当用户输入内容包含以下高风险症状时，系统会优先提醒用户及时就医：

```text
胸痛
呼吸困难
喘不上气
咳血
高热不退
意识模糊
抽搐
严重腹痛
呕血
黑便
```

例如用户输入：

```text
我胸痛，而且喘不上气，怎么办？
```

系统会直接返回危险症状提醒，而不是进行普通问答。

---

### 4. RAG 检索

系统将常见病知识库和药品知识库整理为可检索文档，并通过 FAISS 构建向量索引。当用户提出问题时，系统会先检索与问题最相关的知识片段，再将这些资料交给大模型生成回答。

本项目第一版采用简化关键词向量方式实现 RAG 检索，后续可以升级为 sentence-transformers 等语义向量模型。

---

### 5. 大模型生成与本地降级

系统通过 OpenAI-compatible API 实现基于检索资料的回答生成。当前系统采用如下策略：

```text
RAG 检索成功
↓
将检索到的知识库资料作为上下文
↓
调用已配置的大模型生成结构化回答
↓
如果大模型调用失败，则自动回退到本地模板回答
```

前端页面会显示大模型状态，例如：

```text
AI 大模型参与：当前配置的模型名称
```

---

### 6. 知识库浏览

系统提供知识库页面，可以查看：

* 常见病知识库
* 药品知识库
* 危险症状规则库

该功能便于展示系统回答的知识来源。

---

### 7. 问答历史记录

系统会自动保存用户的症状自查记录，包括：

* 用户问题
* 系统回答
* 危险症状结果
* RAG 检索结果
* 创建时间

用户可以在历史记录页面查看最近问答，也可以清空历史记录。

---

### 8. 首页统计看板

首页展示系统当前数据情况，包括：

* 常见病知识数量
* 药品知识数量
* 危险症状规则数量
* 累计问答次数
* 危险提醒次数
* RAG 检索问答次数

---

## 四、项目目录结构

```text
rag-medical-assistant/
├── backend/
│   ├── data/
│   │   ├── diseases.json
│   │   ├── medicines.json
│   │   ├── warning_rules.json
│   │   └── history.json
│   ├── main.py
│   ├── safety_check.py
│   ├── knowledge_service.py
│   ├── rag_service.py
│   ├── history_service.py
│   ├── analytics_service.py
│   ├── auth_service.py
│   ├── storage.py
│   ├── migrate_json_to_mysql.py
│   ├── llm_service.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── api.js
│   │   ├── router/
│   │   │   └── index.js
│   │   └── views/
│   │       ├── HomeView.vue
│   │       ├── ChatView.vue
│   │       ├── MedicineView.vue
│   │       ├── KnowledgeView.vue
│   │       └── HistoryView.vue
│   ├── package.json
│   ├── .env.example
│   └── vite.config.js
│
├── DEPLOY_DATABASE.md
├── README.md
└── .gitignore
```

---

## 五、后端运行方式

### 1. 进入后端目录

```bash
cd backend
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

`requirements.txt` 内容如下：

```txt
fastapi
uvicorn
numpy==2.3.5
faiss-cpu==1.13.1
requests
python-dotenv
pymysql
Pillow
```

### 3. 配置大模型 API

在 `backend` 目录下创建 `.env` 文件，参考 `.env.example` 填写：

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=你的API Key
OPENAI_BASE_URL=https://你的OpenAI-compatible服务地址/v1
OPENAI_MODEL=你的模型名称
LLM_TIMEOUT_SECONDS=30

# 可选：多模态视觉模型，支持多数 OpenAI-compatible /chat/completions 视觉接口
VISION_LLM_PROVIDER=custom
VISION_LLM_API_KEY=你的多模态模型API Key
VISION_LLM_BASE_URL=https://你的模型服务地址
VISION_LLM_MODEL=你的视觉模型名称
```

注意：`.env` 文件中包含真实 API Key，不应上传到 GitHub 或公开展示。

### 4. 配置数据存储

当前正式运行使用 MySQL，例如同机部署：

```env
DATABASE_URL=
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=rag_medical
MYSQL_PASSWORD=你的数据库密码
MYSQL_DATABASE=rag_medical
MYSQL_CHARSET=utf8mb4
MYSQL_JSON_TABLE=app_json_store
```

首次启用 MySQL 时运行一次迁移：

```bash
python migrate_json_to_mysql.py
```

更多宝塔/阿里云部署步骤见 [DEPLOY_DATABASE.md](DEPLOY_DATABASE.md)。

### 5. 启动后端服务

```bash
uvicorn main:app --reload
```

后端默认地址：

```text
http://127.0.0.1:8000
```

接口文档地址：

```text
http://127.0.0.1:8000/docs
```

验证当前存储模式：

```bash
curl http://127.0.0.1:8000/api/storage/status
```

---

## 六、前端运行方式

### 1. 进入前端目录

```bash
cd frontend
```

### 2. 安装依赖

```bash
npm install
```

### 3. 启动前端项目

如果前端需要连接云端后端，可以在 `frontend/.env` 写入：

```env
VITE_API_BASE_URL=http://你的服务器公网IP:8000
```

不配置时，默认使用 `frontend/src/api.js` 中的默认后端地址。

```bash
npm run dev
```

前端默认地址：

```text
http://localhost:5173
```

---

## 七、主要接口说明

| 接口                     | 请求方式 | 功能          |
| ---------------------- | ---- | ----------- |
| `/`                    | GET  | 测试后端服务是否启动  |
| `/api/disease/list`    | GET  | 获取常见病知识库    |
| `/api/medicine/list`   | GET  | 获取药品知识库     |
| `/api/warning/list`    | GET  | 获取危险症状规则库   |
| `/api/medicine/search` | POST | 查询药品信息      |
| `/api/rag/init`        | GET  | 初始化 RAG 向量库 |
| `/api/rag/search`      | POST | 测试 RAG 检索   |
| `/api/chat`            | POST | 症状自查问答      |
| `/api/history/list`    | GET  | 查看问答历史      |
| `/api/history/clear`   | POST | 清空问答历史      |
| `/api/llm/test`        | GET  | 测试大模型连接     |
| `/api/stats/summary`   | GET  | 获取首页统计数据    |
| `/api/storage/status`  | GET  | 查看当前 JSON/MySQL 存储状态 |
| `/api/auth/login`      | POST | 用户登录          |
| `/api/auth/register`   | POST | 用户注册          |
| `/api/analytics/summary` | GET | 获取可视化分析数据 |
| `/api/multimodal/image/analyze` | POST | 图片上传识别，返回视觉质量、标签和拍摄建议 |
| `/api/multimodal/video/analyze` | POST | 视频关键帧识别，汇总关键帧视觉结果 |
| `/api/multimodal/voice/analyze` | POST | 语音文本分析，返回危险提醒和RAG提示 |

---

## 八、接口测试示例

### 1. 症状自查接口

请求地址：

```text
POST /api/chat
```

请求参数：

```json
{
  "question": "我咳嗽、流鼻涕、喉咙痛，怎么办？"
}
```

返回内容包括：

```json
{
  "question": "我咳嗽、流鼻涕、喉咙痛，怎么办？",
  "answer": "大模型生成的结构化回答",
  "warning": {
    "has_warning": false,
    "matched": [],
    "message": ""
  },
  "retrieved_docs": [],
  "llm": {
    "used": true,
    "provider": "openai",
    "model": "当前配置的模型名称",
    "error": ""
  }
}
```

---

### 2. 危险症状提醒接口

请求参数：

```json
{
  "question": "我胸痛，而且喘不上气，怎么办？"
}
```

预期结果：

```text
系统识别胸痛、喘不上气等危险症状，并提醒用户及时就医。
```

---

### 3. 药品查询接口

请求地址：

```text
POST /api/medicine/search
```

请求参数：

```json
{
  "keyword": "布洛芬"
}
```

预期结果：

```text
返回布洛芬的药品类别、适用情况、注意事项、禁忌人群和不良反应。
```

---

## 九、测试用例

| 编号 | 测试内容   | 输入示例             | 预期结果           |
| -- | ------ | ---------------- | -------------- |
| 1  | 普通症状自查 | 我咳嗽、流鼻涕、喉咙痛，怎么办？ | 返回普通感冒、咽炎等相关回答 |
| 2  | 消化系统症状 | 我肚子疼，还一直拉肚子，怎么办？ | 返回腹泻、胃痛等相关建议   |
| 3  | 皮肤症状   | 我皮肤起红疹，很痒，怎么办？   | 返回皮肤过敏、湿疹等相关建议 |
| 4  | 危险症状识别 | 我胸痛，而且喘不上气，怎么办？  | 触发危险提醒         |
| 5  | 药品查询   | 布洛芬              | 返回药品信息         |
| 6  | 无结果查询  | 不存在的药品           | 返回暂无相关信息       |
| 7  | 大模型连接  | `/api/llm/test`  | 返回大模型连接结果      |
| 8  | 历史记录   | 查看历史记录页面         | 显示历史问答         |
| 9  | 知识库浏览  | 访问知识库页面          | 显示疾病、药品和危险规则   |
| 10 | 首页统计   | 访问首页             | 显示系统统计数据       |

---

## 十、项目运行注意事项

1. 后端和前端需要分别启动。
2. 使用大模型功能前，需要在 `.env` 文件中配置所选模型服务的 API Key。
3. `.env` 文件不要公开，不要提交到代码仓库；本仓库只保留 `.env.example`。
4. 启用 MySQL 后，`migrate_json_to_mysql.py` 只在首次部署或明确要覆盖数据时运行。
5. 云端部署时不要开放 MySQL `3306` 到公网；后端和 MySQL 同机时使用 `127.0.0.1`。
6. 如果大模型调用失败，系统会自动使用本地模板回答作为兜底。
7. 本系统不提供医学诊断、处方建议、个体化精确剂量或化验单指标解读。
8. 未登录咨询可能匿名用于统计和质量改进，请勿输入身份信息。

---

## 十一、项目特色

1. 采用前后端分离架构，系统结构清晰。
2. 使用 FastAPI 构建后端接口，便于调试和扩展。
3. 使用 Vue 3 实现多页面交互。
4. 使用 FAISS 实现知识库检索，体现 RAG 技术流程。
5. 接入 OpenAI-compatible 大模型，并提供本地安全降级回答。
6. 设置危险症状规则库，增强系统安全性。
7. 支持问答历史记录和首页统计看板。
8. 使用 MySQL 保存业务数据，并保留隔离测试和质量分析流程。

---

## 十二、后续优化方向

1. 使用 sentence-transformers 等语义向量模型提升检索准确率。
2. 继续规范正式知识库名称、别名和来源信息。
3. 完善匿名咨询数据的保留期限和脱敏策略。
4. 扩展为移动端或小程序，并开展真实用户可用性测试。

---

## 十三、安全声明

本系统仅用于常见病健康信息参考和安全用药注意事项查询，不构成疾病确诊、治疗方案、处方或个体化精确剂量建议，也不提供化验单指标解读。用户如出现症状严重、持续加重，或存在胸痛、呼吸困难、高热不退、意识模糊等危险症状，应及时前往正规医疗机构就诊。
