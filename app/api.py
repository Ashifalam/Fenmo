from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from app.database import SessionLocal, create_tables
from app.schemas import ExpenseCreate, ExpenseListResponse, ExpenseRead, SummaryResponse
from app.service import ExpenseService


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Fenmo - Expense Tracker API", lifespan=lifespan)
service = ExpenseService(SessionLocal)


@app.post("/expenses", response_model=ExpenseRead, status_code=201)
def create_expense(data: ExpenseCreate):
    expense, was_created = service.create_expense(data)
    status = 201 if was_created else 200
    return JSONResponse(
        content=expense.model_dump(mode="json"),
        status_code=status,
    )


@app.get("/expenses", response_model=ExpenseListResponse)
def list_expenses(
    category: Optional[str] = Query(default=None),
    sort: str = Query(default="date_desc", pattern="^(date_desc|date_asc)$"),
):
    return service.list_expenses(category=category, sort=sort)


@app.get("/expenses/summary", response_model=SummaryResponse)
def get_summary():
    return service.get_summary()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.api:app", host="0.0.0.0", port=8000, reload=True)
