# 项目学习笔记（B1：LLM 抽象接口与工厂）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **B1：LLM 抽象接口与工厂**：

- 新增 LLM 抽象接口：`src/libs/llm/base_llm.py`
- 新增 LLM 工厂：`src/libs/llm/llm_factory.py`
- 新增工厂路由单元测试：`tests/unit/test_llm_factory.py`

---

## 2) 关键知识点

### 2.1 为什么先做抽象接口

- `BaseLLM` 统一了 `chat(messages) -> str` 契约。
- 后续接 OpenAI、Azure、Ollama 等 provider 时，调用层不需要改。

### 2.2 工厂模式在这里解决什么问题

- `LLMFactory` 根据 `settings.llm.provider` 选择实现。
- 业务代码只关心 `BaseLLM`，不关心具体 provider。
- 便于做 provider 切换与测试替身（Fake provider）。

### 2.3 注册机制

- 通过 `LLMFactory.register(provider, builder)` 注册 provider。
- 通过 `LLMFactory.create(settings)` 构建实例。
- 未注册 provider 时抛出可读错误，快速定位配置问题。

---

## 3) 测试与验证

- 测试文件：`tests/unit/test_llm_factory.py`
- 覆盖点：
  - 已注册 provider 可以正确路由到 Fake LLM
  - 未注册 provider 抛出包含 provider 名称的错误

执行命令：

- `python -m pytest -q tests/unit/test_llm_factory.py`

结果：

- `2 passed`

---

## 4) 本模块常见问题

### Q1：为什么测试里要用 Fake provider？

因为 B1 的目标是验证“工厂路由逻辑”，不是验证真实模型调用。
使用 Fake provider 可以让测试稳定、快速、无外部依赖。

