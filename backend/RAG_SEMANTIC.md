# RAG 语义检索说明

当前 RAG 链路已经升级为：

```text
规范化 MySQL 知识库（diseases / medicines / warning_rules）
-> 结构化父文档
-> 文档切片
-> BAAI/bge-small-zh-v1.5 embedding
-> FAISS 持久化索引
-> lexical rerank
-> 来源引用
-> 召回率 / MRR / 答案关键词准确率评估
```

## 模型

默认 embedding 模型：

```env
RAG_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

默认 rerank 模型：

```env
RAG_RERANK_MODEL=lexical
RAG_RERANK_ENABLED=true
```

`bge-small-zh-v1.5` 是轻量中文通用语义模型，适合先把本地常见病、症状和用药说明检索链路跑通。后续如果要换成更强的通用模型或本地医学专用 embedding，只需要把 `RAG_EMBEDDING_MODEL` 指向本地模型目录或 Hugging Face 模型名，然后重建索引。

## 文档切片

每条疾病、药品和危险症状规则记录先构造成父文档，再切成片段。切片会保留：

- `parent_id`
- `chunk_index`
- `chunk_count`
- `source.table`
- `source.record_id`
- `citation`

默认切片参数：

```env
RAG_CHUNK_MAX_CHARS=360
RAG_CHUNK_OVERLAP=80
```

## 索引持久化

索引目录：

```text
backend/data/rag_index/
```

持久化文件：

- `knowledge.faiss`
- `documents.json`
- `manifest.json`

`manifest.json` 会记录模型、切片参数、语料 fingerprint 和索引版本。知识库、模型或切片配置变化时，`/api/rag/init` 会自动重建。

## 来源引用

检索结果和最终回答会携带来源引用，例如：

```text
disease:12:chunk:1 | 疾病知识库 diseases#12 片段 1/2 | 普通感冒
```

这能定位到规范化 MySQL 表中的记录和具体切片。

## 评估

评估用例：

```text
backend/data/rag_eval_cases.json
```

命令：

```bash
python evaluate_rag.py --top-k 5
```

输出指标：

- `recall_at_k`
- `mrr`
- `answer_accuracy`
- `citation_rate`
- 每条 case 的 top results、rerank score、answer preview

`answer_accuracy` 使用本地模板答案做关键词核验，不调用大模型，不产生 API 成本。
