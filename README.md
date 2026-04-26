# Modular RAG MCP Server

一个可插拔、可观测、可评估的模块化 RAG 工程，支持离线摄取、混合检索、MCP Tools、Dashboard 可视化和 golden set 回归评估。

## 快速开始

项目默认使用 `uv` 管理环境，并已配置清华 PyPI 镜像。

```bash
uv sync
```

### 使用 `.env` 配置环境变量

项目根目录支持自动加载 `.env`，不需要你每次手动 `export`。

先复制模板：

```bash
cp .env.example .env
```

然后编辑 `.env`：

```bash
OPENAI_API_KEY=你的真实key
```

之后直接运行：

```bash
uv run pytest
uv run mcp-server
uv run python scripts/query.py --query "Azure deployment guide"
```

测试和项目入口都会自动读取根目录 `.env`。

常见运行命令：

```bash
uv run pytest
uv run python scripts/ingest.py --collection demo --path tests/fixtures/sample_documents/simple.pdf
uv run python scripts/query.py --query "Azure deployment guide" --verbose
uv run python scripts/evaluate.py
uv run python scripts/start_dashboard.py
uv run mcp-server
```

## 配置说明

主配置文件是 `config/settings.yaml`，当前核心字段：

- `llm.provider`：LLM 后端
- `embedding.provider`：Embedding 后端
- `splitter.provider`：切分器后端
- `vector_store.provider`：向量库后端
- `retrieval.top_k`：默认召回条数
- `rerank.provider`：Reranker 后端
- `evaluation.provider`：Evaluator 后端
- `observability.level`：日志级别

常用环境变量：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_EMBEDDING_MODEL`
- `CHROMA_PERSIST_PATH`
- `BM25_PERSIST_PATH`
- `IMAGE_ROOT_DIR`
- `IMAGE_INDEX_DB_PATH`

## MCP 配置示例

GitHub Copilot / 其他 MCP Client 可将项目 server 配置为：

```json
{
  "servers": {
    "modular-rag": {
      "command": "uv",
      "args": ["run", "mcp-server"]
    }
  }
}
```

Claude Desktop 风格配置可写成：

```json
{
  "mcpServers": {
    "modular-rag": {
      "command": "uv",
      "args": ["run", "mcp-server"]
    }
  }
}
```

当前 MCP tools：

- `query_knowledge_hub`
- `list_collections`
- `get_document_summary`

## Dashboard 使用

启动命令：

```bash
uv run python scripts/start_dashboard.py
```

页面包括：

- `Overview`：当前系统配置概览
- `Data Browser`：浏览已摄取文档与 chunk
- `Ingestion Manager`：查看 ingestion 入口与文档总量
- `Ingestion Traces`：查看 ingestion trace
- `Query Traces`：查看 query trace
- `Evaluation Panel`：运行和查看评估

Dashboard 基于 `streamlit`，若本地尚未安装，脚本会给出提示。

## 评估体系

支持的评估组件：

- `CustomEvaluator`：提供 `hit_rate` 和 `mrr`
- `RagasEvaluator`：提供 `faithfulness`、`answer_relevancy`、`context_precision`
- `CompositeEvaluator`：组合多个 evaluator

golden test set 位于：

`tests/fixtures/golden_test_set.json`

运行评估：

```bash
uv run python scripts/evaluate.py --test-set tests/fixtures/golden_test_set.json
```

## 测试说明

全部测试：

```bash
uv run pytest
```

定向测试示例：

```bash
uv run pytest tests/unit -q
uv run pytest tests/integration -q
uv run pytest tests/e2e -q
```

需要真实 API Key 的集成测试在缺少环境变量时会自动跳过。

## 常见问题

### 1. `uv sync` 失败

优先确认当前 Python 版本满足项目要求 `>=3.11`，并确认网络可访问或镜像源配置正确。

### 2. 查询没有结果

先运行 ingestion：

```bash
uv run python scripts/ingest.py --collection demo --path tests/fixtures/sample_documents/simple.pdf
```

### 3. Dashboard 无法启动

需要先安装 `streamlit`。如果当前环境没有该依赖，`scripts/start_dashboard.py` 会直接提示。

### 4. MCP tool 调用失败

确认 `uv run mcp-server` 能正常启动，并检查 `stderr` 中的日志输出。

## 项目状态

当前开发排期已经全部完成：

- A：工程骨架
- B：可插拔抽象层
- C：Ingestion Pipeline
- D：Hybrid Retrieval
- E：MCP Server 与 Tools
- F：Trace / Observability 基础设施
- G：Dashboard 管理平台
- H：Evaluation 评估体系
- I：E2E 验收与文档收口

详细排期见 [DEV_SPEC.md](DEV_SPEC.md)。
