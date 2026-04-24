"""Utilities for optional Streamlit imports."""

from __future__ import annotations


def get_streamlit():
    try:
        import streamlit as st  # type: ignore
    except ImportError as error:
        raise ImportError("Dashboard 运行需要安装 streamlit") from error
    return st
