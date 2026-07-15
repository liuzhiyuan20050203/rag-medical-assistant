import hashlib
import os
import re
import faiss
import numpy as np

from knowledge_service import get_all_diseases, get_all_medicines


index = None
documents = []
vocab = []
term_to_id = {}
vector_dimension = 4096
active_index_mode = "keyword"
configured_index_mode = "keyword"
active_embedding_model_name = ""
embedding_model = None
fallback_reason = ""


# 检索分数阈值：太低的结果不返回，避免不相关知识混进回答
# 如果后面发现检索不到内容，可以把 0.03 调低到 0.02
MIN_SCORE = 0.03
SEMANTIC_MIN_SCORE = 0.25
KEYWORD_RESULT_MIN_SCORE = 0.10
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TITLE_MATCH_BOOST = 0.45
KEYWORD_MATCH_BOOST = 0.08
MAX_KEYWORD_BOOST = 0.32


SYNONYMS = {
    # 咽喉相关
    "喉咙痛": ["咽痛", "咽喉痛", "咽部不适", "咽炎", "扁桃体炎"],
    "嗓子痛": ["咽痛", "咽喉痛", "咽部不适", "咽炎", "扁桃体炎"],
    "嗓子疼": ["咽痛", "咽喉痛", "咽部不适", "咽炎", "扁桃体炎"],
    "嗓子不舒服": ["咽部不适", "咽炎", "咽痛"],
    "吞咽痛": ["咽痛", "扁桃体炎", "咽炎"],

    # 鼻部相关
    "流鼻涕": ["流涕", "鼻塞", "清水样鼻涕", "鼻炎", "过敏性鼻炎"],
    "鼻子堵": ["鼻塞", "鼻炎", "过敏性鼻炎"],
    "鼻塞": ["鼻炎", "过敏性鼻炎", "鼻窦炎"],
    "打喷嚏": ["喷嚏", "鼻痒", "过敏性鼻炎", "鼻炎"],
    "鼻子痒": ["鼻痒", "过敏性鼻炎"],
    "清水鼻涕": ["清水样鼻涕", "过敏性鼻炎", "鼻炎"],
    "黄鼻涕": ["黄绿色鼻涕", "鼻窦炎", "鼻炎"],

    # 发热感冒相关
    "发烧": ["发热", "高热", "低热", "普通感冒", "流感样症状"],
    "体温高": ["发热", "高热"],
    "浑身酸痛": ["肌肉酸痛", "乏力", "流感样症状"],
    "怕冷": ["畏寒", "发热"],
    "感冒": ["普通感冒", "流鼻涕", "鼻塞", "咳嗽", "咽痛"],

    # 咳嗽呼吸相关
    "干咳": ["咳嗽", "咽痒", "急性支气管炎"],
    "白痰": ["咳痰", "急性支气管炎"],
    "有痰": ["咳痰", "痰液黏稠", "急性支气管炎"],
    "痰多": ["咳痰", "痰液黏稠", "祛痰"],
    "胸闷": ["胸部不适", "呼吸困难", "急性支气管炎"],
    "喘不上气": ["呼吸困难", "气促", "危险症状"],

    # 胃肠相关
    "拉肚子": ["腹泻", "大便次数增多", "肠胃炎"],
    "老想上厕所": ["腹泻", "大便次数增多"],
    "大便稀": ["腹泻", "大便次数增多"],
    "肚子疼": ["腹痛", "胃痛", "上腹痛", "肠胃炎"],
    "肚子痛": ["腹痛", "胃痛", "上腹痛", "肠胃炎"],
    "胃疼": ["胃痛", "上腹痛", "胃部不适"],
    "胃痛": ["胃部不适", "上腹痛", "消化不良"],
    "胃不舒服": ["胃痛", "上腹不适", "消化不良", "胃酸反流"],
    "胃胀": ["腹胀", "消化不良", "嗳气"],
    "肚子胀": ["腹胀", "消化不良", "排气增多"],
    "反酸水": ["反酸", "烧心", "胃酸反流"],
    "反酸": ["胃酸反流", "烧心"],
    "烧心": ["胃酸反流", "反酸", "胸口灼热"],
    "恶心想吐": ["恶心", "呕吐", "反胃"],
    "想吐": ["恶心", "呕吐", "反胃"],
    "吐了": ["呕吐", "恶心呕吐"],
    "排便困难": ["便秘", "大便干结"],
    "大便干": ["便秘", "大便干结"],

    # 皮肤过敏相关
    "皮肤痒": ["皮肤瘙痒", "瘙痒", "过敏", "湿疹", "荨麻疹"],
    "皮肤很痒": ["皮肤瘙痒", "瘙痒", "过敏", "湿疹", "荨麻疹"],
    "身上痒": ["皮肤瘙痒", "湿疹", "荨麻疹"],
    "起红疹": ["红疹", "皮疹", "皮肤过敏", "湿疹"],
    "起疹子": ["红疹", "皮疹", "皮肤过敏", "湿疹"],
    "起风团": ["荨麻疹", "风团", "皮肤瘙痒"],
    "皮肤红": ["红斑", "皮肤过敏", "接触性皮炎"],
    "脱皮": ["皮肤干燥", "足癣", "湿疹"],
    "脚痒": ["足癣", "脚痒", "脱皮"],
    "脚脱皮": ["足癣", "脚痒", "脱皮"],
    "脚趾缝痒": ["足癣", "脚痒", "脚趾缝糜烂"],
    "被蚊子咬": ["蚊虫叮咬", "局部红肿", "瘙痒"],
    "烫伤": ["轻度烫伤", "局部红肿", "水疱"],

    # 疼痛相关
    "牙疼": ["牙痛", "牙龈肿痛", "咬合痛"],
    "头疼": ["头痛", "头晕", "偏头痛"],
    "头很痛": ["头痛", "偏头痛"],
    "一边头痛": ["偏头痛", "一侧头痛"],
    "腰疼": ["腰背痛", "腰痛", "肌肉劳损"],
    "背疼": ["腰背痛", "背痛", "肌肉劳损"],
    "关节疼": ["关节痛", "关节疼痛"],
    "肌肉疼": ["肌肉酸痛", "肌肉疼痛"],

    # 女性健康
    "来月经肚子疼": ["痛经", "下腹痛", "腰酸"],
    "经期肚子疼": ["痛经", "下腹痛", "腰酸"],
    "姨妈痛": ["痛经", "下腹痛", "腰酸"],

    # 眼耳口腔
    "眼睛干": ["眼干", "眼涩", "眼疲劳"],
    "眼睛酸": ["眼疲劳", "眼胀", "视物模糊"],
    "看电脑眼睛累": ["眼疲劳", "眼干", "眼涩"],
    "耳朵疼": ["耳痛", "耳闷", "听力下降"],
    "嘴里烂了": ["口腔溃疡", "口腔疼痛"],
    "口腔疼": ["口腔溃疡", "口腔疼痛"],
    "溃疡": ["口腔溃疡", "口腔疼痛", "进食疼痛"],

    # 睡眠和全身不适
    "睡不着": ["失眠", "入睡困难"],
    "老醒": ["失眠", "易醒"],
    "早醒": ["失眠", "早醒"],
    "没精神": ["疲劳乏力", "乏力", "精神差"],
    "很累": ["疲劳乏力", "乏力"],
    "头晕": ["头晕", "低血糖样不适", "中暑", "晕车"],
    "心慌": ["低血糖样不适", "心慌", "出汗"],
    "手抖": ["低血糖样不适", "手抖", "饥饿感"],

    # 环境和出行
    "晕车": ["恶心", "头晕", "呕吐", "晕车"],
    "坐车想吐": ["晕车", "恶心", "呕吐"],
    "晒晕了": ["中暑", "头晕", "乏力"],
    "中暑了": ["中暑", "头晕", "恶心"],

    # 泌尿相关
    "尿急": ["尿频尿急", "尿痛"],
    "尿频": ["尿频尿急", "尿痛"],
    "尿痛": ["尿频尿急", "泌尿系统"],

    # 危险症状补充
    "说话不清楚": ["言语不清", "口角歪斜", "肢体无力"],
    "嘴歪": ["口角歪斜", "言语不清"],
    "一边没力气": ["肢体无力", "言语不清"],
    "突然剧烈头痛": ["突发剧烈头痛", "危险症状"],
    "大便带血": ["便血", "黑便"],
    "尿里有血": ["尿血"],
    "脸肿嘴肿": ["面唇肿胀", "过敏反应"],
    "喉咙肿喘不上气": ["喉头水肿", "呼吸困难", "过敏性休克"]
}


def clean_text(text: str):
    """
    清理文本中的空格和特殊符号
    """
    if text is None:
        return ""

    return re.sub(r"\s+", "", str(text))


def normalize_symptoms(symptoms):
    """
    兼容 symptoms 为 list 或字符串的情况
    """
    if symptoms is None:
        return []

    if isinstance(symptoms, list):
        return [str(item).strip() for item in symptoms if str(item).strip()]

    if isinstance(symptoms, str):
        return [
            item.strip()
            for item in re.split(r"[，,、;；\s]+", symptoms)
            if item.strip()
        ]

    return []


def extract_terms(text: str):
    """
    从文本中提取简单关键词和中文短语。
    这是轻量级向量化方法，不依赖外部 embedding 模型。
    """
    text = clean_text(text)
    terms = set()

    if not text:
        return terms

    # 按常见标点切分短语
    parts = re.split(r"[，。；、：:！？!?《》\n\r\t（）()【】\[\] ]+", text)
    for part in parts:
        part = part.strip()
        if 2 <= len(part) <= 12:
            terms.add(part)

    # 提取 2 字、3 字、4 字短语，适合中文关键词匹配
    for n in [2, 3, 4]:
        for i in range(len(text) - n + 1):
            term = text[i:i + n]
            if re.search(r"[\u4e00-\u9fff]", term):
                terms.add(term)

    return terms


def expand_question_terms(question: str):
    """
    对用户问题进行同义词扩展，提高检索命中率
    """
    question = clean_text(question)
    terms = extract_terms(question)

    for key, values in SYNONYMS.items():
        if key in question:
            terms.add(key)
            for value in values:
                terms.add(value)

    return terms


def build_documents():
    """
    把疾病知识库和药品知识库整理成统一的检索文档
    """
    docs = []

    diseases = get_all_diseases()
    for item in diseases:
        symptoms = normalize_symptoms(item.get("symptoms", []))

        text = (
            f"类型：常见病\n"
            f"疾病名称：{item.get('name', '')}\n"
            f"疾病类别：{item.get('category', '')}\n"
            f"常见症状：{'、'.join(symptoms)}\n"
            f"疾病描述：{item.get('description', '')}\n"
            f"护理建议：{item.get('care_advice', '')}\n"
            f"用药注意：{item.get('medicine_notice', '')}\n"
            f"就医提醒：{item.get('warning', '')}"
        )

        keywords = [
            item.get("name", ""),
            item.get("category", "")
        ] + symptoms

        docs.append({
            "doc_type": "disease",
            "title": item.get("name", ""),
            "content": text,
            "keywords": [keyword for keyword in keywords if keyword],
            "raw": {
                **item,
                "symptoms": symptoms
            }
        })

    medicines = get_all_medicines()
    for item in medicines:
        usage = item.get("usage", "") or item.get("usage_info", "")

        text = (
            f"类型：药品\n"
            f"药品名称：{item.get('name', '')}\n"
            f"药品类别：{item.get('type', '')}\n"
            f"适用情况：{usage}\n"
            f"注意事项：{item.get('notice', '')}\n"
            f"禁忌人群：{item.get('contraindication', '')}\n"
            f"不良反应：{item.get('side_effect', '')}"
        )

        keywords = [
            item.get("name", ""),
            item.get("type", "")
        ]

        docs.append({
            "doc_type": "medicine",
            "title": item.get("name", ""),
            "content": text,
            "keywords": [keyword for keyword in keywords if keyword],
            "raw": {
                **item,
                "usage": usage
            }
        })

    return docs


def build_vocab(docs):
    """
    构建词表
    """
    vocab_set = set()

    for doc in docs:
        for keyword in doc.get("keywords", []):
            if keyword:
                vocab_set.add(keyword)

        content_terms = extract_terms(doc.get("content", ""))
        vocab_set.update(content_terms)

    return vocab_set


def get_vector_dimension():
    try:
        return max(512, int(os.getenv("RAG_VECTOR_DIM", "4096")))
    except ValueError:
        return 4096


def get_configured_index_mode():
    mode = os.getenv("RAG_EMBEDDING_MODE", "keyword").strip().lower()
    if mode in {"semantic", "embedding", "sentence-transformers", "sentence_transformers"}:
        return "semantic"
    return "keyword"


def get_embedding_model_name():
    return os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip() or DEFAULT_EMBEDDING_MODEL


def load_embedding_model():
    global embedding_model, active_embedding_model_name

    model_name = get_embedding_model_name()
    if embedding_model is not None and active_embedding_model_name == model_name:
        return embedding_model

    allow_download = os.getenv("RAG_ALLOW_MODEL_DOWNLOAD", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not allow_download:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    from sentence_transformers import SentenceTransformer

    try:
        embedding_model = SentenceTransformer(model_name, local_files_only=not allow_download)
    except TypeError:
        embedding_model = SentenceTransformer(model_name)
    active_embedding_model_name = model_name
    return embedding_model


def normalize_embeddings(embeddings):
    embeddings = np.asarray(embeddings, dtype="float32")
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)

    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return embeddings / norms


def encode_semantic_texts(texts):
    model = load_embedding_model()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return normalize_embeddings(embeddings)


def normalize_match_text(text: str):
    return re.sub(r"\s+", "", str(text or "")).lower()


def title_match_boost(query_text: str, title: str):
    query_text = normalize_match_text(query_text)
    title = normalize_match_text(title)

    if not query_text or not title:
        return 0.0, []

    matched = []
    boost = 0.0
    if title in query_text:
        boost = TITLE_MATCH_BOOST
        matched.append(f"标题命中：{title}")
    elif len(title) >= 3:
        core_title = re.sub(r"(片|胶囊|颗粒|口服液|滴眼液|喷雾|软膏|乳膏|散|丸|贴|说明书)$", "", title)
        if len(core_title) >= 2 and core_title in query_text:
            boost = TITLE_MATCH_BOOST
            matched.append(f"标题核心词命中：{core_title}")

    return boost, matched


def keyword_match_boost(query_text: str, keywords):
    query_text = normalize_match_text(query_text)
    matched = []

    for keyword in keywords or []:
        normalized = normalize_match_text(keyword)
        if len(normalized) >= 2 and normalized in query_text:
            matched.append(keyword)

    unique_matched = []
    for item in matched:
        if item not in unique_matched:
            unique_matched.append(item)

    boost = min(len(unique_matched) * KEYWORD_MATCH_BOOST, MAX_KEYWORD_BOOST)
    return boost, unique_matched


def expanded_keyword_match_boost(query_text: str, keywords, direct_matches=None):
    expanded_terms = {
        normalize_match_text(term)
        for term in expand_question_terms(query_text)
        if normalize_match_text(term)
    }
    direct_matches = {normalize_match_text(item) for item in (direct_matches or [])}
    matched = []

    for keyword in keywords or []:
        normalized = normalize_match_text(keyword)
        if len(normalized) >= 2 and normalized in expanded_terms and normalized not in direct_matches:
            matched.append(keyword)

    unique_matched = []
    for item in matched:
        if item not in unique_matched:
            unique_matched.append(item)

    boost = min(len(unique_matched) * KEYWORD_MATCH_BOOST, MAX_KEYWORD_BOOST)
    return boost, unique_matched


def has_population_mismatch(question: str, doc: dict):
    scope_text = normalize_match_text(" ".join([
        doc.get("title", ""),
        (doc.get("raw") or {}).get("name", ""),
        (doc.get("raw") or {}).get("category", ""),
    ]))
    question_text = normalize_match_text(question)
    child_markers = ("儿童", "小儿", "婴儿", "婴幼儿", "幼儿")
    child_query_markers = child_markers + ("孩子", "小孩", "宝宝", "儿子", "女儿")

    return any(marker in scope_text for marker in child_markers) and not any(
        marker in question_text for marker in child_query_markers
    )


def add_exact_match_candidates(question: str, candidates):
    seen_titles = {item["doc"].get("title", "") for item in candidates}

    for doc in documents:
        if doc.get("title", "") in seen_titles:
            continue

        title_boost, _title_matches = title_match_boost(question, doc.get("title", ""))
        keyword_boost, _keyword_matches = keyword_match_boost(question, doc.get("keywords", []))
        if title_boost > 0 or keyword_boost > 0:
            candidates.append({
                "doc": doc,
                "score": 0.0,
            })
            seen_titles.add(doc.get("title", ""))

    return candidates


def hybrid_rank_results(question: str, candidates):
    ranked = []

    for candidate in candidates:
        doc = candidate["doc"]
        base_score = float(candidate["score"])
        title_boost, title_matches = title_match_boost(question, doc.get("title", ""))
        keyword_boost, keyword_matches = keyword_match_boost(question, doc.get("keywords", []))
        synonym_boost, synonym_matches = expanded_keyword_match_boost(
            question,
            doc.get("keywords", []),
            direct_matches=keyword_matches,
        )
        hybrid_score = min(base_score + title_boost + keyword_boost + synonym_boost, 1.0)

        ranked.append({
            **candidate,
            "hybrid_score": hybrid_score,
            "boost": title_boost + keyword_boost + synonym_boost,
            "match_reason": title_matches + [
                f"关键词命中：{item}" for item in keyword_matches
            ] + [
                f"同义词命中：{item}" for item in synonym_matches
            ],
        })

    ranked.sort(key=lambda item: item["hybrid_score"], reverse=True)
    return ranked


def term_hash_id(term: str, dimension: int):
    digest = hashlib.blake2b(term.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little") % dimension


def vectorize_text(terms, keywords=None):
    """
    把关键词集合转换成向量。
    terms：普通词，权重 1
    keywords：重要词，权重 3
    """
    vector = np.zeros(vector_dimension, dtype="float32")

    for term in terms:
        if term in vocab:
            vector[term_hash_id(term, vector_dimension)] += 1.0

    # 标题、症状、药品名称、用户问题命中词等重要关键词加权
    if keywords:
        for keyword in keywords:
            if keyword in vocab:
                vector[term_hash_id(keyword, vector_dimension)] += 3.0

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector


def init_vector_store():
    """
    初始化 FAISS 向量库
    """
    global index, documents, vocab, term_to_id, vector_dimension
    global active_index_mode, configured_index_mode, active_embedding_model_name, fallback_reason

    documents = build_documents()

    if not documents:
        raise ValueError("知识库为空，无法构建向量索引。")

    configured_index_mode = get_configured_index_mode()
    fallback_reason = ""
    vocab = build_vocab(documents)
    term_to_id = {}

    if configured_index_mode == "semantic":
        try:
            embeddings = encode_semantic_texts([doc["content"] for doc in documents])
            vector_dimension = embeddings.shape[1]
            dimension = embeddings.shape[1]

            index = faiss.IndexFlatIP(dimension)
            index.add(embeddings)
            active_index_mode = "semantic"

            return {
                "doc_count": len(documents),
                "dimension": dimension,
                "vocab_size": len(vocab),
                "index_mode": active_index_mode,
                "configured_mode": configured_index_mode,
                "embedding_model": active_embedding_model_name,
                "fallback": False,
                "fallback_reason": "",
                "message": "使用 sentence-transformers 语义向量构建FAISS索引成功"
            }
        except Exception as exc:
            fallback_reason = f"语义向量模型不可用，已降级为关键词检索：{exc}"

    active_index_mode = "keyword"
    active_embedding_model_name = ""
    vector_dimension = get_vector_dimension()
    embeddings = np.zeros((len(documents), vector_dimension), dtype="float32")

    for row_index, doc in enumerate(documents):
        terms = extract_terms(doc["content"])
        embeddings[row_index] = vectorize_text(terms, keywords=doc.get("keywords", []))

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    return {
        "doc_count": len(documents),
        "dimension": dimension,
        "vocab_size": len(vocab),
        "index_mode": active_index_mode,
        "configured_mode": configured_index_mode,
        "embedding_model": active_embedding_model_name,
        "fallback": configured_index_mode != active_index_mode,
        "fallback_reason": fallback_reason,
        "message": "使用固定维度关键词哈希向量构建FAISS索引成功"
    }


def search_knowledge(question: str, top_k: int = 3, score_threshold: float = MIN_SCORE):
    """
    根据用户问题检索最相关的知识
    """
    global index, documents

    if index is None:
        init_vector_store()

    if active_index_mode == "semantic":
        query_vector = encode_semantic_texts([question]).astype("float32")
        effective_score_threshold = SEMANTIC_MIN_SCORE if score_threshold == MIN_SCORE else score_threshold
    else:
        query_terms = expand_question_terms(question)

        # 给用户问题中的命中词加权，提高症状词、同义词对检索结果的影响
        query_vector = vectorize_text(
            query_terms,
            keywords=list(query_terms)
        ).reshape(1, -1).astype("float32")
        effective_score_threshold = score_threshold

    # 如果问题完全没有命中词表，直接返回空
    if np.linalg.norm(query_vector) == 0:
        return []

    # 多取一些，再做混合重排，避免语义召回把精确药名/病名挤掉
    search_k = min(max(top_k * 8, top_k, 20), len(documents))
    scores, indices = index.search(query_vector, search_k)

    candidates = []

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        if score < effective_score_threshold:
            continue

        doc = documents[idx]

        candidates.append({
            "doc": doc,
            "score": float(score),
        })

    candidates = add_exact_match_candidates(question, candidates)
    ranked_candidates = hybrid_rank_results(question, candidates)

    results = []
    for candidate in ranked_candidates:
        result_min_score = (
            SEMANTIC_MIN_SCORE
            if active_index_mode == "semantic"
            else KEYWORD_RESULT_MIN_SCORE
        )
        has_explicit_match = bool(candidate.get("match_reason"))
        if candidate["hybrid_score"] < result_min_score and not has_explicit_match:
            continue

        doc = candidate["doc"]

        if has_population_mismatch(question, doc):
            continue

        results.append({
            "title": doc["title"],
            "doc_type": doc["doc_type"],
            "score": float(candidate["hybrid_score"]),
            "base_score": float(candidate["score"]),
            "boost": float(candidate["boost"]),
            "match_reason": candidate["match_reason"],
            "index_mode": active_index_mode,
            "content": doc["content"],
            "raw": doc["raw"]
        })

        if len(results) >= top_k:
            break

    return results


def filter_answer_docs(retrieved_docs: list, database_context=None, min_score: float = 0.02):
    """
    过滤用于生成回答的RAG文档，避免低相似度噪声进入大模型或兜底模板。
    数据库已经命中的同名记录会保留，便于和结构化记录交叉验证。
    """
    database_context = database_context or {}
    matched_titles = {
        item.get("title", "")
        for item in (
            database_context.get("diseases", [])
            + database_context.get("medicines", [])
        )
    }
    effective_min_score = 0.04 if matched_titles else min_score

    filtered = []
    for doc in retrieved_docs:
        title = doc.get("title", "")
        score = doc.get("score", 0)

        if score >= effective_min_score or title in matched_titles:
            filtered.append(doc)

    return filtered


def format_match_info(item):
    matches = item.get("matched_fields", [])
    if not matches:
        return ""
    return f"匹配依据：{'；'.join(matches)}\n"


def build_simple_answer(question: str, retrieved_docs: list, database_context=None):
    """
    根据数据库命中和RAG检索结果生成简单结构化回答。
    该回答作为大模型不可用时的兜底方案，仍然优先使用结构化数据库记录。
    """
    database_context = database_context or {}
    db_disease_docs = database_context.get("diseases", [])
    db_medicine_docs = database_context.get("medicines", [])

    if not retrieved_docs and not db_disease_docs and not db_medicine_docs:
        return (
            "数据库和知识库中暂未检索到足够相关的信息。"
            "建议你补充更详细的症状描述，例如主要不适、伴随症状、是否用药和特殊人群情况。"
            "本系统仅提供健康信息参考，不能替代医生诊断或药师指导。"
        )

    disease_docs = [doc for doc in retrieved_docs if doc.get("doc_type") == "disease"]
    medicine_docs = [doc for doc in retrieved_docs if doc.get("doc_type") == "medicine"]

    answer = "根据你描述的情况，系统已结合数据库命中记录和RAG知识库检索结果，得到以下相关信息：\n\n"

    if db_disease_docs:
        answer += "一、数据库命中的常见病方向：\n"

        for item in db_disease_docs:
            raw = item.get("raw", {})

            answer += f"\n【{raw.get('name', '')}】\n"
            answer += format_match_info(item)
            answer += f"常见症状：{'、'.join(normalize_symptoms(raw.get('symptoms', [])))}\n"
            answer += f"症状说明：{raw.get('description', '')}\n"
            answer += f"日常护理：{raw.get('care_advice', '')}\n"
            answer += f"用药注意：{raw.get('medicine_notice', '')}\n"
            answer += f"就医提醒：{raw.get('warning', '')}\n"

    if db_medicine_docs:
        answer += "\n二、数据库命中的药品或用药注意：\n"

        for item in db_medicine_docs:
            raw = item.get("raw", {})

            answer += f"\n【{raw.get('name', '')}】\n"
            answer += format_match_info(item)
            answer += f"药品类别：{raw.get('type', '')}\n"
            answer += f"适用情况：{raw.get('usage', '')}\n"
            answer += f"注意事项：{raw.get('notice', '')}\n"
            answer += f"禁忌人群：{raw.get('contraindication', '')}\n"
            answer += f"不良反应：{raw.get('side_effect', '')}\n"

    shown_titles = {
        item.get("title", "")
        for item in db_disease_docs + db_medicine_docs
    }
    rag_supplements = [
        doc for doc in disease_docs + medicine_docs
        if doc.get("title", "") not in shown_titles
    ]

    if rag_supplements:
        answer += "\n三、RAG知识库补充：\n"

        for doc in rag_supplements[:3]:
            raw = doc.get("raw", {})
            if doc.get("doc_type") == "disease":
                answer += f"\n【{raw.get('name', doc.get('title', ''))}】\n"
                answer += f"常见症状：{'、'.join(raw.get('symptoms', []))}\n"
                answer += f"护理建议：{raw.get('care_advice', '')}\n"
                answer += f"就医提醒：{raw.get('warning', '')}\n"
            else:
                answer += f"\n【{raw.get('name', doc.get('title', ''))}】\n"
                answer += f"适用情况：{raw.get('usage', '')}\n"
                answer += f"注意事项：{raw.get('notice', '')}\n"

    answer += "\n四、系统提示：\n"
    answer += (
        "本系统仅提供健康信息参考，不能替代医生诊断或药师指导。"
        "如症状持续加重、出现高热不退、呼吸困难、胸痛、意识异常等情况，应及时就医。"
    )

    return answer
