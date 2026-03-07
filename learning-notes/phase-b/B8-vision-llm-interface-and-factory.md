# 项目学习笔记（B8：Vision LLM 抽象接口与工厂集成）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **B8：Vision LLM 抽象接口与工厂集成**：

- 新增 Vision LLM 抽象接口：`src/libs/llm/base_vision_llm.py`
- 扩展 `LLMFactory` 支持 Vision LLM 路由：`src/libs/llm/llm_factory.py`
- 新增单元测试：`tests/unit/test_vision_llm_factory.py`

---

## 2) 模块功能 / 流程位置 / 作用

### 2.1 模块功能

- 定义多模态接口 `chat_with_image(text, image_input, trace)`。
- 统一 Vision LLM 的调用形态，支持图片路径或 bytes 输入。
- 为后续 Vision LLM provider 提供标准化接入点。

### 2.2 在整体流程中的位置

- 属于 LLM 插件层的扩展分支（Vision LLM 子类）。
- 主要供 C7 的 ImageCaptioner 或多模态链路调用。
- 通过 `LLMFactory.create_vision_llm` 统一创建实例。

### 2.3 模块作用

- 将多模态能力纳入统一工厂体系，降低接入成本。
- 预留图片预处理扩展点（压缩、格式转换）。
- 保证上层业务逻辑不耦合具体 Vision provider。

---

## 3) 测试与验证

- 测试文件：`tests/unit/test_vision_llm_factory.py`
- 覆盖点：
  - Vision provider 注册与工厂路由正确
  - 未注册 provider 抛出可读错误

执行命令：

- `python -m pytest -q -p no:cacheprovider tests/unit/test_vision_llm_factory.py tests/unit/test_llm_factory.py`
- `python -m pytest -q -p no:cacheprovider tests/unit/test_smoke_imports.py tests/unit/test_config_loading.py tests/unit/test_llm_factory.py tests/unit/test_vision_llm_factory.py tests/unit/test_llm_providers_smoke.py tests/unit/test_ollama_llm.py tests/unit/test_embedding_factory.py tests/unit/test_embedding_providers_smoke.py tests/unit/test_ollama_embedding.py tests/unit/test_splitter_factory.py tests/unit/test_recursive_splitter_lib.py tests/unit/test_vector_store_contract.py tests/integration/test_chroma_store_roundtrip.py tests/unit/test_reranker_factory.py tests/unit/test_llm_reranker.py tests/unit/test_cross_encoder_reranker.py tests/unit/test_custom_evaluator.py`

结果：

- B8 定向：`4 passed`
- 当前回归集合：`71 passed`

---

## 4) 本模块常见问题

### Q1：为什么 Vision LLM 不直接复用 BaseLLM？

Vision LLM 输入包含图片，接口签名与文本 LLM 不同。
独立抽象可以更清晰地表达多模态输入，同时避免影响现有文本链路。

### Q2：为什么要在工厂里单独新增 create_vision_llm？

为了保持与文本 LLM 的职责分离。
不同的 provider、鉴权和输入格式差异，最好在独立分支处理。

