from __future__ import annotations

import pandas as pd
import streamlit as st

from components.header import render_header
from services.inventory_service import add_product, delete_product, get_products, update_product, update_stock
from utils.calculations import stock_status
from utils.formatting import format_inr

render_header("Inventory management", "Maintain product master data and stock levels")
products = get_products()
if not products:
    st.info("No products are available. Add the first product below.")

search = st.text_input("Search products", placeholder="Product name or ID")
categories = sorted({str(item.get("category", "Uncategorized")) for item in products})
category = st.selectbox("Category", ["All"] + categories)
filtered = [item for item in products if (not search or search.lower() in str(item.get("product_name", "")).lower() or search.lower() in str(item.get("product_id", "")).lower()) and (category == "All" or item.get("category") == category)]
if filtered:
    view = pd.DataFrame([{**item, "stock_status": stock_status(float(item.get("current_stock", 0) or 0), float(item.get("reorder_level", 0) or 0)), "price": format_inr(item.get("price"))} for item in filtered])
    columns = [column for column in ["product_id", "product_name", "category", "price", "current_stock", "max_capacity", "reorder_level", "stock_status"] if column in view]
    st.dataframe(view[columns], use_container_width=True, hide_index=True)

with st.expander("Add new product"):
    with st.form("add_product"):
        product_id = st.text_input("Product ID")
        name = st.text_input("Product name")
        category_value = st.text_input("Category")
        price = st.number_input("Price (INR)", min_value=0.0, step=1.0)
        capacity = st.number_input("Maximum capacity", min_value=1, step=1)
        reorder = st.number_input("Reorder level", min_value=0, step=1)
        if st.form_submit_button("Add product"):
            ok, message = add_product(product_id, name, category_value, price, capacity, reorder)
            (st.success if ok else st.error)(message)
            if ok: st.rerun()

if products:
    selected = st.selectbox("Select a product to manage", [item["product_id"] for item in products])
    product = next(item for item in products if item["product_id"] == selected)
    with st.expander("Edit product details"):
        with st.form("edit_product"):
            name = st.text_input("Product name", value=str(product.get("product_name", "")))
            category_value = st.text_input("Category", value=str(product.get("category", "")))
            price = st.number_input("Price (INR)", min_value=0.0, value=float(product.get("price", 0) or 0), step=1.0)
            capacity = st.number_input("Maximum capacity", min_value=1, value=int(product.get("max_capacity", 1) or 1), step=1)
            reorder = st.number_input("Reorder level", min_value=0, value=int(product.get("reorder_level", 0) or 0), step=1)
            if st.form_submit_button("Save changes"):
                ok, message = update_product(selected, {"product_name": name, "category": category_value, "price": price, "max_capacity": capacity, "reorder_level": reorder})
                (st.success if ok else st.error)(message)
                if ok: st.rerun()
    with st.form("stock_update"):
        new_stock = st.number_input("New stock quantity", min_value=0, max_value=int(product.get("max_capacity", 1) or 1), value=int(product.get("current_stock", 0) or 0), step=1)
        if st.form_submit_button("Save stock adjustment"):
            ok, message = update_stock(selected, new_stock)
            (st.success if ok else st.error)(message)
            if ok: st.rerun()
    if st.button("Delete selected product", type="secondary"):
        st.session_state["confirm_delete"] = selected
    if st.session_state.get("confirm_delete") == selected:
        st.warning("Confirm deletion: this removes the product record but not historical sales.")
        if st.button("Confirm delete", type="primary"):
            ok, message = delete_product(selected)
            (st.success if ok else st.error)(message)
            st.session_state.pop("confirm_delete", None)
            if ok: st.rerun()
