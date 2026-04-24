"""Integration tests for the stdio MCP server."""

from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys

from core.types import Chunk
from ingestion.storage.bm25_indexer import BM25Indexer
from ingestion.storage.image_storage import ImageStorage


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _start_server(env: dict[str, str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=PROJECT_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def _send_request(process: subprocess.Popen[str], payload: dict[str, object]) -> dict[str, object]:
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
    process.stdin.flush()
    line = process.stdout.readline().strip()
    assert line
    return json.loads(line)


def _prepare_sparse_search_data(tmp_path: Path, with_image: bool = False) -> dict[str, str]:
    chroma_dir = tmp_path / "chroma"
    bm25_dir = tmp_path / "bm25"
    image_root = tmp_path / "images"
    image_db = tmp_path / "image_index.db"
    chroma_dir.mkdir()
    bm25_dir.mkdir()

    text = "Azure deployment guide"
    if with_image:
        text += " [IMAGE: img-001]"

    (chroma_dir / "records.json").write_text(
        json.dumps(
            [
                {
                    "chunk_id": "chunk-1",
                    "vector": [1.0, 0.0],
                    "text": text,
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
                text=text,
                metadata={"source_path": "guide.md", "doc_type": "md", "title": "Azure Guide"},
                start_offset=0,
                end_offset=len(text),
                source_ref="doc-001",
            )
        ],
        sparse_vectors=[{"azure": 0.5, "deployment": 0.5}],
    )

    if with_image:
        image_storage = ImageStorage(image_root_dir=str(image_root), db_path=str(image_db))
        image_storage.save_image(
            image_id="img-001",
            image_bytes=b"fake-png",
            collection="docs",
            doc_hash="doc-001",
        )

    return {
        "CHROMA_PERSIST_PATH": str(chroma_dir),
        "BM25_PERSIST_PATH": str(bm25_dir),
        "IMAGE_ROOT_DIR": str(image_root),
        "IMAGE_INDEX_DB_PATH": str(image_db),
    }


def test_mcp_server_when_initialize_then_stdout_only_contains_json_and_stderr_has_logs(
    tmp_path: Path,
) -> None:
    env = {**os.environ, **_prepare_sparse_search_data(tmp_path)}
    process = _start_server(env)
    try:
        response = _send_request(
            process,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert response["result"]["serverInfo"]["name"] == "modular-rag-mcp-server"

        assert process.stdin is not None
        process.stdin.close()
        stderr = process.stderr.read() if process.stderr is not None else ""
        process.wait(timeout=5)
        assert "MCP server started" in stderr
    finally:
        process.kill()


def test_mcp_server_when_query_knowledge_hub_called_then_return_markdown_and_citations(
    tmp_path: Path,
) -> None:
    env = {**os.environ, **_prepare_sparse_search_data(tmp_path)}
    process = _start_server(env)
    try:
        _send_request(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        response = _send_request(
            process,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "query_knowledge_hub",
                    "arguments": {"query": "Azure", "top_k": 1, "collection": "docs"},
                },
            },
        )

        result = response["result"]
        assert result["content"][0]["type"] == "text"
        assert "[1]" in result["content"][0]["text"]
        assert result["structuredContent"]["citations"][0]["chunk_id"] == "chunk-1"
    finally:
        process.kill()


def test_mcp_server_when_query_hits_image_then_return_image_content(tmp_path: Path) -> None:
    env = {**os.environ, **_prepare_sparse_search_data(tmp_path, with_image=True)}
    process = _start_server(env)
    try:
        _send_request(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        response = _send_request(
            process,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "query_knowledge_hub",
                    "arguments": {"query": "Azure", "top_k": 1, "collection": "docs"},
                },
            },
        )

        content = response["result"]["content"]
        assert any(item["type"] == "image" for item in content)
        image_content = next(item for item in content if item["type"] == "image")
        assert image_content["mimeType"] == "image/png"
        assert isinstance(image_content["data"], str) and image_content["data"]
    finally:
        process.kill()
