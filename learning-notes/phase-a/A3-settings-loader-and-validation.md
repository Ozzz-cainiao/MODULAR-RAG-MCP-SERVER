# 项目学习笔记（A3：配置加载与校验）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **A3：配置加载与校验（Settings）**：

- 新增配置模型与加载逻辑：`src/core/settings.py`
- 新增占位日志模块：`src/observability/logger.py`
- 更新启动入口以加载配置并 fail-fast：`main.py`
- 保持配置文件关键区块齐全：`config/settings.yaml`
- 新增配置加载单元测试：`tests/unit/test_config_loading.py`

---

## 2) 关键知识点

### 2.1 配置职责边界

- `Settings` dataclass 只负责配置结构与最小校验。
- 不在配置层做外部网络调用或业务初始化。

### 2.2 配置加载流程

1. 读取 YAML
2. 解析为结构化 dataclass
3. 执行集中校验（`validate_settings`）
4. 缺失关键字段时抛出可读错误（带字段路径）

### 2.3 Fail-fast 启动策略

- `main.py` 启动阶段立即调用 `load_settings("config/settings.yaml")`
- 若文件缺失或字段缺失，返回非 0 并记录错误
- 配置正确才继续启动流程

### 2.4 可读错误信息

- 缺字段错误应包含路径，例如：`embedding.provider`
- 方便快速定位配置问题

---

## 3) 测试与验证

- 测试文件：`tests/unit/test_config_loading.py`
- 覆盖点：
  - 有效配置可成功加载
  - 缺失 `embedding.provider` 时抛出可读错误

执行命令：

- `python -m pytest -q tests/unit/test_config_loading.py`

结果：

- `2 passed`

---

## 4) 本模块常见问题

### Q1：为什么要单独做 `validate_settings()`？

为了把校验规则集中管理，避免散落在各处；
后续新增字段时也更容易统一维护与扩展。

### Q2：仓库里代码注释为什么要统一中文？

统一中文注释有三个直接收益：

- 降低团队沟通成本，读代码时上下文一致。
- 新同学更容易快速理解设计意图与约束。
- 规范稳定后，后续代码审查更容易执行一致标准。

### Q3：英语术语要不要翻译成中文？

不需要。执行规则是：

- 注释说明使用中文；
- 技术术语保留英文（如 `MCP`、`LLM`、`Embedding`、`Vector Store`、`Dashboard`）。
