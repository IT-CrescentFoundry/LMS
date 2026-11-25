# First Release — Master Completion Matrix

| | |
|---|---|
| **Date** | 24 November 2026 (audit baseline: commit `2604b1a`, clean working tree, `crescent_lms_dev` at Alembic `0011`) |
| **Target** | First-release completion **15 December 2026** |
| **Authority** | **Single source of truth for first-release task status and acceptance.** Status changes are made here first, with evidence. |
| **Companion documents** | [Gap & dependency register](FIRST_RELEASE_GAP_AND_DEPENDENCY_REGISTER.md) (impact, next action, decisions D-xx / SC-xx, data readiness) · [Execution plan to 15 Dec](FIRST_RELEASE_EXECUTION_PLAN_TO_20261215.md) (tasks E-xx) · [Acceptance checklist](FIRST_RELEASE_ACCEPTANCE_CHECKLIST.md) (gates AC-xx) |
| **Status** | **Draft for owner review and approval.** No requirement or milestone has been changed by this document; scope conflicts are listed in §2 for decision. |

## 1. How this matrix was built

**Evidence used:**
* Repository source code: backend routes, models, services, permissions and migrations `0001`–`0011`; frontend router, pages, services and tests.
* Project documentation:
  * [revised first-release scope](../product/REVISED_FIRST_RELEASE_SCOPE.md) (the approved scope);
  * [roadmap](../LMS_IMPLEMENTATION_ROADMAP.md);
  * [product](../product/LMS_PRODUCT_REQUIREMENTS.md), [competency & compliance](../product/COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md) and [training-operations](../product/TRAINING_OPERATIONS_REQUIREMENTS.md) requirements;
  * the [API reference](../architecture/API_REFERENCE.md);
  * the [0011 execution report](../database/verification/MIGRATION_0011_EXECUTION_REPORT_20261123.md);
  * reference analyses `00`–`05`.
* A read-only inspection of the source workbooks in `LMS Data Reference` and of the `docs/business-data-readiness` templates.

**Test figures:**
* The figures quoted are from the execution report §11.10.5 (24 Nov 2026): backend 532 passed, frontend 404 passed, plus lint, types and build.
* **They were not re-run in this audit.** The backend suite rebuilds `crescent_lms_test`, and this audit writes no database.

**What "COMPLETE" means here.** A stage was technically accepted: tests passed and there is operator or acceptance-review evidence (Stages B, C1–C3, D). Release-level business acceptance (UAT with real data) is a separate gate, `AC-UAT` in the [checklist](FIRST_RELEASE_ACCEPTANCE_CHECKLIST.md).

**Why the 0011 modules are "IMPLEMENTED, NOT FULLY VERIFIED".** The first-release modules from migration `0011` are not marked COMPLETE because of the following:
* They were browser-checked only in their **empty state**. There are 0 employees, events, competencies and matrices in `crescent_lms_dev`.
* They have no committed browser E2E.
* They have thin workflow-level tests:
  * backend: 14 integration tests across `test_first_release_api.py` and `test_first_release_review.py`;
  * frontend: about 27 UI tests.
* There has been no stakeholder UAT.

**Status vocabulary** (exactly one per row): COMPLETE · IMPLEMENTED, NOT FULLY VERIFIED · PARTIALLY IMPLEMENTED · NOT IMPLEMENTED · BLOCKED BY BUSINESS DECISION · BLOCKED BY SOURCE DATA · DEFERRED TO FUTURE RELEASE.

**Priority:**

| Priority | Meaning |
|---|---|
| P0 | Release blocker |
| P1 | Mandatory for first release |
| P1-C | Mandatory **only if** the linked scope decision (SC-xx) or business decision is approved; otherwise P3 |
| P2 | Can follow the initial rollout if the owner explicitly accepts it |
| P3 | Future enhancement |

## 2. Scope conflicts found (decision required — nothing has been chosen silently)

| ID | Conflict | Evidence | Recommendation |
|---|---|---|---|
| **SC-01** | Milestone 4, *"Training Compliance, Certifications, Reports and Dashboards" (6–10 Dec)*, conflicts with approved scope §3, which lists *"compliance matrix and certification register … certificate generation"* as **out of scope** and includes no reports beyond the register summary. | [Scope §3](../product/REVISED_FIRST_RELEASE_SCOPE.md); roadmap Stages J, K "Not started" | **Approve a reduced M4:**<ul><li>operational reports + audited Excel export (RPT-02, -03, -05, -08), and a management dashboard if KPIs are approved (RPT-09);</li><li>a record-based **mandatory-training and certification-validity register** (CPL-01…04) **only if** HR supplies the "who must do what, valid for how long" matrix by **3 Dec**. No such source exists today.</li></ul>Keep certificate generation/QR (CPL-06) and effectiveness (RPT-04) deferred. |
| **SC-02** | Milestone 3 names **Manager and Trainer experience**; the brief lists nomination approval, training needs and trainer attendance capture. The approved scope has no trainer role or nomination approval, and defers Dev-Plan training needs (D-08). | Scope §2 (Module 2 deferred list), §4 ("no new roles") | Approve **trainer read-and-attendance access** (TRS-01/02) and **nomination approval** (TRN-09) only if D-09 and D-11 are decided by **1 Dec**; otherwise defer. Keep D-08 training needs deferred. |
| **SC-03** | Organisation **reference-data import** (designations, grades, levels, locations) is not in scope. The employee import needs those 266 designation codes to exist first. | Stage D deferral (Q-47, Q-53); `app/services/imports/profiles.py` (only `employees`, `organisation`) | Approve a small reference-data profile, or formally accept manual keying of 266 designations by HR. |
| **SC-04** | `CLAUDE.md` §5 requires *scope-based permissions*. The approved scope defers plant-scoped admin roles (C4), so organisation, employee and import permissions are global. | `app/api/routes/employees.py:4`; scope §2 Module 1 | Accept the deferral **only if** every first-release HR Admin is a company-wide administrator; record it in the checklist (AC-SEC-04). |
| **SC-05** | Scope defers the calendar, competency-library and skill-matrix imports (D-04, D-05). Without them the ~810 planned sessions, 168 competencies and 23 matrices must be keyed by hand, so the register would be practically empty at UAT. | Scope §2; [gap register §5](FIRST_RELEASE_GAP_AND_DEPENDENCY_REGISTER.md) | Bring forward the **calendar (planned-only)** and **competency-library** imports (P1-C). Keep the wide skill-matrix import P1-C, lower in the order. |
| **SC-06** | Outstanding effort exceeds the 18 working days (Mon–Sat) left before 15 Dec: about 24 mandatory effort-days (≈ 19 developer + ≈ 5 IT/DBA) plus about 27 conditional days. | [Execution plan §2](FIRST_RELEASE_EXECUTION_PLAN_TO_20261215.md) | Approve the **recommended baseline** in the plan (mandatory + ≈ 10.5 days of conditional imports and reports), and confirm **two** parallel development streams. |

## 3. Master completion matrix

### A. Organisation management

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| ORG-01 | Organisation | Configurable unit types and parent/child rules | COMPLETE | `org_structure.py` (`/org/unit-types`, parent-rules); UnitTypesPage; `test_org_structure_api.py` (16), `configuration.test.tsx` (15); C2 operator acceptance | — | — | HR creates a new unit type and rule without code change | P1 |
| ORG-02 | Organisation | Hierarchy of any depth; effective-dated create / move / close / reopen; history and as-of tree | COMPLETE | `OrgUnitHierarchy` (effective-dated); `/units/{id}/move,close,reopen,history`; `test_org_structure_api.py`, `test_org_concurrency.py` | — | — | As-of tree returns the historical placement | P1 |
| ORG-03 | Organisation | Plants and locations (entity and management) | COMPLETE | `location` model and LocationsPage. A plant is a unit of a plant type linked to a location (`models/organisation.py`) | Placement → ORG-05 | — | Locations maintained in the UI with audit | P1 |
| ORG-04 | Organisation | Top-level functions as approved by HR. **The brief lists six (HR separate from Admin & IT); the seed and every source have five, with "HR, Admin & IT" as one function** | BLOCKED BY BUSINESS DECISION | Migration `0005` FUNCTIONS (`ACC_COM`, `HR_ADMIN_IT`, `OPERATION`, `PURCHASE`, `SALES_BD`); TC Library and template 01 use the same five | HR confirms the list. If six, HR renames or creates units in the UI (codes and names are editable); no migration needed | **D-15** | Function units in the database match the HR-signed list exactly | P0 |
| ORG-05 | Organisation | Real organisation hierarchy: plant placement, department→function mapping, departments, sub-functions | BLOCKED BY BUSINESS DECISION | No source maps departments to functions (01 analysis, G-ORG-04). S1 has 43 departments, 5 plants and 84 pairs. S2 has 7 locations and 31 normalised departments. 12 departments have no plant | Decisions; HR-approved hierarchy workbook; load through ORG-09 | D-01, D-02, D-03, D-15 | Tree in the database matches the HR-approved structure; import job approved and audited; no department placed by inference | P0 |
| ORG-06 | Organisation | Job families, grades, levels, designations (management) | COMPLETE | `org_reference.py`; Designations, Grades, Levels, JobFamilies pages; `test_org_reference_api.py` (8) | — | — | — | P1 |
| ORG-07 | Organisation | Canonical designation / grade / level data loaded | BLOCKED BY SOURCE DATA | S1 has 266 designation codes with 16 near-duplicate pairs. Grade band and level band disagree on 17 of 441 S2 rows and 13 of 266 S1 rows. Q-45 and Q-53 are open | HR-validated canonical list; load through ORG-08 or by manual entry | D-01, Q-45, Q-53, SC-03 | Approved list loaded; employee dry run resolves 100 % of designations without unreviewed mappings | P0 |
| ORG-08 | Organisation | Reference-data Excel import (designations, grades, levels, locations) | NOT IMPLEMENTED | Stage D deferred these worksheets; `profiles.py` registers only `employees` v1 and `organisation` v1 | New profile on the Stage D pipeline (preview, validation, approval, audit, provenance) | SC-03 | Integration tests (synthetic) for preview, duplicates, approval and idempotent re-import; dry run on the approved list | P1-C |
| ORG-09 | Organisation | Organisation-unit Excel import (profile `organisation` v1) | IMPLEMENTED, NOT FULLY VERIFIED | `profiles.py` organisation v1; `test_organisation_import.py` (4); update rows only with `apply_updates` | Browser walkthrough with a realistic synthetic workbook; real dry run on the HR file | ORG-05 | Dry run and commit of the approved file; zero silent moves; audit and provenance present | P0 |
| ORG-10 | Organisation | Organisation chart | IMPLEMENTED, NOT FULLY VERIFIED | OrgChartPage; `orgChart.test.tsx` (5); only the 5-node seed seen in the browser | Verify with the full approved hierarchy on phone and desktop | ORG-05 | Full hierarchy renders, search works, usable at 360 px | P1 |
| ORG-11 | Organisation | "Employees in this unit" navigation | IMPLEMENTED, NOT FULLY VERIFIED | `UnitDetailsPanel.tsx` links to the filtered directory | Verify with real employees | EMP-08 | Unit panel lists exactly the employees with an open assignment there | P1 |
| ORG-12 | Organisation | Functional roles, responsibilities, designation→role mapping (management) | COMPLETE | `org_reference.py` functional-roles and responsibilities endpoints; pages; C2/C3 acceptance | — | — | — | P1 |
| ORG-13 | Organisation | Functional-role catalogue data | BLOCKED BY SOURCE DATA | S1 §E "Unique roles" has 0 rows; only 17 of 64 matrix designation labels match HR titles | HR/L&D supplies a catalogue, or decides that matrices are scoped by designation only | Q-23 | Decision recorded; catalogue loaded if supplied | P2 |
| ORG-14 | Organisation | Positions | DEFERRED TO FUTURE RELEASE | Not in scope §2; no model | — | — | — | P3 |
| ORG-15 | Organisation | Plant- or unit-scoped administration (Stage C4) | DEFERRED TO FUTURE RELEASE | Scope §2 defers it; organisation, employee and import permissions are global | Owner acceptance that all first-release HR Admins are company-wide | SC-04 | Written acceptance recorded (AC-SEC-04) | P2 |

### B. Employee management

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| EMP-01 | Employees | Employee master; code validation (Q-54); no compensation data | COMPLETE | `employees.py`; `test_employees_api.py` (16), `test_employee_rules.py`; C3 browser verification | — | — | — | P1 |
| EMP-02 | Employees | Effective-dated assignments (unit, designation, grade, level, location; one primary) | COMPLETE | `test_employee_assignments_api.py` (9); assignment UI tests (10) | — | — | — | P1 |
| EMP-03 | Employees | Functional-role and responsibility assignments | COMPLETE | Employee role endpoints; `rolesResponsibilities` tests (11) | — | — | — | P1 |
| EMP-04 | Employees | Employment status and separation with preview | COMPLETE | `/employment-status`, `/separation-preview`; separation tests (10) | — | — | — | P1 |
| EMP-05 | Employees | Reporting managers (`LINE_MANAGER`, cycle protection) | COMPLETE | `test_employee_reporting_accounts_api.py` (10) | — | — | — | P1 |
| EMP-06 | Employees | Employee ↔ user-account linking | COMPLETE | `PUT /employees/{id}/account`; AccountTab | — | — | — | P1 |
| EMP-07 | Employees | Employee Excel import (`employees` v1): mapping, validation, preview, duplicates, approval, transactional commit, history, error report | COMPLETE | Stage D acceptance review (17 Nov); `test_imports_api.py` (14), `test_import_safety.py` (10), 2,000-row volume test | — | — | — | P1 |
| EMP-08 | Employees | Real employee master loaded (about 441 employees with assignments and reporting lines) | BLOCKED BY SOURCE DATA | S2 has 441 rows. Its problems:<ul><li>managers are recorded **by name**, and 17 manager names (72 rows) match no employee;</li><li>codes are stored as numbers (leading zeros at risk);</li><li>no employment status or e-mail;</li><li>4 repeated names, 2 invalid joining dates, 3 incomplete levels.</li></ul>Which file is authoritative is open (D-01) | HR-corrected extract (manager **codes**, status); dry run, HR review, approval, commit | D-01, ORG-05, ORG-07, D-16 | Committed with 0 unresolved errors; data-quality view reviewed and signed off by HR; reporting lines complete for the rollout audience | P0 |
| EMP-09 | Employees | History, as-of views, data-quality view | COMPLETE | `services/employees/quality.py`; DataQualityPage | — | — | — | P1 |
| EMP-10 | Employees | Employee profile shows training records and skills | NOT IMPLEMENTED | No training or skills content in `features/employees` | Profile tab using `/training/participations?employee=` and `/competency/employees/{id}/skills` | — | HR (and a manager, within scope) sees the employee's records and matrices from the profile | P2 |

### C. Learning programme and training management

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| TRN-01 | Training | Training programme catalogue: create, edit, deactivate | IMPLEMENTED, NOT FULLY VERIFIED | `/training/programmes`; ProgrammeDialog; `training.test.tsx` | UAT with real programmes | — | HR creates and edits programmes; audit rows present | P1 |
| TRN-02 | Training | Training categories / types as a controlled list | PARTIALLY IMPLEMENTED | `category` is free text; delivery mode is an enum | Agreed category list (or formal acceptance of free text) | D-05 | Category list approved; register filter by category is consistent | P2 |
| TRN-03 | Training | Programme ↔ competency link | PARTIALLY IMPLEMENTED | `training_programme.competency_id` (model, service); **not in `schemas/training.py` or the UI** | Expose in the API and UI | CMP-06 | Programme shows and edits its linked competency | P2 |
| TRN-04 | Training | Events: planned month / planned dates vs actual dates; status lifecycle (planned, scheduled, completed, postponed, cancelled) | IMPLEMENTED, NOT FULLY VERIFIED | `records.py:76-82`; DB CHECKs; `test_planned_scheduled_completed_flow_with_evidence_rules`, `test_status_transitions_and_cancellation_notice` | UAT on real events; E2E | E-2.10 | A planned item is never shown or counted as delivered; transitions and reasons as specified | P0 |
| TRN-05 | Training | Sessions: add, reschedule, change venue, cancel | IMPLEMENTED, NOT FULLY VERIFIED | Session endpoints; EventDialogs | UAT; E2E | — | Reschedule notifies participants once; cancelled session shown as cancelled | P1 |
| TRN-06 | Training | Classroom / online / hybrid / OJT delivery modes | IMPLEMENTED, NOT FULLY VERIFIED | `DeliveryMode` enum; join URL | UAT | — | Each mode recorded and shown | P1 |
| TRN-07 | Training | Internal (employee) and external trainer recorded on the event | IMPLEMENTED, NOT FULLY VERIFIED | `trainer_type`, `trainer_employee_id`, `trainer_name`, `provider_name` | UAT | — | An external trainer cannot be linked to an employee record | P1 |
| TRN-08 | Training | Nomination / confirmation by the training administrator | IMPLEMENTED, NOT FULLY VERIFIED | `POST /events/{id}/participants`; separated-employee rule tests | UAT; E2E | EMP-08 | Nominated employee notified; separated-employee rule enforced | P0 |
| TRN-09 | Training | Nomination approval workflow (manager/HR), capacity and waitlist | BLOCKED BY BUSINESS DECISION | Nomination states are only nominated, confirmed and withdrawn; no approver | Approval states, approver resolution, UI, notifications (NTF-06) | D-11, SC-02 | A nomination is approved or rejected by the configured approver; audited; nominee notified | P1-C |
| TRN-10 | Training | Individual attendance (present, partial with minutes, absent, excused) | IMPLEMENTED, NOT FULLY VERIFIED | `records.py:1026-1049`; flow test | UAT; E2E. Per-session attendance is TRN-16 | — | Attendance only on started scheduled or completed events; minutes only when present or partial | P0 |
| TRN-11 | Training | Completion, assessment result, certificate number (recorded, not generated) | IMPLEMENTED, NOT FULLY VERIFIED | DB CHECKs and service rules (`records.py:1050-1076`) | UAT | — | Completion only with attendance; certificate number only with completion | P0 |
| TRN-12 | Training | Register summary, employee-level records and filters; scope-limited views (all / team / own) | IMPLEMENTED, NOT FULLY VERIFIED | `/training/summary`, `/participations`; `test_employee_and_manager_scopes`, `test_calendar_labels_and_records_are_limited_to_the_callers_scope` | Verify with real reporting lines | EMP-08, ADM-06 | A manager sees exactly the team; a learner sees only their own; 404 outside scope | P0 |
| TRN-13 | Training | Training calendar (month / week / list) with admin, team and own views | IMPLEMENTED, NOT FULLY VERIFIED | TrainingCalendarPage (agenda below 768 px); `/training/calendar` | UAT with real events | TRN-14 | Calendar shows the caller's scope; month-only plans flagged | P0 |
| TRN-14 | Training | Bulk training-calendar import, FY 2026-27 **planned** sessions only (about 810 distinct) | BLOCKED BY BUSINESS DECISION | Scope defers it (D-05). Source: 1,532 rows, 722 consolidated copies, unknown duration unit, free-text trainer initials | D-05 answers; new import profile (planned fields only) | D-05, SC-05 | Planned events loaded; **no actual date or attendance inferred**; duplicates resolved by recorded decision | P1-C |
| TRN-15 | Training | Attendance import and historical training records | DEFERRED TO FUTURE RELEASE | Scope §2; no source exists (1 of 1,532 rows has an executed date; no pre-FY 2026-27 records) | — | Source data | — | P3 |
| TRN-16 | Training | Batches, venue/vendor masters, finalisation lock, per-session attendance, recurring events | DEFERRED TO FUTURE RELEASE | Scope §2 deferred list; model docstring defers per-session attendance | — | — | — | P3 |
| TRN-17 | Training | Training feedback / effectiveness capture | DEFERRED TO FUTURE RELEASE | Scope §2 defers feedback | — | SC-01 | — | P3 |
| TRN-18 | Training | Training requests by employees or managers | DEFERRED TO FUTURE RELEASE | Scope §2; `training_requests.submit` has no endpoint | — | — | — | P3 |
| TRN-19 | Training | Learning content, courses, curricula, learning paths, e-learning delivery | DEFERRED TO FUTURE RELEASE | Scope §3; no code (grep `course`, `curricul`, `learning_path`: none) | — | — | — | P3 |
| TRN-20 | Training | Online assessment engine and question bank | DEFERRED TO FUTURE RELEASE | Scope §3; no code | — | — | — | P3 |

### D. Learner experience

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| LRN-01 | Learner | Personal dashboard: upcoming 30 days, notifications, my-skills widget | IMPLEMENTED, NOT FULLY VERIFIED | DashboardPage widgets; `dashboard.test.tsx` (2); owner browser check as an **unlinked** HR account only | Verify as a linked learner with real data | EMP-08, ADM-06 | A linked learner sees their own sessions, notifications and skills | P0 |
| LRN-02 | Learner | Own upcoming training and calendar ("My schedule") | IMPLEMENTED, NOT FULLY VERIFIED | `/training/calendar?mine=true` | Same | Same | Only own sessions shown | P0 |
| LRN-03 | Learner | Own learning history | IMPLEMENTED, NOT FULLY VERIFIED | `/training/participations` (own scope); register Records tab | No dedicated "My Learning" page; its nav item is a "Coming soon" placeholder (`navigation.ts:175`) | ADM-10 | A learner sees their attended and completed records only | P1 |
| LRN-04 | Learner | Personal skill matrix (My Skills) | IMPLEMENTED, NOT FULLY VERIFIED | MySkillsPage; the linked path is tested only with synthetic fixtures (§11.10.5) | Verify with a real linked employee and matrix | EMP-08, SKM-03 | Learner sees required vs assessed and gaps for their matrices | P1 |
| LRN-05 | Learner | Personal competency gap against the library's grade-band requirement | BLOCKED BY BUSINESS DECISION | No employee gap is derived from bands until D-04 (`library.py:12-15`) | Band→grade/designation mapping and computation | D-04 | Gap shown only from an approved mapping | P2 |
| LRN-06 | Learner | View or download certificates | DEFERRED TO FUTURE RELEASE | Scope §3; `certificates.own.view` unused | — | D-10 | — | P3 |
| LRN-07 | Learner | Course access, progress, assessment participation | DEFERRED TO FUTURE RELEASE | Scope §3 | — | — | — | P3 |

### E. Manager experience

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| MGR-01 | Manager | Team training visibility (register, records, calendar) | IMPLEMENTED, NOT FULLY VERIFIED | Team scope through `LINE_MANAGER` lines (`services/training/scope.py:64-80`); scope tests | Real reporting lines; Supervisor/HOD roles granted to managers | EMP-08, ADM-06 | A manager sees direct and indirect reports only | P0 |
| MGR-02 | Manager | Team skill-gap visibility | IMPLEMENTED, NOT FULLY VERIFIED | Matrix grid scoped rows (`/matrices/{id}/grid`) | Same | Same, SKM-03 | Manager sees team rows only, with gaps | P1 |
| MGR-03 | Manager | Dedicated team overview (due, attended, gaps per member) | NOT IMPLEMENTED | No manager page; team scope only narrows the shared pages | Team page | — | Manager sees team status on one page | P2 |
| MGR-04 | Manager | Training needs from Dev-Plan markers (Y / US) | DEFERRED TO FUTURE RELEASE | Scope §2 defers it (D-08) | — | D-08, SC-02 | — | P3 |
| MGR-05 | Manager | Development-plan **flag** per gap (gap ≥ configured steps) | IMPLEMENTED, NOT FULLY VERIFIED | `gap.py:78-85`; grid summary | UAT | — | Flag matches the library rule (gap ≥ 2) | P1 |
| MGR-06 | Manager | Development-plan entity (items, targets, interventions, progress) | DEFERRED TO FUTURE RELEASE | Scope §2; FR-DEV-001…007 | — | D-08 | — | P3 |
| MGR-07 | Manager | Managers or plant assessors record skill assessments | BLOCKED BY BUSINESS DECISION | Only `competency.assess` holders (HR Admin, Super Admin) | Permission or role change per D-09 | D-09 | Configured assessors can assess within scope only; audited | P2 |

### F. Trainer and SME experience

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| TRS-01 | Trainer/SME | Trainer sees own sessions and participant lists | NOT IMPLEMENTED | Trainer is a data field only; there is no trainer role or permission | Trainer scope (events where the trainer is the linked employee) | SC-02, D-09 | Trainer sees only their own events | P1-C |
| TRS-02 | Trainer/SME | Trainer records attendance and outcomes | NOT IMPLEMENTED | Only `training_events.manage` may update participation | Scoped attendance permission; audit | SC-02, D-09 | Trainer records attendance for their own events only; audited | P1-C |
| TRS-03 | Trainer/SME | SME validation of technical learning content | DEFERRED TO FUTURE RELEASE | Content governance out of scope (§3); `learning_content.review` unused | — | — | — | P3 |
| TRS-04 | Trainer/SME | SME / L&D approval of competency-library entries | BLOCKED BY BUSINESS DECISION | Approve and return-to-draft exist for `competency.manage` (HR) only; the approver is undecided | Assign the approver role per D-04 | D-04 | Only the designated approver can approve; audited | P1 |

### G. Competency management

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| CMP-01 | Competency | Configurable proficiency scales; **library 1–4 scale kept separate from skill-matrix 1–5 scale** | IMPLEMENTED, NOT FULLY VERIFIED | Seeded `CF_TC_LIBRARY_1_4` and `CF_SKILL_MATRIX_1_5` (report §7.5); `test_scale_levels_in_use_cannot_be_removed` | Business confirmation of the seeded values | D-06 | Scales confirmed by L&D; no cross-scale comparison | P0 |
| CMP-02 | Competency | Competency library: code, category, sub-category, level descriptors | IMPLEMENTED, NOT FULLY VERIFIED | `models/competency.py`; CompetencyLibraryPage | UAT with real entries | CMP-06 | Entry with 4 descriptors created and viewed | P0 |
| CMP-03 | Competency | Draft / approved governance | IMPLEMENTED, NOT FULLY VERIFIED | Audited approve and return-to-draft; `test_competencies_start_as_drafts_and_approval_is_explicit_and_audited` | **Not enforced downstream:** draft competencies can be used in matrix items and assessments (`set_matrix_items`, `record_assessment` have no status check). The edit-after-approval rule is undecided | D-04 | Behaviour matches the D-04 decision, with tests | P1 |
| CMP-04 | Competency | Grade-band requirement editor (codes as written) | IMPLEMENTED, NOT FULLY VERIFIED | `PUT /band-requirements`; review test | UAT | — | Before/after audited; assessments untouched | P1 |
| CMP-05 | Competency | Competency-library Excel import (TC Library layout) | NOT IMPLEMENTED | Scope defers it; no profile | New profile: TCs, descriptors, bands; drafts stay drafts | SC-05 | Synthetic-workbook tests; dry run on the real file shows 168 rows, 68 as drafts | P1-C |
| CMP-06 | Competency | Library data loaded (168 TCs; 68 drafts have blank columns F–O) | BLOCKED BY BUSINESS DECISION | D-04 open; library labelled "Draft v1"; Read Me/Coverage ranges exclude 5 Sand Plant TCs | L&D/HR approval; load | D-04, CMP-05 | Approved entries loaded as approved; drafts as drafts; counts reconcile to source | P1 |
| CMP-07 | Competency | Competency assessments: append-only, method, assessor, date, evidence | IMPLEMENTED, NOT FULLY VERIFIED | `POST /competency/assessments`; self-assessment refused | UAT | D-09 | History is append-only; no future dates | P0 |
| CMP-08 | Competency | Gap computation (blank = not assessed; ordinal and numeric) | IMPLEMENTED, NOT FULLY VERIFIED | `gap.py`; `test_first_release_rules.py` (17) | UAT | — | Gap states match the documented rules | P0 |
| CMP-09 | Competency | Achievement rules and the promotion (≥ 80 %) rule | DEFERRED TO FUTURE RELEASE | Scope §2 | — | — | — | P3 |

### H. Skill Matrix

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| SKM-01 | Skill Matrix | Matrix templates scoped to unit, location, designation and functional role | IMPLEMENTED, NOT FULLY VERIFIED | MatrixDialogs (`MatrixDialogs.tsx:39-75`). Scope fields are descriptive; members are added explicitly | UAT. Note: membership is not derived from the scope | — | HR creates a scoped matrix | P0 |
| SKM-02 | Skill Matrix | Items with required level **and** required headcount | IMPLEMENTED, NOT FULLY VERIFIED | `PUT /matrices/{id}/items` | UAT | — | Pending required level shown as pending | P0 |
| SKM-03 | Skill Matrix | Matrix members | IMPLEMENTED, NOT FULLY VERIFIED | `POST /matrices/{id}/members` | UAT with real employees | EMP-08 | Members added and removed; audited | P0 |
| SKM-04 | Skill Matrix | Assessment history per employee and item | IMPLEMENTED, NOT FULLY VERIFIED | AssessmentPanel; `/employees/{id}/assessments` | UAT | — | History shown newest first, unchanged | P1 |
| SKM-05 | Skill Matrix | Gap per cell, skilled count, staffing risk (workbook formula preserved) | IMPLEMENTED, NOT FULLY VERIFIED | `gap.py:94-109`; `test_seeded_scales_and_skill_matrix_gap_and_risk` | Confirm the thresholds | D-06 | Risk equals the workbook formula on a reconciled sample sheet | P0 |
| SKM-06 | Skill Matrix | Sheet-specific banding variants (Moulding, NPD, Paint) | BLOCKED BY BUSINESS DECISION | Per-level counts shown instead | — | D-07 | Decision recorded | P2 |
| SKM-07 | Skill Matrix | Skill-matrix data import (23 Bagnan sheets, wide format) | BLOCKED BY BUSINESS DECISION | Scope defers it. A CTC column is on at least 22 of 23 sheets; no assessment date or assessor; one `#REF!` | D-06, D-14 answers; wide-matrix profile with CTC exclusion | D-06, D-14, SC-05 | CTC provably never stored; values imported as `imported_matrix` with the stated as-of date | P1-C |
| SKM-08 | Skill Matrix | Matrices for plants other than Bagnan | BLOCKED BY SOURCE DATA | Only Bagnan supplied | — | Source data | — | P2 |
| SKM-09 | Skill Matrix | Matrix filtering, reporting and export | PARTIALLY IMPLEMENTED | List filters; grid summary; no export | Export (with RPT-08) | RPT-08 | Grid exported to `.xlsx`; export audited | P2 |

### I. Training compliance and certifications (see SC-01)

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| CPL-01 | Compliance | Mandatory and role-specific training requirements (by unit, location, designation, functional role) | NOT IMPLEMENTED | No model or endpoint (grep `compliance`, `mandatory`: none relevant); no source compliance matrix | Requirement-rule model and UI | SC-01, Q-11, Q-34, compliance source data | Rules configured from the HR-approved matrix | P1-C |
| CPL-02 | Compliance | Compliance status per employee (compliant / due soon / expired / missing) | NOT IMPLEMENTED | — | Status derivation from completions | CPL-01 | Status correct on a synthetic fixture and on a UAT sample | P1-C |
| CPL-03 | Compliance | Certification records (number, issue date, validity, expiry) | PARTIALLY IMPLEMENTED | Only a free-text `certificate_number` on participation | Validity on programme; issue and expiry on the record | SC-01, Q-10, Q-11 | Expiry computed from validity; history never overwritten | P1-C |
| CPL-04 | Compliance | Renewal requirements and expiry tracking | NOT IMPLEMENTED | grep `validity`, `renewal`, `expir` in training: none | Expiry window queries; reminders (NTF-07) | CPL-03 | Expiring records listed 30/60/90 days ahead | P1-C |
| CPL-05 | Compliance | Supporting evidence attachments | NOT IMPLEMENTED | No file store for training | Protected upload | SC-01, Q-21 | Evidence stored outside webroot; access-controlled | P1-C |
| CPL-06 | Compliance | Certificate generation (template, numbering, QR verification) | DEFERRED TO FUTURE RELEASE | Scope §3; D-10 open; only JPG appreciation designs exist | — | D-10 | — | P3 |

### J. Notifications and scheduling

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| NTF-01 | Notifications | In-app notification centre, bell, read / unread | IMPLEMENTED, NOT FULLY VERIFIED | NotificationsPage, NotificationBell; `notifications.test.tsx` (3); `test_notifications_of_another_user_cannot_be_read_or_changed` | UAT with linked learners | ADM-06 | Learner sees only own notifications | P0 |
| NTF-02 | Notifications | Training notifications: nominated, scheduled, changed, postponed, cancelled, completed, certificate recorded | IMPLEMENTED, NOT FULLY VERIFIED | `services/notifications.py:43-50`; emitted from `records.py` | Delivered only to **linked, non-disabled accounts**, so it depends on provisioning | ADM-06 | Each event type creates exactly one notification per recipient | P0 |
| NTF-03 | Notifications | Notification preferences (mandatory types locked) | IMPLEMENTED, NOT FULLY VERIFIED | `PUT /notifications/preferences` | UAT | — | Opt-out respected; mandatory types cannot be disabled | P1 |
| NTF-04 | Notifications | Reminders: configurable offsets, deduplication, IST text | IMPLEMENTED, NOT FULLY VERIFIED | `generate_due_reminders`; `test_reminders_are_generated_once_and_follow_reschedules`, `test_scheduled_job_creates_reminders_in_business_time_idempotently` | Offsets confirmed | D-12 | Reminders at the agreed offsets, once each | P1 |
| NTF-05 | Notifications | Background reminder scheduler on the server | PARTIALLY IMPLEMENTED | `python -m app.jobs training-reminders` exists with exit codes; **not scheduled anywhere** | Windows Task Scheduler (or equivalent) on the production host; owner named | D-12, OPS-01 | Task runs at the agreed interval; log reviewed; idempotent re-run | P0 |
| NTF-06 | Notifications | Approval notifications | NOT IMPLEMENTED | Depends on TRN-09 | With TRN-09 | TRN-09 | Approver and nominee notified | P1-C |
| NTF-07 | Notifications | Certification-renewal reminders | NOT IMPLEMENTED | Depends on CPL-04 | With CPL-04 | CPL-04 | Reminder at the agreed window before expiry | P1-C |
| NTF-08 | Notifications | Outlook and Teams delivery | DEFERRED TO FUTURE RELEASE | `/notifications/channels` reports *not connected*; IT prerequisites in doc 05 §4 | — | D-13 | Shown as "not connected" in the UI | P3 |
| NTF-09 | Notifications | Notification text in the recipient's language | PARTIALLY IMPLEMENTED | UI chrome is translated; notification titles and bodies are English strings built in `records.py` | Template keys rendered per language | X-01 | Notification shown in the user's selected language | P2 |

### K. Reports and dashboards (see SC-01)

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| RPT-01 | Reports | Register summary counts (scoped) | IMPLEMENTED, NOT FULLY VERIFIED | `GET /training/summary`; summary cards | UAT | — | Counts reconcile with the register list | P1 |
| RPT-02 | Reports | Training participation and completion by plant / department / period | PARTIALLY IMPLEMENTED | `/participations` filters (unit, designation, attendance, completion); no aggregation | Aggregated report page | SC-01, ORG-05 | Totals per unit and month reconcile with records | P1-C |
| RPT-03 | Reports | Training coverage: planned vs actual events and manhours by plant / department / month | PARTIALLY IMPLEMENTED | Per-event planned vs reported manhours on EventDetailPage | Aggregation; planned and actual kept separate | SC-01, TRN-14, Q-14 | Planned and actual shown side by side, never merged | P1-C |
| RPT-04 | Reports | Training effectiveness | NOT IMPLEMENTED | No feedback or evaluation data (TRN-17 deferred); no KPI definition | Definition, then build | SC-01, KPI decision | — | P3 |
| RPT-05 | Reports | Skill-gap analysis across matrices and plants | PARTIALLY IMPLEMENTED | Per-matrix grid and summary only | Cross-matrix gap and risk report | SC-01 | Gap counts reconcile with grids | P1-C |
| RPT-06 | Reports | Competency status report (library coverage, draft/approved) | NOT IMPLEMENTED | Library list filter by status only | Report | CMP-06 | — | P2 |
| RPT-07 | Reports | Mandatory-training compliance and certification status / expiry reports | NOT IMPLEMENTED | Depends on CPL-01…04 | With CPL | SC-01 | Plant-wise compliance matches the rule set | P1-C |
| RPT-08 | Reports | Audited Excel export of register, records and reports | NOT IMPLEMENTED | Only the import template and error-report downloads exist | Scoped, audited `.xlsx` export, formula-safe | SC-01 | Export respects scope; audit event written; formula injection neutralised | P1-C |
| RPT-09 | Reports | Management dashboard (plant-wise KPIs) | BLOCKED BY BUSINESS DECISION | KPI list unapproved (Q-29; template 07 has 18 draft KPI rows) | KPI approval, then build | SC-01, Q-29 | Each KPI matches its approved definition | P1-C |
| RPT-10 | Reports | Employee training history | IMPLEMENTED, NOT FULLY VERIFIED | `/participations?employee=` (scoped) | UAT | — | Full history for one employee, scoped | P1 |

### L. Administration, governance and access control

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| ADM-01 | Administration | Sign-in, server-side sessions, idle/absolute expiry, CSRF, throttling, password policy | COMPLETE | Stage B: 32/32 browser E2E checks, operator acceptance; security tests | — | — | — | P0 |
| ADM-02 | Administration | RBAC (6 roles), deny by default, route inventory | COMPLETE | `test_route_protection.py`, `test_access_control.py` (15) | — | — | — | P0 |
| ADM-03 | Administration | Team / own record scoping for training and competency | IMPLEMENTED, NOT FULLY VERIFIED | `scope.py:64-80`; scope tests | Real reporting lines | EMP-08 | 404 outside scope, verified in UAT | P0 |
| ADM-04 | Administration | Append-only audit trail and viewer | COMPLETE | Triggers (`0003`); `test_audit.py` (10); AuditLogPage | — | — | — | P0 |
| ADM-05 | Administration | User-account administration UI: create, suspend, disable, reset password, assign roles | PARTIALLY IMPLEMENTED | API complete (`admin_users.py`); **UI read-only** (`UsersPage.tsx:27-31`); the smoke-test account had to be created via the API | Admin UI over the existing API | — | HR Admin creates an account, assigns roles and resets a password in the UI; all audited | P0 |
| ADM-06 | Administration | Account provisioning for the rollout audience (bulk create and link; initial credential handover) | NOT IMPLEMENTED | Only one-by-one API creation | Bulk provisioning from linked employees; handover procedure | D-16, EMP-08 | Every rollout user can sign in and must change their password first; no plaintext passwords stored or e-mailed | P0 |
| ADM-07 | Administration | Role boundaries for trainer, SME, assessor, training coordinator | BLOCKED BY BUSINESS DECISION | Roles: employee, supervisor, hod, sme, hr_admin, super_admin; no trainer or coordinator role | Decision; permission grants (migration if new roles) | D-09, SC-02 | Approved permission matrix implemented and tested | P1 |
| ADM-08 | Administration | Content governance and publishing authority | DEFERRED TO FUTURE RELEASE | Scope §3; `learning_content.*` unused | — | — | — | P3 |
| ADM-09 | Administration | Configuration management UI (reminder offsets, etc.) | DEFERRED TO FUTURE RELEASE | Settings via environment; `settings.manage` unused | — | — | — | P3 |
| ADM-10 | Administration | Navigation shows only released modules | PARTIALLY IMPLEMENTED | Six "Coming soon" items are visible to every user (`navigation.ts:175-180`: My Learning, Courses, Assessments, Career, Certifications, Reports) | Owner decision: hide or keep labelled | Owner | Navigation agreed for UAT | P1 |

### M. Accessibility, languages and integrations

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| X-01 | Accessibility | UI in English, Bengali, Hindi, Gujarati | IMPLEMENTED, NOT FULLY VERIFIED | 1,934 keys in each locale; parity test (`i18n.test.ts`); **bn/hi/gu are machine drafts (Q-58)** | Native-speaker review and corrections | D-19 | Reviewer sign-off per language for learner-facing screens | P0 |
| X-02 | Accessibility | Employee's preferred language applied at sign-in | PARTIALLY IMPLEMENTED | `employee.preferred_language` is stored; the UI language comes only from the device selector | Apply at sign-in | — | A linked user sees their preferred language on first sign-in | P2 |
| X-03 | Accessibility | Translated business content (programme titles, competency names) | BLOCKED BY BUSINESS DECISION | Translation tables exist only for organisation entities; Q-42 (is the library English-only?) | Decision | Q-42 | Decision recorded | P2 |
| X-04 | Accessibility | Phones, tablets, desktops | IMPLEMENTED, NOT FULLY VERIFIED | Mobile drawer; agenda calendar below 768 px; MobileUnitBrowser; Stage B tested 5 widths. **First-release screens not device-tested** | Device check at 360 / 768 / 1280 px | OPS-04 | Key journeys usable at 360 px with no horizontal scroll | P0 |
| X-05 | Accessibility | Accessibility (WCAG 2.2 AA, learner pages) | IMPLEMENTED, NOT FULLY VERIFIED | Semantic components, role-based tests; **no accessibility audit run** | Automated and manual audit | OPS-04 | No critical axe violations on learner pages | P2 |
| X-06 | Integrations | HRMS integration | DEFERRED TO FUTURE RELEASE | Boundary documented (doc 05 §5); `external_ref` columns | — | — | — | P3 |
| X-07 | Integrations | PMS integration | DEFERRED TO FUTURE RELEASE | FR-INT-002 (not until scoped) | — | Q-20 | — | P3 |
| X-08 | Integrations | AI tutoring and recommendations (provider-independent; Claude first) | DEFERRED TO FUTURE RELEASE | Scope §3. **No AI code or provider interface exists** (grep `anthropic`, `claude`, `ai_provider`: none) | — | — | — | P3 |
| X-09 | Integrations | SCORM and advanced e-learning | DEFERRED TO FUTURE RELEASE | Scope §3; Q-16 | — | — | — | P3 |
| X-10 | Integrations | Kiosk, badge QR, PIN, OTP / SSO | DEFERRED TO FUTURE RELEASE | Scope §3; Q-07, Q-08, Q-09 | — | — | — | P3 |
| X-11 | Integrations | Career, future-role and succession learning | DEFERRED TO FUTURE RELEASE | Roadmap Stage M; not in scope | — | — | — | P3 |
| X-12 | Integrations | Advanced analytics | DEFERRED TO FUTURE RELEASE | Roadmap Stage K/L | — | — | — | P3 |

### N. Release operations and quality

| ID | Domain | Requirement | Current Status | Existing Evidence | Missing Work | Dependency | Acceptance Criteria | Priority |
|---|---|---|---|---|---|---|---|---|
| OPS-01 | Operations | Production hosting: server, HTTPS reverse proxy, process supervision, secret store, production configuration | NOT IMPLEMENTED | No deployment artefacts (no Dockerfile, service definition or proxy config); production config guards exist (`config.py:271-277`) | Host provisioning; deployment procedure | D-17 | Application reachable over HTTPS on the agreed host; `secure` cookies; API docs off | P0 |
| OPS-02 | Operations | Production database: schema, accounts, migrations `0001`–`0011`, audit-trigger privilege (DBA) | NOT IMPLEMENTED | Dev procedure proven (execution report); the audit-trigger privilege is a dev-only setting (ADR-048) | DBA plan and execution | D-17 | `alembic current` = head on production; triggers present; separate runtime and migration accounts | P0 |
| OPS-03 | Operations | Production backup schedule and restore test | PARTIALLY IMPLEMENTED | Dev backup and isolated restore validated (23 Nov); restore needs a DBA | Scheduled backups and a restore test on production | D-17 | Restore of a production backup into an isolated schema passes | P0 |
| OPS-04 | Operations | Automated browser E2E for first-release journeys | NOT IMPLEMENTED | None committed (report §8, §11.11.6) | Playwright (or similar) suite; **needs approval to add a dev dependency** | DEP-01 | E2E suite passes for the learner, manager and HR journeys at 3 widths | P1 |
| OPS-05 | Operations | Workflow-level automated test depth for first-release modules | PARTIALLY IMPLEMENTED | Backend: 14 integration tests for training, competency and notifications; frontend: about 27 UI tests | Add tests per new and changed workflow | — | Every P0/P1 workflow has at least one integration test and one UI test | P1 |
| OPS-06 | Operations | CI pipeline | NOT IMPLEMENTED | Only `scripts/check.ps1` (local) | CI configuration | — | — | P2 |
| OPS-07 | Operations | Monitoring, log retention, alerting | PARTIALLY IMPLEMENTED | Structured logging; `/health/live`, `/health/ready` | Monitoring on the production host | OPS-01 | — | P2 |
| OPS-08 | Operations | Operational runbooks and ownership (deploy, backup, reminder job, account admin, imports, incidents) | NOT IMPLEMENTED | Fragments in README, `jobs.py` docstring, 0011 approval package | Runbook and owner list | D-17, D-12 | Each runbook executed once by its named owner | P1 |
| OPS-09 | Operations | HR-admin guide and end-user quick guides (four languages for learners) | NOT IMPLEMENTED | — | Guides | X-01 | Guides used in UAT | P1 |
| OPS-10 | Operations | Stakeholder UAT on real data with sign-off | NOT IMPLEMENTED | Owner browser check on empty data only | UAT plan, participants, scripts, defect triage, sign-off | D-18, EMP-08 | Signed UAT for every in-scope domain (checklist §3) | P0 |
| OPS-11 | Operations | Performance at real volume | IMPLEMENTED, NOT FULLY VERIFIED | 2,000-row import volume test; no load check of register, calendar or grid | Timing check with loaded data | EMP-08, TRN-14 | Typical API response < 300 ms (NFR-007) on loaded data | P2 |
| OPS-12 | Operations | Production security review (HTTPS origins, cookies, dependency audit, headers) | PARTIALLY IMPLEMENTED | Production guards in config; no dependency audit or production review | Review and remediation | OPS-01 | Review signed; no open high findings | P1 |
| OPS-13 | Operations | Privacy: compensation and sensitive columns never stored | COMPLETE | ADR-052; import safety tests; exclusion list blocks CTC headers | Must be re-proven for any new profile (SKM-07) | D-14 | — | P0 |

## 4. Status summary (141 requirements)

| Status | Count | IDs |
|---|---|---|
| COMPLETE | **17** | ORG-01, 02, 03, 06, 12 · EMP-01…07, 09 · ADM-01, 02, 04 · OPS-13 |
| IMPLEMENTED, NOT FULLY VERIFIED | **42** | ORG-09, 10, 11 · TRN-01, 04–08, 10–13 · LRN-01–04 · MGR-01, 02, 05 · CMP-01–04, 07, 08 · SKM-01–05 · NTF-01–04 · RPT-01, 10 · ADM-03 · X-01, 04, 05 · OPS-11 |
| PARTIALLY IMPLEMENTED | **16** | TRN-02, 03 · SKM-09 · CPL-03 · NTF-05, 09 · RPT-02, 03, 05 · ADM-05, 10 · X-02 · OPS-03, 05, 07, 12 |
| NOT IMPLEMENTED | **24** | ORG-08 · EMP-10 · MGR-03 · TRS-01, 02 · CMP-05 · CPL-01, 02, 04, 05 · NTF-06, 07 · RPT-04, 06, 07, 08 · ADM-06 · OPS-01, 02, 04, 06, 08, 09, 10 |
| BLOCKED BY BUSINESS DECISION | **13** | ORG-04, 05 · TRN-09, 14 · LRN-05 · MGR-07 · TRS-04 · CMP-06 · SKM-06, 07 · RPT-09 · ADM-07 · X-03 |
| BLOCKED BY SOURCE DATA | **4** | ORG-07, 13 · EMP-08 · SKM-08 |
| DEFERRED TO FUTURE RELEASE | **25** | ORG-14, 15 · TRN-15–20 · LRN-06, 07 · MGR-04, 06 · TRS-03 · CMP-09 · CPL-06 · NTF-08 · ADM-08, 09 · X-06–12 |

## 5. Release classification

**First-release mandatory** (P0/P1, must work before the initial rollout):
* **Organisation:** ORG-01…07, 09…12.
* **Employees:** EMP-01…09.
* **Training:** TRN-01, 04…08, 10…13.
* **Learner:** LRN-01…04.
* **Manager:** MGR-01, 02, 05.
* **Trainer/SME:** TRS-04.
* **Competency:** CMP-01…04, 06…08.
* **Skill Matrix:** SKM-01…05.
* **Notifications:** NTF-01…05.
* **Reports:** RPT-01, 10.
* **Administration:** ADM-01…07, 10.
* **Languages and devices:** X-01, X-04.
* **Operations:** OPS-01…05, 08, 09, 10, 12, 13.

**First-release conditional** (P1-C, depending on a decision, data, external access or approval):
* ORG-08 (SC-03)
* TRN-09 and NTF-06 (D-11, SC-02)
* TRN-14 (D-05, SC-05)
* TRS-01, 02 (SC-02, D-09)
* CMP-05 (SC-05)
* SKM-07 (D-06, D-14, SC-05)
* CPL-01…05 and NTF-07 (SC-01 plus HR compliance source data)
* RPT-02, 03, 05, 07, 08, 09 (SC-01; RPT-09 also needs KPI approval)

**Future enhancements** (P2/P3; the rollout is valid without them):
* **P2, post-rollout if explicitly accepted:**
  * Organisation and employees: ORG-13, 15 · EMP-10
  * Training and learner: TRN-02, 03 · LRN-05
  * Manager: MGR-03, 07
  * Skill Matrix: SKM-06, 08, 09
  * Notifications and reports: NTF-09 · RPT-06
  * Languages and accessibility: X-02, 03, 05
  * Operations: OPS-06, 07, 11
* **P3:** every DEFERRED row, plus RPT-04:
  * AI tutoring and recommendations: X-08
  * SCORM and e-learning: X-09, TRN-19
  * Outlook / Teams: NTF-08
  * HRMS and PMS: X-06, X-07
  * Advanced analytics: X-12
  * Career and succession: X-11

None of these was explicitly included in the approved first-release scope (scope §3 lists AI, e-learning, HRMS and kiosk as out of scope, and Outlook/Teams as *not connected*), so no mandatory scope is being dropped. The two places where the brief or milestones go beyond the approved scope are raised as **SC-01** and **SC-02**, not resolved here.

## 6. Change control

* Status changes require evidence: a test run with its date and result, a UAT record, or a signed decision. Record the change in the row and in the [execution plan](FIRST_RELEASE_EXECUTION_PLAN_TO_20261215.md) task.
* A requirement moves to COMPLETE only when its row's acceptance criterion **and** the matching gate in the [acceptance checklist](FIRST_RELEASE_ACCEPTANCE_CHECKLIST.md) are met.
* Changing a priority to P2 or P3, or accepting an SC-xx, requires the owner's recorded approval in the [gap register §3](FIRST_RELEASE_GAP_AND_DEPENDENCY_REGISTER.md).
