# 项目学习笔记（B4：VectorStore 抽象接口与工厂）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **B4：VectorStore 抽象接口与工厂**：

- 新增 Vector Store 抽象契约：`src/libs/vector_store/base_vector_store.py`
- 新增 Vector Store 工厂：`src/libs/vector_store/vector_store_factory.py`
- 新增契约测试：`tests/unit/test_vector_store_contract.py`

---

## 2) 关键知识点

### 2.1 为什么 B4 强调“先定义契约”

- 先明确 `upsert/query` 输入输出 shape，后续接真实数据库不容易跑偏。
- 业务层先依赖抽象，后端实现（Chroma 等）可以后续替换接入。

### 2.2 `BaseVectorStore` 的核心接口

- `upsert(records, trace=None)`：写入或更新向量记录。
- `query(vector, top_k, filters, trace=None)`：按向量检索结果。

其中 `query` 返回结果约定至少包含：

- `chunk_id`
- `score`
- `text`
- `metadata`

### 2.3 Contract Test 的意义

- 不是测数据库性能，而是测“输入输出约束是否一致”。
- 防止后续不同 provider 返回 shape 不一致，导致上层崩溃。

---

## 3) 测试与验证

- 测试文件：`tests/unit/test_vector_store_contract.py`
- 覆盖点：
  - `upsert/query` 的 shape 契约
  - 缺少必填键时抛出可读错误
  - 工厂对未注册 provider 抛出可读错误

执行命令：

- `python -m pytest -q tests/unit/test_vector_store_contract.py`

结果：

- `3 passed`

回归结果：

- `python -m pytest -q tests/unit/test_smoke_imports.py tests/unit/test_config_loading.py tests/unit/test_llm_factory.py tests/unit/test_embedding_factory.py tests/unit/test_splitter_factory.py tests/unit/test_vector_store_contract.py`
- `13 passed`

---

## 4) 本模块常见问题

### Q1：为什么契约测试里用 FakeVectorStore，不直接连真实数据库？

因为 B4 的目标是“契约正确”，不是“后端能力完整”。
先用 Fake 保证稳定性和可复现性，后续 B7.6 再接真实 Chroma 实现。

