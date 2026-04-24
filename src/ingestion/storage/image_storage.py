"""ImageStorage for filesystem persistence with SQLite-backed image lookup."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any


class ImageStorage:
    """Persist images to disk and keep an SQLite mapping from image_id to file path."""

    def __init__(
        self,
        image_root_dir: str = "data/images",
        db_path: str = "data/db/image_index.db",
    ) -> None:
        self.image_root_dir = Path(image_root_dir)
        self.db_path = Path(db_path)
        self.image_root_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def save_image(
        self,
        image_id: str,
        image_bytes: bytes,
        collection: str,
        doc_hash: str | None = None,
        page_num: int | None = None,
        extension: str = ".png",
    ) -> str:
        """Save image bytes to disk and persist the mapping."""

        normalized_image_id = self._require_non_empty_string(image_id, "image_id")
        normalized_collection = self._require_non_empty_string(collection, "collection")
        if not isinstance(image_bytes, bytes) or not image_bytes:
            raise ValueError("image_bytes 必须是非空 bytes")

        normalized_extension = extension if extension.startswith(".") else f".{extension}"
        image_dir = self.image_root_dir / normalized_collection
        image_dir.mkdir(parents=True, exist_ok=True)
        file_path = image_dir / f"{normalized_image_id}{normalized_extension}"
        file_path.write_bytes(image_bytes)

        sql = """
        INSERT INTO image_index(image_id, file_path, collection, doc_hash, page_num)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(image_id)
        DO UPDATE SET
            file_path = excluded.file_path,
            collection = excluded.collection,
            doc_hash = excluded.doc_hash,
            page_num = excluded.page_num
        """
        with self._get_connection() as conn:
            conn.execute(
                sql,
                (
                    normalized_image_id,
                    str(file_path),
                    normalized_collection,
                    doc_hash,
                    page_num,
                ),
            )
            conn.commit()

        return str(file_path)

    def get_path(self, image_id: str) -> str | None:
        """Return the persisted file path for an image id."""

        normalized_image_id = self._require_non_empty_string(image_id, "image_id")
        sql = "SELECT file_path FROM image_index WHERE image_id = ? LIMIT 1"
        with self._get_connection() as conn:
            row = conn.execute(sql, (normalized_image_id,)).fetchone()
        return str(row[0]) if row is not None else None

    def list_images(
        self,
        collection: str | None = None,
        doc_hash: str | None = None,
    ) -> list[dict[str, Any]]:
        """List persisted images, optionally filtered by collection or doc hash."""

        clauses: list[str] = []
        params: list[Any] = []
        if collection is not None:
            clauses.append("collection = ?")
            params.append(collection)
        if doc_hash is not None:
            clauses.append("doc_hash = ?")
            params.append(doc_hash)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            "SELECT image_id, file_path, collection, doc_hash, page_num "
            f"FROM image_index {where_clause} ORDER BY image_id"
        )
        with self._get_connection() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()

        return [
            {
                "image_id": row[0],
                "file_path": row[1],
                "collection": row[2],
                "doc_hash": row[3],
                "page_num": row[4],
            }
            for row in rows
        ]

    def _initialize_database(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS image_index (
                    image_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    collection TEXT,
                    doc_hash TEXT,
                    page_num INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collection ON image_index(collection)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_doc_hash ON image_index(doc_hash)")
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
