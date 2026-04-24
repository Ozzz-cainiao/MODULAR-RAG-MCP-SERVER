"""Unit tests for JSONL trace logging."""

from __future__ import annotations

import json
from pathlib import Path

from observability import logger as logger_module


def test_write_trace_when_called_then_append_jsonl_line(tmp_path: Path, monkeypatch) -> None:
    log_path = tmp_path / "logs" / "traces.jsonl"
    original_get_trace_logger = logger_module.get_trace_logger

    monkeypatch.setattr(
        logger_module,
        "get_trace_logger",
        lambda name="modular_rag.trace.test", log_path=str(log_path): original_get_trace_logger(
            name=name,
            log_path=str(log_path),
        ),
    )

    logger_module.write_trace({"trace_id": "t1", "trace_type": "query"})

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["trace_id"] == "t1"
    assert payload["trace_type"] == "query"
