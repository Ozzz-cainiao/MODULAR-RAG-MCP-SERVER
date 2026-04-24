"""Fetch a lightweight document summary from persisted chunks."""

from __future__ import annotations

import json
import os
from pathlib import Path


def get_document_summary(
    doc_id: str,
    chroma_persist_path: str | None = None,
) -> dict[str, object]:
    """Return title/summary/tags for a document id based on persisted chunk metadata."""

    if not isinstance(doc_id, str) or not doc_id.strip():
        raise ValueError("doc_id 必须是非空字符串")

    persist_root = Path(chroma_persist_path or os.getenv("CHROMA_PERSIST_PATH", "data/db/chroma"))
    data_file = persist_root / "records.json"
    if not data_file.exists():
        raise FileNotFoundError(f"未找到文档索引: {data_file}")

    records = json.loads(data_file.read_text(encoding="utf-8") or "[]")
    matched = [
        record
        for record in records
        if isinstance(record, dict)
        and isinstance(record.get("metadata"), dict)
        and record["metadata"].get("source_ref") == doc_id
    ]
    if not matched:
        raise ValueError(f"未找到 doc_id 对应文档: {doc_id}")

    first = matched[0]
    metadata = dict(first["metadata"])
    texts = [" ".join(str(record.get("text", "")).split()) for record in matched]
    summary = " ".join(text for text in texts if text)[:240]
    tags = []
    for key in ("doc_type", "collection", "title"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            tags.append(value.strip())

    return {
        "content": [
            {
                "type": "text",
                "text": f"{metadata.get('title', doc_id)}\n\n{summary}",
            }
        ],
        "structuredContent": {
            "doc_id": doc_id,
            "title": metadata.get("title", doc_id),
            "summary": summary,
            "tags": tags,
            "source_path": metadata.get("source_path"),
        },
    }


def tool_entry(arguments: dict[str, object] | None = None) -> dict[str, object]:
    payload = arguments or {}
    return get_document_summary(
        doc_id=str(payload.get("doc_id", "")),
        chroma_persist_path=(
            str(payload["chroma_persist_path"]) if payload.get("chroma_persist_path") else None
        ),
    )
