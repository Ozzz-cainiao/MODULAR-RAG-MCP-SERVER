# 项目学习笔记（C2：文件完整性检查 SHA256）

## 1) 本模块完成内容

本轮完成了 DEV_SPEC 中的 **C2：文件完整性检查（SHA256）**：

- 新增文件完整性模块：`src/libs/loader/file_integrity.py`
- 更新 Loader 导出：`src/libs/loader/__init__.py`
- 新增单元测试：`tests/unit/test_file_integrity.py`
- 更新进度：`DEV_SPEC.md` 与自动拆分规格文件

---

## 2) 模块功能 / 流程位置 / 作用

### 2.1 模块功能

- 提供 `FileIntegrityChecker` 抽象接口，统一完整性检查能力。
- 提供 `SQLiteIntegrityChecker` 默认实现：
  - `compute_sha256(path)`：计算文件 SHA256；
  - `should_skip(file_hash)`：判断是否已成功摄取；
  - `mark_success(file_hash, file_path)`：记录成功；
  - `mark_failed(file_hash, error_msg)`：记录失败。
- 自动创建数据库文件：`data/db/ingestion_history.db`。
- 启用 SQLite WAL 模式，支持并发写入场景。

### 2.2 在整体流程中的位置

- 位于 Ingestion Pipeline 入口附近，属于“预处理守卫层”。
- 在 Loader 真正解析文档前先做“是否跳过”判定，避免重复摄取。
- 为后续 C3~C15 提供可复用的摄取历史状态源。

### 2.3 模块作用

- 用内容哈希作为幂等键，降低重复计算与重复存储成本。
- 把“成功/失败历史”结构化落库，便于后续追踪与回放。
- 为并行摄取提供基本并发保障（WAL + upsert）。

---

## 3) 关键设计点

- **哈希稳定性**：使用流式读取（分块）计算 SHA256，适配大文件。
- **状态语义清晰**：`should_skip` 仅在 `status=success` 时返回 `True`。
- **并发可用性**：连接级设置 `PRAGMA journal_mode=WAL`，减少写入冲突。
- **接口可替换**：抽象基类预留后续切换 Redis/PostgreSQL 的实现空间。

---

## 4) 测试与验证

- 测试文件：`tests/unit/test_file_integrity.py`
- 覆盖点：
  - 同文件重复计算哈希一致
  - 标记成功后 `should_skip` 为 `True`
  - 默认路径下数据库自动创建
  - 并发写入成功且 journal mode 为 WAL

执行命令：

- `cmd /c ".venv\Scripts\activate.bat && where python && pytest -q tests/unit/test_file_integrity.py tests/unit/test_smoke_imports.py"`

结果：

- `5 passed`

---

## 5) 本模块常见问题

### Q1：为什么 `should_skip` 只看 success，不看 failed？

失败记录用于诊断，不应阻塞后续重试。
只有已成功摄取的内容才应被跳过。

### Q2：为什么要启用 SQLite WAL？

WAL 能提升并发读写能力，降低“database is locked”概率，更适合批量摄取场景。

