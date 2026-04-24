"""Unit tests for ImageStorage persistence and lookup contract."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ingestion.storage.image_storage import ImageStorage


def test_image_storage_when_save_image_then_file_exists_and_lookup_returns_path(tmp_path: Path) -> None:
    """保存图片后文件应存在，且 lookup 可返回路径。"""

    storage = ImageStorage(
        image_root_dir=str(tmp_path / "images"),
        db_path=str(tmp_path / "db" / "image_index.db"),
    )

    path = storage.save_image(
        image_id="img-001",
        image_bytes=b"fake-image-bytes",
        collection="knowledge-hub",
        doc_hash="doc-hash-001",
        page_num=1,
    )

    assert Path(path).exists()
    assert storage.get_path("img-001") == path


def test_image_storage_when_reopen_then_mapping_persists_in_sqlite(tmp_path: Path) -> None:
    """重建实例后映射关系应仍然存在。"""

    db_path = tmp_path / "db" / "image_index.db"
    storage = ImageStorage(
        image_root_dir=str(tmp_path / "images"),
        db_path=str(db_path),
    )
    saved_path = storage.save_image(
        image_id="img-001",
        image_bytes=b"fake-image-bytes",
        collection="knowledge-hub",
    )

    reopened = ImageStorage(
        image_root_dir=str(tmp_path / "images"),
        db_path=str(db_path),
    )

    assert reopened.get_path("img-001") == saved_path


def test_image_storage_when_list_images_filtered_then_return_matching_rows(tmp_path: Path) -> None:
    """按 collection / doc_hash 过滤时应返回匹配图片。"""

    storage = ImageStorage(
        image_root_dir=str(tmp_path / "images"),
        db_path=str(tmp_path / "db" / "image_index.db"),
    )
    storage.save_image("img-001", b"a", "col-a", doc_hash="doc-1")
    storage.save_image("img-002", b"b", "col-a", doc_hash="doc-2")
    storage.save_image("img-003", b"c", "col-b", doc_hash="doc-1")

    collection_rows = storage.list_images(collection="col-a")
    doc_rows = storage.list_images(doc_hash="doc-1")

    assert [row["image_id"] for row in collection_rows] == ["img-001", "img-002"]
    assert [row["image_id"] for row in doc_rows] == ["img-001", "img-003"]


def test_image_storage_when_database_created_then_wal_mode_enabled(tmp_path: Path) -> None:
    """SQLite 数据库应启用 WAL 模式。"""

    db_path = tmp_path / "db" / "image_index.db"
    storage = ImageStorage(
        image_root_dir=str(tmp_path / "images"),
        db_path=str(db_path),
    )
    storage.save_image("img-001", b"x", "col-a")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute("PRAGMA journal_mode").fetchone()

    assert row is not None
    assert str(row[0]).lower() == "wal"
