# Crescent Foundry LMS — Backend

FastAPI application for the Crescent Foundry Learning Management System. See the [root README](../README.md) for full setup and the [system architecture](../docs/architecture/LMS_SYSTEM_ARCHITECTURE.md) for design.

## Layout

```text
app/
├── main.py          create_app() factory (run with uvicorn --factory)
├── core/            config, logging, middleware, error handling
├── api/             router.py, deps.py, routes/ (health)
├── services/        business logic
├── schemas/         Pydantic request/response models
├── models/          SQLAlchemy models (none in Stage A)
└── db/              declarative base, engine and session management
alembic/             migration environment (no revisions in Stage A)
tests/               pytest suite (no real database or employee data)
```

## Commands (PowerShell, from `LMS_Backend/`)

```powershell
# One-time setup
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]" -c requirements.lock.txt

# Run the API (http://127.0.0.1:8000, docs at /api/docs)
.venv\Scripts\python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000

# Quality checks
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m mypy

# Migrations (require a configured LMS database)
.venv\Scripts\python -m alembic current
.venv\Scripts\python -m alembic revision --autogenerate -m "describe change"
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m alembic upgrade head --sql   # offline: print SQL only
```

Always invoke tools as modules (`python -m …`); see the root README for why.

## Configuration

Copy `.env.example` to `.env` and adjust. All variables use the `LMS_` prefix. Without `LMS_DB_*` values the API starts, `/api/v1/health/live` returns 200 and `/api/v1/health/ready` returns 503 `not_configured`. Partial database settings stop start-up with an error. There is no fallback database.

## Endpoints (Stage A)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health/live` | Liveness — process is up; never touches the database. |
| GET | `/api/v1/health/ready` | Readiness — checks the database; 200 ready / 503 not ready. |
| GET | `/api/docs` | Swagger UI (disabled by default in production). |
| GET | `/api/v1/openapi.json` | OpenAPI schema (disabled by default in production). |
