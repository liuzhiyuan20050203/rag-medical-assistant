from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from llm_service import generate_llm_answer, test_llm_connection
from safety_check import check_warning, load_warning_rules
from knowledge_service import (
    get_all_diseases,
    get_all_medicines,
    search_medicine,
    search_knowledge_items,
    delete_knowledge_item,
    parse_disease_upload,
    parse_medicine_upload,
    summarize_upload_results
)
from rag_service import (
    search_knowledge,
    filter_answer_docs,
    build_simple_answer,
    init_vector_store
)
from database_context_service import search_database_context
from history_service import (
    add_history_record,
    get_history_list,
    get_review_issue_list,
    clear_history_records,
    mark_history_error,
    set_history_feedback
)
from auth_service import (
    authenticate_user,
    create_session,
    create_user,
    delete_user,
    change_current_password,
    list_public_users,
    register_user,
    update_current_profile,
    update_user,
    user_from_token
)
from analytics_service import add_search_log, build_analytics
from agent_service import run_agent
from conversation_service import (
    ensure_conversation_tables,
    get_session_detail,
    get_latest_session_medicine_topic,
    list_agent_runs,
    list_sessions,
    record_agent_interaction,
)
from storage import get_storage_status
from multimodal_service import (
    analyze_image_payload,
    analyze_video_payload,
    analyze_voice_transcript,
    get_multimodal_status
)

app = FastAPI(title="基于RAG的常见病自查与用药指南系统")

# 允许前端跨域访问后端
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_init_tables():
    ensure_conversation_tables()


def require_admin(authorization: str = Header(default="")):
    user = user_from_token(authorization)

    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    return user


def optional_user(authorization: str = Header(default="")):
    return user_from_token(authorization)


MEDICINE_CONTEXT_REFERENCES = [
    "这个药",
    "这种药",
    "该药",
    "这个药品",
    "这种药品",
    "这个说明书",
    "刚才那个药",
    "上面那个药",
]


def enrich_medicine_context(data: dict, user: dict | None = None):
    """
    处理“这个药/该药有什么禁忌”这类承接问题时，补上同一会话最近检索到的药品主题。
    这样 Agent 不会从上一轮回答正文里误抓到阿司匹林等安全提示里的药名。
    """
    if not isinstance(data, dict):
        return data

    text = str(data.get("text") or data.get("question") or data.get("transcript") or "")
    if not any(keyword in text for keyword in MEDICINE_CONTEXT_REFERENCES):
        return data

    history = data.get("history") if isinstance(data.get("history"), list) else []
    for item in history:
        if not isinstance(item, dict):
            continue
        docs = item.get("docs") if isinstance(item.get("docs"), list) else []
        if any(isinstance(doc, dict) and doc.get("doc_type") == "medicine" and doc.get("title") for doc in docs):
            return data
        if item.get("current_topic") and search_medicine(str(item.get("current_topic"))):
            return data

    session_id = data.get("session_id")
    if not session_id:
        return data

    latest_topic = get_latest_session_medicine_topic(
        session_id,
        user_id=user.get("id") if user else None,
    )
    if not latest_topic:
        return data

    data["history"] = [
        *history,
        {
            "role": "assistant",
            "content": f"当前药品：{latest_topic}",
            "current_topic": latest_topic,
            "docs": [{"title": latest_topic, "doc_type": "medicine"}],
        },
    ]
    return data


@app.get("/")
def home():
    return {
        "message": "RAG常见病自查与用药指南系统后端已启动"
    }


@app.get("/api/storage/status")
def storage_status():
    return get_storage_status()


@app.get("/api/disease/list")
def disease_list():
    """
    查看常见病知识库
    """
    diseases = get_all_diseases()

    return {
        "count": len(diseases),
        "data": diseases
    }


@app.get("/api/medicine/list")
def medicine_list():
    """
    查看药品知识库
    """
    medicines = get_all_medicines()

    return {
        "count": len(medicines),
        "data": medicines
    }


@app.get("/api/warning/list")
def warning_list():
    """
    查看危险症状规则库
    """
    rules = load_warning_rules()

    return {
        "count": len(rules),
        "data": rules
    }


@app.post("/api/auth/login")
def auth_login(data: dict):
    """
    登录接口。演示项目使用本地JSON用户文件，不做真实会话管理。
    """
    username = data.get("username", "")
    password = data.get("password", "")
    user = authenticate_user(username, password)

    if not user:
        return {
            "success": False,
            "message": "用户名或密码错误",
            "user": None
        }

    return {
        "success": True,
        "message": "登录成功",
        "user": user,
        "token": create_session(user["username"])
    }


@app.post("/api/auth/register")
def auth_register(data: dict):
    """
    注册普通用户。
    """
    user, message = register_user(data.get("username", ""), data.get("password", ""))

    return {
        "success": user is not None,
        "message": message,
        "user": user
    }


@app.get("/api/auth/me")
def auth_me(user: dict = Depends(optional_user)):
    """
    获取当前登录用户资料。
    """
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "请先登录后查看个人资料", "user": None}
        )

    return {
        "success": True,
        "message": "获取成功",
        "user": user
    }


@app.put("/api/auth/profile")
def auth_update_profile(data: dict, user: dict = Depends(optional_user)):
    """
    当前用户修改个人资料、头像和用户名。
    """
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "请先登录后修改个人资料", "user": None}
        )

    updated_user, message = update_current_profile(user.get("username", ""), data or {})

    return {
        "success": updated_user is not None,
        "message": message,
        "user": updated_user
    }


@app.put("/api/auth/password")
def auth_update_password(data: dict, user: dict = Depends(optional_user)):
    """
    当前用户修改密码。
    """
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "请先登录后修改密码", "user": None}
        )

    updated_user, message = change_current_password(
        user.get("username", ""),
        data.get("old_password", ""),
        data.get("new_password", "")
    )

    return {
        "success": updated_user is not None,
        "message": message,
        "user": updated_user
    }


@app.post("/api/medicine/search")
def medicine_search(data: dict):
    """
    药品查询接口
    """
    keyword = data.get("keyword", "")

    if not keyword:
        return {
            "keyword": keyword,
            "count": 0,
            "data": [],
            "message": "请输入药品名称或药品类别。"
        }

    result = search_medicine(keyword)
    add_search_log("medicine", keyword, [item.get("name", "") for item in result])

    return {
        "keyword": keyword,
        "count": len(result),
        "data": result,
        "message": "查询成功" if result else "暂未查询到相关药品信息。"
    }


@app.post("/api/multimodal/image/analyze")
def multimodal_image_analyze(data: dict):
    """
    图片识别分析。接收前端上传的Base64图片，返回基础视觉特征和拍摄建议。
    """
    image_data = data.get("image", "")

    if not image_data:
        return {
            "success": False,
            "message": "请上传图片。"
        }

    try:
        return analyze_image_payload(
            image_data=image_data,
            file_name=data.get("file_name", ""),
            note=data.get("note", "")
        )
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc)
        }


@app.get("/api/multimodal/status")
def multimodal_status():
    """
    查看多模态视觉模型配置状态。
    """
    return get_multimodal_status()


@app.post("/api/multimodal/video/analyze")
def multimodal_video_analyze(data: dict):
    """
    视频识别分析。前端抽取关键帧后提交，后端逐帧分析并汇总。
    """
    frames = data.get("frames", [])

    if not frames:
        return {
            "success": False,
            "message": "请上传视频并抽取至少一个关键帧。"
        }

    try:
        return analyze_video_payload(
            frames=frames,
            file_name=data.get("file_name", ""),
            note=data.get("note", ""),
            duration=data.get("duration", 0)
        )
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc)
        }


@app.post("/api/multimodal/voice/analyze")
def multimodal_voice_analyze(data: dict):
    """
    语音输入分析。语音转文字由浏览器完成，后端负责危险症状和RAG提示。
    """
    return analyze_voice_transcript(data.get("transcript", ""))


@app.get("/api/admin/knowledge")
def admin_knowledge(_admin: dict = Depends(require_admin)):
    """
    管理员查看当前知识库。
    """
    diseases = get_all_diseases()
    medicines = get_all_medicines()
    rules = load_warning_rules()

    return {
        "knowledge": {
            "disease_count": len(diseases),
            "medicine_count": len(medicines),
            "warning_rule_count": len(rules),
            "total_knowledge_count": len(diseases) + len(medicines)
        },
        "diseases": diseases,
        "medicines": medicines,
        "warning_rules": rules
    }


@app.post("/api/admin/upload/disease")
def admin_upload_disease(data: dict, _admin: dict = Depends(require_admin)):
    """
    上传疾病知识文档。支持JSON结构化内容或普通文本。
    """
    content = data.get("content", "")
    file_name = data.get("file_name", "disease-upload.txt")

    if not content.strip():
        return {
            "success": False,
            "message": "上传内容不能为空",
            "data": []
        }

    try:
        records = parse_disease_upload(file_name, content)
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
            "data": []
        }

    summary = summarize_upload_results(records)

    return {
        "success": True,
        "message": (
            f"疾病知识处理完成：新增 {summary['created']} 条，"
            f"更新 {summary['updated']} 条，疑似重复 {summary['similar']} 条"
        ),
        "summary": summary,
        "data": records
    }


@app.post("/api/admin/upload/medicine")
def admin_upload_medicine(data: dict, _admin: dict = Depends(require_admin)):
    """
    上传药品说明书。支持JSON结构化内容或普通文本。
    """
    content = data.get("content", "")
    file_name = data.get("file_name", "medicine-upload.txt")

    if not content.strip():
        return {
            "success": False,
            "message": "上传内容不能为空",
            "data": []
        }

    try:
        records = parse_medicine_upload(file_name, content)
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
            "data": []
        }

    summary = summarize_upload_results(records)

    return {
        "success": True,
        "message": (
            f"药品知识处理完成：新增 {summary['created']} 条，"
            f"更新 {summary['updated']} 条，疑似重复 {summary['similar']} 条"
        ),
        "summary": summary,
        "data": records
    }


@app.post("/api/admin/knowledge/search")
def admin_search_knowledge(data: dict, _admin: dict = Depends(require_admin)):
    """
    管理员按关键词搜索疾病或药品知识，用于删除前确认。
    """
    kind = data.get("kind", "")
    keyword = data.get("keyword", "")

    if not keyword.strip():
        return {
            "success": False,
            "message": "请输入要搜索的关键词",
            "count": 0,
            "data": []
        }

    try:
        items = search_knowledge_items(kind, keyword)
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
            "count": 0,
            "data": []
        }

    return {
        "success": True,
        "message": f"找到 {len(items)} 条匹配知识",
        "count": len(items),
        "data": items
    }


@app.delete("/api/admin/knowledge/{kind}/{item_id}")
def admin_delete_knowledge(kind: str, item_id: int, _admin: dict = Depends(require_admin)):
    """
    管理员删除本地 MySQL 中的疾病或药品知识。
    """
    try:
        deleted = delete_knowledge_item(kind, item_id)
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
            "data": None
        }

    if not deleted:
        return {
            "success": False,
            "message": "未找到对应知识记录，可能已被删除",
            "data": None
        }

    return {
        "success": True,
        "message": f"已删除“{deleted.get('name', '')}”。请更新向量索引，让 RAG 检索同步删除结果。",
        "data": deleted
    }


@app.post("/api/admin/vector/rebuild")
def admin_rebuild_vector(_admin: dict = Depends(require_admin)):
    """
    重建RAG向量索引。
    """
    result = init_vector_store()

    return {
        "success": True,
        "message": "向量索引更新成功",
        "data": result
    }


@app.get("/api/admin/history")
def admin_history(_admin: dict = Depends(require_admin)):
    """
    管理员查看用户问答记录。
    """
    history = get_history_list()

    return {
        "count": len(history),
        "data": history
    }


@app.get("/api/admin/conversations/sessions")
def admin_conversation_sessions(_admin: dict = Depends(require_admin)):
    """
    管理员查看多轮对话会话。
    """
    sessions = list_sessions(limit=100)

    return {
        "count": len(sessions),
        "data": sessions
    }


@app.get("/api/conversations/sessions")
def conversation_sessions(user: dict = Depends(optional_user)):
    """
    普通用户查看自己的多轮对话会话列表。
    """
    if not user:
        return {
            "count": 0,
            "data": [],
            "message": "请先登录后查看个人会话"
        }

    sessions = list_sessions(user_id=user.get("id"), limit=100)

    return {
        "count": len(sessions),
        "data": sessions
    }


@app.get("/api/conversations/{session_id}")
def conversation_detail(session_id: int, user: dict = Depends(optional_user)):
    """
    普通用户查看自己的某个多轮对话详情。
    """
    if not user:
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "请先登录后查看个人会话"}
        )

    detail = get_session_detail(session_id, user_id=user.get("id"))
    if not detail:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "未找到该会话或无权访问"}
        )

    return {
        "success": True,
        "data": detail
    }


@app.get("/api/admin/agent/runs")
def admin_agent_runs(_admin: dict = Depends(require_admin)):
    """
    管理员查看 Agent 调度运行日志。
    """
    runs = list_agent_runs(limit=100)

    return {
        "count": len(runs),
        "data": runs
    }


@app.get("/api/admin/review/issues")
def admin_review_issues(only_need_review: bool = False, _admin: dict = Depends(require_admin)):
    """
    管理员查看低置信度、用户差评和知识库缺口样本。
    """
    issues = get_review_issue_list(limit=100, only_need_review=only_need_review)

    return {
        "count": len(issues),
        "data": issues
    }


@app.post("/api/admin/history/{record_id}/mark-error")
def admin_mark_history_error(record_id: int, data: dict, _admin: dict = Depends(require_admin)):
    """
    管理员标记错误回答。
    """
    result = mark_history_error(record_id, data.get("reason", ""))

    if not result:
        return {
            "success": False,
            "message": "未找到对应问答记录"
        }

    return {
        "success": True,
        "message": "已标记错误回答",
        "data": result
    }


@app.get("/api/admin/users")
def admin_user_list(_admin: dict = Depends(require_admin)):
    """
    管理员查看用户列表。
    """
    users = list_public_users()

    return {
        "count": len(users),
        "data": users
    }


@app.post("/api/admin/users")
def admin_user_create(data: dict, _admin: dict = Depends(require_admin)):
    """
    管理员创建用户并分配角色权限。
    """
    user, message = create_user(
        data.get("username", ""),
        data.get("password", ""),
        data.get("role", "user"),
        data.get("active", True)
    )

    return {
        "success": user is not None,
        "message": message,
        "data": user
    }


@app.put("/api/admin/users/{username}")
def admin_user_update(username: str, data: dict, _admin: dict = Depends(require_admin)):
    """
    管理员更新用户角色、启停状态或重置密码。
    """
    user, message = update_user(username, data)

    return {
        "success": user is not None,
        "message": message,
        "data": user
    }


@app.delete("/api/admin/users/{username}")
def admin_user_delete(username: str, admin: dict = Depends(require_admin)):
    """
    管理员删除用户。
    """
    success, message = delete_user(username, admin.get("username", ""))

    return {
        "success": success,
        "message": message
    }


@app.get("/api/rag/init")
def rag_init():
    """
    初始化RAG向量库
    """
    result = init_vector_store()

    return {
        "message": "RAG向量库初始化成功",
        "data": result
    }


@app.post("/api/rag/search")
def rag_search(data: dict):
    """
    测试RAG检索效果
    """
    question = data.get("question", "")
    top_k = data.get("top_k", 3)

    if not question:
        return {
            "question": question,
            "count": 0,
            "data": [],
            "database_context": {
                "diseases": [],
                "medicines": [],
                "has_matches": False
            },
            "message": "请输入检索问题。"
        }

    results = search_knowledge(question, top_k=top_k)
    database_context = search_database_context(
        question,
        disease_limit=top_k,
        medicine_limit=top_k
    )

    return {
        "question": question,
        "count": len(results),
        "data": results,
        "database_context": database_context,
        "message": "检索成功"
    }


@app.post("/api/chat")
def chat(data: dict, user: dict = Depends(optional_user)):
    """
    症状自查问答接口
    """
    question = data.get("question", "")

    if not question:
        return {
            "question": question,
            "answer": "请输入你的症状描述。",
            "warning": None,
            "retrieved_docs": [],
            "database_context": {
                "diseases": [],
                "medicines": [],
                "has_matches": False
            }
        }

    # 第一步：危险症状检查
    warning_result = check_warning(question)

    if warning_result["has_warning"]:
        answer = warning_result["message"]

        # 保存危险提醒历史记录
        record = add_history_record(
            question=question,
            answer=answer,
            warning=warning_result,
            retrieved_docs=[],
            database_context={
                "diseases": [],
                "medicines": [],
                "has_matches": False
            },
            user_id=user.get("id") if user else None
        )

        return {
            "question": question,
            "answer": answer,
            "warning": warning_result,
            "retrieved_docs": [],
            "database_context": {
                "diseases": [],
                "medicines": [],
                "has_matches": False
            },
            "history_id": record.get("id")
        }

    # 第二步：数据库结构化记录匹配
    database_context = search_database_context(
        question,
        disease_limit=3,
        medicine_limit=3
    )

    # 第三步：RAG知识库检索
    retrieved_docs = filter_answer_docs(
        search_knowledge(question, top_k=8),
        database_context=database_context
    )

    # 第四步：先生成本地模板回答，作为兜底方案
    fallback_answer = build_simple_answer(question, retrieved_docs, database_context)

    # 第五步：调用大模型，基于数据库命中和RAG检索结果生成回答
    llm_result = generate_llm_answer(question, retrieved_docs, database_context)

    if llm_result["success"]:
        answer = llm_result["answer"]
    else:
        answer = fallback_answer

    # 第六步：保存问答历史
    record = add_history_record(
        question=question,
        answer=answer,
        warning=warning_result,
        retrieved_docs=retrieved_docs,
        llm=llm_result,
        database_context=database_context,
        user_id=user.get("id") if user else None
    )

    return {
        "question": question,
        "answer": answer,
        "warning": warning_result,
        "retrieved_docs": retrieved_docs,
        "database_context": database_context,
        "history_id": record.get("id"),
        "llm": {
            "used": llm_result["success"],
            "provider": llm_result["provider"],
            "model": llm_result["model"],
            "error": llm_result["error"]
        }
    }


@app.post("/api/agent/chat")
def agent_chat(data: dict, user: dict = Depends(optional_user)):
    """
    Agent 调度入口：统一接收文本、语音转文字和图片识别结果，
    决定是否危险提醒、追问、查询药品知识库或调用 RAG。
    """
    try:
        data = dict(data or {})
        if user:
            data["user_id"] = user.get("id")
        data = enrich_medicine_context(data, user)
        response = run_agent(data)
        if response.get("success"):
            conversation = record_agent_interaction(
                data=data,
                response=response,
                user_id=user.get("id") if user else None,
            )
            response["session_id"] = conversation.get("session_id")
            response["agent_run_id"] = conversation.get("agent_run_id")
        return response
    except Exception as exc:
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "action": "agent_error",
                "need_followup": False,
                "is_danger": False,
                "question": (data or {}).get("text") or (data or {}).get("question") or "",
                "answer": "Agent 处理过程中遇到错误，请检查数据库、知识库或模型服务配置后重试。",
                "followup_questions": [],
                "warning": None,
                "retrieved_docs": [],
                "history_id": None,
                "llm": None,
                "normalized_input": {},
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
                "agent_trace": {
                    "action": "agent_error",
                    "used_tools": ["agent_chat"],
                    "reason": "Agent 调度链路中的某个工具调用失败，已转换为前端可处理的错误结果。",
                },
            },
        )


@app.get("/api/history/list")
def history_list(user: dict = Depends(optional_user)):
    """
    查看问答历史记录
    """
    if not user:
        return {
            "count": 0,
            "data": [],
            "message": "请先登录后查看个人历史记录"
        }

    history = get_history_list(user_id=user.get("id"))

    return {
        "count": len(history),
        "data": history
    }


@app.post("/api/history/clear")
def history_clear(user: dict = Depends(optional_user)):
    """
    清空问答历史记录
    """
    if not user:
        return {
            "success": False,
            "message": "请先登录后清空个人历史记录"
        }

    clear_history_records(user_id=user.get("id"))

    return {
        "success": True,
        "message": "历史记录已清空"
    }


@app.post("/api/history/{record_id}/feedback")
def history_feedback(record_id: int, data: dict, user: dict = Depends(optional_user)):
    """
    设置问答满意度反馈，支持1-5星评分和详细评价。
    """
    if not user:
        return {
            "success": False,
            "message": "请先登录后提交反馈"
        }

    result = set_history_feedback(
        record_id,
        data.get("rating", 0),
        data.get("feedback_text", ""),
        user_id=user.get("id")
    )

    if not result:
        return {
            "success": False,
            "message": "反馈保存失败，请检查记录ID或星级评分"
        }

    return {
        "success": True,
        "message": "反馈已保存",
        "data": result
    }


@app.get("/api/analytics/summary")
def analytics_summary(deep_recheck: bool = False):
    """
    可视化分析数据接口。
    """
    return build_analytics(deep_recheck=deep_recheck)


@app.get("/api/llm/test")
def llm_test():
    """
    测试大模型连接
    """
    result = test_llm_connection()

    return result


@app.get("/api/stats/summary")
def stats_summary():
    """
    系统数据统计接口
    """
    diseases = get_all_diseases()
    medicines = get_all_medicines()
    warning_rules = load_warning_rules()
    history = get_history_list()

    total_history = len(history)

    warning_count = 0
    rag_count = 0

    for item in history:
        warning = item.get("warning") or {}

        if warning.get("has_warning"):
            warning_count += 1

        retrieved_docs = item.get("retrieved_docs") or []
        if len(retrieved_docs) > 0:
            rag_count += 1

    return {
        "knowledge": {
            "disease_count": len(diseases),
            "medicine_count": len(medicines),
            "warning_rule_count": len(warning_rules),
            "total_knowledge_count": len(diseases) + len(medicines)
        },
        "history": {
            "total_history": total_history,
            "warning_count": warning_count,
            "rag_count": rag_count
        }
    }
