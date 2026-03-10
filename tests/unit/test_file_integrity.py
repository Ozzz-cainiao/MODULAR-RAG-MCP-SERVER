"""文件完整性检查器测试。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3

from libs.loader.file_integrity import SQLiteIntegrityChecker


def test_compute_sha256_when_same_file_then_result_stable(tmp_path: Path) -> None:
    """同一文件重复计算哈希结果应一致。"""

    file_path = tmp_path / "sample.txt"
    file_path.write_text("modular rag mcp", encoding="utf-8")
    checker = SQLiteIntegrityChecker(db_path=str(tmp_path / "db" / "history.db"))

    hash_one = checker.compute_sha256(str(file_path))
    hash_two = checker.compute_sha256(str(file_path))

    assert hash_one == hash_two


def test_should_skip_when_mark_success_then_returns_true(tmp_path: Path) -> None:
    """标记成功后 should_skip 应返回 True。"""

    checker = SQLiteIntegrityChecker(db_path=str(tmp_path / "db" / "history.db"))
    file_hash = "hash-success-1"

    assert checker.should_skip(file_hash) is False
    checker.mark_success(file_hash=file_hash, file_path="tests/fixtures/sample_documents/sample.md")
    assert checker.should_skip(file_hash) is True


def test_sqlite_checker_when_use_default_path_then_create_database_file(tmp_path: Path, monkeypatch) -> None:
    """默认路径应自动创建 data/db/ingestion_history.db。"""

    monkeypatch.chdir(tmp_path)
    checker = SQLiteIntegrityChecker()
    checker.mark_failed(file_hash="hash-failed-1", error_msg="mock error")

    database_path = tmp_path / "data" / "db" / "ingestion_history.db"
    assert database_path.exists()


def test_sqlite_checker_when_concurrent_writes_then_persist_all_records_and_enable_wal(tmp_path: Path) -> None:
    """并发写入应成功，且数据库处于 WAL 模式。"""

    database_path = tmp_path / "db" / "history.db"
    checker = SQLiteIntegrityChecker(db_path=str(database_path))

    def _write_record(index: int) -> None:
        checker.mark_success(
            file_hash=f"hash-{index}",
            file_path=f"tests/fixtures/sample_documents/sample_{index}.md",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(_write_record, range(30)))

    with sqlite3.connect(database_path) as conn:
        rows = conn.execute(
            "SELECT COUNT(*) FROM ingestion_history WHERE status = 'success'"
        ).fetchone()
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()

    assert rows is not None
    assert rows[0] == 30
    assert journal_mode is not None
    assert str(journal_mode[0]).lower() == "wal"

