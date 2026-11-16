# Crescent Foundry LMS

Learning Management System for Crescent Foundry employees, covering induction, foundry process education, role-based learning paths, competency development, theoretical and practical assessment, certification, career development and AI-assisted learning. It is multilingual (English, Bengali, Hindi, Gujarati) and usable on phones, tablets, laptops and desktops.

## Current status: Stage C3 (employee management) implemented, pending review and commit

| Area | State |
|---|---|
| Frontend shell (branding, navigation, language selector, responsive layout, API connectivity indicator, dashboard placeholder) | Implemented |
| Sign-in, session restoration, sign-out, change password, permission-aware navigation | Implemented (Stage B) |
| Read-only administration: User accounts and Audit log pages | Implemented (Stage B; C3 adds the employee-link filter and a linked-employee column shown only with `employees.view`) |
| Organisation structure and reference data API; Organisation Builder screens | Implemented (Stages C1, C2) |
| Employee master API: employees, effective-dated assignments, functional roles (derived, manual, excluded), responsibilities, reporting lines, account links, separation with preview, history, data quality | Implemented (Stage C3a, C3b CP0); **uncommitted, awaiting review** |
| Employee screens: directory, profile tabs, create/edit, status, assignments, roles, responsibilities, reporting, separation, account linking, data quality | Implemented (Stage C3b); **uncommitted, awaiting review** — see [frontend README](LMS_Frontend/README.md#employee-area-stage-c3) |
| Language switching across en / bn / hi / gu | Implemented (Bengali, Hindi and Gujarati strings, including all C2 and C3 screens, are machine drafts awaiting native-speaker review — register Q-58) |
| Backend API: configuration, structured logging, error handling, CORS, liveness and readiness checks | Implemented |
| Identity and access: user accounts, Argon2id passwords, server-side sessions, CSRF protection, login throttling, access roles and permissions, administration API | Implemented (Stage B) |
| Append-only audit trail; Super Admin bootstrap through the CLI | Implemented (Stage B) |
| MySQL with separate runtime, migration and test accounts; Alembic head `0009` (employees) in the repository | Migrations `0008`–`0009` are verified on the test database only; applying them to `crescent_lms_dev` is a separate, explicit decision |
| Kiosk PIN sign-in, badge QR, OTP/SSO, organisation-scoped roles (C4) | **Not implemented** — open questions Q-07, Q-08, Q-09; Stage C4 |
| Imports, learning, assessments, competency, certification, reports, AI | **Not implemented** — see the [roadmap](docs/LMS_IMPLEMENTATION_ROADMAP.md) |

## Repository structure

```text
LMS/
├── LMS_Frontend/   React + TypeScript + Vite + Tailwind CSS v4 single-page app
├── LMS_Backend/    Python FastAPI API, SQLAlchemy models, Alembic migrations, CLI, tests
├── docs/
│   ├── architecture/   system architecture, API reference, organisation architecture
│   ├── database/       database design and import profiles
│   ├── decisions/      architectural decision records (ADR-001 … ADR-050)
│   ├── product/        product requirements and open-questions register
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
| MySQL | 8.0, with dedicated LMS schemas and accounts (see §3) | 8.0.46 (`crescent_lms_dev`, `crescent_lms_test`) |
| Git | any recent | 2.56 |

Commands below use **PowerShell** on Windows. Run them from the repository root unless stated.

## 1. Backend setup

```powershell
cd LMS_Backend
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]" -c requirements.lock.txt
Copy-Item .env.example .env      # then edit .env (never commit it)
```

Required in `LMS_Backend/.env` (see [`.env.example`](LMS_Backend/.env.example) for every variable):

| Variable | Notes |
|---|---|
| `LMS_SECRET_KEY` | ≥ 32 random characters: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `LMS_TRUSTED_ORIGINS` | Addresses users open in the browser, e.g. `http://localhost:5173,http://127.0.0.1:5173` |
| `LMS_SESSION_COOKIE_SECURE` | `false` **only** for local plain-http development (production refuses to start otherwise) |
| `LMS_DB_HOST`, `LMS_DB_NAME`, `LMS_DB_USER`, `LMS_DB_PASSWORD` | Runtime account (data access only) |
| `LMS_MIGRATION_DB_USER`, `LMS_MIGRATION_DB_PASSWORD` | Migration account, used only by Alembic; must differ from the runtime account |

Optional for database integration tests: copy [`.env.test.example`](LMS_Backend/.env.test.example) to `LMS_Backend/.env.test` (git-ignored) — see §6.

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

Always run tools as modules — `python -m uvicorn`, `python -m alembic`, `python -m pytest`, `python -m app.cli` — rather than through `.venv\Scripts\*.exe` launchers. (Decision record: ADR-020.)

## 2. Frontend setup

```powershell
cd LMS_Frontend
npm ci
# optional: Copy-Item .env.example .env.local   (defaults work for local development)
```

## 3. Database: provisioning and migrations

The LMS uses **its own** MySQL schemas and least-privilege accounts — never the PMS database or credentials. Nothing in this repository creates databases or accounts; a database administrator does (details: [database design §2.10 and §16](docs/database/LMS_DATABASE_DESIGN.md)).

| Account | Rights | Used for |
|---|---|---|
| `lms_app` | `SELECT, INSERT, UPDATE, DELETE` on the LMS schema | The running API and the admin CLI |
| `lms_migrator` | DDL + `TRIGGER` on the LMS schema | Alembic only — **privileged; protect its credentials** |
| `lms_test` | All rights on `crescent_lms_test` only | Automated database tests |

**Audit triggers prerequisite.** Revision `0003` creates append-only triggers on `audit_event`. With binary logging enabled, MySQL allows this for a non-SUPER account only when `log_bin_trust_function_creators = 1`. The **local development** server uses `SET PERSIST log_bin_trust_function_creators = 1`; **production or any shared database needs a separate DBA decision first**. No LMS account is ever granted SUPER or SET_USER_ID.

Apply migrations (Alembic connects with `LMS_MIGRATION_DB_*`, verifies `DATABASE()`, and never falls back to another database):

```powershell
cd LMS_Backend
.venv\Scripts\python -m alembic upgrade head        # production additionally needs: -x allow_production=true (after a backup)
.venv\Scripts\python -m alembic current             # expect: 0003 (head)
```

Then check `GET /api/v1/health/ready` returns `200` with `"database": {"status": "ok"}`.

## 4. First Super Admin

There is no default administrator and no sign-up page. Create the first Super Admin yourself, in an interactive terminal (ADR-047):

```powershell
cd LMS_Backend
.venv\Scripts\python -m app.cli create-super-admin --login-id <login-id> --display-name "<Name>"
```

The command shows the target database and asks you to type its name to confirm, reads the password twice without echo, refuses if a Super Admin already exists, and records `super_admin.bootstrapped` in the audit log. `grant-super-admin` / `revoke-super-admin --login-id <id>` manage further Super Admins (the last one cannot be revoked). HR Admins and other roles are granted through the administration API by authorised users.

## 5. Run both applications

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

Open **http://localhost:5173** and sign in. The Vite dev server proxies `/api` to the backend, so the browser talks to a single origin; that origin must be listed in `LMS_TRUSTED_ORIGINS`.

- Signed out, every page redirects to `/login`. After sign-in you return to the page you asked for.
- Users holding `user_accounts.view` / `audit.view` see **Administration → User accounts / Audit log**.
- If the backend is stopped, the indicator shows **"API unreachable"** with a retry option.

API documentation (development only): **http://localhost:5173/api/docs**, plus the human-readable [API reference](docs/architecture/API_REFERENCE.md).

## 6. Tests and quality checks

Run everything:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check.ps1
```

Or individually:

```powershell
# Backend (from LMS_Backend)
.venv\Scripts\python -m pytest            # unit tests + database tests (if .env.test exists)
.venv\Scripts\python -m pytest -m db      # database integration tests only
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m mypy

# Frontend (from LMS_Frontend)
npm run check                             # typecheck + lint + test + build
```

- **Unit tests** never connect to a database and never read `.env`.
- **Database integration tests** (`db` marker) run **only** against `crescent_lms_test` as MySQL account `lms_test@127.0.0.1`. Both are verified with `SELECT DATABASE(), CURRENT_USER()` on every connection before anything runs; the development database is unreachable from the test harness. Each test session rebuilds the test schema from scratch (drop all tables → upgrade → downgrade → upgrade, each phase verified), so leftovers from earlier runs cannot break it. Without `.env.test` these tests are skipped with an explicit reason.
- All test data is synthetic — never real employee data.

## 7. Configuration reference

- Backend: [`LMS_Backend/.env.example`](LMS_Backend/.env.example) — all variables prefixed `LMS_`; [`LMS_Backend/.env.test.example`](LMS_Backend/.env.test.example) — test database (`LMS_TEST_DB_*`).
- Frontend: [`LMS_Frontend/.env.example`](LMS_Frontend/.env.example) — `VITE_*` variables are public (embedded in the bundle).

## 8. Documentation

| Document | Contents |
|---|---|
| [Product requirements](docs/product/LMS_PRODUCT_REQUIREMENTS.md) | Labels and document map, vision, users, the three user experiences, glossary, requirements, NFRs, **source documents and open-questions register** |
| [Competency & compliance requirements](docs/product/COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md) | Competency framework, development plans, compliance skills, certification, Skill Passport |
| [Training operations requirements](docs/product/TRAINING_OPERATIONS_REQUIREMENTS.md) | Calendars, planned vs actual, events, sessions, nominations, attendance, finalisation, hours, feedback |
| [System architecture](docs/architecture/LMS_SYSTEM_ARCHITECTURE.md) | Frontend, backend, domain architecture, API conventions, i18n, **security (§11)**, AI, integrations, deployment |
| [API reference](docs/architecture/API_REFERENCE.md) | Every implemented endpoint: access, permission, CSRF, request/response, errors |
| [Organisation architecture](docs/architecture/ORGANISATION_ARCHITECTURE.md) | Configurable organisation model, functional roles, responsibilities, access vs functional roles, effective dating |
| [Database design](docs/database/LMS_DATABASE_DESIGN.md) | Conventions, database accounts, implemented identity/audit tables, role–permission matrix, proposed tables for later stages |
| [Excel import profiles](docs/database/EXCEL_IMPORT_PROFILES.md) | Import framework and the six import profiles |
| [Architectural decisions](docs/decisions/ARCHITECTURAL_DECISIONS.md) | ADR-001 to ADR-050 (Stage B: ADR-040–050) |
| [Implementation roadmap](docs/LMS_IMPLEMENTATION_ROADMAP.md) | Stages A, A.1 and B–O with dependencies and status |
| Component READMEs | [Backend](LMS_Backend/README.md) · [Frontend](LMS_Frontend/README.md) |

## 9. Ground rules

- Never commit `.env` / `.env.test` files, credentials or real employee/organisation data (`.gitignore` excludes `.env*` except the two templates, plus `private-data/`, `data/private/`, `data/imports/`).
- All schema changes go through reviewed Alembic migrations run with the migration account; never modify a shared or production database silently; never delete existing data without explicit approval.
- Automated tests touch **only** `crescent_lms_test`; never run them against the development or any other database.
- Super Admins are created only by an operator through the CLI — never by tooling or seeded credentials.
- Do not connect the LMS to the PMS database.
- AI-generated learning material requires human review before publication.
- Work in defined stages; run tests, linting and type checks before handing over.

## 10. Verified dependency versions (Stage B)

**Frontend** (exact versions in `LMS_Frontend/package-lock.json`; unchanged in Stage B): React 19.3.1, TypeScript 6.0.3, Vite 8.3.8, Tailwind CSS 4.3.5 (`@tailwindcss/vite` 4.3.5), React Router 8.5.1, TanStack Query 5.107.1, i18next 27.1.1, react-i18next 18.0.1, lucide-react 1.72.0, Vitest 5.1.0, React Testing Library 16.3.3, jsdom 31.0.0, ESLint 10.14.0.

**Backend** (exact versions in `LMS_Backend/requirements.lock.txt`): FastAPI 0.162.5, Starlette 1.10.0, Uvicorn 0.54.0, Pydantic 2.14.3, Pydantic Settings 2.16.2, SQLAlchemy 2.1.8, Alembic 1.20.1, PyMySQL 1.2.4, cryptography 50.0.2, **argon2-cffi 25.1.0** (Stage B), Pytest 9.2.0, httpx2 2.16.0, Ruff 0.17.4, mypy 2.4.1, **tzdata 2026.6** (dev, Stage B).
