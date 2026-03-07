# 项目学习笔记（B9：Azure Vision LLM 实现）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **B9：Azure Vision LLM 实现**：

- 新增 Azure Vision LLM：`src/libs/llm/azure_vision_llm.py`
- Vision LLM 工厂默认支持 `provider=azure`：`src/libs/llm/llm_factory.py`
- 新增单元测试：`tests/unit/test_azure_vision_llm.py`

---

## 2) 模块功能 / 流程位置 / 作用

### 2.1 模块功能

- 支持文本 + 图片输入的多模态对话。
- 支持图片路径或 base64 输入，并封装为 data URL。
- 提供图片压缩扩展点（max size 默认 2048px）。

### 2.2 在整体流程中的位置

- 位于 Vision LLM 插件层，供 ImageCaptioner 等多模态模块调用。
- 由 `LLMFactory.create_vision_llm` 按 `vision_llm.provider` 路由创建。
- 与文本 LLM 并行，服务不同链路。

### 2.3 模块作用

- 在本项目中承担“图片理解与描述”的核心能力。
- 将 Azure Vision API 封装为统一接口，降低上层耦合。
- 通过清晰错误与结构化输出保证稳定集成。

---

## 3) 关键设计点

- **输入兼容**：支持图片路径或 base64 字符串输入。
- **错误可读性**：Azure 返回 error 时抛出包含 code 的错误。
- **压缩扩展点**：若可用 Pillow，则按 max size 缩放；否则保持原图。

---

## 4) 测试与验证

- 测试文件：`tests/unit/test_azure_vision_llm.py`
- 覆盖点：
  - 工厂路由 Azure Vision LLM
  - 图片路径 / base64 输入可用
  - Azure error payload 可读报错
  - 压缩 hook 可触发
  - 传输异常时抛出包含 provider 的错误

执行命令：

- `python -m pytest -q -p no:cacheprovider tests/unit/test_azure_vision_llm.py tests/unit/test_vision_llm_factory.py`
- `python -m pytest -q -p no:cacheprovider tests/unit/test_smoke_imports.py tests/unit/test_config_loading.py tests/unit/test_llm_factory.py tests/unit/test_vision_llm_factory.py tests/unit/test_azure_vision_llm.py tests/unit/test_llm_providers_smoke.py tests/unit/test_ollama_llm.py tests/unit/test_embedding_factory.py tests/unit/test_embedding_providers_smoke.py tests/unit/test_ollama_embedding.py tests/unit/test_splitter_factory.py tests/unit/test_recursive_splitter_lib.py tests/unit/test_vector_store_contract.py tests/integration/test_chroma_store_roundtrip.py tests/unit/test_reranker_factory.py tests/unit/test_llm_reranker.py tests/unit/test_cross_encoder_reranker.py tests/unit/test_custom_evaluator.py`

结果：

- B9 定向：`9 passed`
- 当前回归集合：`78 passed`

---

## 5) 本模块常见问题

### Q1：为什么要把图片转换成 data URL？

Azure Vision Chat 接口要求 `image_url` 字段。
data URL 是无需上传外部图片即可传递图像内容的通用方式。

### Q2：为什么压缩逻辑是“可选依赖”？

项目当前依赖尽量保持轻量。
如果后续引入 Pillow，可自动启用真实压缩；没有依赖时仍可运行。

