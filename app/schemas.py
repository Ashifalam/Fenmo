from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpenseCreate(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=64)
    amount: Decimal = Field(..., gt=Decimal("0"), max_digits=12, decimal_places=2)
    category: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    date: date

    @field_validator("amount")
    @classmethod
    def amount_max_two_decimals(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent < -2:  # type: ignore[operator]
            raise ValueError("Amount cannot have more than 2 decimal places")
        return v


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idempotency_key: str
    amount: Decimal
    category: str
    description: str
    date: date
    created_at: datetime


class ExpenseListResponse(BaseModel):
    expenses: list[ExpenseRead]
    total: Decimal
    count: int


class CategorySummary(BaseModel):
    category: str
    total: Decimal
    count: int


class SummaryResponse(BaseModel):
    by_category: list[CategorySummary]
    grand_total: Decimal
