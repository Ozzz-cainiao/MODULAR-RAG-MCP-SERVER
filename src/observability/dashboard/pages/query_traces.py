"""Query trace dashboard page."""

from __future__ import annotations

from observability.dashboard.services.trace_service import TraceService
from observability.dashboard.streamlit_compat import get_streamlit


def render(trace_service: TraceService) -> None:
    st = get_streamlit()
    st.title("Query Traces")
    traces = trace_service.list_traces(trace_type="query")
    st.write({"trace_count": len(traces)})
    for trace in traces[:20]:
        st.write(trace)
