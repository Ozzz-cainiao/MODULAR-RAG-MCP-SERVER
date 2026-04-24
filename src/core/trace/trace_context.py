"""Trace context primitives with timing and serialization support."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import perf_counter
import uuid
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class TraceStage:
    """Single trace stage record."""

    name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "metadata": dict(self.metadata),
            "started_at": self.started_at,
        }


@dataclass(slots=True)
class TraceContext:
    """Trace lifecycle for query and ingestion flows."""

    trace_type: str = "query"
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    stages: list[TraceStage] = field(default_factory=list)
    started_at: str = field(default_factory=_utc_now)
    finished_at: str | None = None
    _started_perf: float = field(default_factory=perf_counter, repr=False)
    _finished_perf: float | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.trace_type not in {"query", "ingestion"}:
            raise ValueError("trace_type 必须是 query 或 ingestion")

    def record_stage(self, name: str, metadata: dict[str, Any] | None = None) -> None:
        """Record a stage event."""

        if not isinstance(name, str) or not name.strip():
            raise ValueError("stage name 必须是非空字符串")
        self.stages.append(TraceStage(name=name.strip(), metadata=dict(metadata or {})))

    def finish(self) -> None:
        """Mark the trace as completed."""

        self.finished_at = _utc_now()
        self._finished_perf = perf_counter()

    def elapsed_ms(self, stage_name: str | None = None) -> float:
        """Return elapsed milliseconds for the full trace or a named stage."""

        if stage_name is None:
            end = self._finished_perf if self._finished_perf is not None else perf_counter()
            return round((end - self._started_perf) * 1000, 3)

        for stage in reversed(self.stages):
            if stage.name == stage_name:
                value = stage.metadata.get("elapsed_ms", 0.0)
                if isinstance(value, (int, float)):
                    return round(float(value), 3)
                return 0.0
        raise KeyError(f"未找到阶段: {stage_name}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the trace as a JSON-safe dict."""

        return {
            "trace_id": self.trace_id,
            "trace_type": self.trace_type,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_elapsed_ms": self.elapsed_ms(),
            "stages": [stage.to_dict() for stage in self.stages],
        }
