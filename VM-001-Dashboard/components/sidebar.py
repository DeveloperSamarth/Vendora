from __future__ import annotations

import streamlit as st

from config import MACHINE_ID


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("<div class='brand-mark'>VM<span>-001</span></div><div class='brand-caption'>SMART VENDING<br>INTELLIGENCE</div>", unsafe_allow_html=True)
        st.markdown("---")
        st.caption(f"Machine {MACHINE_ID}")
        st.info("Use the page navigation above to manage inventory, sales, alerts, refills, and machine records.")
        st.markdown("<div class='sidebar-footer'>DATABASE-REPORTED STATUS<br><b>Atlas connection is read from Secrets</b></div>", unsafe_allow_html=True)
