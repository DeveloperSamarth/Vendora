from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MACHINE_ID = "VM-001"
MACHINE_NAME = "Campus Smart Vending Machine"
MACHINE_LOCATION = "VESIT Campus, Mumbai, India"
DEFAULT_DATABASE_NAME = "VendingMachineDB"
PROJECT_ROOT = Path(__file__).parent


def get_setting(name: str, default: str = "") -> str:
    """Read Streamlit secrets first, then local environment variables."""
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


MONGO_URI = get_setting("MONGO_URI")
DATABASE_NAME = get_setting("DATABASE_NAME", DEFAULT_DATABASE_NAME)
