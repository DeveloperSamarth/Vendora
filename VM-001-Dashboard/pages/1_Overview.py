from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from components.charts import render_daily_chart, render_product_chart
from components.header import render_header
from components.metric_cards import render_metrics
from config import MACHINE_ID
from database import get_collection
from services.alert_service import get_alerts
from services.inventory_service import get_products
from services.sales_service import get_product_sales, get_sales, get_sales_summary
from utils.formatting import format_inr, format_number

render_header("Operations overview", "A live view of sales, stock, and machine health")
now = datetime.utcnow()
sales = get_sales(now.replace(hour=0, minute=0, second=0, microsecond=0), now + timedelta(days=1))
products = get_products()
alerts = get_alerts()
summary = get_sales_summary(sales)
critical = sum(1 for alert in alerts if str(alert.get("severity", "")).upper() == "CRITICAL" and str(alert.get("status", "ACTIVE")).upper() == "ACTIVE")
low_stock = sum(1 for product in products if float(product.get("current_stock", 0) or 0) <= float(product.get("reorder_level", 0) or 0))
render_metrics([("REVENUE TODAY", format_inr(summary["revenue"]), "Successful sales"), ("UNITS SOLD", format_number(summary["units"]), "Today"), ("TOTAL PRODUCTS", format_number(len(products)), "Registered in VM-001"), ("LOW STOCK", format_number(low_stock), "Needs attention"), ("CRITICAL ALERTS", format_number(critical), "Active")])

left, right = st.columns([1.5, 1])
with left:
    st.subheader("Sales by product")
    render_product_chart(get_product_sales(sales))
with right:
    st.subheader("Critical alerts")
    critical_alerts = [item for item in alerts if str(item.get("severity", "")).upper() == "CRITICAL" and str(item.get("status", "ACTIVE")).upper() == "ACTIVE"]
    if critical_alerts:
        for alert in critical_alerts[:5]:
            st.error(alert.get("message", "Critical alert"))
    else:
        st.success("No active critical alerts.")

st.subheader("Recent transactions")
if sales:
    table = pd.DataFrame(sales[:10])
    columns = [column for column in ["transaction_id", "product_name", "quantity", "total_amount", "payment_status", "timestamp"] if column in table]
    st.dataframe(table[columns], use_container_width=True, hide_index=True)
else:
    st.info("No sales records are available for today.")

machine = get_collection("machines")
record = machine.find_one({"machine_id": MACHINE_ID}) if machine is not None else None
st.subheader("Machine information")
if record:
    st.dataframe(pd.DataFrame([{"Machine": record.get("machine_name", MACHINE_ID), "Location": record.get("location", "Not recorded"), "Connectivity": record.get("connectivity", "Not recorded"), "Lock status": record.get("status", "Not recorded")}]), use_container_width=True, hide_index=True)
else:
    st.info("No machine record is available in MongoDB.")
