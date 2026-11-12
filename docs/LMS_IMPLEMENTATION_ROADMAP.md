# LMS Implementation Roadmap

The LMS is built in explicitly defined stages. Each stage has a clear scope, depends on earlier stages, and ends with tests, documentation updates and a completion report. **Stage order after C is a proposal [P]** that respects dependencies; business priority is to be confirmed ([A] Q-22).

| Stage | Name | Status |
|---|---|---|
| **A** | Project foundation and technical architecture | **Complete** — database connectivity unverified |
| **A.1** | Architecture alignment with business requirements (documentation only) | **Complete** |
| B | Identity, access and audit (employee ID login, kiosk PIN, badges, idle logout, access roles) | Not started |
| C | Organisation and employee core (incl. functional roles, responsibilities) + Control Room v1 | Not started |
| D | Import framework + profile 1 (organisation & employees) | Not started |
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

Frontend shell, backend API foundation, health checks, database/Alembic infrastructure, tests and documentation. **Outstanding:** dedicated LMS database not provisioned (connectivity unverified); translations pending native review.

## Stage A.1 — Architecture alignment *(complete)*

Documentation only: learning hierarchy, organisation extensions (functional roles, responsibilities, access-role separation), competency and compliance domain, training operations domain, assessments and practical evaluation, certification and Skill Passport, three user experiences and kiosk mode, report catalogue, import framework with six profiles, AI updates, database design for all domains, ADR-022…039, assumptions register Q-01…Q-34. **No code, dependencies, tables or migrations changed.**

## Stage B — Identity, access and audit

**Depends on:** A; **a provisioned LMS database**.
**Scope:** `user_account`, credentials (password; kiosk PIN), badge tokens, kiosk registration, server-side login sessions with idle/absolute timeouts, CSRF, **access roles** and scoped assignments, access provisioning rules, audit log, first Alembic migrations, `/api/v1/me`, frontend sign-in (employee ID; kiosk badge + PIN), route areas for the three experiences (shells only), idle-logout UX, admin bootstrap procedure (no default passwords).
**Decisions needed:** Q-07 (credential/SSO), Q-08 (badges), Q-09 (kiosk/PIN policy).
**Exit criteria:** security tests (session fixation, CSRF, brute force on password and PIN, PIN rejected off-kiosk, badge-only sign-in impossible, idle expiry, authorisation denial); audit entries for auth events.

## Stage C — Organisation and employee core

**Depends on:** B.
**Scope:** unit types/rules, units, effective-dated hierarchy, plants/locations, job families, grades, designations, positions, **functional roles**, **responsibilities**, designation/position→role mappings, employees (no compensation data), assignments, employee roles/responsibilities, reporting relationships, as-of queries, history, data-quality view, scope evaluation; Control Room v1 for organisation management.
**Decisions needed:** Q-23, Q-27, Q-30.
**Exit criteria:** cycle/overlap/one-primary rules and role resolution covered by tests; scope filtering verified.

## Stage D — Import framework + profile 1

**Depends on:** C.
**Scope:** shared pipeline (staging, mapping profiles, header aliases, value mappings, protected exclusion list, validation layers, duplicate candidates, diff/preview, confirmation with stale check, transactional commit, provenance, history, error export); **profile 1** (organisation & employees).
**Decisions needed:** Q-28, Q-31, Q-21.
**Exit criteria:** idempotent re-import; CTC/compensation columns provably never stored; hostile files rejected; synthetic large-file test.

## Stage E — Training operations + profiles 4, 5, 6

**Depends on:** C, D.
**Scope:** financial years; location/department/company calendars; planned activities; training programmes; events, batches, sessions; venues, platforms; internal/external trainers, vendors; event plans; nominations and participants; attendance (manual, upload, QR self-check-in, badge scan); corrections; finalisation and reopening; recurring events; `.ics` notifications; hours/manhours; feedback (shared survey component); training requests; historical records; **profiles 4–6** with calendar overlap reconciliation.
**Decisions needed:** Q-04, Q-05, Q-06, Q-12, Q-13, Q-14, Q-15, Q-19, Q-25.
**Exit criteria:** planned and actual never conflated (tests); finalisation lock and audited corrections; overlapping calendar fixtures reconciled without loss.

## Stage F — Competency framework & development plans + profiles 2, 3

**Depends on:** C, D.
**Scope:** skill-level sets (Bagnan scale as data), competency skills, functional-role requirements, designation-to-role mapping use, employee skill assessments (assessor/manager/imported) with approval, current levels, gap computation, development plans with raw indicators, **profiles 2–3** (wide matrices).
**Decisions needed:** Q-01, Q-02, Q-03.
**Exit criteria:** blank ≠ level; raw indicators preserved; history as-of queries.

## Stage G — Learning catalogue & content governance

**Depends on:** B, C (and E for classroom assets).
**Scope:** academies, paths, sections, curricula, items, assets (files, video, podcast, external, SCORM), localised content, versioning, curriculum-to-competency mapping, audience rules and visibility, governance workflow (SME validation, safety review, HR approval/publishing), certificate references.
**Decisions needed:** Q-16, Q-33.
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
