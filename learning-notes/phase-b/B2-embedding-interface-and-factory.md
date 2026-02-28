# 项目学习笔记（B2：Embedding 抽象接口与工厂）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **B2：Embedding 抽象接口与工厂**：

- 新增 Embedding 抽象接口：`src/libs/embedding/base_embedding.py`
- 新增 Embedding 工厂：`src/libs/embedding/embedding_factory.py`
- 新增工厂路由单元测试：`tests/unit/test_embedding_factory.py`

---

## 2) 关键知识点

### 2.1 为什么抽象接口要带 `trace` 参数

- `embed(texts, trace=None)` 预留 Trace 扩展点。
- 当前阶段可不使用 trace，但后续接入链路追踪时无需改接口。

### 2.2 EmbeddingFactory 的职责

- 根据 `settings.embedding.provider` 路由到已注册实现。
- 业务层只依赖 `BaseEmbedding`，降低 provider 耦合。

### 2.3 Fake provider 测试策略

- 用 Fake Embedding 验证“工厂分流”而不是验证真实模型。
- 测试更稳定，不受外部网络和模型服务波动影响。

---

## 3) 测试与验证

- 测试文件：`tests/unit/test_embedding_factory.py`
- 覆盖点：
  - 已注册 provider 返回对应 Fake Embedding 实现
  - 未注册 provider 抛出包含 provider 名称的可读错误

执行命令：

- `python -m pytest -q tests/unit/test_embedding_factory.py`

结果：

- `2 passed`

---

## 4) 本模块常见问题

### Q1：为什么 B2 还不直接接真实 Embedding API？

因为 B2 的目标是先把抽象层和工厂路由打牢，
真实 provider 实现在后续子任务（如 B7.3、B7.4）再接入。

