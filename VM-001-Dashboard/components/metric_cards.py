from __future__ import annotations

from typing import Any

import streamlit as st


def render_metrics(metrics: list[tuple[str, Any, str]]) -> None:
    columns = st.columns(len(metrics))
    for column, (label, value, detail) in zip(columns, metrics):
        with column:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-detail'>{detail}</div></div>", unsafe_allow_html=True)
