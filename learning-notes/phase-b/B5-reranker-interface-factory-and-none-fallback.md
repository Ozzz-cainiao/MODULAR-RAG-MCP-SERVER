# 项目学习笔记（B5：Reranker 抽象接口与工厂）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **B5：Reranker 抽象接口与工厂（含 None 回退）**：

- 新增 Reranker 抽象接口：`src/libs/reranker/base_reranker.py`
- 新增 Reranker 工厂及 `NoneReranker` 回退实现：`src/libs/reranker/reranker_factory.py`
- 新增工厂路由单元测试：`tests/unit/test_reranker_factory.py`

---

## 2) 关键知识点

### 2.1 为什么要有 `NoneReranker`

- 在某些场景不希望增加重排成本（时延/费用）时，可以显式关闭 rerank。
- `NoneReranker` 保证“关闭重排”时行为可预测：保持原候选顺序。

### 2.2 RerankerFactory 的作用

- 根据 `settings.rerank.provider` 路由具体实现。
- 内置 `none` provider，保证默认可回退。

### 2.3 错误行为设计

- 未知 provider 必须明确报错，而不是静默降级。
- 这样可以尽快暴露配置问题，避免线上结果不可控。

---

## 3) 测试与验证

- 测试文件：`tests/unit/test_reranker_factory.py`
- 覆盖点：
  - backend=`none` 时不改变候选顺序
  - 已注册自定义 provider 能正确路由
  - 未知 provider 抛出可读错误

执行命令：

- `python -m pytest -q tests/unit/test_reranker_factory.py`

结果：

- `3 passed`

回归结果：

- `python -m pytest -q tests/unit/test_smoke_imports.py tests/unit/test_config_loading.py tests/unit/test_llm_factory.py tests/unit/test_embedding_factory.py tests/unit/test_splitter_factory.py tests/unit/test_vector_store_contract.py tests/unit/test_reranker_factory.py`
- `16 passed`

---

## 4) 本模块常见问题

### Q1：为什么 unknown provider 不直接回退到 none？

因为“静默回退”会掩盖配置错误，导致结果偏差不易发现。
明确报错更符合 fail-fast 原则，也更有利于线上排障。

