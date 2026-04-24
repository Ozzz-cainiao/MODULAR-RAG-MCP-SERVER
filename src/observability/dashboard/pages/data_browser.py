"""Data browser dashboard page."""

from __future__ import annotations

from observability.dashboard.services.data_service import DataService
from observability.dashboard.streamlit_compat import get_streamlit


def render(data_service: DataService) -> None:
    st = get_streamlit()
    st.title("Data Browser")
    documents = data_service.list_documents()
    st.write(f"Documents: {len(documents)}")
    for document in documents:
        st.write(
            {
                "source_path": document.source_path,
                "collection": document.collection,
                "chunk_count": document.chunk_count,
                "image_count": document.image_count,
            }
        )
