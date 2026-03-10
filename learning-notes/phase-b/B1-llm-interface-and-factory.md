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

### Q2：抽象与工厂在运行时到底怎么工作？

可以按 4 步理解：

1. 业务层只调用统一接口（例如 `llm.chat(messages)`），不写 provider 分支。
2. 启动时读取配置（如 `settings.llm.provider = "openai"`）。
3. `LLMFactory.create(settings)` 根据 provider 从注册表取到对应实现类并实例化。
4. 返回对象类型虽然不同（OpenAI/Azure/Ollama），但都实现了 `BaseLLM.chat`，所以上层调用代码保持不变。

一句话：**抽象定义“怎么调用”，工厂决定“调用谁”。**

### Q3：不同模型能力不一样，怎么处理？是不是所有方法都得一模一样？

不是“能力完全一样”，而是“**对外暴露的最小公共接口一致**”。

在当前项目里：

- `BaseLLM` 只要求 `chat(messages) -> str`（公共能力）；
- 各 provider 内部实现细节不同（URL、认证、payload、响应解析）：
  - OpenAI: `src/libs/llm/openai_llm.py`
  - Azure: `src/libs/llm/azure_llm.py`
  - Ollama: `src/libs/llm/ollama_llm.py`
- 当能力明显不同（如图像输入）时，不强塞进 `BaseLLM`，而是单独抽象为 `BaseVisionLLM`：
  - `src/libs/llm/base_vision_llm.py`

结论：

- 公共能力走同一抽象接口；
- 专有能力走“单独接口/单独工厂”；
- 避免把所有 provider 的特性硬塞到一个臃肿基类里。

### Q4：工厂实例化对象与 `OpenAILLM` 的关系是什么？

- `OpenAILLM` 是 `BaseLLM` 的派生类（具体实现）。
- `LLMFactory` 里的 `_registry` 是 provider 到实现类的映射表：
  - 例如 `"openai" -> OpenAILLM`。
- 当配置是 `llm.provider=openai` 时，`LLMFactory.create(settings)` 会从映射表取出 `OpenAILLM` 并实例化。

一句话：**工厂不实现模型能力，只负责按配置选择并创建具体实现类。**

### Q5：`_registry` 是不是就是“映射实现”的地方？

是的。`_registry` 本质是“provider 路由表”：

- key：配置里的 provider 名称；
- value：对应实现类（或构建器）。

`create()` 只是做：读取 provider -> 查路由表 -> 实例化返回（查不到就报错）。

## 5) 工厂执行 5 步（速记版）

当业务调用 `LLMFactory.create(settings)` 时，运行顺序是：

1. **读取配置**：获取 `settings.llm.provider`。
2. **标准化 provider**：执行 `strip().lower()`，消除大小写和空格干扰。
3. **查注册表**：在 `_registry` 中查找 `provider -> builder/class` 映射。
4. **实例化对象**：执行 `builder(settings)`，例如 `OpenAILLM(settings)`。
5. **按抽象接口使用**：上层仅通过 `BaseLLM.chat(...)` 调用，不依赖具体类名。

一句话总结：**工厂负责“选谁并创建”，派生类负责“具体能力实现”。**

## 6) 新增一个 provider 的最小流程（教学示例）

以测试中的 `FakeLLM` 为例（见 `tests/unit/test_llm_factory.py`）：

1. **实现派生类**
   - 继承 `BaseLLM`
   - 实现 `chat(messages) -> str`

2. **注册到工厂**
   - 调用 `LLMFactory.register("fake-b1", FakeLLM)`

3. **配置 provider**
   - 设置 `settings.llm.provider = "fake-b1"`

4. **通过工厂创建**
   - `llm = LLMFactory.create(settings)`

5. **按抽象接口调用并断言**
   - 调用 `llm.chat(...)`
   - 断言返回值符合预期

关键点：

- 业务层没有 import `FakeLLM` 直接实例化；
- 扩展新 provider 只需“新增实现 + 注册映射”，不改业务调用代码。
