"""E2E MCP client simulation."""

from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys

from core.types import Chunk
from ingestion.storage.bm25_indexer import BM25Indexer


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _prepare_sparse_search_data(tmp_path: Path) -> dict[str, str]:
    chroma_dir = tmp_path / "chroma"
    bm25_dir = tmp_path / "bm25"
    image_root = tmp_path / "images"
    image_db = tmp_path / "image_index.db"
    chroma_dir.mkdir()
    bm25_dir.mkdir()
    (chroma_dir / "records.json").write_text(
        json.dumps(
            [
                {
                    "chunk_id": "chunk-1",
                    "vector": [1.0, 0.0],
                    "text": "Azure deployment guide",
                    "metadata": {
                        "source_path": "guide.md",
                        "doc_type": "md",
                        "title": "Azure Guide",
                        "collection": "docs",
                        "source_ref": "doc-001",
                        "page": 1,
                    },
                }
            ]
        ),
        encoding="utf-8",
    )
    bm25 = BM25Indexer(persist_dir=str(bm25_dir))
    bm25.build(
        chunks=[
            Chunk(
                id="chunk-1",
                text="Azure deployment guide",
                metadata={"source_path": "guide.md", "doc_type": "md", "title": "Azure Guide"},
                start_offset=0,
                end_offset=22,
                source_ref="doc-001",
            )
        ],
        sparse_vectors=[{"azure": 0.5, "deployment": 0.5}],
    )
    return {
        "CHROMA_PERSIST_PATH": str(chroma_dir),
        "BM25_PERSIST_PATH": str(bm25_dir),
        "IMAGE_ROOT_DIR": str(image_root),
        "IMAGE_INDEX_DB_PATH": str(image_db),
    }


def test_mcp_client_roundtrip_when_list_and_call_tools_then_return_citations(tmp_path: Path) -> None:
    env = {**os.environ, **_prepare_sparse_search_data(tmp_path)}
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=PROJECT_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        assert process.stdin is not None and process.stdout is not None
        for payload in [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "query_knowledge_hub", "arguments": {"query": "Azure"}},
            },
        ]:
            process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            process.stdin.flush()
        responses = [json.loads(process.stdout.readline()) for _ in range(3)]
        assert responses[1]["result"]["tools"]
        assert responses[2]["result"]["structuredContent"]["citations"]
    finally:
        process.kill()
