"""Trace collection and persistence helpers."""

from __future__ import annotations

from core.trace.trace_context import TraceContext
from observability.logger import write_trace


class TraceCollector:
    """Collect completed traces and persist them."""

    def collect(self, trace: TraceContext) -> None:
        if not isinstance(trace, TraceContext):
            raise TypeError("trace 必须是 TraceContext")
        if trace.finished_at is None:
            trace.finish()
        write_trace(trace.to_dict())
