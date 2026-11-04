from __future__ import annotations


def stock_status(current_stock: float, reorder_level: float) -> str:
    if current_stock <= 0:
        return "OUT OF STOCK"
    if current_stock <= reorder_level:
        return "LOW STOCK"
    return "HEALTHY"


def safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def average_transaction_value(revenue: float, transactions: int) -> float:
    return revenue / transactions if transactions else 0.0
