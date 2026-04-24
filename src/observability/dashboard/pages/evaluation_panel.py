"""Evaluation dashboard page."""

from __future__ import annotations

from observability.dashboard.streamlit_compat import get_streamlit


def render() -> None:
    st = get_streamlit()
    st.title("Evaluation Panel")
    st.write("在此页面运行 golden set 评估并查看指标。")
