# 项目学习笔记（A2：pytest 测试基座）

## 1) 本环节做了什么

本轮完成了 DEV_SPEC 中的 **A2：引入 pytest 并建立测试目录约定**，主要改动如下：

- 在 `pyproject.toml` 中新增 `pytest` 依赖。
- 在 `pyproject.toml` 中新增 `[tool.pytest.ini_options]` 配置，规范测试发现规则。
- 新增冒烟测试文件 `tests/unit/test_smoke_imports.py`。
- 新增最小测试样例文档 `tests/fixtures/sample_documents/sample.md`。
- 在 `DEV_SPEC.md` 中将 A2 标记为完成，并同步阶段/总进度。
- 在 `.gitignore` 中增加 `*.mp4`，忽略视频文件。

---

## 2) pytest 配置是什么

`pytest` 配置就是告诉测试框架：

- 去哪里找测试
- 哪些文件/函数算测试
- 测试如何分类（如 unit / integration / e2e）

当前项目配置含义：

- `testpaths = ["tests"]`：只在 `tests/` 目录找测试。
- `python_files = ["test_*.py"]`：以 `test_` 开头的文件视为测试文件。
- `python_functions = ["test_*"]`：以 `test_` 开头的函数视为测试函数。
- `markers`：声明了 `unit`、`integration`、`e2e` 三类测试标记。

这样做的好处是：团队成员执行测试时行为一致，测试组织更清晰。

---

## 3) 冒烟测试是什么、作用是什么

冒烟测试（Smoke Test）是最小、最快的健康检查。

本项目中的冒烟测试目前验证：

- 项目顶层包（如 `mcp_server`、`core`、`ingestion` 等）能否成功导入。

它的价值：

- 快速发现基础问题（路径错误、包结构错误、缺失 `__init__.py`、环境不对等）。
- 在进入更复杂业务测试前，先确认“工程骨架是活的”。

---

## 4) 最小测试样例文档是干什么的

`tests/fixtures/sample_documents/sample.md` 是测试输入样本（fixture）。

用途：

- 为后续 ingestion/解析流程测试提供稳定、可重复的数据。
- 避免依赖真实大文件，提高测试速度与稳定性。
- 让新同学拉代码后可以直接复现测试场景。

即使当前 A2 的核心测试还没直接用到它，提前放好 fixture 能减少后续阶段反复补文件的成本。

---

## 5) 常用 pytest 命令（快速上手）

- 跑全部测试：`python -m pytest -q`
- 只跑冒烟测试：`python -m pytest -q tests/unit/test_smoke_imports.py`
- 按标记跑（示例）：`python -m pytest -q -m unit`

> 注：按 `auto-coder` 规范，运行 Python/pytest 前优先使用项目 `.venv`。

---

## 6) 本模块常见问题（来自你的提问）

### Q1：pytest 配置是什么？

pytest 配置是测试运行规则，告诉框架：

- 去哪里找测试（`testpaths`）
- 哪些文件/函数是测试（`python_files` / `python_functions`）
- 如何分组测试（`markers`）

### Q2：冒烟测试有什么用？

冒烟测试用于快速验证“系统最基本能力是否正常”，
本项目 A2 中主要检查顶层包可导入，帮助提前发现路径/结构问题。

### Q3：为什么要有最小测试样例文档？

最小样例文档（fixture）是后续 ingestion 测试的稳定输入样本，
用于提高测试可复现性、减少对真实大文件的依赖。

### Q4：`.gitkeep` 文件有什么作用？

`.gitkeep` 不是 Git 官方功能，而是社区常用约定。

- Git 只能跟踪文件，不能直接跟踪空目录。
- 当需要保留空目录结构时，会放一个 `.gitkeep` 作为占位。
- 这样团队成员拉取仓库时，目录结构不会丢失。

在本项目里，像 `learning-notes/phase-a/`、`learning-notes/phase-b/` 这类目录先用 `.gitkeep` 保留骨架，后续再逐步填充内容。

### Q5：如果以后我自己写 spec，怎么描述“建立 pytest 测试基座”？

建议用结构化描述，最少包含 6 个要素：

1. **目标**：说明要建立统一测试基座，而不是实现业务逻辑。
2. **必改文件**：明确列出要修改/新增的文件路径。
3. **配置要求**：写清 `testpaths`、命名规则、`markers`。
4. **测试要求**：至少 1 个可通过的冒烟测试（如顶层包可导入）。
5. **验收标准**：给出可执行命令和通过条件。
6. **非目标**：明确不要做的事，避免模型过度扩展。

可直接复用的指令模板：

```text
请完成“pytest测试基座”任务：
1) 仅修改：pyproject.toml、tests/unit/test_smoke_imports.py、tests/fixtures/sample_documents/sample.md
2) 在pyproject.toml添加pytest依赖和pytest配置（testpaths/python_files/python_functions/markers）
3) 新增一个可通过的冒烟测试，只验证顶层包导入
4) 新增最小fixture文档
5) 运行 python -m pytest -q tests/unit/test_smoke_imports.py 并汇报结果
6) 不做与任务无关改动
```

### Q6：`pyproject.toml` 的作用与使用方法是什么？

它是 Python 项目的统一配置入口，通常包含三类信息：

1. **项目元信息（[project]）**
   - 例如：项目名、版本、Python 版本、依赖包。
   - 用途：让安装/运行环境有明确边界。

2. **构建系统（[build-system]）**
   - 例如：`setuptools`、`wheel`、构建后端。
   - 用途：定义项目如何被打包与构建。

3. **工具配置（[tool.xxx]）**
   - 例如：`[tool.pytest.ini_options]`、`[tool.ruff]`、`[tool.mypy]`。
   - 用途：把测试/静态检查/格式化规则集中管理，避免散落多个配置文件。

在本项目中，`pyproject.toml` 主要承担：

- 管理 `pytest` 依赖；
- 定义 pytest 的测试发现规则（`testpaths/python_files/python_functions`）；
- 定义测试分组标记（`unit/integration/e2e`）。

### Q7：新建项目时，怎样描述才能让大模型生成“带测试基座”的 `pyproject.toml`？

建议使用“目标 + 文件清单 + 明确约束 + 验收命令”的提示词结构。可直接复制：

```text
请为一个 Python 3.11 项目创建最小可用的 pyproject.toml，并建立 pytest 测试基座。

要求：
1) 使用 setuptools 作为 build backend
2) 在 [project] 中设置：
   - name = "<your-project-name>"
   - version = "0.1.0"
   - requires-python = ">=3.11"
   - dependencies 至少包含 pytest
3) 在 [tool.pytest.ini_options] 中设置：
   - testpaths = ["tests"]
   - python_files = ["test_*.py"]
   - python_classes = ["Test*"]
   - python_functions = ["test_*"]
   - markers = ["unit: unit tests", "integration: integration tests", "e2e: end-to-end tests"]
4) 同时创建：
   - tests/unit/test_smoke_imports.py（只验证顶层包可导入）
   - tests/fixtures/sample_documents/sample.md（最小 fixture）
5) 输出完成后给出以下验证命令：
   - pytest -q tests/unit/test_smoke_imports.py
6) 不要添加与上述目标无关的复杂配置。

请输出：
- 完整 pyproject.toml 内容
- 新增测试文件内容
- 验证命令
```
