"""文件完整性检查与摄取历史管理。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
import hashlib
import sqlite3


class FileIntegrityChecker(ABC):
    """文件完整性检查器抽象接口。"""

    @abstractmethod
    def compute_sha256(self, path: str) -> str:
        """计算文件 SHA256 哈希值。

        参数:
            path: 文件路径。

        返回:
            文件内容的 SHA256 十六进制字符串。
        """

    @abstractmethod
    def should_skip(self, file_hash: str) -> bool:
        """判断文件是否应被跳过。

        参数:
            file_hash: 文件哈希值。

        返回:
            当该哈希已成功摄取时返回 True，否则返回 False。
        """

    @abstractmethod
    def mark_success(self, file_hash: str, file_path: str) -> None:
        """标记文件摄取成功。"""

    @abstractmethod
    def mark_failed(self, file_hash: str, error_msg: str) -> None:
        """标记文件摄取失败。"""


class SQLiteIntegrityChecker(FileIntegrityChecker):
    """基于 SQLite 的文件完整性检查器默认实现。"""

    def __init__(self, db_path: str = "data/db/ingestion_history.db") -> None:
        """初始化检查器并确保数据库可用。

        参数:
            db_path: SQLite 数据库文件路径。
        """

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def compute_sha256(self, path: str) -> str:
        """计算文件 SHA256 哈希值。"""

        file_path = Path(path)
        hasher = hashlib.sha256()

        with file_path.open("rb") as stream:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)

        return hasher.hexdigest()

    def should_skip(self, file_hash: str) -> bool:
        """判断文件是否已成功摄取。"""

        normalized_hash = self._require_non_empty_string(file_hash, "file_hash")
        query = "SELECT 1 FROM ingestion_history WHERE file_hash = ? AND status = 'success' LIMIT 1"

        with self._get_connection() as conn:
            row = conn.execute(query, (normalized_hash,)).fetchone()
        return row is not None

    def mark_success(self, file_hash: str, file_path: str) -> None:
        """记录成功摄取状态。"""

        normalized_hash = self._require_non_empty_string(file_hash, "file_hash")
        normalized_path = self._require_non_empty_string(file_path, "file_path")

        sql = """
        INSERT INTO ingestion_history(file_hash, file_path, status, error_msg, updated_at)
        VALUES (?, ?, 'success', NULL, CURRENT_TIMESTAMP)
        ON CONFLICT(file_hash)
        DO UPDATE SET
            file_path = excluded.file_path,
            status = 'success',
            error_msg = NULL,
            updated_at = CURRENT_TIMESTAMP
        """

        with self._get_connection() as conn:
            conn.execute(sql, (normalized_hash, normalized_path))
            conn.commit()

    def mark_failed(self, file_hash: str, error_msg: str) -> None:
        """记录失败摄取状态。"""

        normalized_hash = self._require_non_empty_string(file_hash, "file_hash")
        normalized_error = self._require_non_empty_string(error_msg, "error_msg")

        sql = """
        INSERT INTO ingestion_history(file_hash, file_path, status, error_msg, updated_at)
        VALUES (?, '', 'failed', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(file_hash)
        DO UPDATE SET
            status = 'failed',
            error_msg = excluded.error_msg,
            updated_at = CURRENT_TIMESTAMP
        """

        with self._get_connection() as conn:
            conn.execute(sql, (normalized_hash, normalized_error))
            conn.commit()

    def _initialize_database(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_history (
                    file_hash TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_msg TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ingestion_history_status ON ingestion_history(status)"
            )
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level="DEFERRED")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _require_non_empty_string(self, value: str, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} 必须是非空字符串")
        return value.strip()

