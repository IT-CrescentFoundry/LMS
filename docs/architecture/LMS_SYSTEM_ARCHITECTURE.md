# LMS System Architecture

| | |
|---|---|
| **Status** | Stage A implemented the foundation; Stage A.1 aligned the architecture with the extended business requirements. Sections are marked **Implemented** or **Planned**; planned items are designs, not working features. |
| **Labels** | **[C]** confirmed · **[P]** proposed · **[A]** assumption (register `Q-xx` in [product requirements §13](../product/LMS_PRODUCT_REQUIREMENTS.md)) · **[F]** future |
| **Related** | [Product requirements](../product/LMS_PRODUCT_REQUIREMENTS.md) · [Competency & compliance](../product/COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md) · [Training operations](../product/TRAINING_OPERATIONS_REQUIREMENTS.md) · [Organisation architecture](ORGANISATION_ARCHITECTURE.md) · [Database design](../database/LMS_DATABASE_DESIGN.md) · [Import profiles](../database/EXCEL_IMPORT_PROFILES.md) · [Decisions](../decisions/ARCHITECTURAL_DECISIONS.md) · [Roadmap](../LMS_IMPLEMENTATION_ROADMAP.md) |

---

## 1. Overview

```text
 Phones · Tablets · Laptops · Desktops · Shared kiosks
            │  HTTPS (one origin)
            ▼
 ┌─────────────────────────────────────────────┐
 │ Reverse proxy (planned)                     │  TLS, static files, security headers
 │  /        → React SPA                       │   Learner Portal · Manager Portal ·
 │  /api/*   → FastAPI                         │   HR/Admin Control Room · Kiosk mode
 └──────────────────┬──────────────────────────┘
                    ▼
 ┌─────────────────────────────────────────────┐      ┌───────────────────────┐
 │ LMS API — FastAPI modular monolith          │─────►│ MySQL 8 — dedicated   │
 │ identity · organisation · learning ·        │      │ LMS schema            │
 │ assessment · competency · compliance &      │      └───────────────────────┘
 │ certification · training operations ·       │      ┌───────────────────────┐
 │ imports · reporting · ai · notifications    │─────►│ Protected file store  │ (planned)
 └───────┬─────────────────────┬───────────────┘      └───────────────────────┘
         ▼                     ▼
   AI provider            Future: PMS (separate application and database),
   (Claude via            identity provider, email/SMS — via integration adapters
   provider-neutral       (planned; nothing implemented)
   interface)
```

One deployable backend and one frontend build, kept independent in the repository (`LMS_Backend/`, `LMS_Frontend/`). **[C]**

## 2. Architectural style: modular monolith — *Implemented (structure)*

A single FastAPI application organised into domain modules with explicit boundaries (ADR-001). **[C]**

**Module boundary rules** **[P]**

1. Routes contain HTTP concerns only; business logic lives in services.
2. A module accesses another module's data **through that module's service functions**, not by querying its tables directly.
3. Shared infrastructure (`app/core`, `app/db`) never imports domain modules.
4. External systems are reached only through adapters in `app/integrations`.
5. Cross-domain effects (e.g. event finalisation completing curriculum items) go through explicit service calls or in-process domain events (§6.8).

## 3. Repository layout — *Implemented*

```text
LMS/
├── LMS_Frontend/        React + TypeScript + Vite SPA
├── LMS_Backend/         FastAPI application, Alembic migrations, tests
├── docs/                architecture/, database/, decisions/, product/, roadmap
├── scripts/             check.ps1 (all quality checks)
├── .gitignore           excludes .env, virtualenvs, node_modules, build output, private data folders
├── CLAUDE.md            project instructions for AI-assisted development
└── README.md            setup and development guide
```

## 4. Frontend architecture — *Implemented (shell)*

**Stack:** React 19, TypeScript 6, Vite 8, Tailwind CSS 4 (via `@tailwindcss/vite`), React Router 8, TanStack Query 5, i18next 27 + react-i18next 18, Lucide icons. Tests: Vitest 5, React Testing Library, jsdom.

```text
src/
├── app/            providers (TanStack Query), router (route table), navigation model
├── layouts/        AppLayout (header, sidebar, mobile drawer), SidebarNav
├── features/       dashboard/, system-status/, errors/
├── components/     BrandMark, LanguageSelector, ConnectivityIndicator, LoadingState, ErrorState
├── hooks/          cross-feature hooks (none yet)
├── services/       typed API functions per backend area (healthService)
├── lib/            apiClient (typed fetch wrapper), config (env validation)
├── i18n/           i18next setup, language registry, locales/{en,bn,hi,gu}
├── styles/         Tailwind entry + design tokens (@theme)
├── types/          shared TypeScript types (API contracts, env)
└── test/           test setup and render helpers
```

**Data flow:** component → feature hook (TanStack Query) → service → `apiRequest` → `fetch`; every response passes a runtime `parse` function. **State:** server state in TanStack Query; UI state local; no global store yet. **Errors/loading:** `ApiError` (network, timeout, http, invalid_response) with backend code and request ID; shared `LoadingState`/`ErrorState`; router error boundary. **API configuration:** `VITE_API_BASE_URL` (default `/api/v1`), dev/preview proxy to the backend (ADR-011). **Responsive:** drawer navigation below `lg`, sidebar at `lg`+; verified at 360/390 px in all four languages. **Accessibility baseline:** landmarks, skip link, labelled controls, `aria-live` status, keyboard-operable drawer.

### 4.1 Planned experiences — *Planned* (ADR-031)

Three experiences plus kiosk mode, as route areas of the one SPA, each with its own layout and navigation: **[C]** (experiences) / **[P]** (structure)

| Area | Route prefix | Layout | Audience |
|---|---|---|---|
| Learner Portal | `/` | **Mobile-first**; bottom navigation on phones; dashboard, upcoming actions, Skill Passport, calendar | All employees |
| Manager Portal | `/manager` | Responsive; team-centric | Line managers, HODs |
| HR / Admin Control Room | `/admin` | Desktop-first, responsive; dense tables and workflows | HR, coordinators, SMEs, administrators |
| Kiosk mode | `/kiosk` | Large touch targets, badge scan + PIN sign-in, visible idle countdown | Registered kiosk devices |
| Certificate verification | `/verify/:token` | Public, minimal | Anyone with a certificate QR |

Visible areas and navigation come from the signed-in user's **access-role permissions** (`/api/v1/me`, Stage B). The Stage A shell's placeholder navigation will be restructured into these areas then; no frontend code changed in Stage A.1.

## 5. Backend architecture

**Stack:** Python ≥ 3.12 (developed on 3.13), FastAPI 0.162, Starlette 1.10, Pydantic 2.14, Pydantic Settings 2.16, SQLAlchemy 2.1, Alembic 1.20, PyMySQL 1.2, Uvicorn 0.54; Pytest 9, HTTPX 2; Ruff, mypy (strict).

### 5.1 Layers — *Implemented*

```text
app/
├── main.py        create_app() factory: settings, logging, middleware, routers, lifespan
├── core/          config, logging (JSON/console), middleware (request ID, security headers,
│                  access log, 500 handling), errors
├── api/           router.py (mounted at /api/v1), deps.py, routes/ (health.py)
├── services/      business logic (health_service.py)
├── schemas/       Pydantic request/response models
├── models/        SQLAlchemy ORM models (none in Stage A)
└── db/            declarative base + naming convention, engine/session management
```

### 5.2 Planned domain modules — *Planned* (revised in A.1)

Each domain adds sub-packages in `models/`, `schemas/`, `services/` and a module in `api/routes/`.

| Module | Responsibility | Stage |
|---|---|---|
| `identity` | User accounts, credentials (password, kiosk PIN), badges, kiosks, login sessions, **access roles**, scoped permissions | B |
| `audit` | Append-only audit trail | B |
| `organisation` | Units, types, plants/locations, job families, designations, positions, **functional roles**, **responsibilities**, employees, assignments, reporting | C |
| `imports` | Import framework and profiles 1–6 | D (framework), E, F |
| `training_ops` | FY calendars, planned activities, programmes, events, batches, sessions, venues, trainers, vendors, nominations, attendance, finalisation, hours, training requests, historical records | E |
| `competency` | Skill-level sets, competency skills, role requirements, mappings, skill assessments, achievements, development plans | F (core), I (achievement rules) |
| `learning` | Academies, paths, curricula, assets, versions, content governance, visibility, allocations, enrolments, progress, retraining, reinforcement | G (catalogue), H (delivery) |
| `assessment` | Question banks, assessments, attempts, manual evaluation, assignments, practical checklists and evaluations, acknowledgements | I |
| `compliance` | Compliance skills, requirement and fulfilment rules, status, exemptions; certification definitions, templates, issuances, status events, external certifications, verification, Skill Passport read model | J |
| `surveys` | Shared survey/feedback component | E (events), G (assets) |
| `reporting` | Report read models and exports | K |
| `ai` | Provider-neutral AI services | L |
| `career` | Career paths, next-role readiness | M |
| `notifications` | In-app/email notifications, `.ics` invitations | E onward |
| `files` | Protected file storage service | E onward |
| `integrations` | Adapters: AI provider, future PMS, identity provider, notification channels | as needed |

### 5.3 Database access — *Implemented (infrastructure)*

Synchronous SQLAlchemy 2 + PyMySQL (ADR-006); `def` endpoints run in the thread pool; one session per request; services commit explicitly; pool pre-ping, recycling, timeouts, `utf8mb4`, UTC session time zone; **no fallback database** (ADR-009).

## 6. Domain architecture — *Planned*

### 6.1 Domain map

```text
                    identity ── access roles (scoped) ──► who may do what
                       │
 organisation ─────────┼──────────────► functional roles, responsibilities, structure, scope
     │                 │
     ├──► competency ◄─┼─── requirements per functional role; scales; assessments; achievements
     │        ▲        │
     │        │ evidence
     ├──► learning ────┼─── academies → paths → curricula → assets; enrolments; progress
     │        ▲  │     │
     │        │  └──► assessment ─── questions, attempts, assignments, practical evaluations
     │        │                │
     ├──► training_ops ───────┼─── plans (calendar) ≠ actuals (events, sessions, attendance)
     │                         │
     └──► compliance ◄─────────┴─── certifications, issuances, compliance status, Skill Passport
                 │
             reporting (read models over all) · imports (writes into org, competency, training_ops)
```

### 6.2 Learning architecture **[C]** / structure **[P]** (ADR-022)

```text
Learning Academy (owning department)
 └── Learning Path ── version (published = immutable)
       └── Section (ordered; completion rule: all mandatory | at least N; due offset)
             └── Path item (mandatory/optional, sequence, prerequisite, due offset) ──► Curriculum
                                                                                         │ (reusable across paths)
 Curriculum ── version (validity, retraining lead time, refresher curriculum, certificate, competency mapping)
   └── Curriculum item (mandatory/optional, sequence, completion requirement) ──► Learning Asset
                                                                                    │ (reusable across curricula)
 Learning Asset ── version (localised content per language)
   ├── reference · document (PDF) · presentation · video · podcast · SCORM · external resource
   ├── assessment ─────► assessment domain
   ├── assignment ─────► assessment domain (online / face-to-face)
   ├── survey/feedback ► surveys
   ├── classroom ──────► training programme (training_ops): fulfilled by attendance at a finalised event
   └── OJT/practical ──► practical checklist (assessment): fulfilled by a submitted practical evaluation
```

Rules **[P]**:
- **Composition by reference**: paths reference curricula; curricula reference assets. Reuse is the default; copying is an explicit "duplicate" action.
- **Versioning**: published versions are immutable; edits create a new draft version that passes governance again. An enrolment pins the path/curriculum version; progress records the asset version actually used. Moving active learners to a new version is an explicit administrator decision.
- **Sequence**: `free`, `sequential`, or per-item prerequisites. **Minimum completion**: curriculum = all mandatory + at least N optional; section/path = all mandatory or at least N items.
- **Deadlines**: allocation-level due date; path items/sections may add offsets relative to enrolment.
- **Validity and retraining**: completion of a curriculum version with validity sets `valid_until`; before expiry the LMS allocates the curriculum (or its refresher curriculum) again.
- **Visibility vs allocation**: *visibility* (who may see/self-enrol) and *allocation* (who must complete, by when) both use reusable **audience rules** (unit subtree, location, designation, functional role, job family, responsibility, employment type).
- **Approvals**: content governance (§6.2.1); enrolment approvals where configured.
- **Certificates**: curriculum/path versions may name a certification of kind *completion*.
- **Reinforcement**: post-completion reinforcement tasks generated from curriculum reinforcement rules.

#### 6.2.1 Content governance **[C]** / workflow **[P]** (ADR-033)

```text
Draft ──► SME technical validation (department SME) ──► [safety review, if safety-critical] ──► HR approval ──► Published ──► Retired
  ▲                │ reject                                     │ reject                         │ reject
  └────────────────┴────────────────────────────────────────────┴────────────────────────────────┘
```

Applies to asset, curriculum and path versions, official (final) assessments, question versions, practical checklist versions and certificate template versions. **HR is the final approval and publishing authority.** AI-generated drafts enter at *Draft*.

### 6.3 Assessment architecture **[C]** / structure **[P]** (ADR-034)

- Question bank → question → **question version** (type: MCQ, multiple response, fill-in-the-blanks, match-the-following, subjective).
- Assessment → **assessment version** (mode *practice* or *final*, pass mark, attempts, timing, fixed items and/or random selection rules).
- Attempt stores the **exact question versions** shown and responses; auto-scored types are scored immediately; subjective responses go to a **manual evaluation queue**; a final result with subjective parts is confirmed by an authorised evaluator.
- Assignments (online submission; face-to-face recorded by trainer/assessor).
- **Practical evaluation** against a **checklist version**: item results, assessor remarks, evidence attachments, outcome, then **employee acknowledgement** (with re-authentication). Submitted evaluations are immutable; corrections void and re-evaluate.

### 6.4 Competency architecture **[C]** / structure **[P]** (ADR-024, ADR-025)

Skill-level sets and levels (numeric values) → competency skills → **functional role requirements**; designations map to functional roles; curricula map to competencies (max contribution). Employee levels come from **approved skill assessments** (assessor/manager ratings, practical evaluations, imported matrices) and **achievements** (rules satisfied by evidence). Development plans hold targets and interventions with **raw source indicators preserved**.

### 6.5 Compliance and certification architecture **[C]** / structure **[P]** (ADR-026, ADR-028)

Compliance skills (binary, validity-based, separate from competency skills) with **requirement rules** (audiences) and **fulfilment options** (certificate, curriculum completion, verified external certificate) produce an **employee compliance status**. Certification definitions (completion, appreciation, compliance, authorisation, external) issue **immutable certificate issuances** with numbers, QR verification tokens, documents and **status events** (suspend, reinstate, revoke); **renewal = new issuance** linked to the previous one. The **Skill Passport** and **Certification Register** are read models.

### 6.6 Training operations architecture **[C]** / structure **[P]** (ADR-027, ADR-035)

```text
Financial year ─► Training calendar (scope: company | location | department; type: general | safety)
                    └── Planned training activity (planned count, planned hours)          ◄── PLAN
                              ▲ 0..1 fulfils
Training programme ──► Training event (mode) ─► Batch ─► Session (venue/platform, trainers)  ◄── ACTUAL
                              │                   │
                              │                   └─► Nomination ─► Participant ─► Attendance record (per session)
                              └─► Finalisation (lock; hours, manhours; downstream effects) ─► Feedback survey
```

Plans and actuals never share records: a calendar line is not an event, a planned count is not attendance. Calendar vs Actual is a report over both.

### 6.7 Evidence chain **[C]** / rules **[P]** (ADR-025)

| Record | Proves | Created by | Can it grant operational authorisation alone? |
|---|---|---|---|
| Curriculum completion (enrolment) | Learning activity done | Progress engine | **No** |
| Graded final assessment attempt | Theoretical knowledge | Assessment engine + human evaluator for subjective parts | No |
| Attendance at a finalised event | Participation | Trainer/coordinator + finalisation | No |
| Submitted practical evaluation | Demonstrated practical competence | Authorised assessor | Only together with the certification's other requirements and signatory approval |
| Competency achievement | Level reached per rule | Rule evaluation over the above | No (it is a competency level, not an authorisation) |
| Certificate issuance (kind *authorisation*) | Authorised to perform the work | Certification rules + **practical validation** + **signatory approval** | — |

### 6.8 Cross-domain flows **[P]**

Effects are triggered by explicit service calls inside the originating transaction where they must be atomic, and by **in-process domain events dispatched after commit** for recalculations (derived caches). Recalculation is idempotent and can be re-run for any employee. Scheduled work (expiry reminders, retraining allocations, reinforcement tasks, notification sending) runs in a separate scheduler/worker process; the mechanism will be selected in Stage E/H.

Examples:
1. **Classroom item**: finalisation of an event of programme *P* → participants meeting minimum attendance get the linked curriculum items completed → curriculum completion → completion certificate (if configured) → compliance status recalculated.
2. **Practical validation**: assessor submits evaluation → employee acknowledges → achievement rules evaluated → achievement recorded; an *authorisation* certification additionally waits for signatory approval before issuance.
3. **Retraining**: `valid_until − retraining_lead_days` reached → refresher allocation + notifications; status shows *due soon*.
4. **Skill matrix import**: committed batch → approved *imported* skill assessments → current levels → gap and Skill Finder reports.

### 6.9 Reporting architecture **[C]** / approach **[P]** (ADR-036)

Reports (FR-RPT-001…013) read from SQL views and derived caches ([database design §13](../database/LMS_DATABASE_DESIGN.md)); every query is scope-filtered by the caller's access-role assignments; exports are audited and formula-injection-safe. Heavy aggregates may be precomputed by the worker.

### 6.10 Import framework

See [EXCEL_IMPORT_PROFILES.md](../database/EXCEL_IMPORT_PROFILES.md) (ADR-029, ADR-030).

## 7. API conventions

| Topic | Convention | Status |
|---|---|---|
| Versioning | Path prefix `/api/v1`; breaking changes → `/api/v2`. | Implemented |
| Format | JSON, UTF-8, `snake_case` fields. | Implemented |
| Errors | `{"error": {"code", "message", "details"?, "request_id"}}`; submitted values never echoed. | Implemented |
| Request ID | `X-Request-ID` accepted if well-formed, else generated; returned and logged. | Implemented |
| Timestamps | ISO 8601 UTC; dates `YYYY-MM-DD`. | Implemented |
| Docs | `/api/v1/openapi.json`, `/api/docs`; off by default in production. | Implemented |
| Caching | `Cache-Control: no-store` by default. | Implemented |
| Pagination | `limit` + opaque `cursor`. | Planned |
| Filtering/sorting | Explicit allow-listed parameters. | Planned |
| Language | `Accept-Language` for messages and content selection. | Planned |
| Idempotency | `Idempotency-Key` for import commits, finalisation, issuance. | Planned |
| Optimistic concurrency | Resource `version` required on update. | Planned |
| Public endpoints | Only `/api/v1/public/*` (certificate verification), rate-limited. | Planned |
| Integration endpoints | `/api/v1/integration/*` for service accounts (future PMS). | Planned [F] |

## 8. Health checks — *Implemented*

| Endpoint | Semantics | Responses |
|---|---|---|
| `GET /api/v1/health/live` | Process serves HTTP; **never touches dependencies**. | `200 {"status":"ok",…}` |
| `GET /api/v1/health/ready` | Dependencies usable (database `SELECT 1`). | `200 ready` / `503 not_ready` with `not_configured` or `unavailable` |

Failure details are logged server-side only; probes log at DEBUG. Planned: migration-head and file-storage checks.

## 9. Internationalisation — *Implemented (UI framework)*

en/bn/hi/gu with English fallback; preference → browser → English; `<html lang>` follows; type-checked keys and a key-parity test; system font stack for Indic scripts. Stage A translations are drafts pending native review. Learning content, question, checklist, certificate and skill-level translations are data (translation tables) with per-language status. **[C]** / **[P]**

## 10. Configuration and logging — *Implemented*

`LMS_`-prefixed settings validated at start-up (partial DB settings, wildcard CORS and malformed prefixes rejected; production requires a database and disables docs). `VITE_*` frontend variables validated; never secret. JSON/console structured logging with request IDs; no secrets, tokens or personal data in logs.

## 11. Security architecture

### 11.1 Implemented in Stage A
No secrets or real data in the repository; `.env` ignored; `SecretStr` DB password; explicit CORS allow-list; security headers (`nosniff`, `DENY`, `no-referrer`, `no-store`); no echo of submitted values; generic 500s; validated request IDs; docs off in production; Alembic safety guards. **No authentication exists yet**; only health endpoints are exposed.

### 11.2 Planned: authentication and login sessions (Stage B) — ADR-012, ADR-032
- **Employee ID login** **[C]**: `login_id` = employee code. Personal-device credential: password (Argon2id, rate limiting, lockout) **[P]**; OTP or corporate SSO for staff **[A] Q-07**.
- **Server-side login sessions**: opaque ≥ 256-bit token in an `HttpOnly`, `Secure`, `SameSite` cookie (`__Host-` prefix in production); only the token hash stored; rotation on login/privilege change; server-side revocation. **[P]**
- **Automatic idle logout** **[C]**: server-enforced idle expiry plus a client countdown; defaults 30 min (personal) and 2 min (kiosk), configurable. **[P]**
- **Kiosk mode** **[C]** / controls **[P]**: kiosks are **registered** by an administrator, receiving a device token (HttpOnly cookie) bound to `kiosk_device`. **PIN sign-in is accepted only with a valid kiosk device token.** Sign-in = **badge QR scan** (camera or scanner) or typed employee ID, **plus PIN**. Sessions are bound to the kiosk; explicit sign-out; no personal data persisted on the device (no-store responses, query cache cleared on logout, no offline caching of API data). PIN policy [A] Q-09.
- **QR badges** **[C]** / tokens **[P]**: the badge QR encodes an **opaque random token**, not the employee code; stored hashed; revocable and re-issuable. **A badge identifies; it never authenticates alone.** Exception: an authenticated trainer's device may scan attendee badges to record attendance, the trainer being accountable. Badge format [A] Q-08.
- **Re-authentication** (PIN/password) for acknowledgements, practical sign-offs and approvals. **[P]**; [A] Q-24

### 11.3 Planned: CSRF protection
`SameSite` cookies; synchronizer token in `X-CSRF-Token` for state-changing requests; `Origin`/`Referer` checks; no state changes on `GET`. **[P]**

### 11.4 Planned: authorisation (RBAC + scope)
Fine-grained permissions grouped into configurable **access roles**, assigned to user accounts with optional org-unit scope; **separate from functional roles**, which never grant permissions (ADR-023). Enforcement server-side, deny by default; every scoped query filtered; tests for cross-scope access. Separation of duties where required (e.g. the assessor of a practical evaluation cannot approve its authorisation certificate). **[C]** / **[P]**

### 11.5 Planned: audit logging
Append-only audit of logins, access changes, organisation changes, imports, governance decisions, assessment grading and overrides, practical evaluations, attendance corrections, finalisation/reopening, certificate issuance/suspension/revocation, compliance exemptions, exports. **[C]** / scope **[P]**

### 11.6 Planned: protected file access
Files (content, evidence photos, import workbooks, certificates, submissions) stored outside the web root; downloads via authorised endpoints or short-lived signed URLs; upload validation by size, type and content sniffing; executable and macro formats rejected. **[P]**

### 11.7 Planned: public certificate verification
`/verify/:token` page calls `GET /api/v1/public/certificates/verify/{token}`; tokens are random (only hashes stored), so certificates cannot be enumerated; response limited to certificate number, holder display name, certification, issue/expiry dates and current status (valid, expired, suspended, revoked); rate-limited; access logged. **[C]** (QR verification) / **[P]**

### 11.8 Planned: other controls
TLS + HSTS; strict CSP for the SPA; rate limiting (login, PIN, verification, AI, imports, reports); secrets in environment/secret store; dependency auditing; DPDP Act 2023 alignment (minimisation, **no compensation data**, retention limits); encrypted, restore-tested backups. **[C]** / **[P]**

## 12. AI service architecture — *Planned (Stage L); nothing implemented*

### 12.1 Use cases **[C]**
AI tutor; learning recommendations; **learning-path recommendations**; course (curriculum/asset) drafting; question generation; AI-assisted skill-gap analysis.

### 12.2 Structure **[P]** (ADR-015)
```text
app/services/ai/                provider-neutral layer
├── provider.py                 AIProvider protocol: generate(), generate_structured(), stream()
├── registry.py                 provider selection (LMS_AI_PROVIDER = anthropic | disabled)
├── policies.py                 enablement, rate limits, budgets, PII redaction
├── grounding.py                retrieval over PUBLISHED, approved learning asset versions only
├── tutor_service.py · recommendation_service.py · path_recommendation_service.py
├── content_drafting.py · question_generation.py · skill_gap_service.py
app/integrations/ai/
└── anthropic_provider.py       Claude adapter (official `anthropic` SDK)
```

### 12.3 Claude as initial provider **[C]** / details **[P]**
Official `anthropic` Python SDK inside the adapter only. Model IDs are configuration (`LMS_AI_MODEL`; current default Opus model at time of writing `claude-opus-5-5`; a smaller model such as `claude-haiku-5-5` may be configured for simple high-volume tasks after evaluation). Credentials (`LMS_AI_API_KEY`, `SecretStr`) are passed explicitly — no implicit SDK credential discovery. The adapter maps streaming, refusal stop reasons, retryable vs non-retryable errors and timeouts to provider-neutral results. No key exists in the repository.

### 12.4 Rules **[C]** / mechanisms **[P]**
- **Company-specific answers come only from approved company learning material** (published versions); the tutor cites sources and says when the material does not cover a question.
- **Official learning content and assessments require authorised human approval** — AI output enters the governance workflow (§6.2.1) as a draft and is never published or used in a final assessment without SME validation and HR approval.
- **Deterministic first**: gaps, compliance status, eligibility and allocations are computed by the LMS; AI explains, ranks and suggests (FR-AI-005, FR-AI-008). Recommendations are drawn only from content the employee may see.
- AI never decides results, levels, compliance, attendance or certificate issuance.
- Data minimisation: no employee names/codes in prompts unless essential; no personal data for content drafting; metadata logging only.
- Evaluation sets and acceptance criteria per feature before rollout.
- Open decision: embedding storage (MySQL + application-side similarity for a small corpus, or a dedicated vector index later).

## 13. Integrations — *Planned*

| System | Direction | Approach | Status |
|---|---|---|---|
| **PMS** | Inbound employee/organisation data; outbound training, certification, competency summaries | **Separate application and database** **[C]**. Boundary: inbound via `app/integrations/pms/` adapter feeding the import/validation/audit pipeline; outbound via versioned `/api/v1/integration/*` endpoints for service accounts. Contracts to be defined with PMS owners. **No direct database access in either direction.** | Not implemented; [A] Q-20 |
| Identity provider | Authentication | OpenID Connect if SSO is adopted | [A] Q-07 |
| Email / SMS / WhatsApp | Outbound | Adapters; email first, others [F] | Planned |
| Calendar | Outbound | `.ics` invitations; Microsoft 365 integration [F] | Planned |
| AI provider | Outbound | §12 | Planned |

## 14. Deployment topology (proposed)

One origin (reverse proxy: TLS, SPA static files, `/api/` → Uvicorn workers via `uvicorn app.main:create_app --factory`); a scheduler/worker process for scheduled jobs (§6.8); MySQL 8 with encrypted, restore-tested backups; protected file storage; separate dev / test-staging / production environments and credentials; kiosks as locked-down browsers in kiosk mode pointing at `/kiosk`. CI (planned): Ruff, mypy, Pytest, ESLint, TypeScript, Vitest, build, dependency audit. **[P]**

## 15. Non-functional targets (initial)

| Area | Target |
|---|---|
| Devices | 360 px phones to desktops and kiosks; learner portal mobile-first; touch-friendly. |
| Network | Usable on modest plant Wi-Fi; route-level code splitting as features grow. |
| Performance | Typical API responses < 300 ms at expected load. |
| Availability | Business-hours availability with planned maintenance windows (to be agreed). |
| Accessibility | WCAG 2.2 AA for learner-facing pages. |
| Languages | en, bn, hi, gu for UI and content. |
