import json
from datetime import datetime

from history_service import get_connection


def json_dumps(data):
    return json.dumps(data if data is not None else {}, ensure_ascii=False)


def json_loads(text, default=None):
    if default is None:
        default = {}
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_conversation_tables():
    """
    创建多轮会话、消息、Agent 调度日志和多模态输入表。
    """
    statements = [
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INT NOT NULL AUTO_INCREMENT,
            user_id INT NULL,
            title VARCHAR(160) NOT NULL DEFAULT '',
            status VARCHAR(30) NOT NULL DEFAULT 'active',
            message_count INT NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            last_message_at DATETIME NULL,
            PRIMARY KEY (id),
            INDEX idx_chat_sessions_user_time (user_id, updated_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='多轮对话会话表'
        """,
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INT NOT NULL AUTO_INCREMENT,
            session_id INT NOT NULL,
            user_id INT NULL,
            history_id INT NULL,
            role VARCHAR(30) NOT NULL,
            content_type VARCHAR(30) NOT NULL DEFAULT 'text',
            content LONGTEXT NULL,
            metadata_json LONGTEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            INDEX idx_chat_messages_session_time (session_id, created_at),
            INDEX idx_chat_messages_user_time (user_id, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='多轮对话消息表'
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_runs (
            id INT NOT NULL AUTO_INCREMENT,
            session_id INT NOT NULL,
            user_message_id INT NULL,
            assistant_message_id INT NULL,
            history_id INT NULL,
            user_id INT NULL,
            action VARCHAR(60) NOT NULL DEFAULT '',
            intent VARCHAR(80) NOT NULL DEFAULT '',
            confidence DECIMAL(5,4) NULL,
            is_danger TINYINT NOT NULL DEFAULT 0,
            need_followup TINYINT NOT NULL DEFAULT 0,
            llm_used TINYINT NOT NULL DEFAULT 0,
            llm_provider VARCHAR(80) NULL,
            llm_model VARCHAR(120) NULL,
            trace_json LONGTEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            INDEX idx_agent_runs_session_time (session_id, created_at),
            INDEX idx_agent_runs_user_time (user_id, created_at),
            INDEX idx_agent_runs_action (action)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent 调度运行表'
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_steps (
            id INT NOT NULL AUTO_INCREMENT,
            run_id INT NOT NULL,
            step_index INT NOT NULL DEFAULT 0,
            name VARCHAR(120) NOT NULL DEFAULT '',
            status VARCHAR(50) NOT NULL DEFAULT '',
            detail_json LONGTEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            INDEX idx_agent_steps_run (run_id, step_index)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent 步骤日志表'
        """,
        """
        CREATE TABLE IF NOT EXISTS agent_tool_calls (
            id INT NOT NULL AUTO_INCREMENT,
            run_id INT NOT NULL,
            tool_name VARCHAR(120) NOT NULL DEFAULT '',
            success TINYINT NOT NULL DEFAULT 1,
            input_json LONGTEXT NULL,
            output_json LONGTEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            INDEX idx_agent_tool_calls_run (run_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Agent 工具调用表'
        """,
        """
        CREATE TABLE IF NOT EXISTS retrieval_logs (
            id INT NOT NULL AUTO_INCREMENT,
            run_id INT NOT NULL,
            session_id INT NOT NULL,
            user_id INT NULL,
            query_text TEXT NULL,
            doc_count INT NOT NULL DEFAULT 0,
            top_score DECIMAL(8,5) NULL,
            docs_json LONGTEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            INDEX idx_retrieval_logs_run (run_id),
            INDEX idx_retrieval_logs_session (session_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='RAG 检索日志表'
        """,
        """
        CREATE TABLE IF NOT EXISTS multimodal_inputs (
            id INT NOT NULL AUTO_INCREMENT,
            session_id INT NOT NULL,
            message_id INT NULL,
            user_id INT NULL,
            input_type VARCHAR(30) NOT NULL DEFAULT 'text',
            text_content LONGTEXT NULL,
            image_summary LONGTEXT NULL,
            image_tags_json LONGTEXT NULL,
            image_result_json LONGTEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            INDEX idx_multimodal_inputs_session (session_id),
            INDEX idx_multimodal_inputs_user_time (user_id, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='多模态输入表'
        """,
    ]

    with get_connection() as conn:
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)


def make_session_title(data, response):
    text = (data or {}).get("text") or (data or {}).get("question") or response.get("question") or ""
    text = str(text).strip()
    if text:
        return text[:60]
    if (data or {}).get("image_summary"):
        return "图片咨询"
    return "新的健康咨询"


def get_or_create_session(user_id, session_id, data, response):
    ensure_conversation_tables()

    with get_connection() as conn:
        with conn.cursor() as cursor:
            if session_id:
                cursor.execute(
                    "SELECT id FROM chat_sessions WHERE id = %s AND user_id <=> %s LIMIT 1",
                    (session_id, user_id),
                )
                row = cursor.fetchone()
                if row:
                    return row["id"]

            cursor.execute(
                """
                INSERT INTO chat_sessions (user_id, title, last_message_at)
                VALUES (%s, %s, %s)
                """,
                (user_id, make_session_title(data, response), now_text()),
            )
            return cursor.lastrowid


def user_message_content(data):
    text = str((data or {}).get("text") or (data or {}).get("question") or "").strip()
    has_image = bool((data or {}).get("image_summary") or (data or {}).get("image_tags"))

    if text and has_image:
        return f"{text}\n[已上传图片]"
    if text:
        return text
    if has_image:
        return "[图片咨询]"
    return ""


def insert_message(session_id, user_id, role, content, content_type="text", history_id=None, metadata=None):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages
                (session_id, user_id, history_id, role, content_type, content, metadata_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session_id,
                    user_id,
                    history_id,
                    role,
                    content_type,
                    content,
                    json_dumps(metadata or {}),
                ),
            )
            return cursor.lastrowid


def max_doc_score(docs):
    scores = []
    for doc in docs or []:
        try:
            scores.append(float(doc.get("score", 0) or 0))
        except (TypeError, ValueError, AttributeError):
            continue
    return max(scores) if scores else None


def record_multimodal_input(session_id, message_id, user_id, data):
    has_multimodal = any([
        (data or {}).get("text"),
        (data or {}).get("question"),
        (data or {}).get("image_summary"),
        (data or {}).get("image_tags"),
        (data or {}).get("image_result"),
    ])
    if not has_multimodal:
        return None

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO multimodal_inputs
                (
                    session_id, message_id, user_id, input_type, text_content,
                    image_summary, image_tags_json, image_result_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session_id,
                    message_id,
                    user_id,
                    (data or {}).get("input_type", "text"),
                    (data or {}).get("text") or (data or {}).get("question") or "",
                    (data or {}).get("image_summary") or "",
                    json_dumps((data or {}).get("image_tags") or []),
                    json_dumps((data or {}).get("image_result") or {}),
                ),
            )
            return cursor.lastrowid


def record_agent_interaction(data, response, user_id=None):
    """
    将一次 /api/agent/chat 调用写入新架构表，同时不影响旧 chat_history。
    """
    ensure_conversation_tables()
    data = data or {}
    response = response or {}
    session_id = get_or_create_session(user_id, data.get("session_id"), data, response)
    history_id = response.get("history_id")
    trace = response.get("agent_trace") or {}
    retrieved_docs = response.get("retrieved_docs") or []
    llm = response.get("llm") or {}

    user_message_id = insert_message(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=user_message_content(data),
        content_type=data.get("input_type", "text"),
        metadata={
            "raw_input_type": data.get("input_type", "text"),
            "has_image": bool(data.get("image_summary") or data.get("image_tags")),
        },
    )
    assistant_message_id = insert_message(
        session_id=session_id,
        user_id=user_id,
        role="assistant",
        content=response.get("answer", ""),
        content_type="text",
        history_id=history_id,
        metadata={
            "action": response.get("action", ""),
            "intent": response.get("intent", ""),
            "confidence": response.get("confidence"),
            "warning": response.get("warning"),
            "followup_questions": response.get("followup_questions") or [],
            "reliability": response.get("reliability") or trace.get("reliability"),
        },
    )
    record_multimodal_input(session_id, user_message_id, user_id, data)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO agent_runs
                (
                    session_id, user_message_id, assistant_message_id, history_id, user_id,
                    action, intent, confidence, is_danger, need_followup,
                    llm_used, llm_provider, llm_model, trace_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    session_id,
                    user_message_id,
                    assistant_message_id,
                    history_id,
                    user_id,
                    response.get("action", ""),
                    response.get("intent") or trace.get("intent", ""),
                    response.get("confidence") or trace.get("confidence"),
                    1 if response.get("is_danger") else 0,
                    1 if response.get("need_followup") else 0,
                    1 if llm.get("used") else 0,
                    llm.get("provider", ""),
                    llm.get("model", ""),
                    json_dumps(trace),
                ),
            )
            run_id = cursor.lastrowid

            for index, step in enumerate(trace.get("steps") or [], start=1):
                cursor.execute(
                    """
                    INSERT INTO agent_steps (run_id, step_index, name, status, detail_json)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        run_id,
                        index,
                        step.get("name", ""),
                        step.get("status", ""),
                        json_dumps(step),
                    ),
                )

            for tool_name in trace.get("used_tools") or []:
                cursor.execute(
                    """
                    INSERT INTO agent_tool_calls (run_id, tool_name, success, input_json, output_json)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        run_id,
                        tool_name,
                        1,
                        json_dumps({"question": response.get("question", "")}),
                        json_dumps({"action": response.get("action", ""), "history_id": history_id}),
                    ),
                )

            if retrieved_docs:
                cursor.execute(
                    """
                    INSERT INTO retrieval_logs
                    (run_id, session_id, user_id, query_text, doc_count, top_score, docs_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run_id,
                        session_id,
                        user_id,
                        response.get("question", ""),
                        len(retrieved_docs),
                        max_doc_score(retrieved_docs),
                        json_dumps(retrieved_docs),
                    ),
                )

            cursor.execute(
                """
                UPDATE chat_sessions
                SET message_count = message_count + 2,
                    last_message_at = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (now_text(), session_id),
            )

    return {
        "session_id": session_id,
        "user_message_id": user_message_id,
        "assistant_message_id": assistant_message_id,
        "agent_run_id": run_id,
    }


def list_sessions(user_id=None, limit=50):
    ensure_conversation_tables()
    try:
        limit = max(1, min(int(limit), 200))
    except (TypeError, ValueError):
        limit = 50

    params = []
    where_clause = ""
    if user_id is not None:
        where_clause = "WHERE user_id = %s"
        params.append(user_id)

    sql = f"""
        SELECT *
        FROM chat_sessions
        {where_clause}
        ORDER BY updated_at DESC, id DESC
        LIMIT %s
    """
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

    return [
        {
            "id": row.get("id"),
            "user_id": row.get("user_id"),
            "title": row.get("title", ""),
            "status": row.get("status", ""),
            "message_count": row.get("message_count", 0),
            "created_at": str(row.get("created_at", "")),
            "updated_at": str(row.get("updated_at", "")),
            "last_message_at": str(row.get("last_message_at", "")),
        }
        for row in rows
    ]


def get_session_detail(session_id, user_id=None, allow_any_user=False):
    """
    获取单个会话及其消息，用于前端从历史记录恢复多轮对话。
    普通用户只能读取自己的会话；管理员可通过 allow_any_user 查看任意会话。
    """
    if not session_id:
        return None

    ensure_conversation_tables()

    session_params = [session_id]
    user_clause = ""
    if not allow_any_user:
        user_clause = "AND user_id <=> %s"
        session_params.append(user_id)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM chat_sessions
                WHERE id = %s {user_clause}
                LIMIT 1
                """,
                session_params,
            )
            session = cursor.fetchone()

            if not session:
                return None

            cursor.execute(
                """
                SELECT
                    m.*,
                    ar.id AS agent_run_id,
                    ar.action,
                    ar.intent,
                    ar.confidence,
                    ar.is_danger,
                    ar.need_followup,
                    ar.trace_json,
                    rl.docs_json
                FROM chat_messages m
                LEFT JOIN agent_runs ar ON ar.assistant_message_id = m.id
                LEFT JOIN retrieval_logs rl ON rl.run_id = ar.id
                WHERE m.session_id = %s
                ORDER BY m.created_at ASC, m.id ASC
                """,
                (session_id,),
            )
            rows = cursor.fetchall()

    messages = []
    for row in rows:
        metadata = json_loads(row.get("metadata_json"), {})
        trace = json_loads(row.get("trace_json"), {})
        docs = json_loads(row.get("docs_json"), [])
        reliability = trace.get("reliability") if isinstance(trace, dict) else None

        message = {
            "id": row.get("id"),
            "session_id": row.get("session_id"),
            "user_id": row.get("user_id"),
            "history_id": row.get("history_id"),
            "role": row.get("role", ""),
            "content_type": row.get("content_type", "text"),
            "content": row.get("content", "") or "",
            "metadata": metadata,
            "created_at": str(row.get("created_at", "")),
        }

        if row.get("role") == "assistant":
            message.update({
                "agent_run_id": row.get("agent_run_id"),
                "action": row.get("action") or metadata.get("action", ""),
                "intent": row.get("intent") or metadata.get("intent", ""),
                "confidence": float(row.get("confidence") or metadata.get("confidence") or 0),
                "is_danger": bool(row.get("is_danger")),
                "need_followup": bool(row.get("need_followup")),
                "warning": metadata.get("warning"),
                "followup_questions": metadata.get("followup_questions") or [],
                "trace": trace,
                "retrieved_docs": docs,
                "reliability": reliability or metadata.get("reliability"),
            })

        messages.append(message)

    return {
        "id": session.get("id"),
        "user_id": session.get("user_id"),
        "title": session.get("title", ""),
        "status": session.get("status", ""),
        "message_count": session.get("message_count", 0),
        "created_at": str(session.get("created_at", "")),
        "updated_at": str(session.get("updated_at", "")),
        "last_message_at": str(session.get("last_message_at", "")),
        "messages": messages,
    }


def list_agent_runs(user_id=None, limit=50):
    ensure_conversation_tables()
    try:
        limit = max(1, min(int(limit), 200))
    except (TypeError, ValueError):
        limit = 50

    params = []
    where_clause = ""
    if user_id is not None:
        where_clause = "WHERE user_id = %s"
        params.append(user_id)

    sql = f"""
        SELECT *
        FROM agent_runs
        {where_clause}
        ORDER BY created_at DESC, id DESC
        LIMIT %s
    """
    params.append(limit)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

    return [
        {
            "id": row.get("id"),
            "session_id": row.get("session_id"),
            "history_id": row.get("history_id"),
            "user_id": row.get("user_id"),
            "action": row.get("action", ""),
            "intent": row.get("intent", ""),
            "confidence": float(row.get("confidence") or 0),
            "is_danger": bool(row.get("is_danger")),
            "need_followup": bool(row.get("need_followup")),
            "llm_used": bool(row.get("llm_used")),
            "llm_provider": row.get("llm_provider", "") or "",
            "llm_model": row.get("llm_model", "") or "",
            "created_at": str(row.get("created_at", "")),
            "trace": json_loads(row.get("trace_json"), {}),
        }
        for row in rows
    ]


def list_agent_run_details(user_id=None, limit=100):
    """
    管理后台使用的 Agent 可观测性日志。
    聚合一次 Agent 运行的步骤、工具、RAG 召回和多模态输入，避免前端再多次请求。
    """
    ensure_conversation_tables()
    runs = list_agent_runs(user_id=user_id, limit=limit)
    if not runs:
        return []

    run_ids = [run["id"] for run in runs]
    placeholders = ",".join(["%s"] * len(run_ids))

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT run_id, step_index, name, status, detail_json, created_at
                FROM agent_steps
                WHERE run_id IN ({placeholders})
                ORDER BY run_id DESC, step_index ASC, id ASC
                """,
                run_ids,
            )
            step_rows = cursor.fetchall()

            cursor.execute(
                f"""
                SELECT run_id, tool_name, success, input_json, output_json, created_at
                FROM agent_tool_calls
                WHERE run_id IN ({placeholders})
                ORDER BY run_id DESC, id ASC
                """,
                run_ids,
            )
            tool_rows = cursor.fetchall()

            cursor.execute(
                f"""
                SELECT run_id, query_text, doc_count, top_score, docs_json, created_at
                FROM retrieval_logs
                WHERE run_id IN ({placeholders})
                ORDER BY run_id DESC, id ASC
                """,
                run_ids,
            )
            retrieval_rows = cursor.fetchall()

            cursor.execute(
                f"""
                SELECT
                    ar.id AS run_id,
                    mi.input_type,
                    mi.text_content,
                    mi.image_summary,
                    mi.image_tags_json,
                    mi.image_result_json
                FROM agent_runs ar
                LEFT JOIN multimodal_inputs mi ON mi.message_id = ar.user_message_id
                WHERE ar.id IN ({placeholders})
                """,
                run_ids,
            )
            input_rows = cursor.fetchall()

    steps_by_run = {run_id: [] for run_id in run_ids}
    for row in step_rows:
        steps_by_run.setdefault(row.get("run_id"), []).append({
            "index": row.get("step_index"),
            "name": row.get("name", ""),
            "status": row.get("status", ""),
            "detail": json_loads(row.get("detail_json"), {}),
            "created_at": str(row.get("created_at", "")),
        })

    tools_by_run = {run_id: [] for run_id in run_ids}
    for row in tool_rows:
        tools_by_run.setdefault(row.get("run_id"), []).append({
            "name": row.get("tool_name", ""),
            "success": bool(row.get("success")),
            "input": json_loads(row.get("input_json"), {}),
            "output": json_loads(row.get("output_json"), {}),
            "created_at": str(row.get("created_at", "")),
        })

    retrieval_by_run = {run_id: [] for run_id in run_ids}
    for row in retrieval_rows:
        retrieval_by_run.setdefault(row.get("run_id"), []).append({
            "query_text": row.get("query_text", "") or "",
            "doc_count": int(row.get("doc_count") or 0),
            "top_score": float(row.get("top_score") or 0),
            "docs": json_loads(row.get("docs_json"), []),
            "created_at": str(row.get("created_at", "")),
        })

    inputs_by_run = {}
    for row in input_rows:
        inputs_by_run[row.get("run_id")] = {
            "input_type": row.get("input_type", "") or "",
            "text_content": row.get("text_content", "") or "",
            "image_summary": row.get("image_summary", "") or "",
            "image_tags": json_loads(row.get("image_tags_json"), []),
            "image_result": json_loads(row.get("image_result_json"), {}),
        }

    detailed_runs = []
    for run in runs:
        run_id = run["id"]
        trace = run.get("trace") or {}
        steps = steps_by_run.get(run_id) or []
        tools = tools_by_run.get(run_id) or []
        retrievals = retrieval_by_run.get(run_id) or []
        multimodal_input = inputs_by_run.get(run_id) or {}
        trace_tools = trace.get("used_tools") if isinstance(trace, dict) else []
        tool_names = {tool.get("name") for tool in tools if tool.get("name")}
        tool_names.update([name for name in (trace_tools or []) if name])

        input_type = str(multimodal_input.get("input_type") or "").lower()
        has_image_input = bool(
            multimodal_input.get("image_summary")
            or multimodal_input.get("image_tags")
            or input_type in {"image", "video", "mixed"}
        )
        retrieval_doc_count = sum(item.get("doc_count", 0) for item in retrievals)
        has_rag = "rag_search" in tool_names or bool(retrievals)
        has_medicine = "medicine_search" in tool_names or run.get("action") == "medicine_query"
        has_llm = bool(run.get("llm_used")) or "llm_answer" in tool_names
        has_no_retrieval = has_rag and retrieval_doc_count == 0
        is_low_confidence = float(run.get("confidence") or 0) < 0.6

        run.update({
            "steps": steps,
            "tool_calls": tools,
            "retrievals": retrievals,
            "multimodal_input": multimodal_input,
            "tool_names": sorted(tool_names),
            "flags": {
                "low_confidence": is_low_confidence,
                "no_retrieval": has_no_retrieval,
                "used_rag": has_rag,
                "used_image": has_image_input,
                "used_medicine": has_medicine,
                "used_llm": has_llm,
            },
            "metrics": {
                "retrieval_doc_count": retrieval_doc_count,
                "retrieval_top_score": max([item.get("top_score", 0) for item in retrievals] or [0]),
                "step_count": len(steps),
                "tool_count": len(tool_names),
            },
        })
        detailed_runs.append(run)

    return detailed_runs


def get_latest_session_medicine_topic(session_id, user_id=None):
    """
    从最近一次同会话 RAG/药品检索日志中恢复当前药品主题。
    用于“这个药/该药”这类指代问题，避免从回答正文里误抓其它药名。
    """
    if not session_id:
        return ""

    ensure_conversation_tables()

    params = [session_id]
    user_clause = ""
    if user_id is not None:
        user_clause = "AND user_id = %s"
        params.append(user_id)

    sql = f"""
        SELECT docs_json
        FROM retrieval_logs
        WHERE session_id = %s {user_clause}
        ORDER BY created_at DESC, id DESC
        LIMIT 10
    """

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

    for row in rows:
        docs = json_loads(row.get("docs_json"), [])
        for doc in docs or []:
            if isinstance(doc, dict) and doc.get("doc_type") == "medicine" and doc.get("title"):
                return str(doc.get("title", "")).strip()

    return ""
