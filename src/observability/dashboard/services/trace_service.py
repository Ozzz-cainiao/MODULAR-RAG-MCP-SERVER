"""Load persisted trace JSON lines for dashboard pages."""

from __future__ import annotations

import json
from pathlib import Path


class TraceService:
    def __init__(self, trace_log_path: str = "logs/traces.jsonl") -> None:
        self._trace_log_path = Path(trace_log_path)

    def list_traces(self, trace_type: str | None = None) -> list[dict[str, object]]:
        if not self._trace_log_path.exists():
            return []
        traces: list[dict[str, object]] = []
        for line in self._trace_log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if trace_type is not None and payload.get("trace_type") != trace_type:
                continue
            traces.append(payload)
        traces.sort(key=lambda item: str(item.get("started_at", "")), reverse=True)
        return traces
