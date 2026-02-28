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

### Q2：Splitter 基类和工厂的设计原则是什么，为什么这样设计？

核心遵循这几条：

1. **面向抽象编程（依赖倒置）**
   - 上层只依赖 `BaseSplitter`，不依赖具体实现。
   - 这样后续替换 `Recursive/Semantic/Fixed` 时，上层调用代码不变。

2. **开闭原则（对扩展开放，对修改关闭）**
   - 新增一种切分策略时，只需新增实现类并 `register` 到工厂。
   - 不需要改业务调用方逻辑。

3. **配置驱动（无代码切换）**
   - 通过 `settings.splitter.provider` 决定实例化哪种 Splitter。
   - 便于环境切换、A/B 测试与快速回退。

4. **可测试性优先**
   - 工厂路由可以用 Fake Splitter 进行稳定测试。
   - 避免在本阶段引入真实外部依赖导致测试不稳定。

5. **接口前向兼容**
   - `split_text(text, trace=None)` 预留 trace 参数，便于后续接入追踪体系。
   - 当前先不强依赖 trace，降低实现复杂度。

### Q3：`provider` 是什么？为什么要这样设计？

`provider` 可以理解为“后端实现的名字”或“实现类型标识”。

例如：

- `llm.provider = openai / azure / ollama`
- `embedding.provider = openai / azure / ollama`
- `splitter.provider = recursive / semantic / fixed`

工厂会根据这个字符串去选择具体实现类。

这样设计的核心收益：

1. **解耦**：业务层不直接依赖具体实现，只依赖抽象接口。
2. **可切换**：改配置就能切后端，不用改业务代码。
3. **可扩展**：新增后端只需新增实现并注册到工厂。
4. **可测试**：测试可使用 Fake provider，避免真实外部依赖。
5. **便于运维**：可按环境/成本/性能快速切换策略。

代价与注意点：

- `provider` 写错会触发“未注册 provider”错误；
- 需要维护好“配置值 ↔ 注册实现”的映射关系。

### Q4：有适配器基类，还会有适配器派生类吗？

会，而且这是这套设计的核心。

- 基类（如 `BaseLLM`、`BaseEmbedding`、`BaseSplitter`）只定义统一接口契约；
- 派生类负责接入具体后端或具体策略；
- Factory 按 `provider` 返回对应派生类实例。

当前阶段主要先把“基类 + Factory”打好，
具体派生类在后续任务逐步补齐（例如 LLM/Embedding 的各 provider、Splitter 的 Recursive 等默认实现）。

### Q5：这种架构设计模式叫什么？新项目怎么让大模型按这个模式设计？

这套设计通常是几种模式的组合：

- **Strategy Pattern（策略模式）**：不同 provider/策略实现同一接口，可互换。
- **Factory Method / Simple Factory（工厂模式）**：按配置创建具体实现实例。
- **Dependency Inversion（依赖倒置）**：上层依赖抽象接口，不依赖具体实现。
- **Plugin-like Architecture（插件化架构）**：通过注册机制扩展新实现。

如果在新项目里希望大模型按这套方式设计，建议明确写出：

1. 先定义抽象基类（接口契约）；
2. 再定义工厂（按 `provider` 路由）；
3. 配置文件驱动选择实现（改配置不改业务代码）；
4. 允许注册新 provider（开闭原则）；
5. 用 Fake provider 写单元测试验证路由；
6. 明确非目标：本阶段不接真实外部 API。

可直接给大模型的指令模板：

```text
请为我的新项目设计“抽象接口 + 工厂路由 + 配置驱动”的可插拔架构：

要求：
1) 先定义 Base 接口（例如 BaseXxx），只包含统一方法签名。
2) 定义 XxxFactory：根据 settings.<module>.provider 返回具体实现。
3) 工厂支持 register(provider, builder) 扩展机制。
4) 业务层只能依赖 Base 接口，不能直接依赖具体实现类。
5) 配置文件提供 provider 字段，实现“改配置切后端”。
6) 先写 Fake provider 单测验证工厂分流，再做真实 provider。
7) 输出文件清单、关键类关系、最小可运行测试命令。
```
