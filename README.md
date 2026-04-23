# Fenmo - Personal Expense Tracker

A minimal full-stack expense tracker built with **Streamlit** (frontend), **FastAPI** (REST API), and **PostgreSQL** (persistence).

## Features

- Add expenses with amount, category, description, and date
- View expense list with filtering by category and sorting by date
- Live total of currently visible expenses
- Category-wise summary table
- **Idempotent submissions** — safe against double-clicks, page refreshes, and network retries
- Input validation (positive amounts, required fields, max 2 decimal places)

## Architecture

```
Streamlit UI  →  ExpenseService (shared logic)  ←  FastAPI REST API
                        ↓
                   PostgreSQL / SQLite
```

- **Service layer pattern**: Both Streamlit and FastAPI call the same `ExpenseService` class. Streamlit calls it directly (no HTTP overhead in production). FastAPI wraps it as REST endpoints for external clients.
- **Streamlit Cloud**: The app connects to an external PostgreSQL instance (e.g., Neon). FastAPI is available for local development and API testing but isn't required in the Streamlit Cloud deployment.

## Key Design Decisions

### Money Handling
`Decimal` everywhere, `float` nowhere. The full path:
- User input (string) → Pydantic `Decimal` → SQLAlchemy `Numeric(12,2)` → PostgreSQL `NUMERIC` → back to `Decimal` → display as `₹X,XXX.XX`
- Summation uses Python's `Decimal` arithmetic or PostgreSQL's `SUM()` (both exact)

### Idempotency (Duplicate Prevention)
The biggest real-world risk with expense forms is accidental duplicates. Our approach:
1. Client generates a UUID `idempotency_key` per form submission (stored in `st.session_state`)
2. Server checks for existing key before INSERT, catches `IntegrityError` for race conditions
3. Same key → returns existing record (HTTP 200). New key → creates new record (HTTP 201)
4. The key is only regenerated **after** confirmed successful creation

This handles: double-clicks, page refreshes, slow network retries, and concurrent submissions.

### Database Choice: PostgreSQL
- `NUMERIC(12,2)` for exact money arithmetic at the database level
- `CHECK` constraint ensures amounts are always positive
- `UNIQUE` constraint on `idempotency_key` enforces duplicate prevention at the DB level
- Indexes on `category` and `date` for efficient filtering/sorting
- Falls back to SQLite for zero-config local development and testing

### Why Streamlit + FastAPI (not just one)
- **Streamlit** provides a clean, interactive UI with zero frontend code
- **FastAPI** provides a proper REST API that can be used by other clients, tested independently, and documented automatically via OpenAPI
- The **service layer** decouples business logic from both, making it easy to swap either

## Trade-offs (due to timebox)

- **No pagination**: The expense list loads all records. Fine for personal use (hundreds of expenses), but would need `LIMIT`/`OFFSET` or cursor pagination for scale.
- **No authentication**: Single-user tool. Multi-user would need auth + per-user data isolation.
- **No Alembic migrations**: Schema changes use `create_all()` (idempotent). For evolving schemas, add Alembic.
- **Category is free-text**: No enum or lookup table. Simple but could lead to inconsistent naming (e.g., "Food" vs "food"). A future improvement would be case-insensitive matching or a category management UI.
- **No expense editing/deletion**: Read and create only. CRUD completion would be a natural next step.

## What I Intentionally Did Not Do

- **Over-engineer the frontend**: No React, no CSS frameworks. Streamlit is sufficient for this scope and keeps the codebase small.
- **Add caching**: The dataset is small enough that queries are fast without caching layers.
- **Add logging/monitoring**: Would be important in production but not for this exercise.
- **Docker for deployment**: Streamlit Cloud handles deployment. Docker Compose is included for local PostgreSQL convenience only.

## Setup

### Prerequisites
- Python 3.9+
- PostgreSQL (optional — falls back to SQLite for local dev)

### Local Development

```bash
# Clone and install
git clone <repo-url> && cd Femo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt

# (Optional) Set PostgreSQL URL
export DATABASE_URL="postgresql+psycopg2://user:pass@localhost:5432/femo"

# Run Streamlit app
make run
# Or: streamlit run streamlit_app.py

# Run FastAPI (separate terminal, for API testing)
make api
# Or: uvicorn app.api:app --reload

# Run tests
make test
# Or: pytest tests/ -v
```

### Streamlit Cloud Deployment

1. Push to GitHub
2. Connect the repo in [Streamlit Cloud](https://share.streamlit.io)
3. Set `DATABASE_URL` in Streamlit Cloud Secrets:
   ```toml
   DATABASE_URL = "postgresql+psycopg2://user:pass@host/db?sslmode=require"
   ```
4. Deploy — the app auto-creates tables on first run

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/expenses` | Create an expense (idempotent via `idempotency_key`) |
| `GET` | `/expenses` | List expenses (`?category=X&sort=date_desc`) |
| `GET` | `/expenses/summary` | Category-wise totals |

Interactive API docs available at `http://localhost:8000/docs` when running FastAPI locally.

## Project Structure

```
Femo/
├── app/
│   ├── config.py       # DATABASE_URL resolution (env / st.secrets / SQLite fallback)
│   ├── database.py     # SQLAlchemy engine, session factory
│   ├── models.py       # Expense ORM model (Numeric, UUID, constraints)
│   ├── schemas.py      # Pydantic validation (Decimal, positive amount)
│   ├── service.py      # Business logic (idempotent create, filtered list, summary)
│   └── api.py          # FastAPI routes
├── streamlit_app.py    # Streamlit frontend
├── tests/
│   ├── conftest.py     # SQLite in-memory fixtures
│   ├── test_schemas.py # Validation edge cases
│   ├── test_service.py # Business logic tests
│   └── test_api.py     # HTTP integration tests
├── requirements.txt
└── Makefile
```
