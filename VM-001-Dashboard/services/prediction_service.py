from __future__ import annotations

"""Prediction service boundary reserved for Stage 2.

Stage 1 intentionally does not display invented forecasts. Existing prediction documents
can be read later without claiming they are model output until validation is added.
"""

import math
from datetime import datetime
from typing import Any, Iterable

from config import MACHINE_ID
from database import get_collection, safe_id
from utils.calculations import safe_float
from utils.formatting import parse_datetime


def get_predictions() -> list[dict[str, Any]]:
    collection = get_collection("predictions")
    if collection is None:
        return []
    try:
        return [safe_id(item) for item in collection.find({"machine_id": MACHINE_ID})]
    except Exception:
        return []


def _finite_number(value: Any, minimum: float = 0.0) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= minimum else None


def _valid_prediction(document: dict[str, Any]) -> bool:
    return bool(document.get("product_id")) and _finite_number(document.get("predicted_demand")) is not None


def _latest_predictions(predictions: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for prediction in predictions:
        if not _valid_prediction(prediction):
            continue
        product_id = str(prediction["product_id"])
        timestamp = parse_datetime(prediction.get("generated_at")) or datetime.min
        previous_timestamp = parse_datetime(latest.get(product_id, {}).get("generated_at")) or datetime.min
        if product_id not in latest or timestamp >= previous_timestamp:
            latest[product_id] = prediction
    return latest


def calculate_sales_velocity(sales: Iterable[dict[str, Any]], product_id: str, historical_hours: float) -> float:
    if historical_hours <= 0:
        return 0.0
    units = sum(
        safe_float(sale.get("quantity"))
        for sale in sales
        if str(sale.get("product_id", "")) == product_id
        and str(sale.get("payment_status", "SUCCESS")).upper() == "SUCCESS"
    )
    return units / historical_hours


def calculate_stockout_time(current_stock: float, sales_velocity: float) -> float | None:
    if current_stock <= 0:
        return 0.0
    return current_stock / sales_velocity if sales_velocity > 0 else None


def calculate_refill_quantity(current_stock: float, sales_velocity: float, lead_time_hours: float, safety_stock: float, max_capacity: float) -> int:
    target_stock = min(max_capacity, max(0.0, sales_velocity * lead_time_hours + safety_stock))
    return max(0, math.ceil(target_stock - current_stock))


def calculate_refill_priority(current_stock: float, reorder_level: float, stockout_hours: float | None, lead_time_hours: float, has_history: bool = True) -> str:
    if not has_history:
        return "INSUFFICIENT DATA"
    if current_stock <= 0 or (stockout_hours is not None and stockout_hours <= lead_time_hours):
        return "CRITICAL"
    if stockout_hours is not None and stockout_hours <= lead_time_hours * 2:
        return "HIGH"
    if current_stock <= reorder_level:
        return "MEDIUM"
    return "LOW"


def build_prediction_rows(
    products: Iterable[dict[str, Any]],
    sales: Iterable[dict[str, Any]],
    predictions: Iterable[dict[str, Any]],
    historical_hours: float,
    lead_time_hours: float = 24.0,
) -> list[dict[str, Any]]:
    """Build explainable replenishment rows from records already loaded by the caller."""
    sales_list = list(sales)
    model_predictions = _latest_predictions(predictions)
    rows: list[dict[str, Any]] = []
    for product in products:
        product_id = str(product.get("product_id", ""))
        current_stock = safe_float(product.get("current_stock"))
        reorder_level = safe_float(product.get("reorder_level"))
        max_capacity = safe_float(product.get("max_capacity"))
        velocity = calculate_sales_velocity(sales_list, product_id, historical_hours)
        stockout_hours = calculate_stockout_time(current_stock, velocity)
        model = model_predictions.get(product_id)
        if model:
            predicted_demand = _finite_number(model.get("predicted_demand")) or 0.0
            model_refill = _finite_number(model.get("recommended_refill_quantity"))
            refill_quantity = math.ceil(model_refill) if model_refill is not None else calculate_refill_quantity(current_stock, velocity, lead_time_hours, max(reorder_level, math.ceil(predicted_demand * 0.25)), max_capacity)
            source = "ML Model Prediction"
            method = str(model.get("prediction_method") or "Stored model output")
        else:
            predicted_demand = velocity * lead_time_hours
            safety_stock = max(reorder_level, math.ceil(predicted_demand * 0.25))
            refill_quantity = calculate_refill_quantity(current_stock, velocity, lead_time_hours, safety_stock, max_capacity)
            source = "Statistical Estimate — Not ML Forecast"
            method = "Historical sales velocity"
        has_history = velocity > 0 or any(str(sale.get("product_id", "")) == product_id for sale in sales_list)
        rows.append({
            "product_id": product_id,
            "product_name": product.get("product_name") or product_id,
            "current_stock": current_stock,
            "average_sales_per_hour": velocity,
            "predicted_demand": predicted_demand,
            "estimated_stockout_hours": stockout_hours,
            "recommended_refill_quantity": refill_quantity,
            "refill_priority": calculate_refill_priority(current_stock, reorder_level, stockout_hours, lead_time_hours, has_history),
            "prediction_source": source,
            "prediction_method": method,
            "has_history": has_history,
        })
    return sorted(rows, key=lambda row: (row["refill_priority"] == "INSUFFICIENT DATA", ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(row["refill_priority"]) if row["refill_priority"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} else 99))
