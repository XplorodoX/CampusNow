"""Gemeinsame Hilfsfunktionen für alle Router."""

from bson import ObjectId


def serialize_doc(doc: dict) -> dict:
    """Konvertiert ObjectId-Felder im Dokument zu Strings."""
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
    return doc


def serialize_docs(docs: list[dict]) -> list[dict]:
    """Konvertiert ObjectId-Felder in einer Liste von Dokumenten."""
    return [serialize_doc(doc) for doc in docs]
