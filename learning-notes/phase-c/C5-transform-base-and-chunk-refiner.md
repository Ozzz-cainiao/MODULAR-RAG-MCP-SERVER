# 项目学习笔记（C5：Transform 基类 + ChunkRefiner）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **C5：Transform 基类 + ChunkRefiner** 的主要实现：

- 新增 Transform 抽象基类：`src/ingestion/transform/base_transform.py`
- 新增 ChunkRefiner 实现：`src/ingestion/transform/chunk_refiner.py`
- 新增 TraceContext 最小实现：`src/core/trace/trace_context.py`
- 更新 Transform 导出：`src/ingestion/transform/__init__.py`
- 更新配置：`config/settings.yaml` + `config/prompts/chunk_refinement.txt`
- 新增 fixtures：`tests/fixtures/noisy_chunks.json`
- 新增测试：`tests/unit/test_chunk_refiner.py`、`tests/integration/test_chunk_refiner_llm.py`
- 更新进度：`DEV_SPEC.md` 与自动拆分规格文件

说明：LLM 集成测试依赖 `OPENAI_API_KEY`，当前环境未配置时会自动跳过。

---

## 2) 模块功能 / 流程位置 / 作用

### 2.1 模块功能

- 提供 `BaseTransform.transform()` 抽象接口。
- `ChunkRefiner` 先做规则去噪，再按配置可选调用 LLM 精炼。
- 失败降级：LLM 失败时回退到规则结果，不阻塞 ingestion。
- metadata 标注：`refined_by` + `refine_fallback_reason`。

### 2.2 在整体流程中的位置

- 位于 Ingestion Pipeline 的 Transform 阶段。
- 上游是 DocumentChunker，下游是 Embedding / Storage。

### 2.3 模块作用

- 统一清洗策略，降低噪声，提高检索质量。
- 通过可选 LLM 增强提升语义完整性。

---

## 3) 关键设计点

- **规则优先**：规则清洗作为稳定兜底。
- **LLM 可插拔**：由 `ingestion.chunk_refiner.use_llm` 控制开关。
- **异常隔离**：单个 chunk 失败不影响整体处理。
- **Prompt 显式占位**：`chunk_refinement.txt` 强制使用 `{text}`。

---

## 4) 测试与验证

- 单元测试：`tests/unit/test_chunk_refiner.py`
- 集成测试：`tests/integration/test_chunk_refiner_llm.py`（需要 `OPENAI_API_KEY`）

执行命令：

- `.\.venv\Scripts\pytest.exe -q tests\unit\test_chunk_refiner.py`
- `.\.venv\Scripts\pytest.exe -q tests\integration\test_chunk_refiner_llm.py`

---

## 5) 本模块常见问题

### Q1：为什么 LLM 失败不直接中断？

DEV_SPEC 要求“失败降级不阻塞 ingestion”，因此默认回退到规则清洗结果。

### Q2：为什么要在 Prompt 中强制 `{text}` 占位？

避免模板缺失导致的空输入或误用，保证 LLM 接收到完整 chunk。
