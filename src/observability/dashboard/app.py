"""Streamlit multi-page dashboard entrypoint."""

from __future__ import annotations

from core.settings import load_settings
from observability.dashboard.pages import (
    data_browser,
    evaluation_panel,
    ingestion_manager,
    ingestion_traces,
    overview,
    query_traces,
)
from observability.dashboard.services.config_service import ConfigService
from observability.dashboard.services.data_service import DataService
from observability.dashboard.services.trace_service import TraceService
from observability.dashboard.streamlit_compat import get_streamlit


def render_app() -> None:
    st = get_streamlit()
    settings = load_settings("config/settings.yaml")
    config_service = ConfigService()
    data_service = DataService(settings)
    trace_service = TraceService()

    pages = {
        "Overview": lambda: overview.render(config_service=config_service),
        "Data Browser": lambda: data_browser.render(data_service=data_service),
        "Ingestion Manager": lambda: ingestion_manager.render(data_service=data_service),
        "Ingestion Traces": lambda: ingestion_traces.render(trace_service=trace_service),
        "Query Traces": lambda: query_traces.render(trace_service=trace_service),
        "Evaluation Panel": evaluation_panel.render,
    }

    st.sidebar.title("Modular RAG Dashboard")
    selected = st.sidebar.radio("Pages", list(pages.keys()))
    pages[selected]()


def main() -> None:
    render_app()


if __name__ == "__main__":
    main()
