# 项目学习笔记（C4：Splitter 集成 / DocumentChunker）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **C4：Splitter 集成（调用 Libs）**：

- 新增 Document→Chunk 适配器：`src/ingestion/chunking/document_chunker.py`
- 更新 chunking 导出：`src/ingestion/chunking/__init__.py`
- 新增单元测试：`tests/unit/test_document_chunker.py`
- 更新进度：`DEV_SPEC.md` 与自动拆分规格文件

---

## 2) 模块功能 / 流程位置 / 作用

### 2.1 模块功能

- 通过 `SplitterFactory` 获取配置驱动的 splitter。
- 将 `List[str]` 转换为 `List[Chunk]`，满足 `core.types.Chunk` 契约。
- 生成稳定的 `chunk_id`，格式为 `{doc_id}_{index:04d}_{hash_8}`。
- 继承 `Document.metadata`，并追加 `chunk_index`。
- 将 `source_ref` 指向父 `Document.id`，便于溯源。

### 2.2 在整体流程中的位置

- 位于 Ingestion Pipeline 的切分层，是 Loader 与 Transform 的桥梁。
- 上游接收标准 `Document`，下游输出结构化 `Chunk`。

### 2.3 模块作用

- 把“纯文本切分”与“业务对象转换”分离，保持 libs 层的纯净性。
- 统一 chunk ID 与元数据继承策略，减少后续检索与存储不一致风险。

---

## 3) 关键设计点

- **适配器职责清晰**：libs.splitter 只处理文本，DocumentChunker 负责业务对象组装。
- **ID 确定性**：chunk_id 由 doc_id + index + 文本哈希生成，稳定可复现。
- **元数据继承**：保留 Document 元数据，附加 `chunk_index`，便于排序与过滤。
- **溯源链接**：source_ref 指向 Document.id，支持后续引用追踪。

---

## 4) 测试与验证

- 测试文件：`tests/unit/test_document_chunker.py`
- 覆盖点：
  - 文本列表转 Chunk
  - 元数据继承 + chunk_index
  - source_ref 溯源
  - Chunk ID 稳定且唯一

执行命令：

- `.\.venv\Scripts\pytest.exe -q tests\unit\test_document_chunker.py`

---

## 5) 本模块常见问题

### Q1：为什么不用 libs.splitter 直接输出 Chunk？

libs 层设计为纯文本工具，不承载业务对象与元数据处理。DocumentChunker 作为适配器让职责边界清晰，后续扩展更稳。

### Q2：chunk_id 的 hash 为什么基于文本？

同一文档的同一切分结果应得到相同 ID。文本哈希能保证确定性，且对内容变更敏感。
