import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

import faiss
import numpy as np
from dotenv import load_dotenv

from knowledge_service import get_all_diseases, get_all_medicines, get_all_warning_rules


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = DATA_DIR / "rag_index"
INDEX_FILE = INDEX_DIR / "knowledge.faiss"
DOCUMENTS_FILE = INDEX_DIR / "documents.json"
MANIFEST_FILE = INDEX_DIR / "manifest.json"
DEFAULT_EVAL_FILE = DATA_DIR / "rag_eval_cases.json"

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_RERANK_MODEL = "lexical"
EMBEDDING_BACKEND = "sentence-transformers"
RERANK_BACKEND = "lexical"
CROSS_ENCODER_RERANK_BACKEND = "cross-encoder"
LEXICAL_RERANK_MODELS = {"lexical", "local", "keyword", "keywords", "bm25", "tfidf", "simple"}
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_+-]+|[\u4e00-\u9fff]+")
CHINESE_PATTERN = re.compile(r"^[\u4e00-\u9fff]+$")
INDEX_VERSION = 3

load_dotenv(BASE_DIR / ".env", override=False)

index = None
documents = []
index_manifest = {}
embedding_provider = None
reranker_provider = None


def env_float(name: str, default: float):
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_int(name: str, default: int):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_bool(name: str, default: bool):
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on", "y"}


MIN_SCORE = env_float("RAG_MIN_SCORE", 0.25)
ANSWER_MIN_SCORE = env_float("RAG_ANSWER_MIN_SCORE", 0.28)
CHUNK_MAX_CHARS = max(160, env_int("RAG_CHUNK_MAX_CHARS", 360))
CHUNK_OVERLAP = max(0, env_int("RAG_CHUNK_OVERLAP", 80))
RERANK_ENABLED = env_bool("RAG_RERANK_ENABLED", True)
RERANK_TOP_N = max(1, env_int("RAG_RERANK_TOP_N", 24))
RERANK_WEIGHT = min(1.0, max(0.0, env_float("RAG_RERANK_WEIGHT", 0.65)))
DEDUP_PARENT = env_bool("RAG_DEDUP_PARENT", True)


def clean_text(text: str):
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def compact_text(value, limit=260):
    if isinstance(value, list):
        value = "、".join(str(item) for item in value if item)

    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def normalize_symptoms(symptoms):
    if symptoms is None:
        return []

    if isinstance(symptoms, list):
        return [str(item).strip() for item in symptoms if str(item).strip()]

    if isinstance(symptoms, str):
        return [
            item.strip()
            for item in re.split(r"[、,，;；\s]+", symptoms)
            if item.strip()
        ]

    return []


def stable_hash(value: str, length=12):
    digest = hashlib.sha256((value or "").encode("utf-8")).hexdigest()
    return digest[:length]


def get_embedding_model_name():
    return os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip() or DEFAULT_EMBEDDING_MODEL


def get_rerank_model_name():
    return os.getenv("RAG_RERANK_MODEL", DEFAULT_RERANK_MODEL).strip() or DEFAULT_RERANK_MODEL


def is_lexical_rerank_model(model_name=None):
    return (model_name or get_rerank_model_name()).strip().lower() in LEXICAL_RERANK_MODELS


def get_rerank_backend():
    if not RERANK_ENABLED:
        return ""
    if is_lexical_rerank_model():
        return RERANK_BACKEND
    return CROSS_ENCODER_RERANK_BACKEND


def get_embedding_batch_size():
    return max(1, env_int("RAG_EMBEDDING_BATCH_SIZE", 32))


def embedding_prefix(is_query=False):
    if is_query:
        return os.getenv("RAG_QUERY_PREFIX", "").strip()
    return os.getenv("RAG_DOCUMENT_PREFIX", "").strip()


class SentenceTransformerEmbeddingProvider:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.device = os.getenv("RAG_EMBEDDING_DEVICE", "").strip() or None
        self._model = None

    @property
    def backend(self):
        return EMBEDDING_BACKEND

    def load_model(self):
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "缺少 sentence-transformers，无法生成真实语义 embedding。"
                "请先在 backend 目录执行：pip install -r requirements.txt"
            ) from exc

        kwargs = {}
        if self.device:
            kwargs["device"] = self.device

        self._model = SentenceTransformer(self.model_name, **kwargs)
        return self._model

    def encode(self, texts, is_query=False):
        if isinstance(texts, str):
            texts = [texts]

        prefix = embedding_prefix(is_query=is_query)
        prepared = [
            f"{prefix} {clean_text(text)}".strip() if prefix else clean_text(text)
            for text in texts
        ]

        model = self.load_model()
        vectors = model.encode(
            prepared,
            batch_size=get_embedding_batch_size(),
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        vectors = np.asarray(vectors, dtype="float32")
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        faiss.normalize_L2(vectors)
        return vectors


class CrossEncoderReranker:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.device = os.getenv("RAG_RERANK_DEVICE", "").strip() or None
        self._model = None

    @property
    def backend(self):
        return CROSS_ENCODER_RERANK_BACKEND

    def load_model(self):
        if self._model is not None:
            return self._model

        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "缺少 sentence-transformers，无法执行 rerank。"
                "请先在 backend 目录执行：pip install -r requirements.txt"
            ) from exc

        kwargs = {}
        if self.device:
            kwargs["device"] = self.device

        self._model = CrossEncoder(self.model_name, **kwargs)
        return self._model

    def score(self, query: str, docs):
        if not docs:
            return []

        model = self.load_model()
        pairs = [
            [query, doc.get("embedding_text") or doc.get("content", "")]
            for doc in docs
        ]
        scores = model.predict(pairs, show_progress_bar=False)
        return [float(score) for score in scores]


def get_embedding_provider():
    global embedding_provider

    model_name = get_embedding_model_name()
    if embedding_provider is None or embedding_provider.model_name != model_name:
        embedding_provider = SentenceTransformerEmbeddingProvider(model_name)

    return embedding_provider


def get_reranker_provider():
    global reranker_provider

    model_name = get_rerank_model_name()
    if is_lexical_rerank_model(model_name):
        return None

    if reranker_provider is None or reranker_provider.model_name != model_name:
        reranker_provider = CrossEncoderReranker(model_name)

    return reranker_provider


def disease_source(item):
    record_id = item.get("id")
    title = item.get("name", "")
    source_id = f"disease:{record_id}" if record_id else f"disease:{stable_hash(title)}"

    return {
        "id": source_id,
        "kind": "structured_database_record",
        "table": "diseases",
        "record_id": record_id,
        "title": title,
        "label": f"疾病知识库 diseases#{record_id}" if record_id else "疾病知识库 diseases",
        "url": item.get("source_url", "") or "",
        "fields": ["name", "category", "symptoms", "description", "care_advice", "medicine_notice", "warning"],
    }


def medicine_source(item):
    record_id = item.get("id")
    title = item.get("name", "")
    source_id = f"medicine:{record_id}" if record_id else f"medicine:{stable_hash(title)}"

    return {
        "id": source_id,
        "kind": "structured_database_record",
        "table": "medicines",
        "record_id": record_id,
        "title": title,
        "label": f"药品知识库 medicines#{record_id}" if record_id else "药品知识库 medicines",
        "url": item.get("source_url", "") or "",
        "fields": ["name", "type", "usage", "notice", "contraindication", "side_effect"],
    }


def warning_rule_source(item):
    record_id = item.get("id")
    keyword = item.get("keyword", "")
    source_id = f"warning_rule:{record_id}" if record_id else f"warning_rule:{stable_hash(keyword)}"

    return {
        "id": source_id,
        "kind": "structured_database_record",
        "table": "warning_rules",
        "record_id": record_id,
        "title": keyword,
        "label": f"危险症状规则 warning_rules#{record_id}" if record_id else "危险症状规则 warning_rules",
        "url": "",
        "fields": ["keyword", "risk_level", "advice"],
    }


def build_citation(source):
    title = source.get("title", "") or "未命名资料"
    label = source.get("label", "") or source.get("table", "knowledge")
    url = source.get("url", "")
    citation = f"{source.get('id', '')} | {label} | {title}"
    if url:
        citation += f" | {url}"
    return citation


def source_to_citation_dict(source, score=None):
    item = {
        "id": source.get("id", ""),
        "parent_id": source.get("parent_id", ""),
        "title": source.get("title", ""),
        "label": source.get("label", ""),
        "table": source.get("table", ""),
        "record_id": source.get("record_id"),
        "chunk_index": source.get("chunk_index"),
        "chunk_count": source.get("chunk_count"),
        "url": source.get("url", ""),
        "citation": build_citation(source),
    }
    if score is not None:
        item["score"] = float(score)
    return item


def chunk_text(text: str, max_chars=None, overlap=None):
    raw_text = "" if text is None else str(text)
    if not raw_text.strip():
        return []

    max_chars = max_chars or CHUNK_MAX_CHARS
    overlap = CHUNK_OVERLAP if overlap is None else overlap

    if len(clean_text(raw_text)) <= max_chars:
        return [clean_text(raw_text)]

    paragraphs = [
        clean_text(part)
        for part in re.split(r"[\n\r]+", raw_text)
        if clean_text(part)
    ]
    if not paragraphs:
        paragraphs = [clean_text(raw_text)]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue

        candidate = f"{current}\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue

        chunks.append(current)
        prefix = current[-overlap:] if overlap and len(current) > overlap else ""
        current = f"{prefix}\n{paragraph}".strip() if prefix else paragraph

        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            prefix = current[max_chars - overlap:max_chars] if overlap else ""
            current = f"{prefix}{current[max_chars:]}".strip()

    if current:
        chunks.append(current)

    return chunks


def chunk_document(doc):
    chunks = chunk_text(doc.get("content", ""))
    if not chunks:
        return []

    parent_id = doc.get("id", "")
    chunk_count = len(chunks)
    result = []

    for index_value, chunk in enumerate(chunks, start=1):
        source = dict(doc.get("source") or {})
        source["parent_id"] = parent_id
        source["chunk_index"] = index_value
        source["chunk_count"] = chunk_count
        source["id"] = f"{parent_id}:chunk:{index_value}"
        source["label"] = f"{source.get('label', source.get('table', 'knowledge'))} 片段 {index_value}/{chunk_count}"

        embedding_text = "\n".join([
            doc.get("title", ""),
            " ".join(doc.get("keywords", [])),
            chunk,
        ])

        result.append({
            **doc,
            "id": source["id"],
            "parent_id": parent_id,
            "chunk_index": index_value,
            "chunk_count": chunk_count,
            "content": chunk,
            "embedding_text": embedding_text,
            "source": source,
            "citation": build_citation(source),
        })

    return result


def chunk_documents(docs):
    chunks = []
    for doc in docs:
        chunks.extend(chunk_document(doc))
    return chunks


def build_documents():
    docs = []

    diseases = get_all_diseases()
    for item in diseases:
        symptoms = normalize_symptoms(item.get("symptoms", []))
        source = disease_source(item)

        content = "\n".join([
            "类型：常见病",
            f"疾病名称：{item.get('name', '')}",
            f"疾病类别：{item.get('category', '')}",
            f"常见症状：{'、'.join(symptoms)}",
            f"疾病描述：{item.get('description', '')}",
            f"护理建议：{item.get('care_advice', '')}",
            f"用药注意：{item.get('medicine_notice', '')}",
            f"就医提醒：{item.get('warning', '')}",
        ])

        keywords = [item.get("name", ""), item.get("category", "")] + symptoms
        embedding_text = "\n".join([
            item.get("name", ""),
            item.get("category", ""),
            " ".join(symptoms),
            content,
        ])

        docs.append({
            "id": source["id"],
            "doc_type": "disease",
            "title": item.get("name", ""),
            "content": content,
            "embedding_text": embedding_text,
            "keywords": [keyword for keyword in keywords if keyword],
            "source": source,
            "citation": build_citation(source),
            "raw": {
                **item,
                "symptoms": symptoms,
            },
        })

    medicines = get_all_medicines()
    for item in medicines:
        usage = item.get("usage", "") or item.get("usage_info", "")
        source = medicine_source(item)

        content = "\n".join([
            "类型：药品",
            f"药品名称：{item.get('name', '')}",
            f"药品类别：{item.get('type', '')}",
            f"适用情况：{usage}",
            f"注意事项：{item.get('notice', '')}",
            f"禁忌人群：{item.get('contraindication', '')}",
            f"不良反应：{item.get('side_effect', '')}",
        ])

        keywords = [item.get("name", ""), item.get("type", "")]
        embedding_text = "\n".join([
            item.get("name", ""),
            item.get("type", ""),
            usage,
            content,
        ])

        docs.append({
            "id": source["id"],
            "doc_type": "medicine",
            "title": item.get("name", ""),
            "content": content,
            "embedding_text": embedding_text,
            "keywords": [keyword for keyword in keywords if keyword],
            "source": source,
            "citation": build_citation(source),
            "raw": {
                **item,
                "usage": usage,
            },
        })

    warning_rules = get_all_warning_rules()
    for item in warning_rules:
        source = warning_rule_source(item)
        keyword = item.get("keyword", "")
        risk_level = item.get("risk_level", "") or "high"
        advice = item.get("advice", "")

        content = "\n".join([
            "类型：危险症状规则",
            f"危险关键词：{keyword}",
            f"风险等级：{risk_level}",
            f"处理建议：{advice}",
            "提示：如果用户描述出现该危险症状，应提醒及时就医或联系急救。",
        ])

        keywords = [keyword, risk_level, "危险症状", "及时就医", "急救"]
        embedding_text = "\n".join([
            keyword,
            risk_level,
            "危险症状 及时就医 急救 红旗症状",
            advice,
            content,
        ])

        docs.append({
            "id": source["id"],
            "doc_type": "warning_rule",
            "title": keyword,
            "content": content,
            "embedding_text": embedding_text,
            "keywords": [term for term in keywords if term],
            "source": source,
            "citation": build_citation(source),
            "raw": item,
        })

    return chunk_documents(docs)


def corpus_fingerprint(docs):
    payload = [
        {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "doc_type": doc.get("doc_type"),
            "content": doc.get("content"),
            "source": doc.get("source"),
        }
        for doc in docs
    ]
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def read_json(path, default=None):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def manifest_matches(manifest, docs, provider):
    if not manifest:
        return False

    return (
        manifest.get("index_version") == INDEX_VERSION
        and manifest.get("backend") == provider.backend
        and manifest.get("model") == provider.model_name
        and manifest.get("corpus_fingerprint") == corpus_fingerprint(docs)
        and manifest.get("doc_count") == len(docs)
        and int(manifest.get("chunk_max_chars", 0) or 0) == CHUNK_MAX_CHARS
        and int(manifest.get("chunk_overlap", 0) or 0) == CHUNK_OVERLAP
        and INDEX_FILE.exists()
        and DOCUMENTS_FILE.exists()
    )


def load_persisted_store(docs, provider):
    global index, documents, index_manifest

    manifest = read_json(MANIFEST_FILE, default={})
    if not manifest_matches(manifest, docs, provider):
        return None

    persisted_docs = read_json(DOCUMENTS_FILE, default=[])
    if len(persisted_docs) != len(docs):
        return None

    index = faiss.read_index(str(INDEX_FILE))
    documents = persisted_docs
    index_manifest = manifest

    return {
        "doc_count": len(documents),
        "dimension": int(manifest.get("dimension", 0)),
        "backend": provider.backend,
        "model": provider.model_name,
        "rerank_enabled": RERANK_ENABLED,
        "rerank_backend": get_rerank_backend(),
        "rerank_model": get_rerank_model_name() if RERANK_ENABLED else "",
        "chunk_max_chars": CHUNK_MAX_CHARS,
        "chunk_overlap": CHUNK_OVERLAP,
        "persisted": True,
        "index_path": str(INDEX_FILE),
        "message": "已从磁盘加载切片语义 FAISS 索引",
    }


def persist_store(store_index, docs, manifest):
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(store_index, str(INDEX_FILE))
    write_json(DOCUMENTS_FILE, docs)
    write_json(MANIFEST_FILE, manifest)


def init_vector_store(force_rebuild=False):
    global index, documents, index_manifest

    docs = build_documents()
    if not docs:
        raise ValueError("知识库为空，无法构建语义向量索引。")

    provider = get_embedding_provider()

    if not force_rebuild:
        loaded = load_persisted_store(docs, provider)
        if loaded:
            return loaded

    texts = [doc.get("embedding_text") or doc.get("content", "") for doc in docs]
    embeddings = provider.encode(texts, is_query=False)
    dimension = int(embeddings.shape[1])

    store_index = faiss.IndexFlatIP(dimension)
    store_index.add(embeddings)

    manifest = {
        "index_version": INDEX_VERSION,
        "backend": provider.backend,
        "model": provider.model_name,
        "dimension": dimension,
        "doc_count": len(docs),
        "corpus_fingerprint": corpus_fingerprint(docs),
        "chunk_max_chars": CHUNK_MAX_CHARS,
        "chunk_overlap": CHUNK_OVERLAP,
        "rerank_enabled": RERANK_ENABLED,
        "rerank_backend": get_rerank_backend(),
        "rerank_model": get_rerank_model_name() if RERANK_ENABLED else "",
        "dedup_parent": DEDUP_PARENT,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "index_file": str(INDEX_FILE),
        "documents_file": str(DOCUMENTS_FILE),
    }

    persist_store(store_index, docs, manifest)

    index = store_index
    documents = docs
    index_manifest = manifest

    return {
        "doc_count": len(documents),
        "dimension": dimension,
        "backend": provider.backend,
        "model": provider.model_name,
        "rerank_enabled": RERANK_ENABLED,
        "rerank_backend": get_rerank_backend(),
        "rerank_model": get_rerank_model_name() if RERANK_ENABLED else "",
        "chunk_max_chars": CHUNK_MAX_CHARS,
        "chunk_overlap": CHUNK_OVERLAP,
        "persisted": True,
        "index_path": str(INDEX_FILE),
        "message": "已使用切片语义 embedding 构建并持久化 FAISS 索引",
    }


def get_vector_store_status():
    manifest = read_json(MANIFEST_FILE, default={}) or {}
    provider = get_embedding_provider()

    return {
        "initialized": index is not None,
        "doc_count": len(documents) if documents else int(manifest.get("doc_count", 0) or 0),
        "dimension": int(manifest.get("dimension", 0) or 0),
        "backend": manifest.get("backend") or provider.backend,
        "model": manifest.get("model") or provider.model_name,
        "rerank_enabled": RERANK_ENABLED,
        "rerank_backend": get_rerank_backend(),
        "rerank_model": get_rerank_model_name() if RERANK_ENABLED else "",
        "chunk_max_chars": int(manifest.get("chunk_max_chars", CHUNK_MAX_CHARS) or CHUNK_MAX_CHARS),
        "chunk_overlap": int(manifest.get("chunk_overlap", CHUNK_OVERLAP) or CHUNK_OVERLAP),
        "index_version": manifest.get("index_version"),
        "persisted": INDEX_FILE.exists() and DOCUMENTS_FILE.exists() and MANIFEST_FILE.exists(),
        "index_path": str(INDEX_FILE),
        "documents_path": str(DOCUMENTS_FILE),
        "manifest_path": str(MANIFEST_FILE),
        "created_at": manifest.get("created_at", ""),
        "min_score": MIN_SCORE,
        "answer_min_score": ANSWER_MIN_SCORE,
    }


def sigmoid(value):
    value = max(-60.0, min(60.0, float(value)))
    return 1.0 / (1.0 + np.exp(-value))


def flatten_lexical_value(value):
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(flatten_lexical_value(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(flatten_lexical_value(item) for item in value)
    return str(value)


def lexical_terms(text):
    terms = set()
    normalized = clean_text(text).lower()

    for token in TOKEN_PATTERN.findall(normalized):
        if not token:
            continue

        if CHINESE_PATTERN.match(token):
            if len(token) <= 12:
                terms.add(token)

            max_ngram = min(6, len(token))
            for size in range(2, max_ngram + 1):
                for start in range(0, len(token) - size + 1):
                    terms.add(token[start:start + size])
        elif len(token) >= 2:
            terms.add(token)

    return terms


def candidate_lexical_text(candidate):
    raw = candidate.get("raw") or {}
    source = candidate.get("source") or {}
    keywords = candidate.get("keywords") or raw.get("keywords") or []

    return clean_text(" ".join([
        candidate.get("title", ""),
        source.get("title", ""),
        candidate.get("doc_type", ""),
        candidate.get("content", ""),
        flatten_lexical_value(keywords),
        flatten_lexical_value(raw),
    ]))


def lexical_rerank_score(question, candidate):
    query_terms = lexical_terms(question)
    if not query_terms:
        return 0.0

    haystack = candidate_lexical_text(candidate).lower()
    title_text = clean_text(candidate.get("title", "")).lower()
    content_text = clean_text(candidate.get("content", "")).lower()

    matched = 0
    weighted = 0.0
    for term in query_terms:
        if term not in haystack:
            continue

        matched += 1
        weight = 1.0 + min(len(term), 6) * 0.08
        if term in title_text:
            weight += 0.65
        elif term in content_text:
            weight += 0.2
        weighted += weight

    compact_query = "".join(TOKEN_PATTERN.findall(clean_text(question).lower()))
    compact_haystack = "".join(TOKEN_PATTERN.findall(haystack))
    exact_bonus = 0.12 if compact_query and compact_query in compact_haystack else 0.0

    coverage = matched / max(len(query_terms), 1)
    density = weighted / max(len(query_terms) * 1.9, 1.0)
    return min(1.0, 0.68 * coverage + 0.32 * min(1.0, density) + exact_bonus)


def combine_embedding_and_rerank_score(candidate, rerank_score):
    embedding_score = float(candidate.get("embedding_score", candidate.get("score", 0)) or 0)
    embedding_norm = max(0.0, min(1.0, (embedding_score + 1.0) / 2.0))
    combined_score = RERANK_WEIGHT * float(rerank_score) + (1.0 - RERANK_WEIGHT) * embedding_norm
    return embedding_score, combined_score


def rerank_candidates(question, candidates):
    if not RERANK_ENABLED or not candidates:
        return candidates

    if is_lexical_rerank_model():
        reranked = []
        for candidate in candidates:
            rerank_score = lexical_rerank_score(question, candidate)
            embedding_score, combined_score = combine_embedding_and_rerank_score(candidate, rerank_score)
            reranked.append({
                **candidate,
                "score": combined_score,
                "embedding_score": embedding_score,
                "rerank_score": float(rerank_score),
                "rerank_raw_score": float(rerank_score),
                "rerank_backend": RERANK_BACKEND,
            })

        reranked.sort(key=lambda item: item.get("score", 0), reverse=True)
        return reranked

    reranker = get_reranker_provider()
    rerank_scores = reranker.score(question, candidates)

    reranked = []
    for candidate, raw_rerank_score in zip(candidates, rerank_scores):
        rerank_score = float(sigmoid(raw_rerank_score))
        embedding_score, combined_score = combine_embedding_and_rerank_score(candidate, rerank_score)
        reranked.append({
            **candidate,
            "score": combined_score,
            "embedding_score": embedding_score,
            "rerank_score": rerank_score,
            "rerank_raw_score": float(raw_rerank_score),
            "rerank_backend": CROSS_ENCODER_RERANK_BACKEND,
        })

    reranked.sort(key=lambda item: item.get("score", 0), reverse=True)
    return reranked


def dedupe_parent_results(results, limit):
    if not DEDUP_PARENT:
        return results[:limit]

    deduped = []
    seen = set()

    for result in results:
        key = result.get("parent_id") or result.get("source", {}).get("parent_id") or result.get("id")
        if key in seen:
            continue
        deduped.append(result)
        seen.add(key)
        if len(deduped) >= limit:
            break

    return deduped


def result_from_doc(doc, score, embedding_score=None):
    return {
        "id": doc.get("id", ""),
        "parent_id": doc.get("parent_id", ""),
        "chunk_index": doc.get("chunk_index"),
        "chunk_count": doc.get("chunk_count"),
        "title": doc.get("title", ""),
        "doc_type": doc.get("doc_type", ""),
        "score": float(score),
        "embedding_score": float(embedding_score if embedding_score is not None else score),
        "content": doc.get("content", ""),
        "keywords": doc.get("keywords", []),
        "source": doc.get("source", {}),
        "citation": doc.get("citation") or build_citation(doc.get("source", {})),
        "raw": doc.get("raw", {}),
    }


def search_knowledge(question: str, top_k: int = 3, score_threshold=None):
    global index, documents

    question = clean_text(question)
    if not question:
        return []

    if index is None or not documents:
        init_vector_store()

    if not documents:
        return []

    if score_threshold is None:
        score_threshold = MIN_SCORE

    provider = get_embedding_provider()
    query_vector = provider.encode([question], is_query=True)
    search_k = min(max(int(top_k) * 6, RERANK_TOP_N, int(top_k)), len(documents))
    scores, indices = index.search(query_vector, search_k)

    candidates = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        if float(score) < score_threshold:
            continue

        candidates.append(result_from_doc(documents[int(idx)], float(score), embedding_score=float(score)))

    reranked = rerank_candidates(question, candidates)
    return dedupe_parent_results(reranked, top_k)


def filter_answer_docs(retrieved_docs: list, database_context=None, min_score=None):
    database_context = database_context or {}
    matched_titles = {
        item.get("title", "")
        for item in (
            database_context.get("diseases", [])
            + database_context.get("medicines", [])
        )
    }

    if min_score is None:
        min_score = ANSWER_MIN_SCORE

    effective_min_score = min_score + 0.04 if matched_titles else min_score

    filtered = []
    for doc in retrieved_docs or []:
        title = doc.get("title", "")
        score = float(doc.get("score", 0) or 0)

        if score >= effective_min_score or title in matched_titles:
            filtered.append(doc)

    return filtered


def format_match_info(item):
    matches = item.get("matched_fields", [])
    if not matches:
        return ""
    return f"匹配依据：{'；'.join(matches)}\n"


def database_item_source(item, doc_type):
    raw = item.get("raw") or {}
    if doc_type == "disease":
        return disease_source(raw)
    return medicine_source(raw)


def collect_citations(retrieved_docs=None, database_context=None):
    citations = []
    seen = set()

    database_context = database_context or {}
    for item in database_context.get("diseases", []):
        source = database_item_source(item, "disease")
        key = source.get("id")
        if key and key not in seen:
            citations.append(source_to_citation_dict(source, score=item.get("score")))
            seen.add(key)

    for item in database_context.get("medicines", []):
        source = database_item_source(item, "medicine")
        key = source.get("id")
        if key and key not in seen:
            citations.append(source_to_citation_dict(source, score=item.get("score")))
            seen.add(key)

    for doc in retrieved_docs or []:
        source = doc.get("source") or {}
        key = source.get("id") or doc.get("id")
        if key and key not in seen:
            citations.append(source_to_citation_dict(source, score=doc.get("score")))
            seen.add(key)

    return citations


def append_citations_to_answer(answer: str, citations):
    citations = citations or []
    if not citations:
        return answer

    lines = ["", "参考来源："]
    for index_value, citation in enumerate(citations[:8], start=1):
        lines.append(f"[{index_value}] {citation.get('citation', '')}")

    return (answer or "").rstrip() + "\n".join(lines)


def build_simple_answer(question: str, retrieved_docs: list, database_context=None):
    database_context = database_context or {}
    db_disease_docs = database_context.get("diseases", [])
    db_medicine_docs = database_context.get("medicines", [])

    if not retrieved_docs and not db_disease_docs and not db_medicine_docs:
        return (
            "数据源中暂未检索到足够相关的信息。建议补充更具体的症状细节，"
            "例如主要不适、伴随症状、是否用药、特殊人群情况等。"
            "本系统仅提供健康信息参考，不能替代医生诊断或药师指导。"
        )

    disease_docs = [doc for doc in retrieved_docs if doc.get("doc_type") == "disease"]
    medicine_docs = [doc for doc in retrieved_docs if doc.get("doc_type") == "medicine"]
    warning_docs = [doc for doc in retrieved_docs if doc.get("doc_type") == "warning_rule"]

    answer = "根据你的描述，系统结合结构化数据库命中记录和语义 RAG 检索结果，得到以下参考信息：\n\n"

    if db_disease_docs:
        answer += "一、结构化数据库命中的常见病方向：\n"

        for item in db_disease_docs:
            raw = item.get("raw", {})
            answer += f"\n【{raw.get('name', item.get('title', ''))}】\n"
            answer += format_match_info(item)
            answer += f"常见症状：{'、'.join(normalize_symptoms(raw.get('symptoms', [])))}\n"
            answer += f"症状说明：{raw.get('description', '')}\n"
            answer += f"日常护理：{raw.get('care_advice', '')}\n"
            answer += f"用药注意：{raw.get('medicine_notice', '')}\n"
            answer += f"就医提醒：{raw.get('warning', '')}\n"

    if db_medicine_docs:
        answer += "\n二、结构化数据库命中的药品或用药注意：\n"

        for item in db_medicine_docs:
            raw = item.get("raw", {})
            answer += f"\n【{raw.get('name', item.get('title', ''))}】\n"
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
    rag_supplements = []
    seen_supplement_titles = set()
    for doc in warning_docs + disease_docs + medicine_docs:
        title = doc.get("title", "")
        if title in shown_titles or title in seen_supplement_titles:
            continue
        rag_supplements.append(doc)
        seen_supplement_titles.add(title)

    if rag_supplements:
        answer += "\n三、语义 RAG 知识库补充：\n"

        for doc in rag_supplements[:3]:
            raw = doc.get("raw", {})
            if doc.get("doc_type") == "warning_rule":
                answer += f"\n【危险症状规则：{raw.get('keyword', doc.get('title', ''))}】\n"
                answer += f"相似度：{float(doc.get('score', 0)):.4f}\n"
                answer += f"风险等级：{raw.get('risk_level', '')}\n"
                answer += f"处理建议：{raw.get('advice', '')}\n"
            elif doc.get("doc_type") == "disease":
                answer += f"\n【{raw.get('name', doc.get('title', ''))}】\n"
                answer += f"相似度：{float(doc.get('score', 0)):.4f}\n"
                answer += f"常见症状：{'、'.join(normalize_symptoms(raw.get('symptoms', [])))}\n"
                answer += f"护理建议：{raw.get('care_advice', '')}\n"
                answer += f"就医提醒：{raw.get('warning', '')}\n"
            else:
                answer += f"\n【{raw.get('name', doc.get('title', ''))}】\n"
                answer += f"相似度：{float(doc.get('score', 0)):.4f}\n"
                answer += f"适用情况：{raw.get('usage', '')}\n"
                answer += f"注意事项：{raw.get('notice', '')}\n"

    answer += "\n四、系统提示：\n"
    answer += (
        "本系统仅提供健康信息参考，不能替代医生诊断或药师指导。"
        "如症状持续加重，或出现高热不退、呼吸困难、胸痛、意识异常等情况，应及时线下就医。"
    )

    return answer


def load_eval_cases(eval_file=None):
    path = Path(eval_file) if eval_file else DEFAULT_EVAL_FILE
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    if not isinstance(cases, list):
        raise ValueError("RAG 评估文件必须是 JSON 数组。")

    return [case for case in cases if isinstance(case, dict) and case.get("query")]


def case_matches_result(case, result):
    expected_doc_ids = set(case.get("expected_doc_ids") or [])
    expected_titles = set(case.get("expected_titles") or [])
    expected_doc_types = set(case.get("expected_doc_types") or [])
    result_ids = {
        result.get("id"),
        result.get("parent_id"),
        (result.get("source") or {}).get("id"),
        (result.get("source") or {}).get("parent_id"),
    }

    if expected_doc_ids and any(item in expected_doc_ids for item in result_ids if item):
        return True

    if expected_titles and result.get("title") in expected_titles:
        return True

    if not expected_doc_ids and not expected_titles and expected_doc_types:
        return result.get("doc_type") in expected_doc_types

    return False


def case_answer_matches(case, answer):
    required_terms = [
        str(term).strip()
        for term in (case.get("expected_answer_terms") or [])
        if str(term).strip()
    ]
    any_terms = [
        str(term).strip()
        for term in (case.get("any_answer_terms") or [])
        if str(term).strip()
    ]

    if required_terms and not all(term in answer for term in required_terms):
        return False

    if any_terms and not any(term in answer for term in any_terms):
        return False

    if not required_terms and not any_terms:
        return True

    return True


def evaluate_retrieval(top_k=5, eval_file=None):
    top_k = max(1, int(top_k))
    cases = load_eval_cases(eval_file)

    if not cases:
        return {
            "case_count": 0,
            "top_k": top_k,
            "recall_at_k": 0,
            "mrr": 0,
            "message": f"未找到评估用例，请创建 {DEFAULT_EVAL_FILE}",
            "cases": [],
        }

    details = []
    hit_count = 0
    answer_hit_count = 0
    citation_hit_count = 0
    reciprocal_rank_sum = 0.0

    for case in cases:
        results = search_knowledge(case.get("query", ""), top_k=top_k, score_threshold=-1.0)
        rank = None

        for offset, result in enumerate(results, start=1):
            if case_matches_result(case, result):
                rank = offset
                break

        if rank is not None:
            hit_count += 1
            reciprocal_rank_sum += 1.0 / rank

        from database_context_service import search_database_context

        database_context = search_database_context(
            case.get("query", ""),
            disease_limit=3,
            medicine_limit=3,
        )
        answer_docs = filter_answer_docs(results, database_context, min_score=-1.0)
        answer = build_simple_answer(case.get("query", ""), answer_docs, database_context)
        citations = collect_citations(answer_docs, database_context)
        answer_hit = case_answer_matches(case, answer)
        citation_hit = bool(citations)

        if answer_hit:
            answer_hit_count += 1
        if citation_hit:
            citation_hit_count += 1

        details.append({
            "id": case.get("id", ""),
            "query": case.get("query", ""),
            "expected_titles": case.get("expected_titles", []),
            "expected_doc_ids": case.get("expected_doc_ids", []),
            "expected_answer_terms": case.get("expected_answer_terms", []),
            "hit": rank is not None,
            "rank": rank,
            "answer_hit": answer_hit,
            "citation_hit": citation_hit,
            "answer_preview": compact_text(answer, 220),
            "top_results": [
                {
                    "id": result.get("id"),
                    "parent_id": result.get("parent_id"),
                    "title": result.get("title"),
                    "doc_type": result.get("doc_type"),
                    "score": round(float(result.get("score", 0)), 4),
                    "embedding_score": round(float(result.get("embedding_score", 0)), 4),
                    "rerank_score": round(float(result.get("rerank_score", 0)), 4) if "rerank_score" in result else None,
                    "chunk_index": result.get("chunk_index"),
                    "chunk_count": result.get("chunk_count"),
                    "citation": result.get("citation", ""),
                }
                for result in results
            ],
        })

    case_count = len(cases)

    return {
        "case_count": case_count,
        "top_k": top_k,
        "recall_at_k": round(hit_count / case_count, 4),
        "mrr": round(reciprocal_rank_sum / case_count, 4),
        "answer_accuracy": round(answer_hit_count / case_count, 4),
        "citation_rate": round(citation_hit_count / case_count, 4),
        "backend": get_embedding_provider().backend,
        "model": get_embedding_provider().model_name,
        "rerank_enabled": RERANK_ENABLED,
        "rerank_backend": get_rerank_backend(),
        "rerank_model": get_rerank_model_name() if RERANK_ENABLED else "",
        "index": get_vector_store_status(),
        "cases": details,
    }
