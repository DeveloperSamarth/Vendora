from __future__ import annotations

from datetime import datetime, time, timedelta

import pandas as pd
import streamlit as st

from components.charts import render_daily_chart, render_product_chart
from components.header import render_header
from components.metric_cards import render_metrics
from services.sales_service import get_daily_sales, get_hourly_sales, get_product_sales, get_sales, get_sales_summary
from utils.formatting import format_inr, format_number

render_header("Sales analytics", "Explore actual successful transactions stored in MongoDB")
period = st.radio("Date range", ["Today", "Last 7 days", "Last 30 days", "Custom"], horizontal=True)
today = datetime.utcnow().date()
if period == "Today": start_date = today
elif period == "Last 7 days": start_date = today - timedelta(days=6)
elif period == "Last 30 days": start_date = today - timedelta(days=29)
else:
    start_date = st.date_input("Start date", today - timedelta(days=6))
end_date = st.date_input("End date", today) if period == "Custom" else today
sales = get_sales(datetime.combine(start_date, time.min), datetime.combine(end_date + timedelta(days=1), time.min))
summary = get_sales_summary(sales)
render_metrics([("REVENUE", format_inr(summary["revenue"]), period), ("UNITS SOLD", format_number(summary["units"]), "Successful payments"), ("AVG TRANSACTION", format_inr(summary["average"]), "Per successful sale"), ("TRANSACTIONS", format_number(summary["transactions"]), "Recorded")])
left, right = st.columns(2)
with left: render_product_chart(get_product_sales(sales), "revenue", "Revenue by product")
with right: render_daily_chart(get_daily_sales(sales))
st.subheader("Hourly sales")
hourly = get_hourly_sales(sales)
if hourly.empty: st.info("No timestamped sales records are available for this range.")
else: st.bar_chart(hourly.set_index("hour"), y="units")
st.subheader("Transactions")
if sales:
    frame = pd.DataFrame(sales)
    columns = [column for column in ["transaction_id", "product_name", "quantity", "unit_price", "total_amount", "payment_status", "timestamp"] if column in frame]
    st.dataframe(frame[columns], use_container_width=True, hide_index=True)
else: st.info("No sales records match the selected date range.")
