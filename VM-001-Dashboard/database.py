from __future__ import annotations

from typing import Any

import streamlit as st
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from config import DATABASE_NAME, MONGO_URI


@st.cache_resource(show_spinner=False)
def get_client(uri: str) -> MongoClient:
    return MongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)


def get_database() -> Database | None:
    if not MONGO_URI:
        return None
    try:
        client = get_client(MONGO_URI)
        client.admin.command("ping")
        return client[DATABASE_NAME]
    except Exception:
        return None


def get_collection(name: str) -> Collection | None:
    database = get_database()
    return database[name] if database is not None else None


def database_status() -> tuple[bool, str]:
    if not MONGO_URI:
        return False, "MongoDB credentials are not configured. Add them to Streamlit Secrets or a local .env file."
    try:
        database = get_database()
        if database is None:
            return False, "MongoDB is unavailable. Check the Atlas URI, network access, and database name."
        return True, f"Connected to MongoDB database: {DATABASE_NAME}"
    except Exception as exc:
        return False, f"MongoDB connection failed: {type(exc).__name__}"


def safe_id(document: dict[str, Any]) -> dict[str, Any]:
    """Return a display-safe copy without exposing internal ObjectIds."""
    result = dict(document)
    if "_id" in result:
        result["_id"] = str(result["_id"])
    return result
