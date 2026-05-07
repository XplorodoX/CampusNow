"""Unit tests for serialization utility helpers."""

from bson import ObjectId

from app.utils import serialize_doc, serialize_docs


def test_serialize_doc_converts_top_level_object_id() -> None:
    oid = ObjectId()
    doc = {"_id": oid, "name": "Raum"}

    serialized = serialize_doc(doc)

    assert serialized["_id"] == str(oid)
    assert serialized["name"] == "Raum"


def test_serialize_doc_leaves_other_types_untouched() -> None:
    doc = {"count": 2, "active": True, "name": "Z106"}

    serialized = serialize_doc(doc)

    assert serialized == {"count": 2, "active": True, "name": "Z106"}


def test_serialize_docs_serializes_multiple_documents() -> None:
    oid_1 = ObjectId()
    oid_2 = ObjectId()
    docs = [{"_id": oid_1}, {"_id": oid_2, "room": "Z106"}]

    serialized = serialize_docs(docs)

    assert serialized == [{"_id": str(oid_1)}, {"_id": str(oid_2), "room": "Z106"}]
