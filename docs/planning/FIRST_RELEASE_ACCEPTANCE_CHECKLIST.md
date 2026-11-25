# First Release — Acceptance Checklist

| | |
|---|---|
| **Date** | 24 November 2026 |
| **Status** | **Draft for owner approval.** All items are **Open**. |
| **Related** | [Master completion matrix](FIRST_RELEASE_MASTER_COMPLETION_MATRIX.md) (requirement-level criteria) · [Gap & dependency register](FIRST_RELEASE_GAP_AND_DEPENDENCY_REGISTER.md) · [Execution plan](FIRST_RELEASE_EXECUTION_PLAN_TO_20261215.md) |

## 1. Principles

1. The first release is **not** complete because code compiles or automated tests pass. Each domain needs the evidence below **and** a named business sign-off.
2. Evidence must be **recorded**: a dated test run with its result, a UAT script with its outcome, a signed decision, or a database verification capture. A claim without a record is not evidence.
3. A matrix row becomes COMPLETE only when its own acceptance criterion and the gate(s) below that reference it are met.
4. Conditional (P1-C) items are accepted only if the related SC-xx or D-xx was approved. Otherwise they must appear in AC-SCOPE-02 as formally deferred.
5. UAT uses **real, HR-approved business data** in an environment approved under D-17. Synthetic data is acceptable for automated tests only.

## 2. Release gates

### Scope and decisions

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-SCOPE-01 | SC-01…SC-06, DEP-01 and every decision marked "Blocks release" are decided and recorded | Gap register §3 updated with answer, approver, date | Owner | E-2.1 |
| AC-SCOPE-02 | Every P1-C item not delivered, and every P2 item, is formally accepted as post-rollout | Signed list referencing matrix IDs | Owner | Matrix §5 |
| AC-SCOPE-03 | No approved first-release requirement was dropped silently | Matrix §4 counts reconciled with the approved scope | Owner | Matrix |

### Authentication, RBAC and security

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-SEC-01 | Sign-in, idle and absolute expiry, CSRF, throttling, forced password change work on the release environment | E2E run on the release host; Stage B results re-run | Dev lead | ADM-01, E-5.6 |
| AC-SEC-02 | Permission matrix (roles × permissions) matches the approved D-09 / D-16 decisions | Exported role–permission listing signed by HR | HR Head | ADM-02, ADM-07, E-3.8 |
| AC-SEC-03 | Team and own scope proven with real reporting lines: a manager sees only the team; a learner only themselves; 404 outside scope | UAT scripts with named sample users | HR + UAT users | ADM-03, TRN-12, MGR-01 |
| AC-SEC-04 | Global (not plant-scoped) HR Admin access accepted for this release (SC-04), with the list of HR Admin holders | Signed acceptance and account list | Owner | ORG-15 |
| AC-SEC-05 | Production security review complete; no open high findings; `secure` cookies, HTTPS origins, API docs off, secrets outside the repository | Review record; dependency-audit reports | Dev lead + IT | OPS-12, E-5.5 |
| AC-SEC-06 | No compensation or sensitive columns stored by any import used for onboarding | Tests plus a database check on loaded data | Dev lead | OPS-13, D-14 |

### Organisation and employee data

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-DATA-01 | Function list matches the HR-signed D-15 answer | Screenshot or database query plus decision record | HR | ORG-04 |
| AC-DATA-02 | Organisation hierarchy loaded from an HR-approved file; no inferred department–function placement | Import job ID, approval audit event, reconciliation | HR | ORG-05, E-2.7 |
| AC-DATA-03 | Designations, grades and levels loaded from the canonical list | Reconciliation count | HR | ORG-07, E-2.8 |
| AC-DATA-04 | Employee master, assignments and reporting lines loaded; data-quality view reviewed with every remaining flag accepted or fixed | Import job ID; data-quality export; HR sign-off | HR | EMP-08, E-2.9 |
| AC-DATA-05 | Rollout accounts provisioned and linked; sample sign-ins per role succeed | Provisioning record (counts, not passwords); sample sign-in log | HR + IT | ADM-05, ADM-06 |
| AC-DATA-06 | Onboarded learning data (library, calendar, matrices as approved) reconciles to source; planned rows remain planned | Signed reconciliation sheet | L&D | E-4.7 |

### Learning workflows

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-LRN-01 | Programme → event (planned → scheduled → completed) → sessions → nomination → attendance → completion → certificate number, end to end on real data | UAT script with event IDs; E2E green | L&D | TRN-01…13 |
| AC-LRN-02 | Planned dates never shown or counted as actual; month-only plans flagged | UAT check on imported or entered plans | L&D | TRN-04, TRN-14 |
| AC-LRN-03 | Learner journey: dashboard, My Learning, calendar, My Skills, notifications, as a linked employee | UAT with at least 3 learners from different units | UAT users | LRN-01…04 |
| AC-LRN-04 | Manager journey: team register, calendar and skill gaps | UAT with at least 2 managers | UAT users | MGR-01, 02, 05 |
| AC-LRN-05 | If approved: nomination approval (SC-02 / D-11) and trainer access (SC-02 / D-09) | UAT scripts | HR | TRN-09, TRS-01/02 |

### Competency and Skill Matrix

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-CMP-01 | Library scale (1–4) and matrix scale (1–5) are separate, confirmed (D-06) and never compared across scales | Decision record; UAT check | L&D | CMP-01 |
| AC-CMP-02 | Library entries loaded with correct draft/approved status; approval by the D-04 approver only; governance rule enforced | Audit events; tests | L&D | CMP-02, 03, 06, TRS-04 |
| AC-CMP-03 | Skill matrix: required level and headcount, members, assessments, gap, plan flag and staffing risk reconcile with a source workbook sample | Reconciliation of one Bagnan sheet | Plant head / L&D | SKM-01…05 |
| AC-CMP-04 | Assessments append-only and recorded only by authorised assessors | Tests; UAT | HR | CMP-07, MGR-07 |

### Compliance and certificates (only if SC-01 approves them)

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-CPL-01 | Mandatory-training rules match the HR-approved compliance matrix; status per employee correct on a sample | Signed rule list; UAT sample | HR | CPL-01, 02 |
| AC-CPL-02 | Certification validity, expiry and renewal reminders correct; history never overwritten | Tests; UAT | HR | CPL-03, 04, NTF-07 |
| AC-CPL-03 | Otherwise: formally deferred in AC-SCOPE-02 | Signed deferral | Owner | — |

### Reporting and dashboards

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-RPT-01 | Register summary and employee history reconcile with records | UAT reconciliation | L&D | RPT-01, 10 |
| AC-RPT-02 | If SC-01: participation, coverage (planned vs actual separate) and skill-gap reports reconcile; exports scope-filtered, audited and formula-safe | Reconciliation; audit events; tests | L&D + management | RPT-02, 03, 05, 08 |
| AC-RPT-03 | If KPIs approved: each dashboard KPI matches its written definition | KPI definition sheet signed | Management | RPT-09 |

### Notifications and scheduling

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-NTF-01 | Each notification type is generated once for each linked recipient; preferences respected; mandatory types locked | Tests plus a UAT sample | HR | NTF-01…04 |
| AC-NTF-02 | Reminder job scheduled on the release host at the D-12 interval, with a named owner; run history shows success; re-run idempotent | Task Scheduler history; job log | IT | NTF-05, E-5.4 |
| AC-NTF-03 | Outlook and Teams clearly shown as "not connected" | Screenshot | Dev lead | NTF-08 |

### Languages and responsive use

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-I18N-01 | bn, hi and gu reviewed by native speakers for learner-facing screens; corrections applied; parity test green | Reviewer sign-off per language | D-19 reviewers | X-01, E-5.9 |
| AC-I18N-02 | Key journeys usable at 360, 768 and 1280 px, no horizontal scrolling; checked on at least one real phone | E2E at 3 widths; device screenshots | Dev lead + UAT | X-04 |
| AC-NAV-01 | Navigation shows only the modules approved for release (or clearly labelled as planned, per the owner's decision) | Screenshot | Owner | ADM-10 |

### Audit, backup and restore

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-AUD-01 | Audit events present for imports, approvals, account administration, training and competency changes; audit triggers present on the release database | Audit query sample; trigger check | Dev lead + DBA | ADM-04, OPS-02 |
| AC-BKP-01 | Release database backup taken before go-live and restore-tested into an isolated schema (schema fingerprint and content hashes match) | Verification captures (existing SQL in `docs/database/verification/`) | DBA | OPS-03, E-5.3 |
| AC-BKP-02 | Backup schedule and retention in place with a named owner | Runbook entry | IT | OPS-08 |

### Automated and browser tests

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-TEST-01 | Backend (on `crescent_lms_test` only), frontend, lint, format, mypy, typecheck and build all pass on the release commit | Dated command outputs in the execution record | Dev lead | OPS-05, E-5.6 |
| AC-TEST-02 | Browser E2E suite committed and green for HR, learner and manager journeys at 3 widths | E2E report | Dev lead | OPS-04 |
| AC-TEST-03 | Every P0/P1 workflow row has at least one integration test and one UI test | Coverage mapping table | Dev lead | OPS-05 |

### Stakeholder UAT

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-UAT-01 | UAT participants and sign-off authorities named (D-18) | Decision record | Owner | D-18 |
| AC-UAT-02 | UAT scripts executed on real data for every in-scope domain; no open P0/P1 defects; P2 defects accepted in writing | UAT log, defect list | UAT authorities | OPS-10, E-5.7 |
| AC-UAT-03 | Domain sign-offs in §3 complete | Signatures | See §3 | — |

### Deployment readiness

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-DEP-01 | Release host provisioned (HTTPS, DNS, service supervision, secrets store) | IT confirmation; smoke test | IT | OPS-01 |
| AC-DEP-02 | Release database at head revision with verified integrity (0 orphans) | Verification capture | DBA | OPS-02 |
| AC-DEP-03 | Deployment and rollback rehearsed from a clean checkout of the release commit | Rehearsal record | Dev lead + IT | E-5.1 |
| AC-DEP-04 | Release commit tagged; working tree clean; no secrets or real data in the repository | Git record | Dev lead (on the owner's instruction) | — |

### Operational ownership and documentation

| ID | Criterion | Evidence required | Owner | Matrix / task |
|---|---|---|---|---|
| AC-OPS-01 | Runbooks for deploy, rollback, backup/restore, reminder job, account admin, imports and incidents, each executed once by its named owner | Runbook sign-off | IT + HR | OPS-08 |
| AC-OPS-02 | HR-admin guide and learner quick guide available (learner guide in the release languages) | Documents | HR | OPS-09 |
| AC-OPS-03 | README, roadmap, scope and API reference updated to the released state | Diff reviewed | Dev lead | `CLAUDE.md` §9 |
| AC-OPS-04 | Post-release support owner and defect channel named | Decision record | Owner | — |

## 3. Domain acceptance and sign-off

| Domain (matrix section) | Evidence that must exist before sign-off | Sign-off by |
|---|---|---|
| A Organisation | AC-DATA-01…03; ORG-09/10/11 verified on real data | HR Head |
| B Employees | AC-DATA-04, AC-DATA-05, AC-SEC-03 | HR Head |
| C Training management | AC-LRN-01, AC-LRN-02, AC-DATA-06 (calendar) | L&D lead |
| D Learner experience | AC-LRN-03, AC-I18N-01, AC-I18N-02 | L&D lead + learner sample |
| E Manager experience | AC-LRN-04, AC-SEC-03 | Manager representatives |
| F Trainer / SME | AC-LRN-05 (if approved), AC-CMP-02 (approver) | L&D lead |
| G Competency | AC-CMP-01, AC-CMP-02, AC-CMP-04 | L&D / HR |
| H Skill Matrix | AC-CMP-03 | Plant head (Bagnan) / L&D |
| I Compliance and certification | AC-CPL-01/02, or AC-CPL-03 | HR Head |
| J Notifications | AC-NTF-01…03 | HR + IT |
| K Reports | AC-RPT-01…03 | Management |
| L Administration and security | AC-SEC-01…06, AC-AUD-01, AC-NAV-01 | Owner + IT |
| M Languages and devices | AC-I18N-01, AC-I18N-02 | Reviewers + owner |
| N Operations | AC-BKP-01/02, AC-DEP-01…04, AC-OPS-01…04, AC-TEST-01…03 | IT + owner |

## 4. Go / no-go (15 December 2026)

**Go** requires all of the following:
* every gate in §2 is closed or formally deferred under AC-SCOPE-02;
* every domain in §3 is signed;
* there are no open P0 defects.

**No-go** in either of these cases:
* any P0 matrix row is not COMPLETE;
* any "Blocks release" decision is still open.

In a no-go, the owner decides between:
1. a release-candidate sign-off with a dated go-live;
2. a reduced rollout audience (D-16).

| Role | Name | Decision | Date |
|---|---|---|---|
| Project owner | | | |
| HR Head | | | |
| L&D lead | | | |
| IT / infrastructure | | | |
