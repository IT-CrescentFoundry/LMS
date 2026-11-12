# Crescent Foundry LMS

Learning Management System for Crescent Foundry employees, covering induction, foundry process education, role-based learning paths, competency development, theoretical and practical assessment, certification, career development and AI-assisted learning. It is multilingual (English, Bengali, Hindi, Gujarati) and usable on phones, tablets, laptops and desktops.

## Current status: Stage A (foundation) and Stage A.1 (architecture alignment) complete

Stage A.1 aligned the architecture and requirements with Crescent Foundry's business requirements (learning hierarchy, competency and compliance, training operations, certification and Skill Passport, three user experiences, six import profiles). It changed documentation only.

| Area | State |
|---|---|
| Frontend shell (branding, navigation placeholder, language selector, responsive layout, API connectivity indicator, dashboard placeholder) | Implemented |
| Language switching across en / bn / hi / gu | Implemented (Bengali, Hindi and Gujarati strings are drafts awaiting native-speaker review) |
| Backend API: configuration, structured logging, error handling, CORS, liveness and readiness checks | Implemented |
| MySQL connectivity infrastructure (SQLAlchemy 2, PyMySQL, Alembic) | Implemented — **connectivity not yet verified**: no dedicated LMS database has been provisioned |
| Business features (login, organisation management, courses, assessments, …) | **Not implemented** — see the [roadmap](docs/LMS_IMPLEMENTATION_ROADMAP.md) |

## Repository structure

```text
LMS/
├── LMS_Frontend/   React + TypeScript + Vite + Tailwind CSS v4 single-page app
├── LMS_Backend/    Python FastAPI API, SQLAlchemy models, Alembic migrations, tests
├── docs/
│   ├── architecture/   system and organisation architecture
│   ├── database/       database design and conventions
│   ├── decisions/      architectural decision records
│   ├── product/        product requirements
│   └── LMS_IMPLEMENTATION_ROADMAP.md
├── scripts/        check.ps1 — runs every quality check
├── .gitignore
├── CLAUDE.md       project instructions for AI-assisted development
└── README.md
```

## Prerequisites

| Tool | Required | Verified with |
|---|---|---|
| Node.js | ≥ 22.22 (required by React Router 8) | 24.21.0 |
| npm | bundled with Node | 12.2.0 |
| Python | ≥ 3.12 | 3.13.16 |
| MySQL | 8.0, with a **dedicated LMS database** (optional for Stage A start-up) | server 8.0.46 present, not connected |
| Git | any recent | 2.56 |

Commands below use **PowerShell** on Windows. Run them from the repository root unless stated.

## 1. Backend setup

```powershell
cd LMS_Backend
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]" -c requirements.lock.txt
Copy-Item .env.example .env      # then edit .env (leave LMS_DB_* blank until a database exists)
```

### Windows Application Control (Smart App Control / WDAC)

On machines with Application Control enforced (as on the original development machine), some compiled Python extensions and pip-generated `.exe` launchers are blocked with *"An Application Control policy has blocked this file"*. If you see that error:

```powershell
# SQLAlchemy without its optional C extensions (pure Python, same behaviour)
$env:DISABLE_SQLALCHEMY_CEXT = "1"
.venv\Scripts\python -m pip install --force-reinstall --no-deps --no-binary sqlalchemy "sqlalchemy==2.1.8"
Remove-Item Env:DISABLE_SQLALCHEMY_CEXT

# mypy built from source (not mypyc-compiled)
.venv\Scripts\python -m pip install --force-reinstall --no-deps --no-binary mypy "mypy==2.4.1"
```

Always run tools as modules — `python -m uvicorn`, `python -m alembic`, `python -m pytest` — rather than through `.venv\Scripts\*.exe` launchers. (Decision record: ADR-020.)

## 2. Frontend setup

```powershell
cd LMS_Frontend
npm ci
# optional: Copy-Item .env.example .env.local   (defaults work for local development)
```

## 3. Run both applications

Terminal 1 — backend:

```powershell
cd LMS_Backend
.venv\Scripts\python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — frontend:

```powershell
cd LMS_Frontend
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to the backend, so the browser talks to a single origin.

Expected with no database configured:

- the header indicator shows **"Connected · database unavailable"** (amber);
- the dashboard's *System status* panel shows *API service: Available*, *Database: Not configured*;
- `http://127.0.0.1:8000/api/v1/health/live` → `200`, `.../health/ready` → `503` with `"database": {"status": "not_configured"}`.

If the backend is stopped, the indicator shows **"API unreachable"** (red) with a retry option.

API documentation (development only): **http://localhost:5173/api/docs** or http://127.0.0.1:8000/api/docs.

## 4. Connecting the LMS database

The LMS must use **its own** MySQL database and least-privilege account — never the PMS database or credentials. Nothing in this repository creates or modifies a database automatically.

1. Ask the database administrator to create a dedicated schema (e.g. `crescent_lms`, `utf8mb4` / `utf8mb4_0900_ai_ci`) and an application account limited to that schema (see [database design §2.10](docs/database/LMS_DATABASE_DESIGN.md#210-database-accounts-to-be-provisioned)).
2. Set all four of `LMS_DB_HOST`, `LMS_DB_NAME`, `LMS_DB_USER`, `LMS_DB_PASSWORD` in `LMS_Backend/.env` (partial settings are rejected at start-up).
3. Restart the backend and check `GET /api/v1/health/ready` returns `200` with `"database": {"status": "ok"}`.

Stage A has **no migrations**; there is nothing to run with Alembic yet.

## 5. Tests and quality checks

Run everything:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check.ps1
```

Or individually:

```powershell
# Backend (from LMS_Backend)
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m mypy

# Frontend (from LMS_Frontend)
npm run typecheck
npm run lint
npm test
npm run build
```

Tests never connect to a real database and use only synthetic data.

## 6. Configuration reference

- Backend: [`LMS_Backend/.env.example`](LMS_Backend/.env.example) — all variables prefixed `LMS_`.
- Frontend: [`LMS_Frontend/.env.example`](LMS_Frontend/.env.example) — `VITE_*` variables are public (embedded in the bundle).

## 7. Documentation

| Document | Contents |
|---|---|
| [Product requirements](docs/product/LMS_PRODUCT_REQUIREMENTS.md) | Labels and document map, vision, users, the three user experiences, glossary, learning, assessment, report and AI requirements, NFRs, **assumptions & open-questions register** |
| [Competency & compliance requirements](docs/product/COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md) | Competency framework, development plans, compliance skills, certification, Skill Passport |
| [Training operations requirements](docs/product/TRAINING_OPERATIONS_REQUIREMENTS.md) | Calendars, planned vs actual, events, sessions, nominations, attendance, finalisation, hours, feedback |
| [System architecture](docs/architecture/LMS_SYSTEM_ARCHITECTURE.md) | Frontend, backend, domain architecture and evidence chain, API conventions, i18n, security (incl. kiosks), AI, integrations, deployment |
| [Organisation architecture](docs/architecture/ORGANISATION_ARCHITECTURE.md) | Configurable organisation model, functional roles, responsibilities, access vs functional roles, effective dating |
| [Database design](docs/database/LMS_DATABASE_DESIGN.md) | Conventions and proposed tables for every domain |
| [Excel import profiles](docs/database/EXCEL_IMPORT_PROFILES.md) | Import framework and the six import profiles |
| [Architectural decisions](docs/decisions/ARCHITECTURAL_DECISIONS.md) | ADR-001 to ADR-039 |
| [Implementation roadmap](docs/LMS_IMPLEMENTATION_ROADMAP.md) | Stages A, A.1 and B–O with dependencies |

## 8. Ground rules

- Never commit `.env` files, credentials or real employee/organisation data (`.gitignore` excludes `.env*`, `private-data/`, `data/private/`, `data/imports/`).
- All schema changes go through reviewed Alembic migrations; never modify a shared or production database silently.
- Do not connect the LMS to the PMS database.
- AI-generated learning material requires human review before publication.
- Work in defined stages; run tests, linting and type checks before handing over.

## 9. Verified dependency versions (Stage A)

**Frontend** (exact versions in `LMS_Frontend/package-lock.json`): React 19.3.1, TypeScript 6.0.3, Vite 8.3.8, Tailwind CSS 4.3.5 (`@tailwindcss/vite` 4.3.5), React Router 8.5.1, TanStack Query 5.107.1, i18next 27.1.1, react-i18next 18.0.1, lucide-react 1.72.0, Vitest 5.1.0, React Testing Library 16.3.3, jsdom 31.0.0, ESLint 10.14.0.

**Backend** (exact versions in `LMS_Backend/requirements.lock.txt`): FastAPI 0.162.5, Starlette 1.10.0, Uvicorn 0.54.0, Pydantic 2.14.3, Pydantic Settings 2.16.2, SQLAlchemy 2.1.8, Alembic 1.20.1, PyMySQL 1.2.4, cryptography 50.0.2, Pytest 9.2.0, httpx2 2.16.0, Ruff 0.17.4, mypy 2.4.1.
