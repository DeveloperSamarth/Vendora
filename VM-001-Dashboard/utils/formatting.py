from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


def format_inr(value: Any) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0.0
    return f"₹{amount:,.2f}"


def format_number(value: Any) -> str:
    try:
        return f"{float(value or 0):,.0f}"
    except (TypeError, ValueError):
        return "0"


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if value is None or value == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime().replace(tzinfo=None)


def display_datetime(value: Any) -> str:
    parsed = parse_datetime(value)
    return parsed.strftime("%d %b %Y, %I:%M %p") if parsed else "Not recorded"
