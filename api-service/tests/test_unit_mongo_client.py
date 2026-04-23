"""Unit tests for MongoDB client wrapper."""

from unittest.mock import MagicMock

import pytest
from pymongo.errors import ServerSelectionTimeoutError

from app.db.mongo_client import MongoDBClient


@pytest.fixture(autouse=True)
def reset_singleton() -> None:
    MongoDBClient._instance = None


def test_mongodb_client_is_singleton() -> None:
    first = MongoDBClient()
    second = MongoDBClient()

    assert first is second


def test_connect_success_sets_db(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = MagicMock()
    fake_client.admin.command.return_value = {"ok": 1}
    fake_db = MagicMock()
    fake_client.__getitem__.return_value = fake_db

    monkeypatch.setattr("app.db.mongo_client.MongoClient", lambda *args, **kwargs: fake_client)

    client = MongoDBClient()
    ok = client.connect()

    assert ok is True
    assert client.db is fake_db
    fake_client.admin.command.assert_called_once_with("ping")


def test_connect_failure_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(*args, **kwargs):
        raise ServerSelectionTimeoutError("timeout")

    monkeypatch.setattr("app.db.mongo_client.MongoClient", raise_timeout)

    client = MongoDBClient()
    ok = client.connect()

    assert ok is False
    assert client.db is None


def test_get_db_triggers_connect_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MongoDBClient()
    fake_db = MagicMock()

    def fake_connect() -> bool:
        client.db = fake_db
        return True

    monkeypatch.setattr(client, "connect", fake_connect)

    returned = client.get_db()

    assert returned is fake_db


def test_get_collection_returns_named_collection(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MongoDBClient()
    fake_db = MagicMock()
    fake_collection = MagicMock()
    fake_db.__getitem__.return_value = fake_collection

    monkeypatch.setattr(client, "get_db", lambda: fake_db)

    collection = client.get_collection("rooms")

    assert collection is fake_collection
    fake_db.__getitem__.assert_called_once_with("rooms")


def test_disconnect_closes_open_client() -> None:
    client = MongoDBClient()
    fake_client = MagicMock()
    client.client = fake_client

    client.disconnect()

    fake_client.close.assert_called_once()
