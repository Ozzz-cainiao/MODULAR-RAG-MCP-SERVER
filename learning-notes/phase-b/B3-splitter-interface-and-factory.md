# 项目学习笔记（B3：Splitter 抽象接口与工厂）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **B3：Splitter 抽象接口与工厂**：

- 新增 Splitter 抽象接口：`src/libs/splitter/base_splitter.py`
- 新增 Splitter 工厂：`src/libs/splitter/splitter_factory.py`
- 新增工厂路由单元测试：`tests/unit/test_splitter_factory.py`
- 补齐配置字段：`config/settings.yaml` 增加 `splitter.provider`
- 扩展配置模型：`src/core/settings.py` 增加 `settings.splitter` 及校验

---

## 2) 关键知识点

### 2.1 `split_text` 为什么带 `trace` 参数

- 与其他抽象层接口保持一致，预留 Trace 扩展点。
- 当前阶段可不使用 trace，后续接入追踪时无需改动接口签名。

### 2.2 SplitterFactory 的价值

- 根据 `settings.splitter.provider` 路由具体实现。
- 支持后续无代码切换策略（Recursive / Semantic / Fixed）。

### 2.3 配置驱动的前提

- 工厂路由要稳定，必须先有配置源。
- 因此本模块同步补齐了 `splitter.provider` 的配置和校验。

---

## 3) 测试与验证

- 测试文件：`tests/unit/test_splitter_factory.py`
- 覆盖点：
  - 已注册 provider 路由到对应 Fake Splitter
  - 不同 provider 返回不同 Splitter 行为
  - 未注册 provider 抛出可读错误

执行命令：

- `python -m pytest -q tests/unit/test_splitter_factory.py`

结果：

- `3 passed`

回归结果：

- `python -m pytest -q tests/unit/test_smoke_imports.py tests/unit/test_config_loading.py tests/unit/test_llm_factory.py tests/unit/test_embedding_factory.py tests/unit/test_splitter_factory.py`
- `10 passed`

---

## 4) 本模块常见问题

### Q1：为什么 B3 就要改 `settings`，不是只改 `splitter` 目录？

因为 B3 的目标是“工厂按配置分流”，
如果 `settings` 没有 `splitter.provider`，工厂就无法做到真正配置驱动。

