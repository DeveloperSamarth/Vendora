from __future__ import annotations

import streamlit as st

from components.sidebar import render_sidebar
from database import database_status

st.set_page_config(page_title="VM-001 Smart Vending", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --ink:#e7edf7; --muted:#8d9bb2; --panel:#111b2b; --line:#20304a; --blue:#4d9fff; --mint:#31d39b; }
.stApp { background: radial-gradient(circle at 90% 0%, #172b4c 0, #0b1321 38%, #080e18 100%); color:var(--ink); font-family:'DM Sans', sans-serif; }
h1,h2,h3 { font-family:'Space Grotesk', sans-serif; color:var(--ink); } h1 { font-size:2rem; margin:.1rem 0; } h2 { font-size:1.35rem; }
[data-testid='stSidebar'] { background:#09111f; border-right:1px solid var(--line); } [data-testid='stSidebar'] hr { border-color:var(--line); }
.brand-mark { font:700 1.7rem 'Space Grotesk'; color:var(--blue); } .brand-mark span { color:var(--ink); } .brand-caption,.eyebrow { color:var(--muted); font-size:.68rem; letter-spacing:.14em; font-weight:700; }
.sidebar-footer { color:var(--muted); font-size:.7rem; line-height:1.7; margin-top:3rem; } .sidebar-footer b { color:var(--ink); font-weight:500; }
.topbar { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; padding:.4rem 0 1.5rem; } .topbar p { color:var(--muted); margin:0; } .machine-pill { border:1px solid var(--line); border-radius:12px; padding:.65rem .85rem; font-weight:700; white-space:nowrap; } .machine-pill small { display:block; color:var(--muted); font-weight:400; margin-top:.25rem; }
.metric-card { background:linear-gradient(145deg,#14233a,#101a2b); border:1px solid var(--line); border-radius:14px; padding:1rem; min-height:108px; } .metric-label,.metric-detail { color:var(--muted); font-size:.78rem; } .metric-value { font:700 1.65rem 'Space Grotesk'; margin:.5rem 0; }
[data-testid='stDataFrame'], .stPlotlyChart { border:1px solid var(--line); border-radius:12px; overflow:hidden; } .stButton button { border-radius:9px; border:1px solid #2b4d79; } .stTabs [data-baseweb='tab-list'] { gap:1.2rem; } .stTabs [aria-selected='true'] { color:var(--blue); }
</style>
""", unsafe_allow_html=True)

connected, message = database_status()
st.session_state["db_connected"] = connected
render_sidebar()

if not connected:
    st.warning(message)

st.title("VM-001 Smart Vending Machine")
st.markdown("Use the page selector in the sidebar to open the Stage 1 dashboard modules.")
st.info("Stage 1 is connected to real MongoDB records only. Prediction analytics will be added in Stage 2 after the next command.")
