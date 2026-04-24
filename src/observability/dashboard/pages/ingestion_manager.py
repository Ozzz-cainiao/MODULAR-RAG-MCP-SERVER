"""Ingestion manager dashboard page."""

from __future__ import annotations

from observability.dashboard.services.data_service import DataService
from observability.dashboard.streamlit_compat import get_streamlit


def render(data_service: DataService) -> None:
    st = get_streamlit()
    st.title("Ingestion Manager")
    st.write("可在此页面查看文档列表并为后续接入上传/删除操作。")
    st.write({"document_count": len(data_service.list_documents())})
