from __future__ import annotations

from datetime import datetime
from typing import Any

from config import MACHINE_ID
from database import get_collection, safe_id
from utils.calculations import safe_float, stock_status


def get_refill_history() -> list[dict[str, Any]]:
    collection = get_collection("refill_logs")
    if collection is None:
        return []
    try:
        return [safe_id(item) for item in collection.find({"machine_id": MACHINE_ID}).sort("timestamp", -1)]
    except Exception:
        return []


def process_refill(product_id: str, quantity: int, staff_name: str) -> tuple[bool, str]:
    products = get_collection("products")
    refills = get_collection("refill_logs")
    stock_logs = get_collection("stock_logs")
    if products is None or refills is None or stock_logs is None:
        return False, "MongoDB is not connected."
    if quantity <= 0 or not staff_name.strip():
        return False, "Enter a positive quantity and staff name."
    product = products.find_one({"machine_id": MACHINE_ID, "product_id": product_id})
    if not product:
        return False, "Product was not found."
    previous = int(safe_float(product.get("current_stock")))
    new_stock = previous + quantity
    maximum = int(safe_float(product.get("max_capacity")))
    if new_stock > maximum:
        return False, f"Refill exceeds capacity. Maximum additional units: {maximum - previous}."
    timestamp = datetime.utcnow()
    products.update_one({"_id": product["_id"]}, {"$set": {"current_stock": new_stock, "status": stock_status(new_stock, safe_float(product.get("reorder_level"))), "updated_at": timestamp}})
    refills.insert_one({"machine_id": MACHINE_ID, "product_id": product_id, "product_name": product.get("product_name"), "quantity_added": quantity, "previous_stock": previous, "new_stock": new_stock, "staff_name": staff_name.strip(), "timestamp": timestamp})
    stock_logs.insert_one({"machine_id": MACHINE_ID, "product_id": product_id, "previous_stock": previous, "new_stock": new_stock, "change": quantity, "reason": "REFILL", "timestamp": timestamp})
    return True, "Refill completed and both stock logs were created."
