from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.service import ExpenseService


@pytest.fixture
def client():
    """FastAPI TestClient with isolated in-memory DB."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    # Import and patch the FastAPI app's service
    from app import api

    api.service = ExpenseService(Session)
    return TestClient(api.app)


class TestPostExpenses:
    def test_create_expense(self, client):
        resp = client.post("/expenses", json={
            "idempotency_key": "k1",
            "amount": "42.50",
            "category": "Groceries",
            "description": "Test",
            "date": "2026-04-23",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["amount"] == "42.50"
        assert data["category"] == "Groceries"
        assert "id" in data

    def test_idempotent_retry(self, client):
        payload = {
            "idempotency_key": "k-dup",
            "amount": "10.00",
            "category": "Transport",
            "description": "",
            "date": "2026-04-23",
        }
        r1 = client.post("/expenses", json=payload)
        r2 = client.post("/expenses", json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 200
        assert r1.json()["id"] == r2.json()["id"]

    def test_negative_amount_rejected(self, client):
        resp = client.post("/expenses", json={
            "idempotency_key": "k-neg",
            "amount": "-5.00",
            "category": "Groceries",
            "description": "",
            "date": "2026-04-23",
        })
        assert resp.status_code == 422

    def test_missing_fields_rejected(self, client):
        resp = client.post("/expenses", json={"amount": "10"})
        assert resp.status_code == 422


class TestGetExpenses:
    def test_empty_list(self, client):
        resp = client.get("/expenses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["expenses"] == []

    def test_filter_by_category(self, client):
        client.post("/expenses", json={
            "idempotency_key": "a", "amount": "10", "category": "Food",
            "description": "", "date": "2026-04-23",
        })
        client.post("/expenses", json={
            "idempotency_key": "b", "amount": "20", "category": "Transport",
            "description": "", "date": "2026-04-23",
        })
        resp = client.get("/expenses?category=Food")
        data = resp.json()
        assert data["count"] == 1
        assert data["expenses"][0]["category"] == "Food"

    def test_sort_by_date(self, client):
        client.post("/expenses", json={
            "idempotency_key": "a", "amount": "10", "category": "Food",
            "description": "", "date": "2026-01-01",
        })
        client.post("/expenses", json={
            "idempotency_key": "b", "amount": "20", "category": "Food",
            "description": "", "date": "2026-06-01",
        })
        resp = client.get("/expenses?sort=date_desc")
        dates = [e["date"] for e in resp.json()["expenses"]]
        assert dates == ["2026-06-01", "2026-01-01"]

    def test_amount_is_string_not_float(self, client):
        client.post("/expenses", json={
            "idempotency_key": "a", "amount": "42.50",
            "category": "Food", "description": "", "date": "2026-04-23",
        })
        resp = client.get("/expenses")
        amount = resp.json()["expenses"][0]["amount"]
        assert isinstance(amount, str)
        assert amount == "42.50"
