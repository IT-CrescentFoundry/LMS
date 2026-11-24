# Crescent Foundry LMS — Backend

FastAPI application for the Crescent Foundry Learning Management System. See the [root README](../README.md) for full setup, the [system architecture](../docs/architecture/LMS_SYSTEM_ARCHITECTURE.md) for design and the [API reference](../docs/architecture/API_REFERENCE.md) for every endpoint.

## Layout

```text
app/
├── main.py          create_app() factory (run with uvicorn --factory)
├── cli.py           administrative CLI: create/grant/revoke Super Admin
├── core/            config, logging, middleware (request ID, security headers, trusted-origin
│                    CSRF check), errors (AppError), ids (UUIDv7), context, security/ (passwords, tokens)
├── api/             router.py, deps.py (session, CSRF, require_permission), cookies, presenters
│                    (+ org_presenters, employee_presenters, import_presenters), routes/ (health,
│                    auth, admin_users, admin_access, admin_audit, org_structure, org_reference,
│                    employees, imports)
├── services/        health, audit (record + queries), identity/ (authentication, sessions,
│                    throttling, accounts, access_control, permissions, bootstrap),
│                    organisation/ (units, hierarchy, reference data), employees/ (records,
│                    assignments, roles, responsibilities, reporting, account links, data quality),
│                    imports/ (profiles, workbook security and reading, normalisation, reference
│                    resolution, employees profile, job lifecycle, storage, reports)
├── schemas/         Pydantic request/response models (no hashes or tokens in any response)
├── models/          SQLAlchemy models: identity, audit, organisation, occupation, employees, imports
└── db/              declarative base, engine/session management, column types
alembic/             env.py + versions/ 0001 tables · 0002 roles & permissions · 0003 audit triggers
                     · 0004–0007 organisation, reference data, permissions (C1)
                     · 0008 employees, assignments, reporting lines, account link · 0009 employee
                     permissions (C3) · 0010 import jobs, rows, issues, value mappings,
                     provenance, import permissions (D)
tests/               unit tests (no database) and integration/ (crescent_lms_test only)
  support/           test-database guards (database.py), schema rebuild (schema_reset.py) and
                     synthetic workbook builder (workbooks.py)
```

## Commands (PowerShell, from `LMS_Backend/`)

```powershell
# One-time setup
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[dev]" -c requirements.lock.txt

# Run the API (http://127.0.0.1:8000, docs at /api/docs outside production)
.venv\Scripts\python -m uvicorn app.main:create_app --factory --reload --host 127.0.0.1 --port 8000

# Quality checks
.venv\Scripts\python -m pytest              # unit + database tests (database tests need .env.test)
.venv\Scripts\python -m pytest -m "not db"  # unit tests only
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m ruff format --check .
.venv\Scripts\python -m mypy

# Migrations — always as the migration account (LMS_MIGRATION_DB_*), never the runtime account
.venv\Scripts\python -m alembic current
.venv\Scripts\python -m alembic upgrade head --sql   # offline: print SQL only, for review
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m alembic revision --autogenerate -m "describe change"   # then review by hand

# First Super Admin (interactive terminal; see ADR-047)
.venv\Scripts\python -m app.cli create-super-admin --login-id <login-id> --display-name "<Name>"
.venv\Scripts\python -m app.cli grant-super-admin --login-id <login-id>
.venv\Scripts\python -m app.cli revoke-super-admin --login-id <login-id>

# Scheduled job (non-interactive; needs migration 0011): create due in-app training
# reminders for every participant, signed in or not. Idempotent - run it every 15 minutes
# from Windows Task Scheduler (Program: .venv\Scripts\python.exe, Arguments:
# "-m app.jobs training-reminders", Start in: LMS_Backend). Exit codes: 0 ok, 1 failed
# (nothing saved, next run retries), 2 not configured, 3 migration 0011 not applied.
.venv\Scripts\python -m app.jobs training-reminders --dry-run   # count only
.venv\Scripts\python -m app.jobs training-reminders

# Regenerate the lock file after an approved dependency change
.venv\Scripts\python -m pip freeze --exclude-editable   # keep the header lines of requirements.lock.txt
```

Always invoke tools as modules (`python -m …`); see the root README for why.

## Configuration

Copy `.env.example` to `.env` (never commit it). All variables use the `LMS_` prefix; blank values mean "not set". Start-up fails with a message naming the variable (never its value) when something is missing or invalid.

| Group | Variables | Notes |
|---|---|---|
| Application | `LMS_ENVIRONMENT`, `LMS_API_V1_PREFIX`, `LMS_ENABLE_API_DOCS`, `LMS_LOG_LEVEL`, `LMS_LOG_FORMAT` | Docs default to off in production. |
| Security (required) | `LMS_SECRET_KEY` (≥ 32 chars), `LMS_TRUSTED_ORIGINS` | HMAC key for CSRF tokens and throttle keys; origins allowed to send state-changing requests. |
| CORS | `LMS_CORS_ALLOWED_ORIGINS` | Only for cross-origin setups; wildcards rejected. |
| Sessions | `LMS_SESSION_COOKIE_SECURE` (default `true`), `LMS_SESSION_COOKIE_SAMESITE` (`lax`), `LMS_SESSION_IDLE_TIMEOUT_MINUTES` (30), `LMS_SESSION_ABSOLUTE_TIMEOUT_HOURS` (12) | Secure cookies are mandatory in production. |
| Passwords & throttling | `LMS_PASSWORD_MIN_LENGTH` (12), `LMS_LOGIN_MAX_FAILURES_PER_IDENTIFIER` (5), `LMS_LOGIN_MAX_FAILURES_PER_IP` (20), `LMS_LOGIN_FAILURE_WINDOW_MINUTES` (15), `LMS_LOGIN_LOCKOUT_MINUTES` (15) | Defaults await business confirmation (Q-43). |
| Runtime database | `LMS_DB_HOST`, `LMS_DB_PORT`, `LMS_DB_NAME`, `LMS_DB_USER`, `LMS_DB_PASSWORD`, pool/timeout settings | All four of host/name/user/password or none; no fallback database. |
| Migration account | `LMS_MIGRATION_DB_USER`, `LMS_MIGRATION_DB_PASSWORD` | Used only by Alembic; must differ from `LMS_DB_USER`. |
| Imports (Stage D) | `LMS_IMPORT_STORAGE_DIR` (default `%LOCALAPPDATA%\CrescentLMS\imports`; refused inside the repository), `LMS_IMPORT_MAX_UPLOAD_BYTES` (10 MiB), `LMS_IMPORT_MAX_EXPANDED_BYTES`, `LMS_IMPORT_MAX_ZIP_ENTRIES`, `LMS_IMPORT_MAX_COMPRESSION_RATIO`, `LMS_IMPORT_MAX_SHEETS` (20), `LMS_IMPORT_MAX_ROWS_PER_SHEET` (20 000), `LMS_IMPORT_MAX_ROWS_TOTAL` (6 000 rows per import: synchronous processing at about 25–30 ms per row must finish within the browser's 5-minute wait), `LMS_IMPORT_MAX_COLUMNS` (100), `LMS_IMPORT_JOB_EXPIRY_DAYS` (7), `LMS_IMPORT_PREVIEW_VALID_HOURS` (24), `LMS_IMPORT_VALIDATION_TIMEOUT_MINUTES` (30: a job left in `validating` by a dead request returns to mapping) | Uploaded files are kept only while their job is open; they are deleted after the job's final status is saved, and `GET /api/v1/imports` removes any left behind (see [import profiles §0](../docs/database/EXCEL_IMPORT_PROFILES.md)). |
| Test database (`.env.test`) | `LMS_TEST_DB_HOST`, `LMS_TEST_DB_PORT`, `LMS_TEST_DB_NAME`, `LMS_TEST_DB_USER`, `LMS_TEST_DB_PASSWORD` | Read only by the test harness; must be `crescent_lms_test` / `lms_test`. |

## Endpoints

| Area | Paths | Access |
|---|---|---|
| Health | `GET /api/v1/health/live`, `GET /api/v1/health/ready` | public |
| Authentication | `POST /api/v1/auth/login`, `GET /api/v1/auth/session` (public); `GET /auth/me`, `POST /auth/logout`, `POST /auth/password` | session (+ CSRF token on POST) |
| User accounts | `/api/v1/admin/users…` (list, create, read, update, activate/suspend/disable, password reset, sessions, roles) | `user_accounts.*`, `user_sessions.revoke`, `user_roles.assign` |
| Access roles | `/api/v1/admin/access-roles…`, `/api/v1/admin/access-permissions` | `access_roles.view` / `access_roles.manage` |
| Audit log | `GET /api/v1/admin/audit-events` (read-only; every read is audited) | `audit.view` |
| Organisation | `/api/v1/org/…` (unit types, units, tree, hierarchy, locations, job families, grades, levels, designations, functional roles and mappings, responsibilities) | `organisation.view`; changes need `organisation.manage`, `designations.manage`, `functional_roles.manage` or `responsibilities.manage` |
| Employees (C3) | `/api/v1/employees…` (directory, records, employment status, assignments, functional roles, responsibilities, reporting lines, account links, history, data quality) | `employees.view`, `employees.history.view`, `employees.manage`, `reporting_lines.manage`; account links also need `user_accounts.manage` (global only until C4) |
| Imports (D) | `/api/v1/imports…` (profiles and templates, upload, jobs, mapping, validate, row decisions, commit, cancel, rows, issues, error report, reference mappings) | `imports.view`; `imports.employees.run` to upload, map, validate, decide and cancel; `imports.employees.commit` **plus** `employees.manage` and `reporting_lines.manage` to commit; `imports.mappings.manage` for mapping decisions |
| API docs | `GET /api/docs`, `GET /api/v1/openapi.json` | development only |

Full contract, error codes and schemas: [API reference](../docs/architecture/API_REFERENCE.md).

## Security notes

- Runtime account `lms_app` has data access only; migrations use `lms_migrator`, whose credentials are privileged and must be kept out of the runtime environment.
- Audit events are append-only (code paths, ORM guard, MySQL triggers). The triggers do **not** stop `TRUNCATE`/`DROP TABLE`, and the migration account can drop them (ADR-048). The development server's `log_bin_trust_function_creators = 1` is a local-development setting; production needs a DBA decision.
- Every `/api/v1` route except the public allow-list requires a session; `tests/test_route_protection.py` fails if a new route forgets it.
- Employee records hold no compensation, bank, government-identifier, date-of-birth, gender, home-address, health, family or personal-contact data. Tests use synthetic employees only; real employee workbooks are never added to the repository.
- Imports (ADR-051…053): `.xlsx` only, hostile-file checks before parsing, `openpyxl` read-only with cached values, `defusedxml` for inspected XML; sensitive columns are never mapped or read; uploads live outside the repository and are deleted when the job closes; nothing is written before an explicit approval, and the commit is one transaction. Import tests build synthetic workbooks in memory (`tests/support/workbooks.py`); real HR workbooks are never used as fixtures.
- Database integration tests are pinned to `crescent_lms_test` as `lms_test@127.0.0.1`; the identity is verified on every connection before anything runs (ADR-041).
