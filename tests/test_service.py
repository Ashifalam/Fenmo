from datetime import date
from decimal import Decimal

from app.schemas import ExpenseCreate


def _make_expense(**overrides):
    base = {
        "idempotency_key": "key-1",
        "amount": Decimal("50.00"),
        "category": "Groceries",
        "description": "Test",
        "date": date(2026, 4, 20),
    }
    base.update(overrides)
    return ExpenseCreate(**base)


class TestCreateExpense:
    def test_creates_expense(self, service):
        expense, created = service.create_expense(_make_expense())
        assert created is True
        assert expense.amount == Decimal("50.00")
        assert expense.category == "Groceries"
        assert expense.id is not None
        assert expense.created_at is not None

    def test_idempotent_on_same_key(self, service):
        e1, created1 = service.create_expense(_make_expense())
        e2, created2 = service.create_expense(_make_expense())
        assert created1 is True
        assert created2 is False
        assert e1.id == e2.id

    def test_different_keys_create_different_records(self, service):
        e1, _ = service.create_expense(_make_expense(idempotency_key="a"))
        e2, _ = service.create_expense(_make_expense(idempotency_key="b"))
        assert e1.id != e2.id


class TestListExpenses:
    def test_empty_list(self, service):
        result = service.list_expenses()
        assert result.count == 0
        assert result.total == Decimal("0")
        assert result.expenses == []

    def test_returns_all_expenses(self, service):
        service.create_expense(_make_expense(idempotency_key="a"))
        service.create_expense(_make_expense(idempotency_key="b", amount=Decimal("25.00")))
        result = service.list_expenses()
        assert result.count == 2
        assert result.total == Decimal("75.00")

    def test_filter_by_category(self, service):
        service.create_expense(_make_expense(idempotency_key="a", category="Groceries"))
        service.create_expense(_make_expense(idempotency_key="b", category="Transport"))
        result = service.list_expenses(category="Groceries")
        assert result.count == 1
        assert result.expenses[0].category == "Groceries"

    def test_filter_no_match(self, service):
        service.create_expense(_make_expense(idempotency_key="a", category="Groceries"))
        result = service.list_expenses(category="NonExistent")
        assert result.count == 0
        assert result.total == Decimal("0")

    def test_sort_date_desc(self, service):
        service.create_expense(_make_expense(idempotency_key="a", date=date(2026, 1, 1)))
        service.create_expense(_make_expense(idempotency_key="b", date=date(2026, 6, 1)))
        result = service.list_expenses(sort="date_desc")
        assert result.expenses[0].date == date(2026, 6, 1)
        assert result.expenses[1].date == date(2026, 1, 1)

    def test_sort_date_asc(self, service):
        service.create_expense(_make_expense(idempotency_key="a", date=date(2026, 1, 1)))
        service.create_expense(_make_expense(idempotency_key="b", date=date(2026, 6, 1)))
        result = service.list_expenses(sort="date_asc")
        assert result.expenses[0].date == date(2026, 1, 1)

    def test_decimal_precision(self, service):
        """Verify no floating point drift: 0.10 + 0.20 == 0.30"""
        service.create_expense(_make_expense(idempotency_key="a", amount=Decimal("0.10")))
        service.create_expense(_make_expense(idempotency_key="b", amount=Decimal("0.20")))
        result = service.list_expenses()
        assert result.total == Decimal("0.30")


class TestGetSummary:
    def test_empty_summary(self, service):
        result = service.get_summary()
        assert result.by_category == []
        assert result.grand_total == Decimal("0")

    def test_groups_by_category(self, service):
        service.create_expense(_make_expense(idempotency_key="a", category="Groceries", amount=Decimal("100")))
        service.create_expense(_make_expense(idempotency_key="b", category="Groceries", amount=Decimal("50")))
        service.create_expense(_make_expense(idempotency_key="c", category="Transport", amount=Decimal("30")))
        result = service.get_summary()
        assert len(result.by_category) == 2
        groceries = next(c for c in result.by_category if c.category == "Groceries")
        assert groceries.total == Decimal("150")
        assert groceries.count == 2
        assert result.grand_total == Decimal("180")
