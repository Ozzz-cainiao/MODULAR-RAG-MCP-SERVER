"""Overview dashboard page."""

from __future__ import annotations

from observability.dashboard.services.config_service import ConfigService
from observability.dashboard.streamlit_compat import get_streamlit


def render(config_service: ConfigService | None = None) -> None:
    st = get_streamlit()
    service = config_service or ConfigService()
    summary = service.summary()
    st.title("System Overview")
    st.write("当前系统配置概览")
    st.json(summary)
