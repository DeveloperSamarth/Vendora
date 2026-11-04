from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st


CHART_TEMPLATE = "plotly_dark"


def empty_chart(message: str = "No records available for this period.") -> None:
    st.info(message)


def render_product_chart(data: pd.DataFrame, value: str = "revenue", title: str = "Sales by product") -> None:
    if data.empty:
        empty_chart()
        return
    figure = px.bar(data, x="product", y=value, title=title, template=CHART_TEMPLATE, color_discrete_sequence=["#4d9fff"])
    figure.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=300)
    st.plotly_chart(figure, use_container_width=True)


def render_daily_chart(data: pd.DataFrame) -> None:
    if data.empty:
        empty_chart()
        return
    figure = px.line(data, x="date", y="revenue", title="Daily revenue", template=CHART_TEMPLATE, markers=True, color_discrete_sequence=["#31d39b"])
    figure.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=300)
    st.plotly_chart(figure, use_container_width=True)
