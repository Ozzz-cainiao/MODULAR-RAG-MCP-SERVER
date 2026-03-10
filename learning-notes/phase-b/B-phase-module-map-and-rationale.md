# 项目学习笔记（阶段 B：模块地图与设计动机）

## 1) 阶段 B 的总目标

- 把“可替换”从口头要求变成代码事实。
- 为后续 Ingestion / Retrieval / MCP 提供稳定、可插拔的能力层。

---

## 2) 为什么有这些模块

### B1：LLM 抽象接口与工厂

- 解决“不同 LLM provider 切换”问题。
- 统一上层调用方式（`chat`），避免业务层写 provider 分支。

### B2：Embedding 抽象接口与工厂

- 解决“文本向量化后端可替换”问题。
- 统一 `embed(texts)` 输入输出契约。

### B3：Splitter 抽象接口与工厂

- 解决“分块策略可替换”问题（递归切分、语义切分等）。
- 让切分策略与业务编排解耦。

### B4：VectorStore 抽象接口与工厂

- 解决“向量存储后端可替换”问题（本地/云端）。
- 统一 `upsert/query` 契约，先定边界再接真实存储。

### B5：Reranker 抽象接口与工厂

- 解决“重排能力可选且可替换”问题。
- 提供 `NoneReranker` 回退，保证无重排时系统仍可用。

### B6：Evaluator 抽象接口与工厂

- 解决“评估体系可插拔”问题。
- 先做轻量评估接口，后续接 Ragas 等实现不影响主链路。

### B7.x：默认实现补齐（可运行实现）

- 解决“只有接口没有实现”的空转问题。
- 把核心链路需要的默认后端补齐到可运行状态：
  - B7.1/B7.2：LLM（OpenAI-Compatible + Ollama）
  - B7.3/B7.4：Embedding（OpenAI/Azure + Ollama）
  - B7.5：Recursive Splitter
  - B7.6：ChromaStore
  - B7.7/B7.8：Reranker（LLM / Cross-Encoder）

### B8：Vision LLM 抽象接口与工厂

- 解决“图像能力与文本能力差异过大”问题。
- 不把多模态能力硬塞进 `BaseLLM`，单独抽象 `BaseVisionLLM`。

### B9：Azure Vision LLM 实现

- 补一个可运行的 Vision 默认实现，打通多模态能力入口。

---

## 3) 阶段 B 在全链路中的位置

- 阶段 A：保证工程可运行、可测试、可配置。
- 阶段 B：保证“能力层可替换且可运行”。
- 阶段 C/D/E：在 B 的能力层上构建摄取、检索和 MCP 对外能力。

一句话：**B 阶段是整个项目的“可插拔能力底座”。**

---

## 4) 对外讲解的 30 秒版本

“B 阶段做了两件事：先用 Base+Factory 把 LLM、Embedding、Splitter、VectorStore、Reranker、Evaluator 抽象成可替换组件；再补齐默认实现（OpenAI/Ollama/Chroma/Recursive 等），确保不仅能切换，而且能实际跑通。多模态能力因为差异大，单独做了 Vision 抽象和 Azure Vision 实现。”

