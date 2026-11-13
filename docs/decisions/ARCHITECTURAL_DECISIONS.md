# Architectural Decision Records

Each record states the decision, why it was made, and its consequences. Status values: **Accepted** (in force), **Proposed** (designed, not yet implemented), **Superseded**.

New decisions are appended with the next number. A changed decision gets a new record that supersedes the old one; old records are not rewritten.

| # | Decision | Status |
|---|---|---|
| 001 | Modular monolith | Accepted |
| 002 | React + TypeScript single-page application built with Vite | Accepted |
| 003 | Tailwind CSS v4 via `@tailwindcss/vite` | Accepted |
| 004 | TanStack Query for server state; no global client store | Accepted |
| 005 | i18next with bundled resources for en/bn/hi/gu | Accepted |
| 006 | FastAPI with synchronous SQLAlchemy 2 and PyMySQL | Accepted |
| 007 | MySQL 8, utf8mb4, UTC timestamps | Accepted |
| 008 | Alembic for all schema changes; no business tables in Stage A | Accepted (Stage B revisions 0001–0003; see 041) |
| 009 | `LMS_`-prefixed settings with no fallback database | Accepted |
| 010 | Separate liveness and readiness probes | Accepted |
| 011 | Same-origin deployment; dev proxy; explicit CORS allow-list | Accepted |
| 012 | Server-side sessions, CSRF tokens, scoped RBAC | Partially implemented in Stage B (043–046); org scoping Stage C |
| 013 | Configurable, effective-dated organisation model | Proposed (extended by 023) |
| 014 | Safe, staged Excel import pipeline | Superseded by 029 |
| 015 | Provider-independent AI layer; Claude first; human review | Proposed (extended by 033, 034) |
| 016 | Structured logging with the standard library and request IDs | Accepted |
| 017 | Uniform JSON error envelope | Accepted |
| 018 | ESLint (not Oxlint) for frontend linting | Accepted |
| 019 | Python 3.13 locally, code targets 3.12+ | Accepted |
| 020 | Pure-Python builds of SQLAlchemy and mypy on Application-Control-restricted Windows machines | Accepted |
| 021 | HTTPX 2 (`httpx2`) for API tests | Accepted |
| 022 | Learning hierarchy: Academy → Path → Curriculum → Asset, composed by reference and versioned | Proposed (A.1) |
| 023 | Access roles separate from functional roles; functional roles and responsibilities in the organisation model | Access roles implemented (Stage B, 046); functional roles Stage C |
| 024 | Configurable competency framework; skill-level sets as data | Proposed (A.1) |
| 025 | Evidence chain: completion, competency, compliance and authorisation are separate records | Proposed (A.1) |
| 026 | Compliance skills separate from competency skills | Proposed (A.1) |
| 027 | Training operations: planned and actual kept separate; finalisation locks events | Proposed (A.1) |
| 028 | Immutable certificate issuances; renewal creates a new issuance; status events; random verification tokens | Proposed (A.1) |
| 029 | Reusable import framework with profiles, provenance and duplicate candidates | Proposed (A.1) |
| 030 | Preserve raw source values; confirmed value mappings only | Proposed (A.1) |
| 031 | Three experiences and kiosk mode as route areas of one SPA | Proposed (A.1); `/admin` area started in Stage B |
| 032 | Employee ID login, kiosk-bound PIN, badge QR tokens, automatic idle logout | Partially implemented (idle logout); kiosk PIN, badges open (Q-08, Q-09) |
| 033 | Content governance: SME validation, HR final approval and publishing | Proposed (A.1) |
| 034 | Human oversight of official assessments and practical validations | Proposed (A.1) |
| 035 | Configurable financial year | Proposed (A.1) |
| 036 | Reporting through scoped read models | Proposed (A.1) |
| 037 | Shared survey component for learning and training feedback | Proposed (A.1) |
| 038 | Typed foreign keys for cross-domain references; immutability for evidence records | Proposed (A.1) |
| 039 | In-process domain events and a separate scheduler/worker for background work | Proposed (A.1) |
| 040 | User accounts separate from employee identity | Accepted (Stage B) |
| 041 | Migration/runtime credential separation; isolated, verified test database | Accepted (Stage B) |
| 042 | Argon2id password hashing and password policy | Accepted (Stage B) |
| 043 | Server-side sessions and session cookie | Accepted (Stage B) |
| 044 | CSRF protection: trusted origins plus session-bound token | Accepted (Stage B) |
| 045 | Database-backed login throttling | Accepted (Stage B) |
| 046 | RBAC with permission codes; seeded roles; assignment guards | Accepted (Stage B) |
| 047 | Super Admin bootstrap only through the CLI | Accepted (Stage B) |
| 048 | Audit event model and append-only protection | Accepted (Stage B) |
| 049 | UUIDv7 public identifiers; internal keys never exposed | Accepted (Stage B) |
| 050 | Frontend authentication and session restoration | Accepted (Stage B) |

---

## ADR-001 — Modular monolith
**Status:** Accepted (Stage A)

**Context.** One development team; one relational database; strongly transactional workflows (imports, assessments, certification); no requirement for independent scaling of parts of the system.

**Decision.** Build one backend application organised into domain modules with enforced boundaries (routes → services → models; cross-module access via services only; external systems via adapters). Frontend and backend remain independent projects in one repository.

**Consequences.** Simple deployment, local transactions, easy refactoring. Discipline is needed to keep module boundaries clean; boundaries are documented in the system architecture and checked in review. Extraction of a module into a service remains possible if a justified need arises.

## ADR-002 — React + TypeScript SPA built with Vite
**Status:** Accepted

**Context.** The LMS is an authenticated application, not a public content site; SEO and server rendering are not required. The project stack specifies React, TypeScript and Vite.

**Decision.** Client-rendered SPA scaffolded with `create-vite` (`react-ts` template) directly in `LMS_Frontend/`. React Router 8 in data-router mode (`createBrowserRouter`) with a route table shared by the app and tests.

**Consequences.** Static build artefacts served by the reverse proxy; fast dev server. Initial bundle size must be watched; route-level code splitting will be introduced as modules arrive.

## ADR-003 — Tailwind CSS v4 via `@tailwindcss/vite`
**Status:** Accepted

**Decision.** Use the first-party Vite plugin and CSS-first configuration (`@import 'tailwindcss'` and `@theme` tokens in `src/styles/index.css`). No `tailwind.config.js`, no PostCSS configuration (v3 patterns are not used).

**Consequences.** Design tokens (brand colours, font stack) live in CSS. Brand colours are provisional until official brand guidelines are supplied.

## ADR-004 — TanStack Query for server state
**Status:** Accepted

**Decision.** All API data goes through TanStack Query hooks (caching, polling, retries, cancellation). UI-only state stays local. No Redux/Zustand-style store until a concrete cross-cutting client-state need appears. Client errors (4xx) are not retried; transient failures are retried once.

**Consequences.** Less hand-written loading/error state; consistent behaviour. Query keys are defined per feature (e.g. `healthQueryKeys`).

## ADR-005 — i18next with bundled resources
**Status:** Accepted

**Decision.** i18next + react-i18next with one `common` namespace per language (`en`, `bn`, `hi`, `gu`) bundled into the build. English is the fallback. The user's choice is stored on the device; otherwise the browser language is used. Translation keys are type-checked; a test enforces key parity and non-empty values across languages. No language-detector dependency: the small amount of detection logic is implemented directly.

**Consequences.** Simple and offline-safe. When the catalogue grows, resources will be split into namespaces and lazy-loaded per language. Stage A translations are drafts pending native-speaker review.

## ADR-006 — FastAPI with synchronous SQLAlchemy 2 and PyMySQL
**Status:** Accepted

**Context.** Expected load is moderate (one company's workforce). Async database drivers add complexity (async sessions, lazy-loading pitfalls, Alembic integration) without a demonstrated need.

**Decision.** Synchronous SQLAlchemy 2.x ORM with PyMySQL (`mysql+pymysql`), `pymysql[rsa]` for MySQL 8's `caching_sha2_password`. Database-touching endpoints are `def` (run in FastAPI's thread pool); purely in-memory endpoints may be `async def`.

**Consequences.** Mature, well-understood stack; pure-Python driver installs anywhere. If profiling ever shows thread-pool saturation, async can be introduced per module.

## ADR-007 — MySQL 8, utf8mb4, UTC
**Status:** Accepted

**Decision.** MySQL 8 (InnoDB), `utf8mb4` / `utf8mb4_0900_ai_ci`, timestamps as UTC `DATETIME(6)` with the session time zone forced to `+00:00`, business dates as `DATE`. Dedicated LMS schema and least-privilege accounts, separate from the PMS.

**Consequences.** Correct storage and sorting for all four languages; no time-zone ambiguity. Display-time conversion is the frontend's responsibility.

## ADR-008 — Alembic for all schema changes; no business tables in Stage A
**Status:** Accepted. Stage B added the first revisions (`0001`–`0003`) under this rule; ADR-041 adds the migration-credential separation.

**Decision.** Every schema change is a reviewed Alembic revision. The migration environment reads the URL only from LMS settings, enables type comparison, and requires `-x allow_production=true` for online production migrations. Stage A ships the environment with **zero revisions**. A deterministic constraint naming convention is defined on the declarative base.

**Consequences.** Reproducible schemas; safe, explicit production changes. Because MySQL DDL is not transactional, revisions must be small.

## ADR-009 — `LMS_`-prefixed settings with no fallback database
**Status:** Accepted

**Context.** The development machine hosts other systems (including, potentially, the PMS database on the same MySQL server). Accidentally connecting to the wrong database would be a serious incident.

**Decision.** All settings use the `LMS_` prefix (generic `DB_HOST`, `DATABASE_URL`, etc. are ignored). There is no default database and no SQLite fallback. Database settings must be all present or all absent; partial settings fail start-up. Without database settings the API still starts, liveness works, and readiness reports `not_configured`. Production requires database settings.

**Consequences.** Misconfiguration is loud, never silent. Developers must create `LMS_Backend/.env` explicitly once a dedicated database exists.

## ADR-010 — Separate liveness and readiness probes
**Status:** Accepted

**Decision.** `/api/v1/health/live` reports only that the process serves HTTP and never checks dependencies. `/api/v1/health/ready` checks dependencies (database) and returns 503 with a structured report when not ready. Error details are logged, not returned.

**Consequences.** A database outage makes instances "not ready" (removed from load balancing) without triggering restart loops. The frontend uses both to distinguish "API unreachable" from "API up, database unavailable".

## ADR-011 — Same-origin deployment, dev proxy, explicit CORS allow-list
**Status:** Accepted

**Decision.** In production the SPA and API share one origin (reverse proxy routes `/api`). In development the Vite server proxies `/api` to the backend, so the browser also sees one origin. CORS is configured only from an explicit origin list (`LMS_CORS_ALLOWED_ORIGINS`); wildcards are rejected.

**Consequences.** Session cookies remain first-party with `SameSite` protection; CSRF defence is simpler; no CORS needed in the default setup. Cross-origin setups remain possible by listing origins.

## ADR-012 — Server-side sessions, CSRF tokens, scoped RBAC
**Status:** Partially implemented in Stage B: sessions (ADR-043), CSRF (ADR-044), throttling (ADR-045) and RBAC with access roles (ADR-046). Organisation-unit scoping of role assignments is deferred to Stage C; the login method remains open (Q-07). Extended in Stage A.1 by ADR-032; the "role" terminology here means **access roles** (ADR-023).

**Decision.** Opaque session tokens in `HttpOnly`/`Secure`/`SameSite` cookies with server-side session records (token hash only), idle/absolute expiry, rotation and revocation. Synchronizer CSRF token in a header for state-changing requests plus `Origin` checks. Permissions grouped into configurable roles; role assignments optionally scoped to an organisation unit and its descendants. Login method(s) — corporate SSO and/or local credentials for shop-floor employees — to be confirmed with the business.

**Rejected alternative.** JWTs in browser storage: exposed to XSS, hard to revoke, and unnecessary for a same-origin application.

## ADR-013 — Configurable, effective-dated organisation model
**Status:** Proposed (Stage C). Extended in Stage A.1 by ADR-023 (functional roles, responsibilities).

**Decision.** Unit types, units, locations, job families, grades, designations, positions, employees, assignments and reporting relationships are separate entities. Hierarchy is stored as effective-dated parent links (one current parent per unit, multiple roots allowed, cycles rejected). All time-varying facts use half-open `[effective_from, effective_to)` periods; changes close and insert rows, corrections update in place with an audit entry. Reporting relationships are typed employee-to-employee links. Subtree queries use recursive CTEs; a closure-table cache may be added only if profiling requires it.

**Consequences.** Any depth and any structure can be represented, including incomplete data; history is queryable. Write paths are more complex (period management, cycle checks) and must be well tested.

## ADR-014 — Safe, staged Excel import pipeline
**Status:** Superseded by ADR-029 (Stage A.1), which generalises this pipeline to six import profiles. The text below is kept as the original record.

**Decision.** Imports proceed through upload → inspect → map → validate → diff → preview → explicit confirmation → single-transaction commit → report, with saved column-mapping profiles, natural-key matching, new/updated/unchanged classification, row-level issues, downloadable error reports, stale-preview detection, idempotent re-imports and full audit. Absence from a file never deletes data by default. `.xlsx` only, parsed with `openpyxl` (read-only) and hardened XML parsing.

**Consequences.** Administrators can load partial, messy HR data safely. The pipeline requires staging tables and careful UX.

## ADR-015 — Provider-independent AI layer; Claude first; mandatory human review
**Status:** Proposed (now Stage L after the A.1 roadmap revision). Extended by ADR-033 (governance workflow: SME validation, HR approval) and ADR-034 (human oversight of assessments). Use cases extended with AI learning-path recommendations.

**Decision.** Use-case services depend on an `AIProvider` protocol in `app/services/ai/`; provider adapters live in `app/integrations/ai/`. The initial adapter uses Anthropic's official `anthropic` SDK. Model IDs and credentials are configuration; credentials are passed explicitly (no implicit SDK credential discovery). AI-generated learning material and questions are stored as drafts and cannot be published without recorded human review. No external AI calls and no AI credentials exist in Stage A.

**Consequences.** Providers can be swapped or mixed per feature; governance (cost, privacy, quality) is centralised.

## ADR-016 — Structured logging with the standard library
**Status:** Accepted

**Decision.** Standard-library `logging` with custom JSON and console formatters; a pure-ASGI middleware assigns/propagates `X-Request-ID` via a context variable, logs one line per request, and adds baseline security headers. Uvicorn logs are routed through the same formatter; uvicorn's access log is disabled to avoid duplicates. No extra logging dependency.

**Consequences.** Machine-parseable logs correlated by request ID, with no third-party dependency. Query strings are not logged.

## ADR-017 — Uniform JSON error envelope
**Status:** Accepted

**Decision.** All errors return `{"error": {"code", "message", "details"?, "request_id"}}`. Validation errors list field locations and messages but never echo submitted values. Unhandled exceptions produce a generic 500 with the request ID.

**Consequences.** One error-handling path in the frontend (`ApiError`); support staff can trace issues via request ID.

## ADR-018 — ESLint for frontend linting
**Status:** Accepted

**Context.** `create-vite` 9 defaults React templates to Oxlint; the project brief specifies ESLint.

**Decision.** Scaffold with `--eslint`; use the template's flat config (`@eslint/js`, `typescript-eslint`, `react-hooks`, `react-refresh`); CI treats warnings as errors.

**Consequences.** `npm audit` currently reports a moderate advisory in a transitive `minimatch` dependency of ESLint/typescript-eslint (development tooling only, not shipped to browsers). The only automatic fix downgrades ESLint; we will upgrade when patched releases are available.

## ADR-019 — Python 3.13 locally; code targets 3.12+
**Status:** Accepted

**Context.** The brief specifies Python 3.12; the development machine has Python 3.13.16 only.

**Decision.** `requires-python = ">=3.12"`; Ruff targets `py312` and mypy checks against 3.12 so no 3.13-only features creep in. Development and testing use 3.13. Production may use 3.12 or 3.13.

**Consequences.** No second interpreter needs to be installed system-wide. A CI job on 3.12 is recommended once CI exists.

## ADR-020 — Pure-Python SQLAlchemy and mypy on Application-Control-restricted Windows
**Status:** Accepted

**Context.** Windows Application Control (Smart App Control / WDAC) on the development machine blocks SQLAlchemy 2.1's compiled Cython extensions and mypy's mypyc-compiled modules (`ImportError: DLL load failed … An Application Control policy has blocked this file`). It also blocked the pip-generated `alembic.exe` launcher.

**Decision.** On affected machines, install SQLAlchemy built without C extensions (`DISABLE_SQLALCHEMY_CEXT=1 … --no-binary sqlalchemy`) and mypy from source (`--no-binary mypy`, which is not mypyc-compiled), and run tools as modules (`python -m alembic`, `python -m uvicorn`, `python -m pytest`). Commands are documented in the README.

**Consequences.** Slightly slower SQLAlchemy row processing and slower mypy runs on those machines; no functional difference. Linux servers and CI use the normal compiled wheels.

## ADR-021 — HTTPX 2 for API tests
**Status:** Accepted

**Context.** Starlette 1.x's TestClient deprecates the original `httpx` package in favour of `httpx2`, the HTTPX 2.x line (same author, maintained by Pydantic).

**Decision.** Use `httpx2` as the test HTTP client dependency.

**Consequences.** No deprecation warnings; aligned with the current FastAPI/Starlette toolchain.

---

# Stage A.1 decisions (architecture alignment)

All ADR-022…039 are **Proposed**: designed in Stage A.1, implemented in the roadmap stage noted. Requirement labels ([C]/[P]/[A]/[F]) are defined in [product requirements §0](../product/LMS_PRODUCT_REQUIREMENTS.md).

## ADR-022 — Learning hierarchy composed by reference and versioned
**Status:** Proposed (Stages G–H)

**Context.** Crescent Foundry requires the hierarchy Learning Academy → Learning Path → Curriculum → Learning Assets [C], with mandatory/optional curriculum items, path sections, sequence, minimum completion, deadlines, validity, retraining, visibility, approvals, certificates and reinforcement [C].

**Decision.** Separate entities for academy, path, curriculum and asset. Paths contain **sections** of **path items** referencing curricula; curricula contain **items** referencing assets. Paths, curricula and assets have immutable **published versions**; enrolments pin the path/curriculum version and progress records the asset version used. Asset types share one `learning_asset` supertype with typed subtype tables (not a generic JSON blob). Classroom and OJT assets point into training operations and practical evaluation respectively. Visibility and allocation use reusable audience rules. "Course" is not a separate entity: it is the everyday name for a curriculum.

**Consequences.** Reuse without copying; learners' records stay explainable after content changes. More tables and version-resolution logic; governance applies per version.

## ADR-023 — Access roles separate from functional roles; functional roles and responsibilities
**Status:** Access roles implemented in Stage B (ADR-046); functional roles, responsibilities and provisioning rules remain Proposed (Stage C). Extends ADR-013.

**Context.** The brief requires functional roles, responsibilities and designation-to-role mapping, and that an employee's application access role is separate from their functional job role [C].

**Decision.** `access_role` (identity domain, assigned to user accounts, scoped) and `functional_role` (organisation domain, assigned to employees, effective-dated) are different tables with different names. Functional roles are derived from designation (optionally unit-scoped) and position mappings, plus manual assignments and exclusions. Responsibilities are separate, effective-dated duties that can drive compliance and allocations. Functional roles never grant permissions; default access provisioning uses explicit, audited rules.

**Consequences.** Clear separation of "what you may do in the LMS" and "what work you do". Role resolution logic must be well tested.

## ADR-024 — Configurable competency framework
**Status:** Proposed (Stage F)

**Decision.** Skill-level sets with ordered levels (numeric value, translated label, description) are data. The Bagnan 1–5 scale (Beginner; Can Work Under Supervision; Can Work Independently; Expert; Can Train Others) [C] is loaded as the first set, not hardcoded. Competency skills reference one set; functional roles carry required levels; curricula map to competencies with a maximum contribution level. Employee levels derive from approved skill assessments and achievements, with history.

**Consequences.** Other plants or skills can use different scales; comparisons happen within a set.

## ADR-025 — Evidence chain: separate records for completion, competency, compliance and authorisation
**Status:** Proposed (Stages H–J)

**Context.** Competency must be achievable through course completion, theory assessment and practical validation per configured rules, and operational authorisation must never be awarded solely for completing an online curriculum [C].

**Decision.** Completion (enrolment), assessment attempts, attendance, practical evaluations, competency achievements, compliance status and certificate issuances are separate records linked by typed evidence references. Achievement rules list required evidence per skill and level; levels implying independent operational work require practical validation (default threshold Bagnan level 3, to confirm). Certifications of kind *authorisation* require a practical validation and signatory approval, enforced by a database CHECK on the certification definition and by the issuance service.

**Consequences.** Auditable "why does this person hold this level/authorisation"; rules need careful configuration UX.

## ADR-026 — Compliance skills separate from competency skills
**Status:** Proposed (Stage J)

**Decision.** `compliance_skill` is its own catalogue: binary, validity-based, with requirement rules (audiences by role, responsibility, location, unit, designation, employment type) and fulfilment options (certificate, curriculum completion within validity, verified external certificate). Compliance status per employee is a derived cache with states compliant / due soon / expired / missing / not applicable / exempt.

**Consequences.** Compliance reporting is simple and plant-wise; competency scales stay free of pass/fail semantics.

## ADR-027 — Training operations: planned and actual separate; finalisation locks events
**Status:** Proposed (Stage E)

**Context.** A calendar entry must not be treated as a completed event; a planned participant count must not be treated as individual attendance; planned and actual records must be separate [C].

**Decision.** `planned_training_activity` (calendar line, with planned count) and `training_event` → `training_batch` → `training_session` → `attendance_record` (per employee per session) are separate tables. An event optionally references the planned activity it fulfils. Training programmes link plans, events and classroom curriculum items across years. Finalisation locks attendance, computes hours/manhours into a derived table and triggers downstream effects; reopening needs elevated permission; corrections are separate audited records.

**Consequences.** Calendar vs Actual is a true comparison. Coordinators must finalise events for hours and completions to count.

## ADR-028 — Immutable certificate issuances
**Status:** Proposed (Stage J)

**Decision.** Each issuance is a row with a unique certificate number, dates, template version, stored PDF and hash, and a random verification token (hash stored). Status changes (suspend, reinstate, revoke, supersede) are `certificate_status_event` rows; the issuance's status column mirrors the latest event. **Renewal creates a new issuance** referencing the previous one. Substantive fields are protected by triggers and service rules. External certifications are separate records with verification status. Completion and appreciation templates are separate, versioned, and based on the supplied Crescent designs [C] (designs not yet in the workspace, [A] Q-10).

**Consequences.** Historical evidence never changes; the register and verification page always reflect truthful history.

## ADR-029 — Reusable import framework with profiles
**Status:** Proposed (Stages D–F). Supersedes ADR-014.

**Decision.** One pipeline (upload → inspect → map → validate → match/duplicate candidates → diff → preview → confirm → transactional commit) with six profiles: organisation & employees, skill matrices, development plans, annual calendars, safety calendars, attendance & historical records [C]. Wide matrices are unpivoted per cell. Every record keeps **source provenance** (file, sheet, row, column). Similar records become **duplicate candidates** with recorded decisions — never automatically discarded [C]. Compensation columns (CTC etc.) are dropped at parse time via a protected exclusion list and never stored [C]. Details: [EXCEL_IMPORT_PROFILES.md](../database/EXCEL_IMPORT_PROFILES.md).

**Consequences.** Overlapping consolidated/departmental calendars can be reconciled safely; more administrator decisions during first imports.

## ADR-030 — Preserve raw source values; confirmed mappings only
**Status:** Proposed (Stage F)

**Decision.** Where source values carry unconfirmed meaning (development-plan indicators such as "Y", "US" [C]), the raw value is stored on the business record and an optional `source_value_mapping` translates it only when marked *confirmed* by an authorised user. Unmapped values are never dropped.

**Consequences.** No invented semantics; reports can show raw indicators until meanings are confirmed (Q-01).

## ADR-031 — Three experiences and kiosk mode in one SPA
**Status:** Proposed (from Stage B). Stage B started the HR/Admin Control Room area with read-only `/admin/users` and `/admin/audit-log` pages and permission-driven navigation (ADR-050); the other areas are not built yet.

**Decision.** Learner Portal (`/`, mobile-first), Manager Portal (`/manager`), HR/Admin Control Room (`/admin`), kiosk mode (`/kiosk`) and public verification (`/verify/:token`) are route areas with separate layouts in the existing React application, sharing the API client, i18n and components. Navigation is permission-driven.

**Rejected alternative.** Separate frontend projects: duplicated tooling and i18n for no current benefit.

## ADR-032 — Employee ID login, kiosk-bound PIN, badge QR tokens, idle logout
**Status:** Partially implemented in Stage B: server-enforced idle and absolute session expiry (ADR-043). Not implemented: kiosk PIN sign-in, kiosk registration and badge QR tokens (Q-08, Q-09 open); the personal-device credential (password today) and SSO remain open (Q-07). Accounts are not yet linked to employee codes (ADR-040). Extends ADR-012.

**Decision.** Login identifier = employee code [C]. PIN sign-in only on administrator-registered kiosks holding a device token [C]/[P]. Badge QR encodes a revocable random token (hash stored), never the bare employee code; **badge identifies, PIN authenticates**; a badge alone opens no session (an authenticated trainer may scan badges for attendance). Automatic idle logout enforced server-side with client countdown (defaults: 30 min personal, 2 min kiosk) [C]/[P]. Re-authentication for sign-offs. Personal-device credential and SSO remain open (Q-07).

**Consequences.** Shop-floor-friendly access without weakening account security; requires badge (re)issuance process (Q-08).

## ADR-033 — Content governance: SME validation, HR final approval
**Status:** Proposed (Stage G). Extends ADR-015.

**Decision.** Draft → department SME technical validation → (safety review for safety-critical content) → HR approval → Published → Retired, recorded in `content_review_task`, for assets, curricula, paths, official assessments, questions, practical checklists and certificate templates. **HR is the final approval and publishing authority** [C]; **department SMEs validate technical content** [C]. AI drafts enter at Draft.

## ADR-034 — Human oversight of official assessments and practical validations
**Status:** Proposed (Stage I)

**Decision.** Practice mode may be fully automatic. Final results containing subjective answers require an authorised evaluator; practical evaluations are performed and submitted by authorised assessors and acknowledged by the employee; submitted evaluations are immutable (void-and-redo for corrections). AI may suggest, never finalise [C].

## ADR-035 — Configurable financial year
**Status:** Proposed (Stage E)

**Decision.** `financial_year` rows (default 1 April – 31 March, Q-13) anchor calendars, development plans and hours reporting; FY is never computed ad hoc from dates in reports.

## ADR-036 — Reporting through scoped read models
**Status:** Proposed (Stage K)

**Decision.** Reports read SQL views over normalised tables plus derived caches; every query is filtered by the caller's access-role scope; exports audited and formula-injection-safe. No separate reporting database initially.

## ADR-037 — Shared survey component
**Status:** Proposed (Stages E, G)

**Decision.** One versioned survey model serves learning-asset surveys and training-event feedback, with typed context links and optional anonymity.

## ADR-038 — Typed foreign keys and immutable evidence
**Status:** Proposed (all stages)

**Decision.** Cross-domain references use typed nullable FKs with exactly-one CHECKs; generic `(entity_type, entity_id)` only for audit, provenance, notifications and import aliases. Evidence records (approved skill assessments, achievements, graded attempts, submitted evaluations, finalised attendance, certificate issuances, historical records, audit log) are immutable; corrections are new records. Derived caches are rebuildable and never edited directly.

## ADR-039 — Domain events and a scheduler/worker
**Status:** Proposed (Stages E–H)

**Decision.** Atomic cross-domain effects run as explicit service calls in the originating transaction; recalculations of derived caches run from in-process domain events after commit, idempotently. Scheduled work (expiry reminders, retraining, reinforcement, notifications, heavy report aggregates) runs in a separate worker process. The concrete library is chosen when first needed (no dependency added now).

---

# Stage B decisions (identity, access and audit)

ADR-040…050 record what Stage B **implemented** (backend phases B0–B5, frontend B6). Earlier records they refine (ADR-008, 012, 023, 031, 032) keep their original text; only their status lines were updated. Parameters marked *configurable* are `LMS_` settings; their default values await business confirmation (Q-43).

## ADR-040 — User accounts separate from employee identity
**Status:** Accepted (Stage B)

**Context.** Organisation and employee data arrive in Stage C/D, but administrators must be able to sign in before then. Stage A.1 requires that an account's access role is independent of the employee's job (ADR-023).

**Decision.** A `user_account` is a system login identity, not an employee record. It has a `login_id` (1–64 characters, `[A-Za-z0-9._-]`, unique and case-insensitive through the column collation), a display name, an optional unique e-mail, a password hash, and a lifecycle status: `pending_activation`, `active`, `suspended` or `disabled`. A CHECK requires a password for active accounts. Accounts created by administrators start as `pending_activation` with a temporary password and `password_must_change`. Suspending or disabling an account revokes its sessions. There is **no employee column yet**: Stage C adds a nullable, unique `employee_id` without changing existing rows. ADR-032's convention that an employee's login identifier is the employee code is applied when employee accounts are provisioned (Stage C/D); it is not enforced in Stage B.

**Consequences.** Accounts can exist before, or without, employee records (for example administrators). Designations, functional roles and job titles grant nothing.

## ADR-041 — Migration/runtime credential separation; isolated, verified test database
**Status:** Accepted (Stage B). Refines ADR-008 and ADR-009.

**Decision.**
- **Three MySQL accounts.** `lms_app` (runtime) has only `SELECT, INSERT, UPDATE, DELETE` on the LMS schema. `lms_migrator` (Alembic only) has DDL plus `TRIGGER` on the same schema. `lms_test` owns the automated-test schema.
- **Separate settings.** `LMS_MIGRATION_DB_USER/PASSWORD` must differ from `LMS_DB_USER`. `alembic/env.py` refuses to run without migration credentials, never falls back to the runtime account, and checks `SELECT DATABASE()` against `LMS_DB_NAME` after connecting.
- **Transaction ownership.** `env.py` commits the transaction that its pre-flight query auto-began. Otherwise Alembic treats the connection as externally managed and the final `alembic_version` update is rolled back. A regression test covers the CLI path.
- **Automated database tests.** They run **only** against `crescent_lms_test`, as MySQL account `lms_test@127.0.0.1`. Every connection checks `SELECT DATABASE(), CURRENT_USER()` before running anything; the name must end in `_test`, differ from `LMS_DB_NAME`, and equal the pinned name. Settings come from `LMS_Backend/.env.test` (git-ignored). Unit tests never read `.env`.
- **Test-schema rebuild.** Once per test session, the schema is rebuilt independently of leftover data. The rebuild drops every foreign key, then every table, in the verified test schema, then runs `upgrade head` → `downgrade base` → `upgrade head`. Each phase is its own transaction, and its **committed** state is verified on a separate connection.

**Rejected alternatives.**
- Running migrations as the runtime account: it would need DDL rights permanently.
- Resetting with `downgrade base` alone: leftover rows that reference seed data (for example browser-test role grants) make it fail part-way, and MySQL DDL cannot be rolled back.

**Consequences.** A compromised application cannot alter the schema. A failed rebuild cannot leave tests running on a partial schema, and the next run repairs it. Allowing any other test database or account needs a reviewed code change.

## ADR-042 — Argon2id password hashing and password policy
**Status:** Accepted (Stage B)

**Decision.**
- **Hashing.** Passwords are hashed with Argon2id using `argon2-cffi`'s defaults. Hashes are upgraded transparently on login when the parameters change (`needs_rehash`).
- **Normalisation.** Passwords are NFKC-normalised before hashing and verification.
- **Policy (NIST SP 800-63B style; no composition rules):**
  - minimum length configurable, default 12 (`LMS_PASSWORD_MIN_LENGTH`);
  - maximum 128;
  - must not contain the login ID;
  - must not be a single repeated character;
  - must not be on a small common-password deny-list;
  - a new password must differ from the current one.
- **Timing.** Unknown login IDs are verified against a dummy hash, so response time does not reveal whether an account exists.
- **Secrecy.** Passwords are `SecretStr` in request schemas, are never logged and never appear in audit metadata.

**Consequences.** A memory-hard hash resists offline guessing. Policy failures return typed issue codes that the UI translates.

## ADR-043 — Server-side sessions and session cookie
**Status:** Accepted (Stage B). Implements the session part of ADR-012 and the idle logout of ADR-032.

**Decision.**
- **Token.** Sign-in creates a `user_session` with a 256-bit random token. Only its SHA-256 hash is stored.
- **Cookie.** The token is sent in a cookie that is `HttpOnly`, `Path=/`, host-only, `SameSite=Lax` (configurable) and `Secure` (configurable; forced in production). The cookie is named `__Host-lms_session` when Secure and `lms_session` for local plain-http development.
- **Expiry.**
  - Idle expiry is configurable, default 30 minutes, and sliding: authenticated requests extend it, writing at most once per minute.
  - Absolute expiry is configurable, default 12 hours.
  - The public `GET /auth/session` check never extends the idle window.
- **Rotation.** Signing in revokes any session cookie already presented, which prevents session fixation. Changing the password revokes all of the user's sessions and issues a new one.
- **Revocation.** Administrators with `user_sessions.revoke` can revoke one or all sessions. Invalid or expired cookies are cleared.

**Rejected alternative.** JWTs or tokens in browser storage (see ADR-012): exposed to XSS and hard to revoke.

**Consequences.** Sessions can be ended instantly server-side. A database read on each authenticated request is acceptable at LMS scale.

## ADR-044 — CSRF protection: trusted origins plus session-bound token
**Status:** Accepted (Stage B). Implements the CSRF part of ADR-012.

**Decision.** There are two layers.
1. **Trusted origin.** `TrustedOriginMiddleware` rejects every POST/PUT/PATCH/DELETE whose `Origin` (or, failing that, `Referer`) is not in `LMS_TRUSTED_ORIGINS`, with `403 origin_not_allowed`. This also covers sign-in, which has no session yet (login CSRF).
2. **Session-bound token.** Authenticated state-changing requests must send `X-CSRF-Token`, equal to HMAC-SHA256(`LMS_SECRET_KEY`, session-token hash) and compared in constant time; otherwise `403 csrf_failed`.

The token is returned in the bodies of the sign-in, `GET /auth/session` and password-change responses. It changes whenever the session rotates. The frontend keeps it in memory only (ADR-050). CORS (ADR-011) is configured separately and is not relied on for CSRF.

**Consequences.** No token storage server-side; a stolen token is useless without the matching session. Opening the app from an origin that is not listed makes sign-in fail until that origin is added.

## ADR-045 — Database-backed login throttling
**Status:** Accepted (Stage B)

**Decision.**
- **Counters.** Failed sign-ins and failed password changes are counted in `login_throttle`, per identifier and per client IP. Keys are HMACs, never raw login IDs or IPs.
- **Limits** (all configurable): 5 failures per identifier or 20 per IP within 15 minutes trigger a 15-minute lockout, reported as `429 too_many_attempts`.
- **Concurrency.** Rows are updated with `INSERT … ON DUPLICATE KEY UPDATE` plus `SELECT … FOR UPDATE`, so the limits hold across multiple worker processes without Redis.
- **Enumeration.** Unknown login IDs are throttled like real ones.
- **Separation.** Throttling is separate from account status: a lockout expires and never disables the account.

**Consequences.** No extra infrastructure. Per-IP limits depend on the real client IP, so production behind a reverse proxy must run Uvicorn with `--proxy-headers --forwarded-allow-ips=<proxy>`.

## ADR-046 — RBAC with permission codes; seeded roles; assignment guards
**Status:** Accepted (Stage B). Implements the RBAC part of ADR-012 and the access-role part of ADR-023.

**Decision.**
- **Permissions.** 17 permission codes (`area.action`, for example `audit.view`). Three are privileged: `user_roles.assign_admin`, `access_roles.manage` and `settings.manage`.
- **Roles.** Six system access roles: `employee`, `supervisor`, `hod`, `sme`, `hr_admin` and `super_admin`. They and their role–permission mapping are seeded by a **versioned data migration** (`0002`), not by application code.
- **Enforcement.**
  - Each route declares `require_permission(...)`, which is deny-by-default.
  - A route-inventory test fails if any `/api/v1` route other than the public allow-list (health checks, `POST /auth/login`, `GET /auth/session`) lacks authentication.
  - Denials return `403 forbidden` and are audited as `authorization.denied`.
  - Accounts that must change their password get `403 password_change_required` on every permission-guarded route.
- **Assignment guards.** These are data-driven: no role names in business logic.
  - A role can be granted only if it is API-assignable and the actor holds its `assign_permission`, plus every permission the role carries (no escalation).
  - Self-modification is refused.
  - Accounts holding permissions the actor lacks cannot be managed.
  - HR Admins can grant Employee, Supervisor, HOD and SME. Only Super Admins can grant HR Admin (`user_roles.assign_admin`).
  - `super_admin` is never API-assignable (ADR-047).
  - Privileged permissions cannot be added to non-Super-Admin roles.
- **Deferred.** Organisation-unit scoping of role assignments is deferred to Stage C.

**Consequences.** Permission sets can change through audited data, not code. The UI decides visibility from permission codes (ADR-050), while the API remains the only enforcement point.

## ADR-047 — Super Admin bootstrap only through the CLI
**Status:** Accepted (Stage B)

**Decision.** There is no default administrator, no seeded credential and no HTTP bootstrap endpoint. `python -m app.cli create-super-admin --login-id … --display-name …`:
- requires an interactive terminal;
- shows the target host and database, which the operator must confirm by typing the database name;
- reads the password twice with `getpass` (no echo) and applies the password policy;
- in one transaction, locks the `super_admin` role row, refuses if any active Super Admin exists, creates an active account, grants the role and writes `super_admin.bootstrapped` (channel `cli`, OS operator).

`grant-super-admin` and `revoke-super-admin` are the only ways to change Super Admin membership. Both are audited, and the last Super Admin cannot be revoked. The CLI uses the restricted runtime account, never the migration account.

**Consequences.** Highest privilege needs shell access to the server plus the application configuration. Operators run the bootstrap themselves; credentials are never chosen by tooling.

## ADR-048 — Audit event model and append-only protection
**Status:** Accepted (Stage B)

**Decision.**
- **Model.** `audit_event` rows record time (UTC), event type, outcome (`success`/`failure`/`denied`), actor, target, request ID, source IP, user agent and JSON metadata.
- **Atomicity.** Rows are written **in the same transaction** as the change they describe.
- **Metadata guard.** Keys containing `password`, `token`, `secret`, `hash`, `csrf`, `cookie` or `credential` are rejected. Failed sign-ins for unknown login IDs store only an HMAC fingerprint.
- **Read API.** The audit API is read-only, and every read is itself audited (`audit.events.viewed`).
- **Append-only, three layers:**
  1. no update or delete code paths or routes;
  2. an ORM `before_flush` guard that raises on any modified or deleted audit event;
  3. MySQL `BEFORE UPDATE` and `BEFORE DELETE` triggers that `SIGNAL SQLSTATE '45000'` (migration `0003`).

  The triggers are created by `lms_migrator`. With binary logging enabled, MySQL requires either the SUPER/SET_USER_ID privilege or `log_bin_trust_function_creators=1` to create them.

**Environment-specific requirement.** The **local development** MySQL instance uses `SET PERSIST log_bin_trust_function_creators = 1`, approved for local development only. **Production and any shared company database require a separate DBA decision** before migration `0003` can be applied there. No LMS account is granted SUPER or SET_USER_ID.

**Limitations (by design, stated explicitly):**
- The triggers stop UPDATE and DELETE only. **`TRUNCATE TABLE` and `DROP TABLE` bypass them.**
- An account with DDL or TRIGGER rights (the migration account) can drop the triggers.
- The audit trail is therefore **not universally tamper-proof**. It is protected against the application runtime account and against application bugs.
- The **migration credentials are privileged and must be protected**: kept out of the runtime environment and used only for migrations.
- Stronger guarantees (for example shipping events to an external write-once store) are future options, not implemented.

**Consequences.** Retention periods for audit data remain open (Q-21).

## ADR-049 — UUIDv7 public identifiers; internal keys never exposed
**Status:** Accepted (Stage B). Implements ADR-038's identifier convention for identity and audit.

**Decision.** Records exposed outside the database carry a `public_id` stored as `BINARY(16)` and generated as UUIDv7 (RFC 9562) by `app/core/ids.py`; Python 3.12/3.13 have no built-in generator. `BIGINT` primary keys are internal and never appear in API responses, URLs or audit targets.

**Consequences.** Identifiers reveal neither row counts nor creation order of unrelated records, and the time-ordered prefix keeps index inserts efficient.

## ADR-050 — Frontend authentication and session restoration
**Status:** Accepted (Stage B6). Applies ADR-043/044 in the browser.

**Decision.**
- **Credentials.** The SPA never sees the session token; requests are same-origin with `credentials: 'same-origin'`. The CSRF token is held only in the API client's memory and sent on POST/PUT/PATCH/DELETE. On `403 csrf_failed` the client re-reads the session once and retries once.
- **Restore and expiry.** `AuthProvider` restores user, permissions and CSRF token after a reload via `GET /auth/session`. It re-checks on window focus and when the server-reported expiry passes. An unreachable API is shown as an error, never as "signed out". A `401 unauthenticated` returns the user to sign-in.
- **Sign-out.** Every cached query except health is purged.
- **Routing.**
  - Everything except `/login` requires a session.
  - The post-login redirect comes only from router state and must be an internal path (no open redirect).
  - Users who must change their password are held on `/change-password`.
- **Permissions.** Screens and navigation check **permission codes**, never role names. This is a UX layer only; the API enforces every permission.
- **Audit page.** Because every audit read is audited, the Audit Log page fetches only on open, filter, Refresh and Load more, never on window focus. Its request is not tied to the query's abort signal, so React StrictMode's development remount does not send a duplicate audited read.
- **Storage.** `localStorage` holds only the language preference. Response parsers whitelist fields, so unexpected fields (for example a hash) never reach the cache or the UI.

**Consequences.** Tokens are not exposed to scripts; multi-tab sign-in and sign-out converge through the focus re-check, the 401 handling and the CSRF retry.
