from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models import Expense
from app.schemas import (
    CategorySummary,
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseRead,
    SummaryResponse,
)


class ExpenseService:
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory

    def create_expense(self, data: ExpenseCreate) -> Tuple[ExpenseRead, bool]:
        """
        Create an expense. Returns (expense, was_created).
        If idempotency_key already exists, returns existing record with was_created=False.
        """
        with self._session_factory() as session:
            # Check for existing record with same idempotency key
            existing = session.execute(
                select(Expense).where(
                    Expense.idempotency_key == data.idempotency_key
                )
            ).scalar_one_or_none()

            if existing is not None:
                return ExpenseRead.model_validate(existing), False

            new_expense = Expense(
                idempotency_key=data.idempotency_key,
                amount=data.amount,
                category=data.category,
                description=data.description,
                date=data.date,
            )
            session.add(new_expense)

            try:
                session.commit()
            except IntegrityError:
                # Race condition: concurrent retry inserted between SELECT and INSERT
                session.rollback()
                existing = session.execute(
                    select(Expense).where(
                        Expense.idempotency_key == data.idempotency_key
                    )
                ).scalar_one()
                return ExpenseRead.model_validate(existing), False

            session.refresh(new_expense)
            return ExpenseRead.model_validate(new_expense), True

    def list_expenses(
        self,
        category: Optional[str] = None,
        sort: str = "date_desc",
    ) -> ExpenseListResponse:
        """List expenses with optional category filter and sort order."""
        with self._session_factory() as session:
            query = select(Expense)

            if category:
                query = query.where(Expense.category == category)

            if sort == "date_asc":
                query = query.order_by(Expense.date.asc(), Expense.created_at.asc())
            else:
                query = query.order_by(Expense.date.desc(), Expense.created_at.desc())

            rows = session.execute(query).scalars().all()
            expenses = [ExpenseRead.model_validate(r) for r in rows]
            total = sum((e.amount for e in expenses), Decimal("0"))

            return ExpenseListResponse(
                expenses=expenses,
                total=total,
                count=len(expenses),
            )

    def get_categories(self) -> List[str]:
        """Return distinct categories from existing expenses."""
        with self._session_factory() as session:
            rows = session.execute(
                select(Expense.category).distinct().order_by(Expense.category)
            ).scalars().all()
            return list(rows)

    def get_summary(self) -> SummaryResponse:
        """Aggregate totals grouped by category."""
        with self._session_factory() as session:
            rows = session.execute(
                select(
                    Expense.category,
                    func.sum(Expense.amount).label("total"),
                    func.count().label("count"),
                ).group_by(Expense.category).order_by(Expense.category)
            ).all()

            by_category = [
                CategorySummary(category=r.category, total=r.total, count=r.count)
                for r in rows
            ]
            grand_total = sum((c.total for c in by_category), Decimal("0"))

            return SummaryResponse(by_category=by_category, grand_total=grand_total)
