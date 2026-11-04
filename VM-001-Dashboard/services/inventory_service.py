from __future__ import annotations

from datetime import datetime
from typing import Any

from pymongo import ReturnDocument

from config import MACHINE_ID
from database import get_collection, safe_id
from utils.calculations import safe_float, stock_status


def get_products() -> list[dict[str, Any]]:
    collection = get_collection("products")
    if collection is None:
        return []
    try:
        return [safe_id(item) for item in collection.find({"machine_id": MACHINE_ID}).sort("product_name", 1)]
    except Exception:
        return []


def add_product(product_id: str, product_name: str, category: str, price: float, max_capacity: int, reorder_level: int) -> tuple[bool, str]:
    values = [product_id.strip(), product_name.strip(), category.strip()]
    if not all(values) or price < 0 or max_capacity < 1 or reorder_level < 0:
        return False, "Enter valid product details."
    collection = get_collection("products")
    if collection is None:
        return False, "MongoDB is not connected."
    if collection.find_one({"machine_id": MACHINE_ID, "product_id": product_id.strip()}):
        return False, "That product ID already exists for this machine."
    collection.insert_one({"product_id": product_id.strip(), "machine_id": MACHINE_ID, "product_name": product_name.strip(), "category": category.strip(), "price": float(price), "current_stock": 0, "max_capacity": int(max_capacity), "reorder_level": int(reorder_level), "status": "OUT OF STOCK", "updated_at": datetime.utcnow()})
    return True, "Product added."


def update_product(product_id: str, fields: dict[str, Any]) -> tuple[bool, str]:
    collection = get_collection("products")
    if collection is None:
        return False, "MongoDB is not connected."
    allowed = {key: fields[key] for key in ("product_name", "category", "price", "max_capacity", "reorder_level") if key in fields}
    if not allowed:
        return False, "No editable fields were provided."
    if safe_float(allowed.get("price", 0)) < 0 or int(allowed.get("max_capacity", 1)) < 1:
        return False, "Price and capacity must be valid positive values."
    allowed["updated_at"] = datetime.utcnow()
    collection.update_one({"machine_id": MACHINE_ID, "product_id": product_id}, {"$set": allowed})
    return True, "Product updated."


def delete_product(product_id: str) -> tuple[bool, str]:
    collection = get_collection("products")
    if collection is None:
        return False, "MongoDB is not connected."
    result = collection.delete_one({"machine_id": MACHINE_ID, "product_id": product_id})
    return (True, "Product deleted.") if result.deleted_count else (False, "Product was not found.")


def update_stock(product_id: str, new_stock: int, reason: str = "MANUAL_ADJUSTMENT") -> tuple[bool, str]:
    products = get_collection("products")
    logs = get_collection("stock_logs")
    if products is None or logs is None:
        return False, "MongoDB is not connected."
    product = products.find_one({"machine_id": MACHINE_ID, "product_id": product_id})
    if not product:
        return False, "Product was not found."
    maximum = int(safe_float(product.get("max_capacity")))
    if new_stock < 0 or new_stock > maximum:
        return False, f"Stock must be between 0 and {maximum}."
    previous = int(safe_float(product.get("current_stock")))
    products.update_one({"_id": product["_id"]}, {"$set": {"current_stock": new_stock, "status": stock_status(new_stock, safe_float(product.get("reorder_level"))), "updated_at": datetime.utcnow()}})
    logs.insert_one({"machine_id": MACHINE_ID, "product_id": product_id, "previous_stock": previous, "new_stock": new_stock, "change": new_stock - previous, "reason": reason, "timestamp": datetime.utcnow()})
    return True, "Stock updated and logged."
