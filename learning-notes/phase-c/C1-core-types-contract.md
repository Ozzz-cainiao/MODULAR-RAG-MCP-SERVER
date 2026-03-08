# 项目学习笔记（C1：核心数据类型契约）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **C1：定义核心数据类型/契约（Document/Chunk/ChunkRecord）**：

- 新增核心类型文件：`src/core/types.py`
- 更新 Core 导出入口：`src/core/__init__.py`
- 新增单元测试：`tests/unit/test_core_types.py`
- 更新进度：`DEV_SPEC.md` + `.github/skills/auto-coder/specs/06-schedule.md`

---

## 2) 模块功能 / 流程位置 / 作用

### 2.1 模块功能

- 定义全链路可复用的数据契约：`Document`、`Chunk`、`ChunkRecord`。
- 提供统一序列化与反序列化能力：`to_dict` / `to_json` / `from_dict` / `from_json`。
- 内置元数据校验：
  - `metadata.source_path` 必填；
  - `metadata.images` 结构按规范校验（`id/path/text_offset/text_length` 等）。
- 提供图片占位符工具：
  - 生成：`build_image_placeholder(image_id)`；
  - 解析：`parse_image_placeholders(text)`。

### 2.2 在整体流程中的位置

- 位于 `core` 层，作为 Ingestion → Retrieval → MCP Server 的通用数据边界。
- 上游 Loader/Splitter/Transform 产物可统一落到 `Document/Chunk`。
- 下游向量存储与检索可统一基于 `ChunkRecord` 扩展 dense/sparse 表达。

### 2.3 模块作用

- 统一“数据语言”，减少子模块间重复定义和隐式约定。
- 在 C2~C15 继续演进时保持字段兼容，降低重构成本。
- 为多模态能力提供稳定基础（`metadata.images` + `[IMAGE: {image_id}]` 约定）。

---

## 3) 关键设计点

- **契约稳定性**：序列化字段顺序固定，便于测试与跨模块传递。
- **向前扩展**：`metadata` 允许新增字段，但保留最小必填约束。
- **多模态定位**：通过 `text_offset/text_length` 支持图片在文本中的精确定位。
- **输入防御**：在对象初始化阶段即完成关键字段校验，尽早失败。

---

## 4) 测试与验证

- 测试文件：`tests/unit/test_core_types.py`
- 覆盖点：
  - Document/Chunk/ChunkRecord 的序列化与反序列化
  - `metadata.source_path` 缺失时的可读报错
  - `metadata.images` 非法结构报错
  - Chunk 偏移区间合法性校验
  - 向量字段类型校验

执行命令：

- `cmd /c ".venv\Scripts\activate.bat && where python && pytest -q tests/unit/test_core_types.py"`

结果：

- `7 passed`

---

## 5) 本模块常见问题

### Q1：为什么 C1 要先做“类型契约”，而不是直接写 Pipeline 逻辑？

因为 C 阶段后续模块（C2~C15）都依赖统一的数据输入输出。
先统一 `Document/Chunk/ChunkRecord`，可以显著降低后续模块对接成本和返工概率。

### Q2：用户提到“自动开发”时，当前仓库是怎么推进任务的？

本仓库通过 `auto-coder` 技能自动执行：同步规格 → 识别下一任务 → 编码 → 定向测试 → 回写进度。
本次自动定位到 C1 并完成落地与验证。

