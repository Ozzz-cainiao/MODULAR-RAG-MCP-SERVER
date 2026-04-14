# 项目学习笔记（C6：MetadataEnricher）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **C6：MetadataEnricher** 的主要实现：

- 新增元数据增强器：`src/ingestion/transform/metadata_enricher.py`
- 新增 prompt：`config/prompts/metadata_enricher.txt`
- 扩展配置：`config/settings.yaml` + `src/core/settings.py`
- 新增测试：`tests/unit/test_metadata_enricher_contract.py`
- 新增集成测试：`tests/integration/test_metadata_enricher_llm.py`
- 更新进度：`DEV_SPEC.md` 与自动拆分规格文件

说明：LLM 集成测试依赖 `OPENAI_API_KEY`，未配置时会自动跳过。

---

## 2) 模块功能 / 流程位置 / 作用

### 2.1 模块功能

- 规则模式生成 `title/summary/tags` 作为兜底。
- 可选 LLM 模式：输出更丰富的语义元数据。
- 失败降级：LLM 失败时回退规则结果，不阻塞 ingestion。

### 2.2 在整体流程中的位置

- 位于 Transform 阶段，在 ChunkRefiner 之后/Embedding 之前使用最合理。

### 2.3 模块作用

- 统一补充结构化 metadata，支撑后续检索过滤与展示。
- 可控地引入 LLM 增强，提高标题与摘要质量。

---

## 3) 关键设计点

- **规则兜底**：保证任何情况下 metadata 完整。
- **LLM 可插拔**：由 `ingestion.metadata_enricher.use_llm` 控制。
- **结构化输出**：要求 LLM 返回 JSON，解析失败则降级。

---

## 4) 测试与验证

- 单元测试：`tests/unit/test_metadata_enricher_contract.py`
- 集成测试：`tests/integration/test_metadata_enricher_llm.py`

执行命令：

- `.\.venv\Scripts\pytest.exe -q tests\unit\test_metadata_enricher_contract.py`
- `.\.venv\Scripts\pytest.exe -q tests\integration\test_metadata_enricher_llm.py`

---

## 5) 本模块常见问题

### Q1：为什么 LLM 失败不直接中断？

保证 ingestion 主链路稳定，失败时回退规则结果。

### Q2：为什么要求 JSON 输出？

结构化结果便于校验与落库，降低后续解析成本。
