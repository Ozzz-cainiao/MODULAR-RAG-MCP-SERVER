# 教学模式学习跟踪

## 使用说明

- 本文档用于记录“教学模式”下的学习进度与问题沉淀。
- 每完成一课，新增一条课次记录。
- 每次记录至少填写：学习目标、核心概念、代码落点、你的疑问、下一步计划。

---

## 学习总览

| 状态 | 课次 | 主题 | 目标 | 对应模块 | 备注 |
|------|------|------|------|----------|------|
| [x] | 第 0 课 | 项目全景与学习路线 | 理解三条主线与分层设计 | 全局 | 已完成 |
| [x] | 第 1 课 | 阶段 A1：工程骨架 | 理解“先骨架后业务”的原因 | A1 | 已完成 |
| [x] | 第 2 课 | 阶段 A2：测试基座 | 理解测试目录与冒烟测试价值 | A2 | 已完成 |
| [x] | 第 3 课 | 阶段 A3：配置加载 | 理解配置驱动与 fail-fast | A3 | 已完成（概念与代码对齐） |
| [~] | 第 4 课 | 阶段 B：可插拔抽象层 | 理解 Factory + Base 接口模式 | B1-B9 | 进行中（已完成 Part 5） |
| [~] | 第 5 课 | 阶段 C：Ingestion MVP | 理解摄取链路设计与增量处理 | C1-C15 | 进行中（已完成 Part 1） |
| [ ] | 第 6 课 | 阶段 D：Retrieval MVP | 理解混合检索与 RRF/Rerank | D1-D7 |  |
| [ ] | 第 7 课 | 阶段 E：MCP Tools | 理解能力暴露与协议边界 | E1-E6 |  |
| [ ] | 第 8 课 | 阶段 F/G/H/I | 理解可观测、评估与验收闭环 | F-I |  |

---

## 课次记录模板

> 复制以下模板到文档末尾，填写一课内容。

```markdown
## 第 X 课：<主题>

### 1) 学习目标
- 

### 2) 设计动机（为什么要这样做）
- 

### 3) 核心概念（只保留 3-5 个）
- 

### 4) 代码落点（文件）
- 

### 5) 验证方式（测试/命令）
- 

### 6) 你的疑问
- 

### 7) 结论（你自己的话）
- 

### 8) 下一步
- 
```

---

## 第 0 课：项目全景与学习路线

### 1) 学习目标
- 建立对项目总体结构的第一层认知。
- 明确后续学习不是“全懂再做”，而是“按模块闭环推进”。

### 2) 设计动机（为什么要这样做）
- 项目体量较大，直接看细节会迷失。
- 先看全景，再按阶段拆解，能降低理解成本。

### 3) 核心概念（只保留 3-5 个）
- Ingestion（离线摄取链路）
- Retrieval（在线检索链路）
- MCP Server（对外工具能力暴露）
- 可插拔架构（接口 + 工厂 + 配置驱动）
- 契约先行（核心数据类型统一）

### 4) 代码落点（文件）
- `DEV_SPEC.md`
- `.github/skills/auto-coder/specs/03-tech-stack.md`
- `.github/skills/auto-coder/specs/05-architecture.md`
- `.github/skills/auto-coder/specs/06-schedule.md`

### 5) 验证方式（测试/命令）
- 本课以认知对齐为主，无代码执行要求。

### 6) 你的疑问
- “还没掌握完整知识，是否不该上来做项目？”
- “为什么要建立 C2 这类模块，以及为什么这样分层？”

### 7) 结论（你自己的话）
- 可以边做边学，不需要全掌握后才开始。
- 每步先理解动机，再看实现和验证。

### 8) 下一步
- 进入第 1 课：A1（工程骨架与最小可运行入口）。

---

## 第 1 课：阶段 A1（工程骨架与最小可运行入口）

### 1) 学习目标
- 理解为什么项目第一步不是写业务逻辑，而是先搭工程骨架。
- 看懂 A1 的交付边界：目录、入口、配置占位、可导入性。

### 2) 设计动机（为什么要这样做）
- 在没有骨架前直接写业务，后续会频繁“搬家式重构”（路径、导入、配置、打包方式都会反复改）。
- 先把目录和入口固定，后续每个模块只关注自身逻辑，开发成本显著下降。
- A1 的本质是把“工程可运行”这件事先成立，哪怕业务功能暂时为空。

### 3) 核心概念（只保留 3-5 个）
- **最小可运行入口**：先保证程序能启动并处理基础错误。
- **模块可导入性**：顶层包能稳定 import，后续开发才可持续。
- **配置与 Prompt 占位**：先留接口位，后续增量填充能力。
- **工程约束先行**：`pyproject.toml`、`.gitignore`、目录约定先定型。

### 4) 代码落点（文件）
- `main.py`
- `pyproject.toml`
- `.gitignore`
- `src/**/__init__.py`
- `config/settings.yaml`
- `config/prompts/*.txt`

### 5) 验证方式（测试/命令）
- `python -m compileall src`
- `python -c "import mcp_server, core, ingestion, libs, observability; print('imports_ok')"`

本次实测结果：
- `compileall` 执行成功（`src` 全部可编译）
- 顶层包导入成功（输出 `imports_ok`）

### 6) 你的疑问
- “我还没掌握全项目，是不是不该上来做项目？”
- “为什么要先做骨架而不是直接写功能？”

### 7) 结论（你自己的话）
- A1 是“工程打地基”，不是业务实现阶段。
- 先确保项目结构稳定，后续模块开发才不会反复返工。

### 8) 下一步
- 进入第 2 课：A2（pytest 测试基座与冒烟测试价值）。

---

## 第 2 课：阶段 A2（pytest 测试基座）

### 1) 学习目标
- 理解为什么在早期就要引入 pytest，而不是功能做完后再补测试。
- 看懂“冒烟测试”在工程中的作用边界。

### 2) 设计动机（为什么要这样做）
- 项目后续会持续新增模块，若没有统一测试入口，回归质量不可控。
- A2 先建立最小测试基座，保证每次改动都能快速验证“工程仍然活着”。
- 冒烟测试不是覆盖业务细节，而是先防止最基础的导入链路断裂。

### 3) 核心概念（只保留 3-5 个）
- **测试基座**：统一 pytest 配置、目录约定、执行入口。
- **冒烟测试**：验证最关键路径是否可运行（这里是顶层包 import）。
- **快速反馈**：用低成本测试尽早发现结构性问题。

### 4) 代码落点（文件）
- `pyproject.toml`（pytest 配置：`testpaths/python_files/markers`）
- `tests/unit/test_smoke_imports.py`（顶层包导入校验）

### 5) 验证方式（测试/命令）
- `pytest -q tests/unit/test_smoke_imports.py`

本次实测结果：
- `1 passed`

### 6) 你的疑问
- “为什么要先建这些基础文件，而不是直接写业务？”
- “`pyproject.toml` 的作用和使用方法是什么？”
- “新建项目时如何描述，才能让大模型正确建立 `pyproject.toml` 和测试基座？”

### 7) 结论（你自己的话）
- A2 的价值是建立“稳定回归入口”，不是追求高覆盖率。
- 有了测试基座，后续每个模块都能在统一框架下验证质量。

### 8) 下一步
- 进入第 3 课：A3（配置加载与校验，为什么要 fail-fast）。

---

## 第 3 课：阶段 A3（配置加载与校验）

### 1) 学习目标
- 理解为什么配置加载必须在启动阶段 fail-fast。
- 看懂 `Settings` 结构、加载流程与错误信息设计。

### 2) 设计动机（为什么要这样做）
- 配置错误若不在启动时拦截，问题会在运行中后置暴露，排查成本高。
- A3 的核心是“把错误前移”：系统宁可启动失败，也不带错运行。

### 3) 核心概念（只保留 3-5 个）
- **配置驱动**：provider 与关键参数来自配置，而非硬编码。
- **集中校验**：`validate_settings()` 统一维护必填字段规则。
- **可读错误**：错误信息包含字段路径（如 `embedding.provider`）。
- **Fail-fast**：启动阶段即校验，失败立即退出。

### 4) 代码落点（文件）
- `main.py`（启动时调用 `load_settings`，失败返回非 0）
- `src/core/settings.py`（`Settings/load_settings/validate_settings`）
- `tests/unit/test_config_loading.py`（有效配置与缺字段异常测试）
- `learning-notes/phase-a/A3-settings-loader-and-validation.md`（A3 模块笔记）

### 5) 验证方式（测试/命令）
- 标准命令：`pytest -q tests/unit/test_config_loading.py`

说明：
- 历史模块记录结果为 `2 passed`（见 A3 学习笔记）。
- 今日会话内由于本机 PowerShell 执行策略与虚拟环境解释器前缀异常，未完成同命令复跑。

### 6) 你的疑问
- “下一课继续怎么学？”

### 7) 结论（你自己的话）
- A3 的价值不是“多一个配置文件”，而是建立稳定启动边界。
- 配置错误越早暴露，系统越可维护。

### 8) 下一步
- 进入第 4 课：阶段 B（可插拔抽象层，为什么要 Base + Factory）。

---

## 第 4 课：阶段 B（可插拔抽象层）- Part 1

### 1) 学习目标
- 理解为什么这个项目要做 `Base + Factory`，而不是直接在业务里 `if provider == ...`。

### 2) 设计动机（为什么要这样做）
- 模型与后端会频繁替换（OpenAI/Azure/Ollama 等）。
- 若把 provider 判断写死在业务层，后续每扩一种实现都要改核心逻辑，耦合会快速失控。
- `Base` 负责统一调用契约，`Factory` 负责实现选择，业务层只依赖抽象接口。

### 3) 核心概念（只保留 3-5 个）
- **契约隔离**：`BaseLLM.chat`、`BaseEmbedding.embed` 统一接口。
- **配置驱动路由**：工厂按 `settings.<module>.provider` 返回具体实现。
- **可扩展注册**：通过 `register()` 增量扩展 provider，而不改业务编排代码。
- **错误前置**：未注册 provider 立即抛可读错误。

### 4) 代码落点（文件）
- `src/libs/llm/base_llm.py`
- `src/libs/llm/llm_factory.py`
- `src/libs/embedding/base_embedding.py`
- `src/libs/embedding/embedding_factory.py`
- `tests/unit/test_llm_factory.py`
- `tests/unit/test_embedding_factory.py`

### 5) 验证方式（测试/命令）
- `pytest -q tests/unit/test_llm_factory.py tests/unit/test_embedding_factory.py`

说明：
- 本节以架构认知为主，测试行为可参考工厂单测中的“已注册返回实例 / 未注册抛可读错误”断言。

### 6) 你的疑问
- “下一课”
- “我该怎么描述这种实现，尤其是给别人讲或让 LLM 设计类似系统时怎么描述？”
- “我不理解抽象与工厂的运行逻辑”
- “不同 provider 能力不一致时，抽象和工厂怎么兼容？”

### 7) 结论（你自己的话）
- Base 解决“怎么被调用”，Factory 解决“用哪个实现”。
- 这两者分开后，业务层才不需要关心具体 provider。

### 8) 下一步
- 第 4 课 Part 2：以 B1 为例，逐行拆 `LLMFactory.create()` 的执行路径与扩展方式。

---

## 第 4 课：阶段 B（可插拔抽象层）- Part 2

### 1) 学习目标
- 能独立读懂 `LLMFactory.create()` 的执行路径。
- 能明确“工厂负责创建，派生类负责能力实现”的职责分工。

### 2) 设计动机（为什么要这样做）
- 避免把 provider 分支逻辑散落到业务代码。
- 把“对象创建”与“对象使用”分离，降低耦合。

### 3) 核心概念（只保留 3-5 个）
- 注册表（`provider -> builder/class`）
- 工厂创建（`create(settings)`）
- 基类契约（`BaseLLM.chat`）
- 派生类实现（`OpenAILLM/AzureLLM/OllamaLLM`）

### 4) 代码落点（文件）
- `src/libs/llm/llm_factory.py`
- `src/libs/llm/base_llm.py`
- `src/libs/llm/openai_llm.py`
- `learning-notes/phase-b/B1-llm-interface-and-factory.md`

### 5) 验证方式（测试/命令）
- `pytest -q tests/unit/test_llm_factory.py`

### 6) 你的疑问
- “工厂实例化对象和 openai_llm.py 的关系是什么？”
- “_registry 映射是不是实现切换的核心？”

### 7) 结论（你自己的话）
- `OpenAILLM` 是基类派生类；工厂通过 `_registry` 做 provider 路由并实例化。
- 业务层只依赖抽象接口，不依赖具体 provider 类名。
- 工厂执行可记为 5 步：读配置 -> 标准化 -> 查注册表 -> 实例化 -> 按抽象接口调用。

### 8) 下一步
- 第 4 课 Part 3：以“新增一个 fake provider”为例，完整走一遍扩展流程（注册、创建、测试）。

---

## 第 4 课：阶段 B（可插拔抽象层）- Part 4

### 1) 学习目标
- 验证 `Base + Factory` 不是 LLM 特例，而是可复用的模块化模板。

### 2) 设计动机（为什么要这样做）
- 若同一思路不能平移到 Embedding，说明架构只是“局部技巧”。
- 能在第二个模块复用，才说明抽象边界设计是正确的。

### 3) 核心概念（只保留 3-5 个）
- 模式复用（LLM -> Embedding）
- 统一调用接口（`chat` vs `embed`）
- 同构工厂流程（读配置 -> 查映射 -> 实例化）
- 可测试性（Fake provider 路由测试）

### 4) 代码落点（文件）
- `src/libs/embedding/base_embedding.py`
- `src/libs/embedding/embedding_factory.py`
- `tests/unit/test_embedding_factory.py`
- `learning-notes/phase-b/B2-embedding-interface-and-factory.md`

### 5) 验证方式（测试/命令）
- `pytest -q tests/unit/test_embedding_factory.py`

### 6) 你的疑问
- “下一课”

### 7) 结论（你自己的话）
- 工厂模板可跨模块复用：LLM 和 Embedding 的运行骨架一致，只是接口语义不同。

### 8) 下一步
- 第 4 课 Part 5：讲“抽象边界设计”与“什么时候不该抽象”。

---

## 第 4 课：阶段 B（可插拔抽象层）- Part 3

### 1) 学习目标
- 能独立完成“新增 provider”的最小闭环（实现、注册、创建、测试）。

### 2) 设计动机（为什么要这样做）
- 架构价值不在“看懂图”，而在“能无侵入扩展”。
- Part 3 用最小示例验证可插拔架构是否真的可扩展。

### 3) 核心概念（只保留 3-5 个）
- 派生类实现（继承 `BaseLLM`）
- 工厂注册（`register`）
- 配置驱动（`settings.llm.provider`）
- 统一调用（`BaseLLM.chat`）

### 4) 代码落点（文件）
- `tests/unit/test_llm_factory.py`（`FakeLLM` 示例）
- `src/libs/llm/llm_factory.py`
- `learning-notes/phase-b/B1-llm-interface-and-factory.md`

### 5) 验证方式（测试/命令）
- `pytest -q tests/unit/test_llm_factory.py`

### 6) 你的疑问
- “继续讲课”

### 7) 结论（你自己的话）
- 新增 provider 的核心流程是：实现派生类 -> 注册映射 -> 配置 provider -> 工厂创建 -> 按统一接口调用。

### 8) 下一步
- 第 4 课 Part 4：从 LLM 平移到 Embedding，验证同一模式在另一个模块里复用。

---

## 第 4 课：阶段 B（可插拔抽象层）- Part 5

### 1) 学习目标
- 掌握“什么时候该抽象、什么时候不该抽象”的实用判断标准。

### 2) 设计动机（为什么要这样做）
- 抽象不足会导致业务层到处写 provider 分支。
- 过度抽象会让代码复杂度先于业务复杂度增长。
- 需要一个可执行的边界判断，而不是“凭感觉抽象”。

### 3) 核心概念（只保留 3-5 个）
- 抽象触发条件
- 最小公共接口
- 专有能力拆分
- 过度抽象反模式

### 4) 代码落点（文件）
- `src/libs/llm/base_llm.py`
- `src/libs/llm/base_vision_llm.py`
- `src/libs/embedding/base_embedding.py`
- `learning-notes/phase-b/B2-embedding-interface-and-factory.md`

### 5) 验证方式（测试/命令）
- 结构性验证：看是否可通过 Fake provider 单测覆盖路由行为
- 典型命令：`pytest -q tests/unit/test_llm_factory.py tests/unit/test_embedding_factory.py`

### 6) 你的疑问
- “下一课”

### 7) 结论（你自己的话）
- 满足“多实现可替换 + 上层需稳定 + 需隔离外部依赖测试”时应抽象。
- 若是一次性脚本、单实现、无替换需求，不要为了模式而模式。

### 8) 下一步
- 第 5 课：阶段 C 入门（从 C1 数据契约看为什么先定义类型再做 Pipeline）。

---

## 第 5 课：阶段 C（Ingestion MVP）- Part 1

### 1) 学习目标
- 理解为什么阶段 C 不是直接写 Pipeline，而是先做 C1 数据契约。

### 2) 设计动机（为什么要这样做）
- Ingestion、Retrieval、MCP 都要传递同一份数据对象。
- 若没有先统一 `Document/Chunk/ChunkRecord`，后续每个模块会各自定义字段，最终出现接口不兼容与反复重构。
- 先定契约，后续模块只需“填充契约”，开发可以并行且稳定。

### 3) 核心概念（只保留 3-5 个）
- 契约先行（Schema First）
- 全链路共享数据模型
- 输入防御与早失败
- 多模态字段预留（`metadata.images`）

### 4) 代码落点（文件）
- `src/core/types.py`
- `tests/unit/test_core_types.py`
- `learning-notes/phase-c/C1-core-types-contract.md`

### 5) 验证方式（测试/命令）
- `pytest -q tests/unit/test_core_types.py`
- 关注点：序列化稳定、字段校验、错误可读性

### 6) 你的疑问
- “下一课”
- “给别人讲或让 LLM 设计时怎么描述这种实现？”
- “B 阶段为什么要拆成这些模块？”
- “RAG 项目为什么需要这些模块，一个典型 RAG 流程是什么？”
- “什么是 dense 检索和 sparse 检索？”
- “教学过程中的所有提问都要记录到文档里。”
- “什么是 BM25，什么是倒排索引？”
- “RAG 是否就是靠关键词查文档以提升效率？”
- “BM25 的打分排序逻辑是什么？”
- “两者融合的 RRF 是什么？”
- “这些算法该从哪里学？有没有教程？”
- “这些算法该从哪里学？有没有一条可执行学习路线？”

### 7) 结论（你自己的话）
- C1 是 C 阶段的“协议层”，不是业务功能层。
- Pipeline 后续步骤本质上都是围绕既定契约生产/消费数据。

### 8) 下一步
- 第 5 课 Part 2：以 C2 为例，看“契约如何约束增量摄取（hash + should_skip）”。
