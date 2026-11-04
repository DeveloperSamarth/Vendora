from __future__ import annotations

import pandas as pd
import streamlit as st

from components.header import render_header
from services.inventory_service import get_products
from services.refill_service import get_refill_history, process_refill
from utils.formatting import display_datetime

render_header("Refill management", "Record validated replenishment operations")
products = get_products()
with st.form("refill_form"):
    if products:
        product_ids = [item["product_id"] for item in products]
        product_id = st.selectbox("Product", product_ids, format_func=lambda value: next((f"{item.get('product_name', value)} ({value})" for item in products if item["product_id"] == value), value))
        quantity = st.number_input("Quantity added", min_value=1, step=1)
        staff = st.text_input("Staff name")
        submitted = st.form_submit_button("Confirm refill")
        if submitted:
            ok, message = process_refill(product_id, quantity, staff)
            (st.success if ok else st.error)(message)
            if ok: st.rerun()
    else:
        st.info("Add a product before recording a refill.")
        st.form_submit_button("Confirm refill", disabled=True)

st.subheader("Refill history")
history = get_refill_history()
if history:
    frame = pd.DataFrame([{**item, "timestamp": display_datetime(item.get("timestamp"))} for item in history])
    columns = [column for column in ["product_name", "previous_stock", "quantity_added", "new_stock", "staff_name", "timestamp"] if column in frame]
    st.dataframe(frame[columns], use_container_width=True, hide_index=True)
else: st.info("No refill records are available.")
