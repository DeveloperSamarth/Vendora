from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from components.header import render_header
from components.metric_cards import render_metrics
from services.inventory_service import get_products
from services.prediction_service import build_prediction_rows, get_predictions
from services.sales_service import get_sales
from utils.formatting import format_number, parse_datetime

render_header("AI predictions", "Explainable replenishment guidance from stored model output or sales history")
lead_time = st.number_input("Refill lead time (hours)", min_value=1, max_value=720, value=24, step=1)
history_days = st.select_slider("Historical sales window", options=[7, 14, 30, 60, 90], value=30, format_func=lambda value: f"{value} days")
now = datetime.utcnow()
window_start = now - timedelta(days=history_days)
window_end = now + timedelta(hours=1)
# Filter parsed timestamps here so both BSON datetimes and ISO strings are supported.
sales = [sale for sale in get_sales() if (timestamp := parse_datetime(sale.get("timestamp"))) and window_start <= timestamp <= window_end]
products = get_products()
predictions = get_predictions()
rows = build_prediction_rows(products, sales, predictions, history_days * 24, float(lead_time))

if not products:
    st.info("No products are available for replenishment analysis.")
elif not sales and not predictions:
    st.warning("Insufficient sales history for a reliable prediction. Add sales records or validated prediction documents.")

critical = sum(row["refill_priority"] == "CRITICAL" for row in rows)
recommended = sum(row["recommended_refill_quantity"] > 0 for row in rows)
ml_count = sum(row["prediction_source"] == "ML Model Prediction" for row in rows)
render_metrics([("PRODUCTS ANALYZED", format_number(len(rows)), f"{history_days}-day window"), ("CRITICAL PRIORITY", format_number(critical), "Before lead time"), ("REFILLS RECOMMENDED", format_number(recommended), "Positive quantity"), ("VALID ML OUTPUT", format_number(ml_count), "Stored in MongoDB")])

if rows:
    frame = pd.DataFrame(rows)
    left, right = st.columns(2)
    with left:
        demand = frame[["product_name", "predicted_demand"]]
        figure = px.bar(demand, x="product_name", y="predicted_demand", title="Demand during lead time", template="plotly_dark", color_discrete_sequence=["#4d9fff"])
        figure.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=320)
        st.plotly_chart(figure, use_container_width=True)
    with right:
        risk = frame[frame["estimated_stockout_hours"].notna()][["product_name", "estimated_stockout_hours"]]
        if risk.empty:
            st.info("Stockout risk is unavailable until a product has sales history.")
        else:
            figure = px.bar(risk, x="product_name", y="estimated_stockout_hours", title="Estimated hours until stockout", template="plotly_dark", color_discrete_sequence=["#f08b7d"])
            figure.update_layout(margin=dict(l=0, r=0, t=40, b=0), height=320)
            st.plotly_chart(figure, use_container_width=True)

    st.subheader("Refill priority table")
    display = frame.copy()
    display["average_sales_per_hour"] = display["average_sales_per_hour"].round(2)
    display["predicted_demand"] = display["predicted_demand"].round(2)
    display["estimated_stockout_hours"] = display["estimated_stockout_hours"].round(2)
    columns = ["product_id", "product_name", "current_stock", "average_sales_per_hour", "predicted_demand", "estimated_stockout_hours", "recommended_refill_quantity", "refill_priority", "prediction_source", "prediction_method"]
    st.dataframe(display[columns], use_container_width=True, hide_index=True)
    st.caption("Statistical estimates use actual successful sales in the selected window. Products without sales history are labeled Insufficient Data and are not presented as reliable forecasts.")
