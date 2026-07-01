import re
import faiss
import numpy as np

from knowledge_service import get_all_diseases, get_all_medicines


index = None
documents = []
vocab = []
term_to_id = {}


SYNONYMS = {
    "喉咙痛": ["咽痛", "咽喉痛", "咽部不适"],
    "嗓子痛": ["咽痛", "咽喉痛", "咽部不适"],
    "流鼻涕": ["流涕", "鼻塞"],
    "鼻子堵": ["鼻塞"],
    "发烧": ["发热", "高热", "低热"],
    "拉肚子": ["腹泻", "大便次数增多"],
    "肚子疼": ["腹痛", "胃痛", "上腹痛"],
    "肚子痛": ["腹痛", "胃痛", "上腹痛"],
    "胃不舒服": ["胃痛", "上腹不适", "消化不良"],
    "皮肤痒": ["皮肤瘙痒", "瘙痒", "过敏"],
    "起红疹": ["红疹", "皮疹", "皮肤过敏"],
    "牙疼": ["牙痛", "牙龈肿痛"],
    "头疼": ["头痛", "头晕"]
}


def clean_text(text: str):
    """
    清理文本中的空格和特殊符号
    """
    return re.sub(r"\s+", "", text)


def extract_terms(text: str):
    """
    从文本中提取简单关键词和中文短语。
    这是简化版向量化方法，不依赖大模型。
    """
    text = clean_text(text)
    terms = set()

    # 按常见标点切分短语
    parts = re.split(r"[，。；、：:\n\r\t（）()【】\[\] ]+", text)
    for part in parts:
        if 2 <= len(part) <= 12:
            terms.add(part)

    # 提取2字、3字、4字短语，适合中文关键词匹配
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
        symptoms = item.get("symptoms", [])

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
            "keywords": keywords,
            "raw": item
        })

    medicines = get_all_medicines()
    for item in medicines:
        text = (
            f"类型：药品\n"
            f"药品名称：{item.get('name', '')}\n"
            f"药品类别：{item.get('type', '')}\n"
            f"适用情况：{item.get('usage', '')}\n"
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
            "keywords": keywords,
            "raw": item
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

    return sorted(list(vocab_set))


def vectorize_text(terms, keywords=None):
    """
    把关键词集合转换成向量
    """
    vector = np.zeros(len(vocab), dtype="float32")

    for term in terms:
        if term in term_to_id:
            vector[term_to_id[term]] += 1.0

    # 标题、症状、药品名称等关键词加权，提高检索准确性
    if keywords:
        for keyword in keywords:
            if keyword in term_to_id:
                vector[term_to_id[keyword]] += 3.0

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector


def init_vector_store():
    """
    初始化FAISS向量库
    """
    global index, documents, vocab, term_to_id

    documents = build_documents()

    if not documents:
        raise ValueError("知识库为空，无法构建向量索引。")

    vocab = build_vocab(documents)
    term_to_id = {term: i for i, term in enumerate(vocab)}

    vectors = []

    for doc in documents:
        terms = extract_terms(doc["content"])
        vector = vectorize_text(terms, keywords=doc.get("keywords", []))
        vectors.append(vector)

    embeddings = np.array(vectors).astype("float32")

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    return {
        "doc_count": len(documents),
        "dimension": dimension,
        "message": "使用简化关键词向量方式构建FAISS索引成功"
    }


def search_knowledge(question: str, top_k: int = 3):
    """
    根据用户问题检索最相关的知识
    """
    global index, documents

    if index is None:
        init_vector_store()

    query_terms = expand_question_terms(question)
    query_vector = vectorize_text(query_terms).reshape(1, -1).astype("float32")

    # 如果问题完全没有命中词表，直接返回空
    if np.linalg.norm(query_vector) == 0:
        return []

    scores, indices = index.search(query_vector, top_k)

    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        if score <= 0:
            continue

        doc = documents[idx]

        results.append({
            "title": doc["title"],
            "doc_type": doc["doc_type"],
            "score": float(score),
            "content": doc["content"],
            "raw": doc["raw"]
        })

    return results


def build_simple_answer(question: str, retrieved_docs: list):
    """
    根据检索结果生成简单结构化回答。
    第一版先不用大模型，后续可以替换成DeepSeek或通义千问生成。
    """
    if not retrieved_docs:
        return (
            "知识库中暂未检索到足够相关的信息。"
            "建议你补充更详细的症状描述，或咨询医生、药师。"
            "本系统仅提供健康信息参考，不能替代医生诊断。"
        )

    disease_docs = [doc for doc in retrieved_docs if doc["doc_type"] == "disease"]
    medicine_docs = [doc for doc in retrieved_docs if doc["doc_type"] == "medicine"]

    answer = "根据你描述的情况，系统从知识库中检索到了以下相关信息：\n\n"

    if disease_docs:
        answer += "一、可能相关的常见病方向：\n"

        for doc in disease_docs:
            raw = doc["raw"]

            answer += f"\n【{raw.get('name', '')}】\n"
            answer += f"常见症状：{'、'.join(raw.get('symptoms', []))}\n"
            answer += f"症状说明：{raw.get('description', '')}\n"
            answer += f"日常护理：{raw.get('care_advice', '')}\n"
            answer += f"用药注意：{raw.get('medicine_notice', '')}\n"
            answer += f"就医提醒：{raw.get('warning', '')}\n"

    if medicine_docs:
        answer += "\n二、相关药品或用药注意：\n"

        for doc in medicine_docs:
            raw = doc["raw"]

            answer += f"\n【{raw.get('name', '')}】\n"
            answer += f"药品类别：{raw.get('type', '')}\n"
            answer += f"适用情况：{raw.get('usage', '')}\n"
            answer += f"注意事项：{raw.get('notice', '')}\n"
            answer += f"禁忌人群：{raw.get('contraindication', '')}\n"
            answer += f"不良反应：{raw.get('side_effect', '')}\n"

    answer += "\n三、系统提示：\n"
    answer += (
        "本系统仅提供健康信息参考，不能替代医生诊断或药师指导。"
        "如症状持续加重、出现高热不退、呼吸困难、胸痛等情况，应及时就医。"
    )

    return answer