from __future__ import annotations

import streamlit as st

from config import MACHINE_ID, MACHINE_NAME


def render_header(title: str, subtitle: str = "") -> None:
    connected = st.session_state.get("db_connected", False)
    status = "ONLINE" if connected else "OFFLINE"
    color = "#31d39b" if connected else "#f08b7d"
    st.markdown(f"<div class='topbar'><div><div class='eyebrow'>{MACHINE_ID} SMART VENDING INTELLIGENCE</div><h1>{title}</h1><p>{subtitle or 'Predictive inventory and sales management system'}</p></div><div class='machine-pill'><span style='color:{color}'>●</span> {status}<small>{MACHINE_NAME}</small></div></div>", unsafe_allow_html=True)
