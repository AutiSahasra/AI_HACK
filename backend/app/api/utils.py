"""Shared serialization utilities for API responses."""
from typing import Any, Dict, List


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a MongoDB document to a JSON-serializable dict.

    Converts _id (ObjectId or str) to a string id field and removes the
    raw _id key so FastAPI JSON encoder never sees it.
    """
    if doc is None:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


def serialize_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply serialize_doc to every item in a list."""
    return [serialize_doc(d) for d in docs]
