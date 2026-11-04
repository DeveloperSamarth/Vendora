from __future__ import annotations

import pandas as pd
import streamlit as st

from components.header import render_header
from config import MACHINE_ID
from database import get_collection
from services.inventory_service import get_products
from services.sales_service import get_sales

render_header("Machine management", "Review database-reported machine metadata")
collection = get_collection("machines")
record = collection.find_one({"machine_id": MACHINE_ID}) if collection is not None else None
products = get_products()
sales = get_sales()
if not record:
    st.info("No machine record is available in MongoDB. This page does not control physical hardware.")
else:
    st.caption("Database-reported status. No ESP8266 controller API is connected to this dashboard.")
    st.dataframe(pd.DataFrame([{"Machine ID": record.get("machine_id", MACHINE_ID), "Machine name": record.get("machine_name", "Not recorded"), "Location": record.get("location", "Not recorded"), "Connectivity": record.get("connectivity", "Not recorded"), "Lock status": record.get("status", "Not recorded"), "Last heartbeat": record.get("last_heartbeat", "Not recorded"), "Total products": len(products), "Total sales": len(sales)}]), use_container_width=True, hide_index=True)
    st.subheader("Edit basic metadata")
    with st.form("machine_metadata"):
        name = st.text_input("Machine name", value=str(record.get("machine_name", "")))
        location = st.text_input("Location", value=str(record.get("location", "")))
        if st.form_submit_button("Save metadata"):
            if collection is None: st.error("MongoDB is not connected.")
            else:
                collection.update_one({"_id": record["_id"]}, {"$set": {"machine_name": name.strip(), "location": location.strip()}})
                st.success("Machine metadata updated.")
                st.rerun()
