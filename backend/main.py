from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from llm_service import generate_llm_answer, test_llm_connection
from safety_check import check_warning, load_warning_rules
from knowledge_service import (
    get_all_diseases,
    get_all_medicines,
    search_medicine,
    parse_disease_upload,
    parse_medicine_upload
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
    clear_history_records,
    mark_history_error,
    set_history_feedback
)
from auth_service import (
    authenticate_user,
    create_session,
    create_user,
    delete_user,
    list_public_users,
    register_user,
    update_user,
    user_from_token
)
from analytics_service import add_search_log, build_analytics
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


def require_admin(authorization: str = Header(default="")):
    user = user_from_token(authorization)

    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    return user


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

    records = parse_disease_upload(file_name, content)

    return {
        "success": True,
        "message": f"已写入 {len(records)} 条疾病知识",
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

    records = parse_medicine_upload(file_name, content)

    return {
        "success": True,
        "message": f"已写入 {len(records)} 条药品知识",
        "data": records
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
def chat(data: dict):
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
            }
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
        database_context=database_context
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


@app.get("/api/history/list")
def history_list():
    """
    查看问答历史记录
    """
    history = get_history_list()

    return {
        "count": len(history),
        "data": history
    }


@app.post("/api/history/clear")
def history_clear():
    """
    清空问答历史记录
    """
    clear_history_records()

    return {
        "message": "历史记录已清空"
    }


@app.post("/api/history/{record_id}/feedback")
def history_feedback(record_id: int, data: dict):
    """
    设置问答满意度反馈，支持1-5星评分和详细评价。
    """
    result = set_history_feedback(
        record_id,
        data.get("rating", 0),
        data.get("feedback_text", "")
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
def analytics_summary():
    """
    可视化分析数据接口。
    """
    return build_analytics()


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
