"""Unit tests for enhanced trace context."""

from __future__ import annotations

import json
import time

from core.trace import TraceContext


def test_trace_context_when_finish_then_to_dict_contains_elapsed_and_trace_type() -> None:
    trace = TraceContext(trace_type="query")
    trace.record_stage("dense_retrieval", {"elapsed_ms": 12.5})
    time.sleep(0.001)
    trace.finish()

    payload = trace.to_dict()

    assert payload["trace_type"] == "query"
    assert payload["finished_at"] is not None
    assert payload["total_elapsed_ms"] >= 0
    assert payload["stages"][0]["name"] == "dense_retrieval"
    json.dumps(payload)


def test_trace_context_when_elapsed_ms_requested_for_stage_then_return_metadata_value() -> None:
    trace = TraceContext(trace_type="ingestion")
    trace.record_stage("load", {"elapsed_ms": 5.25})

    assert trace.elapsed_ms("load") == 5.25
