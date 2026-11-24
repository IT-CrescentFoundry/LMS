# LMS Implementation Roadmap

The LMS is built in explicitly defined stages. Each stage has a clear scope, depends on earlier stages, and ends with tests, documentation updates and a completion report. **Stage order after C is a proposal [P]** that respects dependencies; business priority is to be confirmed ([A] Q-22).

| Stage | Name | Status |
|---|---|---|
| **A** | Project foundation and technical architecture | **Complete** (database connectivity verified in Stage B) |
| **A.1** | Architecture alignment with business requirements (documentation only) | **Complete** |
| **B** | Identity, access and audit (accounts, password sign-in, sessions and idle logout, CSRF, access roles, audit, Super Admin bootstrap, sign-in UI) | **Complete** — kiosk PIN, badges and OTP/SSO deferred (Q-07, Q-08, Q-09) |
| C | Organisation and employee core (incl. functional roles, responsibilities) + Control Room v1 | **In progress** — C1, C2, C3 committed; C4 (scoped access), positions and Control Room remain |
| D | Import framework + profile 1 (organisation & employees) | **Complete** — framework and `employees` v1; migration `0010` applied to the development database; organisation/reference-data part of profile 1 deferred (organisation units later delivered in the first release, profile `organisation` v1) |
| E | Training operations + profiles 4, 5, 6 | Not started |
| F | Competency framework & development plans + profiles 2, 3 | Not started |
| G | Learning catalogue & content governance | Not started |
| H | Learning delivery, Learner Portal and Manager Portal v1 | Not started |
| I | Assessments, practical evaluation and competency achievement rules | Not started |
| J | Compliance, certification and Skill Passport | Not started |
| K | Reports and management analytics | Not started |
| L | AI services | Not started |
| M | Career development | Not started |
| N | PMS integration (future; boundary only until scoped) | Not started |
| O | Production readiness (continuous from Stage B) | Not started |

### Stage letters changed in A.1

| Stage A letter | Stage A name | A.1 letter |
|---|---|---|
| B, C, D | Identity; Organisation; Excel import | B, C, D (unchanged) |
| E | Learning content and authoring | **G** |
| F | Learning delivery | **H** |
| G | Assessments | **I** |
| H | Competency management | **F** |
| I | Certifications and refresher training | **J** |
| J | Training administration and analytics | **E** (training operations) + **K** (reports) |
| K | AI services | **L** |
| L | Career development | **M** |
| M | PMS integration | **N** |
| N | Production readiness | **O** |

## Dependency overview

```text
A ─► A.1 ─► B ─► C ─► D ─┬─► E (training ops) ──────────────┐
                         ├─► F (competency core) ────────────┤
                         │                                   ▼
                         └─► G (catalogue) ─► H (delivery) ─► I (assessment, practical, achievement rules)
                                  ▲   E ───────┘ (classroom items)    │
                                  │                                   ▼
                                  │                         J (compliance, certification, Skill Passport)
                                  │                                   ▼
                                  └──────────── L (AI) ◄──── K (reports) ◄── all
                                                   M (career) ◄── F, I
                                                   N (PMS) ◄── C, D (+ agreed contract)
O: continuous from B
```

**Why this order [P]:** training calendars, attendance and skill matrices exist today as Excel workbooks, so training operations (E) and the competency core (F) deliver value early on top of organisation data (C, D). The catalogue (G) and delivery (H) follow; assessments and practical evaluation (I) unlock evidence-based achievement rules; certification and compliance (J) depend on completions, attendance and practical validation.

---

## Stage A — Foundation *(complete)*

Frontend shell, backend API foundation, health checks, database/Alembic infrastructure, tests and documentation. Database connectivity was verified in Stage B. **Outstanding:** translations pending native review.

## Stage A.1 — Architecture alignment *(complete)*

Documentation only: learning hierarchy, organisation extensions (functional roles, responsibilities, access-role separation), competency and compliance domain, training operations domain, assessments and practical evaluation, certification and Skill Passport, three user experiences and kiosk mode, report catalogue, import framework with six profiles, AI updates, database design for all domains, ADR-022…039, assumptions register Q-01…Q-34. **No code, dependencies, tables or migrations changed.**

## Stage B — Identity, access and audit *(complete)*

**Depends on:** A; a provisioned LMS database (done: `crescent_lms_dev`, `crescent_lms_test`, accounts `lms_app` / `lms_migrator` / `lms_test`).

**Delivered:**
- **Database:** revisions `0001`–`0003` — eight identity/access/audit tables, seeded roles and permissions, audit append-only triggers. Applied to `crescent_lms_dev` (head `0003`).
- **Accounts and passwords:** user accounts separate from employees (ADR-040); Argon2id passwords and policy (ADR-042).
- **Sessions:** server-side, with idle and absolute expiry, rotation and revocation (ADR-043).
- **Protection:** two-layer CSRF (ADR-044); database-backed login throttling (ADR-045).
- **Access control:** RBAC with 17 permission codes and 6 access roles, deny by default, assignment guards (ADR-046).
- **Highest privilege:** CLI-only Super Admin bootstrap (ADR-047). The first Super Admin was created on dev by the operator.
- **Audit:** append-only audit trail with a read-only viewer (ADR-048).
- **Infrastructure:** migration/runtime credential separation; isolated, identity-verified test database with a data-independent rebuild (ADR-041).
- **API:** authentication and administration (see the [API reference](architecture/API_REFERENCE.md)).
- **Frontend (B6):** sign-in, session restoration and expiry, change password, user menu, permission-aware navigation, read-only User accounts and Audit log pages, in en/bn/hi/gu (ADR-050).

**Exit criteria — evidence:**
- **Automated tests**, all executed and passing:
  - 215 backend tests (148 unit + 67 database integration on `crescent_lms_test`);
  - 129 frontend tests.
- **Coverage includes:**
  - session fixation (rotation on sign-in);
  - CSRF (missing or invalid token, untrusted origin);
  - brute-force throttling (identifier and IP);
  - idle and absolute expiry;
  - authorisation denial and the route inventory;
  - assignment guards;
  - Super Admin bootstrap restrictions;
  - audit immutability (ORM guard and database triggers);
  - test-database guards and repeated rebuilds.
- **Real-browser E2E** on `crescent_lms_test`: 32 of 32 checks; HttpOnly/SameSite cookie, Origin and CSRF headers; no tokens in web storage; 80 screenshots across 5 widths × 4 languages.
- **Operator acceptance** on `crescent_lms_dev` with the real Super Admin: sign-in, session restoration, permissions, Users, Audit log, responsive layouts, sign-out.

**Deferred (not part of Stage B as delivered):**
- Kiosk registration and PIN sign-in (Q-09).
- Badge QR identification (Q-08).
- OTP/SSO (Q-07).
- Organisation-scoped role assignments and access provisioning rules (Stage C).
- Re-authentication for sign-offs (Q-24).
- Account-management screens (Q-44).

FR-IAM-002 is met for personal devices only; kiosk timeouts are deferred.

**Open decisions:** Q-07, Q-08, Q-09 (still open); Q-43 (security parameters); Q-44 (interim account provisioning).

**Production prerequisite:** a DBA decision on creating the audit triggers (`log_bin_trust_function_creators` is a local-development setting only; ADR-048).

## Stage C — Organisation and employee core

**Depends on:** B (complete).
**Scope:** unit types/rules, units, effective-dated hierarchy, plants/locations, job families, grades, designations, positions, **functional roles**, **responsibilities**, designation/position→role mappings, employees (no compensation data), assignments, employee roles/responsibilities, reporting relationships, as-of queries, history, data-quality view, scope evaluation; Control Room v1 for organisation management.
**Decisions needed:** Q-23, Q-27, Q-30.
**Exit criteria:** cycle/overlap/one-primary rules and role resolution covered by tests; scope filtering verified.
**Status:** C1 (organisation API) and C2 (Organisation Builder screens) committed. C3a (employee API) and C3b (employee screens, CP0–CP7: directory, profile, write workflows, separation with preview, account linking, data quality, translations, browser verification) committed; migrations `0008`–`0009` applied to the development database. Remaining: C4 (organisation-scoped permissions and scope evaluation), positions, Control Room. Open: Q-45, Q-47, Q-48, Q-53; native-speaker review of bn/hi/gu (Q-58).

## Stage D — Import framework + profile 1

**Depends on:** C.
**Scope:** shared pipeline (staging, mapping profiles, header aliases, value mappings, protected exclusion list, validation layers, duplicate candidates, diff/preview, confirmation with stale check, transactional commit, provenance, history, error export); **profile 1** (organisation & employees).
**Decisions needed:** Q-28, Q-31, Q-21.
**Exit criteria:** idempotent re-import; CTC/compensation columns provably never stored; hostile files rejected; synthetic large-file test.
**Status:** **complete**. Implemented, verified on the test database, acceptance-reviewed and committed; migration `0010` applied to the development database. Delivered: the framework (versioned profiles, job state machine, hostile-file checks, header detection, deterministic column mapping, protected exclusion list, normalisation, layered validation as a dry run through the C3 services, probable-duplicate decisions, reviewed reference-value mappings, preview with stale checks, explicit approval, one-transaction commit, provenance, history, formula-safe error report), profile `employees` v1 (employees, assignments, reporting lines), the Import Control Room screens in four languages, and migration `0010` (tables and four permissions). All four exit criteria are covered by tests (re-import → `unchanged`; sensitive columns refused and never stored, logged, audited or reported; hostile-file suite; 2,000-employee synthetic volume test).

**Acceptance review (2026-11-17):** the implementation was re-inspected and hardened before acceptance. Corrected: a commit that no longer matched the approved preview could apply corrections nobody had reviewed (now refused, `import_records_changed`); expiry was enforced only when a job was viewed (now on every action); the header row could be moved onto a data row through the API, bypassing the exclusion check (now fixed to the detected row); malformed worksheet XML caused server errors (now `422 file_corrupted`); uploaded files were deleted before the job's new status was saved (now released in the same transaction and deleted afterwards, with housekeeping for orphans, overdue jobs and abandoned validations); one import could exceed what finishes within the browser's 5-minute wait (now at most 6,000 rows). The bn/hi/gu catalogues are loaded on demand, reducing the main JavaScript bundle from 795 kB to 387 kB; an intermittent frontend test (a 1-second wait too short for on-demand pages under load) was fixed. Details: [import profiles §0](database/EXCEL_IMPORT_PROFILES.md), ADR-051–053.

Implemented but awaiting human review: the bn/hi/gu translations (machine drafts, Q-58). Deferred: saved mapping profiles, an administrator-maintained exclusion list, header-row selection, a second approver (Q-31), full retention rules (Q-21), a provenance screen, and the organisation and reference-data worksheets of profile 1 (Q-47, Q-53). Open: Q-21, Q-28 (source system), Q-31, Q-47, Q-53, Q-58. **Stage E has not started.**

## First release (2026-11-23) — brought forward from Stages E and F

Implemented per the [revised first-release scope](product/REVISED_FIRST_RELEASE_SCOPE.md): training register (programmes, events with planned vs actual, sessions, participation), training calendar, in-app notifications, competency library, configurable scales, skill matrices with gaps and staffing risk, organisation-unit import profile, org chart.

**Migration `0011`:** verified on the test database, then applied to `crescent_lms_dev` on 2026-11-23 after a backup and an isolated restore test both passed.

**Technical verification (completed 2026-11-24):**
* Database integrity checks: 148 foreign keys, 0 orphaned records.
* HR Admin application smoke test.
* The owner's manual browser verification.
* Automated backend and frontend tests and static checks.

All of these passed, and the synthetic smoke-test account has been disabled. Record: [execution report](database/verification/MIGRATION_0011_EXECUTION_REPORT_20261123.md).

**Business readiness remains outstanding:**
* Production deployment.
* Business-data onboarding.
* Stakeholder UAT.
* Outlook/Teams integration.
* Scheduling of the training-reminder job.
* Open decisions D-01…D-14.

Remaining Stage E/F scope below (batches, venues, finalisation lock, feedback, requests, calendar/attendance/matrix imports, development plans, achievement rules) is unchanged.

## Stage E — Training operations + profiles 4, 5, 6

**Depends on:** C, D.
**Scope:** financial years; location/department/company calendars; planned activities; training programmes; events, batches, sessions; venues, platforms; internal/external trainers, vendors; event plans; nominations and participants; attendance (manual, upload, QR self-check-in, badge scan); corrections; finalisation and reopening; recurring events; `.ics` notifications; hours/manhours; feedback (shared survey component); training requests; historical records; **profiles 4–6** with calendar overlap reconciliation.
**Decisions needed:** Q-04, Q-05, Q-06, Q-12, Q-13, Q-14, Q-15, Q-19, Q-25.
**Exit criteria:** planned and actual never conflated (tests); finalisation lock and audited corrections; overlapping calendar fixtures reconciled without loss.

## Stage F — Competency framework & development plans + profiles 2, 3

**Depends on:** C, D.
**Scope:** skill-level sets (Bagnan scale as data), competency skills, functional-role requirements, designation-to-role mapping use, employee skill assessments (assessor/manager/imported) with approval, current levels, gap computation, development plans with raw indicators, **profiles 2–3** (wide matrices).
**Sources:** Bagnan skill matrices, development plans, **`TC_Library_Crescent_Foundry_v1.xlsx`** (technical competency library; proposed seventh import profile).
**Decisions needed:** Q-01, Q-02, Q-03, Q-35 – Q-42.
**Exit criteria:** blank ≠ level; raw indicators preserved; history as-of queries.

## Stage G — Learning catalogue & content governance

**Depends on:** B, C (and E for classroom assets).
**Scope:** academies, paths, sections, curricula, items, assets (files, video, podcast, external, SCORM), localised content, versioning, curriculum-to-competency mapping, audience rules and visibility, governance workflow (SME validation, safety review, HR approval/publishing), certificate references.
**Decisions needed:** Q-16, Q-33; curriculum-to-competency mapping uses the TC Library competencies (Q-38, Q-41).
**Exit criteria:** unpublished content invisible to learners; published versions immutable; HR approval required to publish.

## Stage H — Learning delivery, Learner Portal and Manager Portal v1

**Depends on:** G (and E for classroom items).
**Scope:** allocation rules and manual allocations, enrolments and approvals, progress engine (sequence, minimum completion, deadlines), SCORM runtime, validity and retraining, reinforcement, induction auto-allocation, learner dashboard (upcoming actions, progress, calendar), manager team view, scheduler/worker for reminders.
**Decisions needed:** Q-18, Q-26.

## Stage I — Assessments, practical evaluation, achievement rules

**Depends on:** G, H; F for achievement rules.
**Scope:** question banks and five question types, practice/final modes, attempts, manual evaluation queue, assignments (online, face-to-face), versioned practical checklists, practical evaluations with evidence and acknowledgement (tablet-friendly), competency achievement rules and evidence links.
**Decisions needed:** Q-17, Q-24.
**Exit criteria:** human confirmation for subjective finals and all practical validations; immutability of submitted evaluations.

## Stage J — Compliance, certification and Skill Passport

**Depends on:** E, H, I.
**Scope:** compliance skills, requirement/fulfilment rules, status, exemptions; certification definitions (completion, appreciation, compliance, authorisation, external); templates (completion and appreciation from the Crescent designs); numbering; issuance, PDF generation, QR verification page; renewal as new issuance; suspension, reinstatement, revocation; external certifications; Certification Register; Skill Passport.
**Decisions needed:** Q-10, Q-11, Q-34.
**Exit criteria:** authorisations impossible without practical validation and signatory approval; issuances immutable; verification non-enumerable.

## Stage K — Reports and management analytics

**Depends on:** C, E, F, H, I, J.
**Scope:** FR-RPT-001…013, scoped read models, exports, Control Room and management dashboards.
**Decisions needed:** Q-12, Q-29.

## Stage L — AI services

**Depends on:** G (approved content), F/H/J (recommendations, gaps).
**Scope:** provider-neutral layer, Claude adapter, grounding on published content, tutor, recommendations, **learning-path recommendations**, drafting and question generation into governance, skill-gap explanations, usage controls, evaluation sets.

## Stage M — Career development

**Depends on:** C, F, I. **Scope:** career paths between functional roles/designations, next-role readiness, development-plan links.

## Stage N — PMS integration (future)

**Depends on:** C, D; agreed interface (Q-20). **Scope:** versioned contracts, service accounts, inbound adapter into the import pipeline, outbound integration endpoints. LMS and PMS remain separate applications and databases. **Not to be implemented until scoped.**

## Stage O — Production readiness (continuous)

CI (lint, types, tests, build, dependency audit); reverse proxy, TLS, CSP; kiosk lockdown guidance; backups and restore tests; monitoring; performance, accessibility and security testing; runbooks.