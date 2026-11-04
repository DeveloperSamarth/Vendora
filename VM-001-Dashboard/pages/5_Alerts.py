from __future__ import annotations

import pandas as pd
import streamlit as st

from components.header import render_header
from services.alert_service import generate_inventory_alerts, get_alerts, resolve_alert
from utils.formatting import display_datetime

render_header("Alerts", "Monitor actionable inventory and machine events")
if st.button("Refresh inventory alerts"):
    created = generate_inventory_alerts()
    st.success(f"Created {created} new alert(s).")
alerts = get_alerts()
severity = st.selectbox("Severity", ["All", "CRITICAL", "WARNING", "INFO"])
status = st.selectbox("Status", ["All", "ACTIVE", "RESOLVED"])
filtered = [item for item in alerts if (severity == "All" or str(item.get("severity", "")).upper() == severity) and (status == "All" or str(item.get("status", "")).upper() == status)]
if filtered:
    frame = pd.DataFrame([{**item, "created_at": display_datetime(item.get("created_at"))} for item in filtered])
    columns = [column for column in ["_id", "severity", "alert_type", "message", "status", "created_at"] if column in frame]
    st.dataframe(frame[columns], use_container_width=True, hide_index=True)
    active = [item for item in filtered if str(item.get("status", "")).upper() == "ACTIVE"]
    if active:
        selected = st.selectbox("Active alert to resolve", range(len(active)), format_func=lambda index: active[index].get("message", "Alert"))
        if st.button("Mark resolved"):
            ok, message = resolve_alert(active[selected].get("_id", ""))
            (st.success if ok else st.error)(message)
            if ok: st.rerun()
else:
    st.info("No alerts match the selected filters.")
