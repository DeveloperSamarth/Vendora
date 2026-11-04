from __future__ import annotations

from datetime import datetime
from typing import Any

from config import MACHINE_ID
from database import get_collection, safe_id


def get_alerts() -> list[dict[str, Any]]:
    collection = get_collection("alerts")
    if collection is None:
        return []
    try:
        return [safe_id(item) for item in collection.find({"machine_id": MACHINE_ID}).sort("created_at", -1)]
    except Exception:
        return []


def resolve_alert(alert_id: str) -> tuple[bool, str]:
    collection = get_collection("alerts")
    if collection is None:
        return False, "MongoDB is not connected."
    from bson import ObjectId
    try:
        query = {"_id": ObjectId(alert_id), "machine_id": MACHINE_ID}
    except Exception:
        return False, "Invalid alert ID."
    result = collection.update_one(query, {"$set": {"status": "RESOLVED", "resolved_at": datetime.utcnow()}})
    return (True, "Alert resolved.") if result.modified_count else (False, "Alert was not found or already resolved.")


def generate_inventory_alerts() -> int:
    """Create only newly observed out-of-stock or low-stock alerts."""
    products = get_collection("products")
    alerts = get_collection("alerts")
    if products is None or alerts is None:
        return 0
    created = 0
    for product in products.find({"machine_id": MACHINE_ID}):
        stock = float(product.get("current_stock", 0) or 0)
        reorder = float(product.get("reorder_level", 0) or 0)
        if stock <= 0:
            alert_type, severity, message = "OUT_OF_STOCK", "CRITICAL", f"{product.get('product_name', product.get('product_id'))} is out of stock."
        elif stock <= reorder:
            alert_type, severity, message = "LOW_STOCK", "WARNING", f"{product.get('product_name', product.get('product_id'))} stock is running low."
        else:
            continue
        existing = alerts.find_one({"machine_id": MACHINE_ID, "product_id": product.get("product_id"), "alert_type": alert_type, "status": "ACTIVE"})
        if not existing:
            alerts.insert_one({"machine_id": MACHINE_ID, "product_id": product.get("product_id"), "alert_type": alert_type, "message": message, "severity": severity, "status": "ACTIVE", "created_at": datetime.utcnow()})
            created += 1
    return created
