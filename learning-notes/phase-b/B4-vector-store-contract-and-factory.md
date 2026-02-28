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

### Q2：什么是契约测试？在什么情况下要执行？

契约测试（Contract Test）是用来验证“模块之间约定是否一致”的测试。

这里的“契约”通常包括：

- 输入参数的 shape（字段、类型、是否必填）
- 输出结果的 shape（必须包含哪些字段）
- 错误行为（异常类型、错误信息是否可读）

它不关注底层实现细节，而关注“调用方依赖的对外行为”是否稳定。

适合执行契约测试的场景：

1. 有抽象接口 + 多个 provider/后端实现时（防止各实现返回结构不一致）
2. 模块由不同人/不同团队并行开发时（提前对齐边界）
3. 要频繁替换后端（例如从 Fake 切到真实 DB/API）时
4. 需要保证向后兼容（避免改动接口导致上层崩溃）时

在本项目 B4 中，契约测试就是保证 `upsert/query` 的输入输出结构稳定，
这样后续接入真实 Vector Store 也不会破坏上层调用。

### Q3：为什么 Vector Store 要有基类和工厂？业务里哪些模块需要这样设计？

Vector Store 使用“基类 + 工厂”的核心原因：

1. **后端可替换**：同一业务可能接 Chroma、Qdrant、Milvus、PGVector。
2. **避免业务层耦合**：业务层只依赖 `BaseVectorStore`，不依赖具体 SDK。
3. **配置切换能力**：通过 `vector_store.provider` 实现“改配置切后端”。
4. **测试稳定**：可用 FakeVectorStore 做单测，不依赖真实数据库。

业务中“适合用基类 + 工厂”的模块通常有这些特征：

- 存在多家供应商/多种实现，且未来可能切换；
- 需要环境差异化（本地/测试/生产）切换实现；
- 外部依赖昂贵、慢或不稳定，需要 Fake/Mock 替身；
- 接口是系统稳定边界，需要长期演进且保持兼容。

典型模块：

- LLM / Embedding / Vector Store / Reranker / Evaluator / Cache / Object Storage / Message Queue。

不一定要用这套设计的模块：

- 纯内部算法函数、短期一次性脚本、几乎不可能替换实现的稳定单体组件。

经验法则：

- 如果“未来 6-12 个月换实现的概率高”，优先上“抽象 + 工厂”；
- 如果“实现唯一且稳定”，先保持简单，避免过度设计。
