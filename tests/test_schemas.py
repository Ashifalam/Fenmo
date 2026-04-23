from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import ExpenseCreate


def _valid_data(**overrides):
    base = {
        "idempotency_key": "test-key-1",
        "amount": Decimal("42.50"),
        "category": "Groceries",
        "description": "Weekly shopping",
        "date": date(2026, 4, 23),
    }
    base.update(overrides)
    return base


class TestExpenseCreate:
    def test_valid_expense(self):
        e = ExpenseCreate(**_valid_data())
        assert e.amount == Decimal("42.50")
        assert e.category == "Groceries"

    def test_amount_from_string(self):
        e = ExpenseCreate(**_valid_data(amount="99.99"))
        assert e.amount == Decimal("99.99")

    def test_negative_amount_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            ExpenseCreate(**_valid_data(amount=Decimal("-10.00")))

    def test_zero_amount_rejected(self):
        with pytest.raises(ValidationError, match="greater than 0"):
            ExpenseCreate(**_valid_data(amount=Decimal("0")))

    def test_three_decimal_places_rejected(self):
        with pytest.raises(ValidationError, match="2 decimal places"):
            ExpenseCreate(**_valid_data(amount=Decimal("1.234")))

    def test_empty_category_rejected(self):
        with pytest.raises(ValidationError):
            ExpenseCreate(**_valid_data(category=""))

    def test_missing_date_rejected(self):
        data = _valid_data()
        del data["date"]
        with pytest.raises(ValidationError):
            ExpenseCreate(**data)

    def test_description_defaults_to_empty(self):
        data = _valid_data()
        del data["description"]
        e = ExpenseCreate(**data)
        assert e.description == ""

    def test_integer_amount_accepted(self):
        e = ExpenseCreate(**_valid_data(amount=Decimal("100")))
        assert e.amount == Decimal("100")
