# 教学模式学习方案（固定执行版）

## 目标

- 以“能落地、能解释、能验证”为标准学习本项目。
- 避免只看代码不成体系，也避免只学理论不动手。

---

## 核心方法（长期不变）

采用 **螺旋式学习**，而不是“先全部学完再开始”：

1. 先建立宏观认知（项目地图）
2. 再吃透一个最小模块（单点突破）
3. 用测试闭环反推理解（验证驱动）
4. 回到宏观图更新认知（形成新一轮）

---

## 每次学习固定 4 问

每进入一个模块，先回答以下 4 个问题：

1. 这个模块解决什么痛点？
2. 输入/输出契约是什么？
3. 为什么放在这一层，而不是别处？
4. 不做它会出现什么问题？

---

## 每课固定流程（教学模式标准流程）

1. **设计动机（Why）**  
   先讲这一课为什么存在、在全链路中的位置。
2. **框架定位（Where）**  
   指出代码落点与上下游依赖关系。
3. **实现要点（How）**  
   只讲关键接口、核心函数、边界处理。
4. **验证方式（Verify）**  
   给出测试命令与通过标准。
5. **学习沉淀（Record）**  
   更新 `TEACHING_MODE_TRACKER.md` 的课次记录。

---

## 学习节奏建议

- 一次只学一个模块，不跨模块贪多。
- 先跑通再优化，先正确再完美。
- 看不懂时先看测试，再回看实现。
- 每课都产出“你自己的一句话总结”。

---

## 项目内执行约定

- 默认按教学模式推进，不需要你每次重复说明。
- 每课结束必须包含：
  - 课程结论（简短）
  - 代码落点（文件路径）
  - 验证结果（命令 + 结果）
  - 下一课入口

---

## 与现有文档关系

- 课程进度记录：`learning-notes/TEACHING_MODE_TRACKER.md`
- 用户协作偏好：`learning-notes/USER_PREFERENCES.md`
- 项目总规范：`DEV_SPEC.md`

---

## 如何描述“抽象 + 工厂”实现（对人讲 / 对 LLM 讲）

### 一、对人讲的 6 句结构（口头版）

1. **问题**：我们有多个 provider，能力相似但实现细节不同。  
2. **目标**：上层调用不随 provider 变化而改动。  
3. **做法**：定义最小公共抽象接口（Base），统一调用方式。  
4. **做法**：用工厂按配置选择并实例化具体实现（Factory + registry）。  
5. **边界**：公共能力走 Base；差异太大的能力拆新抽象（如 Vision）。  
6. **收益**：可替换、可测试、可扩展，业务层与实现解耦。  

### 二、对 LLM 提需求的结构化模板（文本版）

```text
请按“抽象接口 + 工厂路由”设计一个可插拔模块，要求如下：

【业务目标】
- 上层业务只依赖统一接口，不依赖具体 provider 类名。

【输入配置】
- 从 settings.<module>.provider 读取 provider 名称。

【接口层】
- 定义 Base<Module> 抽象类，包含最小公共方法：
  - 例如：chat(messages) -> str / embed(texts) -> list[list[float]]

【实现层】
- 至少实现 2 个 provider 类，均继承 Base<Module>。
- 每个实现类处理自己的认证、请求格式、响应解析、错误包装。

【工厂层】
- 定义 <Module>Factory，包含：
  - _registry: dict[str, Builder]
  - register(provider, builder)
  - create(settings) -> Base<Module>
- create 的流程必须是：
  1) 读取 provider
  2) strip+lower 标准化
  3) 查 _registry
  4) 找不到抛可读错误（包含 provider 名）
  5) 实例化并返回

【测试要求】
- 已注册 provider：create 返回对应实现
- 未注册 provider：抛出包含 provider 的错误
- 使用 Fake provider 验证工厂路由，不访问外部网络

【非目标】
- 不实现与本任务无关的业务逻辑
- 不在业务层写 provider 分支判断
```

### 三、给别人看代码时的“最小图”

```text
settings.yaml
   └── provider = openai
            │
            ▼
      Factory.create(settings)
            │
            ▼
   _registry["openai"] -> OpenAIImpl
            │
            ▼
        OpenAIImpl(...)
            │
            ▼
  上层只调用 Base 接口方法
```
