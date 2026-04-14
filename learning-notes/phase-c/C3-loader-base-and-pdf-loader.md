# 项目学习笔记（C3：Loader 抽象基类与 PDF Loader）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **C3：Loader 抽象基类与 PDF Loader**：

- 新增 Loader 抽象基类：`src/libs/loader/base_loader.py`
- 新增 PDF Loader 默认实现：`src/libs/loader/pdf_loader.py`
- 更新 Loader 导出：`src/libs/loader/__init__.py`
- 新增契约测试：`tests/unit/test_loader_pdf_contract.py`
- 新增 PDF fixture：`tests/fixtures/sample_documents/simple.pdf`、`tests/fixtures/sample_documents/with_images.pdf`
- 更新进度：`DEV_SPEC.md` 与自动拆分规格文件

---

## 2) 模块功能 / 流程位置 / 作用

### 2.1 模块功能

- 提供 `BaseLoader` 抽象接口，统一约束 `load(path) -> Document`。
- 提供 `PdfLoader` 默认实现，负责把 PDF 文件转成 `Document`。
- 生成标准化 metadata，至少包含：
  - `source_path`
  - `doc_type=pdf`
  - `title`
  - `images`
- 支持图片占位符注入：在 `Document.text` 中插入 `[IMAGE: {image_id}]`。
- 支持图片提取降级：图片处理失败时不阻塞文本解析。

### 2.2 在整体流程中的位置

- 位于 Ingestion Pipeline 的最前面，是“原始文件 -> 标准 Document”的入口层。
- 上游对接文件系统与后续的完整性检查结果。
- 下游直接服务于 C4 的 `DocumentChunker`，为切分器提供统一输入。

### 2.3 模块作用

- 把 PDF 解析逻辑收口到 Loader 层，避免后续 Chunking/Transform/Embedding 混入格式解析细节。
- 提前把图片占位与图片 metadata 契约固定下来，减少后续多模态链路返工。
- 通过可注入的 `text_converter` / `image_extractor`，为未来接入 MarkItDown 或更强 PDF 引擎保留扩展点。

---

## 3) 关键设计点

- **接口先行**：先定义 `BaseLoader`，保证后续不止 PDF 一种 Loader 时仍能统一工厂与调用方式。
- **可插拔实现**：`PdfLoader` 不把具体 PDF 三方库写死，而是允许注入文本转换器与图片提取器。
- **默认可运行**：若环境里存在 `markitdown`，优先使用；否则退回内置的最小 PDF 文本提取逻辑。
- **契约优先**：图片 metadata 直接对齐 C1 的 `metadata.images` 结构，避免后续类型漂移。
- **失败隔离**：图片提取异常被内部吞掉并降级为空列表，主流程仍返回可用的 `Document`。

---

## 4) 测试与验证

- 测试文件：`tests/unit/test_loader_pdf_contract.py`
- 覆盖点：
  - 纯文本 PDF 能生成 `Document`
  - metadata 含 `source_path/doc_type/images`
  - 带图片 PDF 会插入 `[IMAGE: image_id]`
  - 图片提取失败时自动降级

执行命令：

- `.\.venv\Scripts\pytest.exe -q tests\unit\test_loader_pdf_contract.py`

结果：

- `3 passed`

---

## 5) 本模块常见问题

### Q1：为什么 `PdfLoader` 没有直接强绑定某个 PDF 解析库？

因为当前阶段先完成 C3 的接口与契约落地，比起绑定具体库，更重要的是把 `Document` 输出格式和图片处理边界稳定下来。
这样后续无论换成 MarkItDown、PyMuPDF 还是别的实现，都不需要改上层业务代码。

### Q2：为什么图片提取失败时不直接报错？

DEV_SPEC 明确要求“图片提取失败不应阻塞文本解析”。
因此这里采用“文本优先可用、图片能力降级”的策略，先保证 Ingestion 主链路可继续推进。
