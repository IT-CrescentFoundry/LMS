# First Release — Execution Plan to 15 December 2026

| | |
|---|---|
| **Date** | 24 November 2026 (Tuesday) |
| **Status** | **Draft for owner approval.** Milestone boundaries are as set by the owner and are **unchanged**. |
| **Governs** | Outstanding rows of the [master completion matrix](FIRST_RELEASE_MASTER_COMPLETION_MATRIX.md). Gaps, decisions and data readiness: [gap register](FIRST_RELEASE_GAP_AND_DEPENDENCY_REGISTER.md). Release gates: [acceptance checklist](FIRST_RELEASE_ACCEPTANCE_CHECKLIST.md). |

## 1. Milestones (owner-defined, unchanged)

| Milestone | Dates | State on 24 Nov | Content in this plan |
|---|---|---|---|
| M1 Platform foundation, identity & security, organisation and employee management | 17–20 Nov | Completed | No outstanding tasks (matrix: COMPLETE rows) |
| M2 Development database migration, Excel import and training operations | 21–30 Nov | In progress (migration `0011` done) | E-2.1 … E-2.11 |
| M3 Competency management; learner, manager and trainer experience | 24 Nov–5 Dec | In progress | E-3.1 … E-3.10 |
| M4 Training compliance, certifications, reports and dashboards | 6–10 Dec | Not started | E-4.1 … E-4.7; **content depends on SC-01** |
| M5 Final integration, UAT and deployment readiness | 11–15 Dec | Not started | E-5.1 … E-5.10 |

**Calendar facts:**
* 18 working days remain if Saturdays are worked: 25–28 Nov, 30 Nov–5 Dec, 7–12 Dec, 14–15 Dec.
* 6 Dec and 13 Dec are Sundays.
* The UAT window, 11–14 Dec, is **three working days plus a Sunday**.

## 2. Effort, capacity and the recommended baseline

| Bucket | Effort (developer-days, incl. tests and review) | Note |
|---|---|---|
| Mandatory | **≈ 24** (≈ 19 developer + ≈ 5 IT/DBA in E-5.1…E-5.3) | Must be done for any release |
| Conditional — recommended (C-01 ORG-08, C-02 TRN-14, C-03 CMP-05, C-08 RPT-02/03/05/08) | **≈ 10.5** | Makes real-data onboarding and basic reporting possible |
| Conditional — stretch (C-04 SKM-07, C-05 TRN-09, C-06 TRS-01/02, C-07 CPL-01…05, C-09 RPT-09) | **≈ 16.5** | Each needs a decision or source data that does not exist today |
| Optional P2 (E-3.9) | ≈ 1 | Only with spare capacity |

**Capacity:**
* A single development stream offers about 18 days, which does **not** cover even the mandatory bucket with a buffer.
* Two parallel streams offer about 36 days. They cover mandatory plus recommended work (≈ 29.5 developer-days) with about 6 days of buffer for UAT defects. The two streams:
  * **Stream A:** backend and data onboarding.
  * **Stream B:** frontend, E2E and operations documentation.

**Recommendation (SC-06):**
* Approve **mandatory + recommended conditional** as the 15 December baseline, with two streams.
* Treat the stretch items as post-rollout unless their decisions and data arrive by the dates in §6 **and** capacity is confirmed.

Stakeholder response time is **not** included in these estimates; it is shown separately as "Business approvals" and in §6.

## 3. Tasks by milestone

Class: **M** mandatory · **C-R** conditional, recommended · **C-S** conditional, stretch · **O** optional.

### M2 — Development database migration, Excel import and training operations (to 30 Nov)

| Task | Expected deliverable | Matrix IDs | Dependencies | Test requirements | Business approvals | Acceptance criteria | Effort | Target | Class |
|---|---|---|---|---|---|---|---|---|---|
| E-2.1 | Decision pack, plus a decision session with HR/L&D/IT; signed decision record | ORG-04, ORG-05, CMP-01, SKM-05 (decisions) | — | — | D-01, D-02, D-03, D-05, D-06, D-15, D-16, SC-01…SC-06, DEP-01 | Each decision recorded with owner, date and answer in the gap register §3 | 0.5 | 27 Nov | M |
| E-2.2 | User-account administration UI: create, edit, suspend, disable, reset password, assign and remove roles (existing API) | ADM-05 | — | Component tests per action; API-error states; E2E create → first sign-in → forced password change | — | HR Admin completes every action in the UI; audit events present; Super Admin role not assignable | 2 | 28 Nov | M |
| E-2.3 | Bulk account provisioning for the D-16 audience; credential handover procedure | ADM-06 | D-16, E-2.9 | Integration: idempotent, no duplicate login IDs, must-change-password set, no plaintext stored or logged | D-16 | All rollout users provisioned on the target environment; sample sign-ins succeed | 1.5 | 30 Nov | M |
| E-2.4 | Reference-data import profile (designations, grades, levels, locations) | ORG-08 | SC-03 | Synthetic-workbook integration tests: preview, near-duplicate candidates, approval, idempotent re-import, audit/provenance | SC-03 | Dry run of the HR-approved list with 0 unreviewed duplicates | 2 | 30 Nov | C-R |
| E-2.5 | Training-calendar import profile, **planned fields only** | TRN-14 | D-05, SC-05 | Tests prove no actual date, attendance or completion is created; duplicate-copy handling; month-text parsing | D-05, SC-05 | Dry run on the source calendars: about 810 planned events, 0 actuals | 2.5 | 30 Nov (slips into M3 if D-05 is later than 27 Nov) | C-R |
| E-2.6 | Release navigation per owner decision (hide or label the six planned modules) | ADM-10 | Owner decision | Navigation test updated | Owner | Navigation as approved | 0.25 | 26 Nov | M |
| E-2.7 | Organisation hierarchy loaded through profile `organisation` v1 | ORG-05, ORG-09, ORG-10, ORG-11 | D-01, D-02, D-03, D-15; HR hierarchy sheet | Browser walkthrough of the full import; org chart at 360 px | HR sign-off on the dry-run preview. **Owner approval to write real data to the target database** | Tree matches the approved structure; job approved and audited | 0.5 + HR | 29 Nov | M |
| E-2.8 | Canonical designations, grades and levels loaded (E-2.4 or manual keying) | ORG-07 | D-01, Q-45, Q-53, E-2.4 | Reconciliation count against the approved list | HR sign-off on the list | 100 % of the employee file's designations resolve | 0.5 + HR | 30 Nov | M |
| E-2.9 | Employee master, assignments and reporting lines loaded (`employees` v1) | EMP-08 | E-2.7, E-2.8; **corrected extract by 28 Nov** | Data-quality view review; reconciliation of counts | HR sign-off on the preview and data-quality result; owner approval to write | 0 unresolved errors; reporting lines complete for the rollout audience | 0.5 + HR | 30 Nov | M |
| E-2.10 | Browser E2E harness; journeys for sign-in, training register, event lifecycle and calendar at 360 / 768 / 1280 px | OPS-04, TRN-04, TRN-08, TRN-10, X-04 | DEP-01 | Runs against `crescent_lms_test` only, with synthetic data | DEP-01 | Suite green; added to `scripts/check.ps1` | 1.5 | 30 Nov | M |
| E-2.11 | Training workflow test expansion (sessions, notifications per type, scope edges) | OPS-05, TRN-05, NTF-02 | — | Integration and UI tests | — | Each TRN/NTF P0/P1 row has an integration test and a UI test | 1 | 30 Nov | M |

### M3 — Competency management; learner, manager and trainer experience (24 Nov–5 Dec)

| Task | Expected deliverable | Matrix IDs | Dependencies | Test requirements | Business approvals | Acceptance criteria | Effort | Target | Class |
|---|---|---|---|---|---|---|---|---|---|
| E-3.1 | Competency-library import profile (TC Library layout: TCs, descriptors, band requirements; drafts stay drafts) | CMP-05 | SC-05 | Synthetic tests: 4 descriptors, band codes verbatim, draft rows with blank columns, the Read Me range defect not relied on | SC-05 | Dry run: 168 rows, 100 complete, 68 draft | 2 | 2 Dec | C-R |
| E-3.2 | Approved library loaded | CMP-06, CMP-02 | D-04, E-3.1 (or manual) | Count reconciliation | L&D/HR approval of entries (D-04) | Counts match the source; statuses match the approval | 0.5 + L&D | 4 Dec | M |
| E-3.3 | Competency governance per D-04 (enforce approved-only use if decided; edit-after-approval rule); library approver per D-04 | CMP-03, TRS-04 | D-04, D-09 | Integration tests for each rule | D-04 | Behaviour equals the decision; audited | 1 | 3 Dec | M |
| E-3.4 | Wide skill-matrix import (Bagnan), CTC excluded, `imported_matrix` with the as-of date | SKM-07 | D-06, D-14, SC-05 | Tests prove CTC is never in staging, logs, audit or reports; blank ≠ level; `#REF!` reported | D-06, D-14 | Sample sheet reconciles to the workbook counts and risk | 3 | 5 Dec | C-S |
| E-3.5 | "My Learning" page: own upcoming, attended and completed records | LRN-03, LRN-01, LRN-02 | E-2.6 | UI tests (own scope only); E2E learner journey | — | Learner sees only own records; replaces the placeholder | 1 | 3 Dec | M |
| E-3.6 | Nomination approval workflow with approval notifications | TRN-09, NTF-06 | D-11, SC-02 | Integration: approve, reject, withdraw, capacity; notification once each | D-11 | Configured approver acts; audited; nominee notified | 3 | 5 Dec | C-S |
| E-3.7 | Trainer access: own events, participant list, attendance capture | TRS-01, TRS-02 | SC-02, D-09 | Scope tests (other events → 404); audit | D-09 | Trainer limited to own events | 2 | 5 Dec | C-S |
| E-3.8 | Role and permission grants per D-09 (assessors, managers' Supervisor/HOD roles); a migration only if new roles or permissions are needed | ADM-07, MGR-07, MGR-01 | D-09, D-16 | Route-protection inventory; scope tests. Any migration: rehearsed on `crescent_lms_test`, SQL preview, **owner approval before dev** | D-09; migration approval if needed | Approved permission matrix in force | 1 | 5 Dec | M |
| E-3.9 | Employee profile tab: training records and skills | EMP-10 | — | UI tests | — | Records and matrices visible on the profile | 1 | 5 Dec | O |
| E-3.10 | Competency and skill-matrix workflow tests; E2E for HR assessment and manager team views | OPS-05, OPS-04, CMP-07, SKM-01…05, MGR-01, MGR-02 | E-2.10 | Integration, UI and E2E | — | Each CMP/SKM P0/P1 row covered | 1 | 5 Dec | M |

### M4 — Training compliance, certifications, reports and dashboards (6–10 Dec)

| Task | Expected deliverable | Matrix IDs | Dependencies | Test requirements | Business approvals | Acceptance criteria | Effort | Target | Class |
|---|---|---|---|---|---|---|---|---|---|
| E-4.1 | Reports: participation and completion; planned vs actual coverage (never merged); cross-matrix skill gap. By plant, department and month, scope-filtered | RPT-02, RPT-03, RPT-05 | SC-01, E-2.7 | Integration: totals reconcile with records; scope; planned ≠ actual | SC-01 | Report totals reconcile on loaded data | 3 | 9 Dec | C-R |
| E-4.2 | Audited, scope-filtered, formula-safe `.xlsx` export (register, records, reports, matrix grid) | RPT-08, SKM-09 | E-4.1 | Formula-injection test; audit event; scope test | SC-01 | Export equals the screen data; audit row written | 1 | 9 Dec | C-R |
| E-4.3 | Management dashboard with approved KPIs | RPT-09 | Q-29 KPI approval **by 3 Dec** | KPI calculation tests | KPI approval | Each KPI equals its definition | 1.5 | 10 Dec | C-S |
| E-4.4 | Mandatory-training requirement rules and per-employee compliance status | CPL-01, CPL-02, RPT-07 | SC-01, Q-11, Q-34; **HR compliance matrix by 3 Dec** | Status derivation tests; migration rehearsal | Migration approval; HR rule approval | Status correct on a UAT sample | 3 | 10 Dec | C-S |
| E-4.5 | Certification validity, issue/expiry records, expiry list and renewal reminders | CPL-03, CPL-04, NTF-07 | E-4.4, D-10 (number format) | Expiry window tests; reminder dedupe | Migration approval | Expiring records listed; reminders once | 2.5 | 10 Dec | C-S |
| E-4.6 | Evidence attachments for compliance and certification | CPL-05 | E-4.5, Q-21 | File security tests | Retention decision | Protected storage | 1.5 | 10 Dec | C-S (recommend defer) |
| E-4.7 | Data-onboarding reconciliation: organisation, employees, designations, library, calendar and matrices loaded vs source; HR sign-off | ORG-05, EMP-08, CMP-06, TRN-14 | E-2.7…E-2.9, E-3.2, E-2.5 | Count and sample reconciliation sheet | HR sign-off | Signed reconciliation | 0.5 + HR | 10 Dec | M |

### M5 — Final integration, UAT and deployment readiness (11–15 Dec)

| Task | Expected deliverable | Matrix IDs | Dependencies | Test requirements | Business approvals | Acceptance criteria | Effort | Target | Class |
|---|---|---|---|---|---|---|---|---|---|
| E-5.1 | Production host: HTTPS reverse proxy, backend service, frontend static build, secrets outside the repository, production `.env`; deployment procedure rehearsed | OPS-01 | D-17 (**server by 5 Dec**; preparation starts 1 Dec) | Smoke test on the host; `secure` cookie, HTTPS origins, docs off | IT approval | Rehearsed deployment from a clean checkout | 2 (dev + IT) | 12 Dec | M |
| E-5.2 | Production database, accounts, migrations `0001`–`0011` (+ any approved later ones), audit triggers via DBA | OPS-02 | D-17 | `alembic current`; trigger and FK checks (the existing verification SQL) | **Explicit owner approval to migrate production**; DBA | Head revision; 0 orphans; triggers present | 1 (DBA) | 12 Dec | M |
| E-5.3 | Scheduled backups and a restore test into an isolated schema | OPS-03 | E-5.2 | Restore verification (schema fingerprint, content hashes) | DBA | Restore passes | 1 (DBA) | 13 Dec | M |
| E-5.4 | Reminder job scheduled (interval and owner per D-12) | NTF-05, NTF-04 | D-12, E-5.1 | Dry-run, then a live run; idempotent re-run | D-12 | Task history shows successful runs | 0.25 | 13 Dec | M |
| E-5.5 | Production security review and dependency audit; remediation | OPS-12, ADM-01 | E-5.1 | `pip-audit`/`npm audit` (read-only reports), header and cookie checks | — | No open high findings | 1 | 12 Dec | M |
| E-5.6 | Full regression: backend, frontend, lint, types, build, E2E; performance timing on loaded data | OPS-05, OPS-11 | All build tasks | All suites run and recorded with dates | — | All green; recorded in the execution record | 1 | 11 Dec | M |
| E-5.7 | UAT execution with scripts per domain; defect triage and fixes; sign-off | OPS-10 (+ every IMPLEMENTED, NOT FULLY VERIFIED row) | D-18, E-4.7, E-5.1 or a dedicated UAT environment | UAT scripts; retest of fixes | **UAT sign-off by D-18 authorities** | Checklist §3 signed per domain | 2 (fix buffer) + users | 11–14 Dec | M |
| E-5.8 | Runbooks (deploy, rollback, backup and restore, reminder job, account admin, imports, incidents) with named owners; HR-admin guide; learner quick guide | OPS-08, OPS-09 | D-12, D-17 | Each runbook executed once by its owner | Owners named | Owners confirm | 2 (drafting from 7 Dec) | 14 Dec | M |
| E-5.9 | Translation corrections from native review (learner-facing screens first) | X-01 | D-19 (reviewers named 1 Dec; review 1–10 Dec) | i18n parity test | Reviewer sign-off per language | Sign-off for bn, hi and gu | 0.5 + reviewers | 12 Dec | M |
| E-5.10 | Go / no-go review and release sign-off | All | Checklist complete | — | Owner, HR Head, IT | Checklist §4 signed | — | 15 Dec | M |

## 4. Parallel streams and critical path

| Stream | 25–30 Nov | 1–5 Dec | 7–10 Dec | 11–15 Dec |
|---|---|---|---|---|
| A — backend and data | E-2.4, E-2.5, E-2.7, E-2.8, E-2.9, E-2.3 | E-3.1, E-3.2, E-3.3, E-3.8 | E-4.1, E-4.7 | E-5.2, E-5.3, E-5.4, UAT fixes |
| B — frontend, quality, operations | E-2.6, E-2.2, E-2.10, E-2.11 | E-3.5, E-3.10, E-5.1 preparation | E-4.2, E-5.8 drafting, E-5.5 | E-5.1, E-5.6, E-5.9, UAT fixes |
| Business (HR / L&D / IT) | Decisions by 27 Nov; corrected employee extract by 28 Nov; hierarchy sheet; designation list | D-04, D-06, D-09, D-18, D-19 by 1 Dec; server by 5 Dec; translation review | Data reconciliation sign-off | UAT 11–14 Dec; sign-off 15 Dec |

**Critical path:**

```text
decisions (27 Nov) → corrected employee extract (28 Nov) → org + designation + employee loads (29–30 Nov)
  → account provisioning (30 Nov–1 Dec) → data reconciliation (10 Dec) → UAT (11–14 Dec) → sign-off (15 Dec)
```

**Parallel critical path:**

```text
server (5 Dec) → production deployment rehearsal (12 Dec)
```

Every day of slippage on either path removes UAT time; there is no float after 10 Dec.

## 5. Approvals required before specific actions (project rules)

* **Writing real organisation or employee data to `crescent_lms_dev`** (E-2.7, E-2.8, E-2.9, E-3.2): explicit owner approval per task, with before/after snapshots (`scripts/db_readonly_snapshot.py`).
  * Also decide whether UAT data should live in `crescent_lms_dev` or in a dedicated UAT/production environment. This is part of D-17, and it is a privacy consideration.
* **Any new migration** (possibly E-3.8, E-4.4, E-4.5): rehearse on `crescent_lms_test`, provide an SQL preview and backup plan, and get **owner approval before applying to dev** (see the `0011` approval package for the pattern).
* **New dependencies** (E-2.10 Playwright): DEP-01.
* **Commits:** only when the owner asks.

## 6. Decision and data deadlines (stakeholder time, separate from development)

| By | Needed from | Items |
|---|---|---|
| 26 Nov | Owner | SC-03, SC-05, SC-06, DEP-01, navigation decision (E-2.6) |
| 27 Nov | HR / Management / L&D / IT | D-01, D-02, D-03, D-05, D-15, D-16, SC-01, SC-02 |
| 28 Nov | HR | Corrected employee extract (manager codes, status, text codes); hierarchy sheet; canonical designation list |
| 1 Dec | L&D / HR / Owner | D-04, D-06, D-09, D-11 (if SC-02), D-14, D-18 (UAT participants), D-19 (reviewers), SC-04 |
| 3 Dec | HR / Management | Compliance matrix and validity periods (only if C-07 proceeds); KPI definitions (only if C-09 proceeds); D-10 number format |
| 5 Dec | IT / DBA | Production server, DNS, certificate, DBA availability (D-17); D-12 task owner |
| 10 Dec | HR | Data reconciliation sign-off (E-4.7) |
| 11–14 Dec | UAT participants | UAT execution |

## 7. Risks to the 15 December target

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | HR decisions (D-01, D-02, D-03, D-15, D-16) arrive after 27 Nov | High (all 56 business decisions in the readiness workbook are still open) | No real data for UAT | Decision session on 26–27 Nov with pre-filled options; escalate to the owner on 28 Nov |
| R-02 | Employee extract cannot be corrected in time (manager names → codes) | Medium | Team scope, manager views and notifications cannot be accepted | Request the extract now; the import's mapping review covers residual mismatches; reduce the rollout audience (D-16 pilot) |
| R-03 | Production server or DBA not available by 5 Dec | Medium | No deployment readiness on 15 Dec | Raise the IT request on 25 Nov; fallback: release-candidate sign-off on a UAT host with production go-live after 15 Dec (needs owner approval) |
| R-04 | UAT window too short (3 working days + Sunday) | High | Defects found late; partial sign-off | Prepare scripts by 7 Dec; begin informal HR walkthroughs on loaded data from 8 Dec |
| R-05 | Capacity below the two-stream assumption | Medium | Mandatory scope at risk | Approve SC-06; keep stretch items out of the baseline |
| R-06 | Scope expansion through M4 (compliance and certification) without source data | High | Unfinished features at UAT | Gate C-07 on data by 3 Dec (SC-01) |
| R-07 | Native-speaker reviewers unavailable | Medium | Learner-facing languages not accepted | Name reviewers by 1 Dec; learner-facing screens first; fallback: English-first rollout with owner approval |
| R-08 | Regressions during intensive change (no E2E today) | Medium | Unstable release candidate | DEP-01 now; regression run on 11 Dec |
| R-09 | Real employee data in a development database (privacy) | Medium | Compliance and privacy exposure | D-17 decides the UAT environment; minimal fields only (no compensation; existing exclusion list) |
| R-10 | Notifications reach only employees with linked, enabled accounts | Certain if the D-16 audience is partial | Unprovisioned nominees are not informed | D-16 decision explicit; communicate the limitation in the guides |
| R-11 | Five vs six functions (D-15) resolved late | Medium | Reports and placement need rework | No migration required; the UI can rename and create units |

## 8. Reporting cadence

After each task:
* report per `CLAUDE.md` §10;
* update the matrix row (status and evidence), this plan's task state and any changed decision in the gap register.

A weekly status (28 Nov, 5 Dec, 10 Dec) reports matrix counts by status and the critical-path dates.
