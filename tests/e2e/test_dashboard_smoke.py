"""Dashboard smoke tests with a fake Streamlit module."""

from __future__ import annotations

from types import ModuleType
import sys


class _Sidebar:
    def title(self, text):  # noqa: ANN001
        return None

    def radio(self, label, options):  # noqa: ANN001
        return options[0]


class FakeStreamlit(ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.sidebar = _Sidebar()

    def title(self, text):  # noqa: ANN001
        return None

    def write(self, value):  # noqa: ANN001
        return None

    def json(self, value):  # noqa: ANN001
        return None


def test_dashboard_smoke_when_render_app_then_no_exception(monkeypatch) -> None:
    fake_streamlit = FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)

    from observability.dashboard.app import render_app

    render_app()


def test_dashboard_pages_when_rendered_individually_then_no_exception(monkeypatch) -> None:
    fake_streamlit = FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)

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

    settings = load_settings("config/settings.yaml")
    data_service = DataService(settings)
    trace_service = TraceService()
    overview.render(ConfigService())
    data_browser.render(data_service)
    ingestion_manager.render(data_service)
    ingestion_traces.render(trace_service)
    query_traces.render(trace_service)
    evaluation_panel.render()
