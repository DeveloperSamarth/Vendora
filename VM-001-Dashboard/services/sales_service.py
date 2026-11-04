from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from config import MACHINE_ID
from database import get_collection, safe_id
from utils.calculations import safe_float
from utils.formatting import parse_datetime


def get_sales(start: datetime | None = None, end: datetime | None = None) -> list[dict[str, Any]]:
    collection = get_collection("sales")
    if collection is None:
        return []
    query: dict[str, Any] = {"machine_id": MACHINE_ID}
    if start or end:
        query["timestamp"] = {}
        if start:
            query["timestamp"]["$gte"] = start
        if end:
            query["timestamp"]["$lt"] = end
    try:
        records = [safe_id(item) for item in collection.find(query).sort("timestamp", -1)]
        normalized = []
        for record in records:
            timestamp = parse_datetime(record.get("timestamp"))
            record["timestamp"] = timestamp
            record["quantity"] = safe_float(record.get("quantity"))
            record["total_amount"] = safe_float(record.get("total_amount"), safe_float(record.get("unit_price")) * record["quantity"])
            normalized.append(record)
        return normalized
    except Exception:
        return []


def get_sales_summary(sales: list[dict[str, Any]]) -> dict[str, Any]:
    successful = [item for item in sales if str(item.get("payment_status", "SUCCESS")).upper() == "SUCCESS"]
    revenue = sum(safe_float(item.get("total_amount")) for item in successful)
    units = sum(safe_float(item.get("quantity")) for item in successful)
    return {"revenue": revenue, "units": units, "transactions": len(successful), "average": revenue / len(successful) if successful else 0.0}


def get_daily_sales(sales: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [{"date": item["timestamp"].date(), "revenue": item["total_amount"]} for item in sales if item.get("timestamp")]
    return pd.DataFrame(rows).groupby("date", as_index=False)["revenue"].sum() if rows else pd.DataFrame(columns=["date", "revenue"])


def get_product_sales(sales: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [{"product": item.get("product_name") or item.get("product_id", "Unknown"), "revenue": item["total_amount"], "units": item["quantity"]} for item in sales]
    return pd.DataFrame(rows).groupby("product", as_index=False).sum(numeric_only=True) if rows else pd.DataFrame(columns=["product", "revenue", "units"])


def get_hourly_sales(sales: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [{"hour": item["timestamp"].hour, "units": item["quantity"]} for item in sales if item.get("timestamp")]
    return pd.DataFrame(rows).groupby("hour", as_index=False)["units"].sum() if rows else pd.DataFrame(columns=["hour", "units"])
