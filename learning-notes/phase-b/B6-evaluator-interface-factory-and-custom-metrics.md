# 项目学习笔记（B6：Evaluator 抽象接口与工厂）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **B6：Evaluator 抽象接口与工厂（先做自定义轻量指标）**：

- 新增 Evaluator 抽象接口：`src/libs/evaluator/base_evaluator.py`
- 新增自定义轻量评估器：`src/libs/evaluator/custom_evaluator.py`
- 新增 Evaluator 工厂并内置 `custom` 路由：`src/libs/evaluator/evaluator_factory.py`
- 新增单元测试：`tests/unit/test_custom_evaluator.py`

---

## 2) 关键知识点

### 2.1 Evaluator 在 RAG 链路中的作用

- Evaluator 用来衡量“检索结果质量”，不是直接参与召回。
- 本模块先关注检索指标，输入是 `query + retrieved_ids + golden_ids`。
- 指标稳定可复现后，后续才能做回归对比和质量基线。

### 2.2 为什么先做轻量 `CustomEvaluator`

- 先建立最小可用评估闭环，降低初期复杂度。
- `hit_rate` 与 `mrr` 都是检索阶段常见、可解释且成本低的指标。
- 通过工厂注册机制，后续可平滑扩展到更多 Evaluator provider。

### 2.3 工厂与配置驱动

- `EvaluatorFactory.create(settings)` 根据 `settings.evaluation.provider` 路由实现。
- 当前默认内置 `custom` provider，开箱可用。
- 未知 provider 明确报错，遵循 fail-fast 原则。

---

## 3) 测试与验证

- 测试文件：`tests/unit/test_custom_evaluator.py`
- 覆盖点：
  - 命中场景：`hit_rate=1.0`、`mrr=0.5`
  - 未命中场景：`hit_rate=0.0`、`mrr=0.0`
  - `EvaluatorFactory` 对 `custom` 路由正确
  - 未知 provider 抛出可读错误

执行命令：

- `python -m pytest -q -p no:cacheprovider tests/unit/test_custom_evaluator.py`
- `python -m pytest -q -p no:cacheprovider tests/unit/test_smoke_imports.py tests/unit/test_config_loading.py tests/unit/test_llm_factory.py tests/unit/test_embedding_factory.py tests/unit/test_splitter_factory.py tests/unit/test_vector_store_contract.py tests/unit/test_reranker_factory.py tests/unit/test_custom_evaluator.py`

结果：

- B6 定向：`4 passed`
- 当前回归集合：`20 passed`

---

## 4) 本模块常见问题

### Q1：`hit_rate` 和 `mrr` 有什么区别？

- `hit_rate` 只关心“是否命中”，不关心命中位置。
- `mrr` 关心“第一个命中的排名”，越靠前分数越高。
- 两者一起看，可以同时衡量“能不能找到”和“找得靠不靠前”。

### Q2：为什么 Evaluator 也要做成“基类 + 工厂”？

因为评估策略会变化（规则指标、LLM 评估器、第三方评测框架），提前统一接口可以：

- 降低后续替换成本；
- 保持调用方稳定；
- 通过配置切换 provider，而不改业务主流程。

