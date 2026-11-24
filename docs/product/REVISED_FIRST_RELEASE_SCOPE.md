# Revised First-Release Scope

| | |
|---|---|
| **Date** | 2026-11-23 |
| **Basis** | Company reference material ([reference analysis](../reference-analysis/00_REFERENCE_FILE_INVENTORY.md)) and the company's revised priority |
| **Replaces** | The stage order E → F → … for the immediate release only; later stages in the [roadmap](../LMS_IMPLEMENTATION_ROADMAP.md) remain valid |

## 1. Release goal

Bring the information and calculations kept today in the training-calendar and
skill-matrix workbooks, the competency library and the organisation template into one
configurable portal, built on the completed Stages A–D (identity, RBAC, audit, organisation,
employees, controlled imports).

## 2. In scope — four modules

| # | Module | Delivered in this release | Deferred |
|---|---|---|---|
| 1 | **Organisation management** (extends Stage C) | Configurable unit types, parent rules, effective-dated hierarchy, locations, occupational lists (existing); **organisation-unit Excel import** (profile `organisation` v1: preview, validation, approval, transactional commit, provenance); **org chart view**; "employees in this unit" navigation | Decisions D-01–D-03 (placement of plants vs functions, department→function map); plant-scoped admin roles (C4) |
| 2 | **Training records register** | Training catalogue (`training_programme`), events with planned vs actual dates and planned month, sessions, participation with separate nomination / attendance / completion / assessment result / certificate number, derived past–ongoing–upcoming timeframe, register summary, employee-level records with filters, scope-limited views (all / team / own), audit | Bulk calendar and attendance import profiles (D-05); batches, venues, vendors, finalisation lock, feedback, training requests |
| 3 | **Skill matrix & competency** | Configurable proficiency scales (two seeded from sources), competency library entity with level descriptors, draft/approved governance and editable grade-band requirements, skill-matrix templates scoped to unit / location / designation / functional role, required level **and** required headcount per item, members, append-only assessments, gap per cell, development-plan flag, staffing risk per item (workbook formula), "my skills" | Library and matrix data import (D-04), Dev-Plan / training-need nominations (D-08), achievement rules, promotion rule |
| 4 | **Training calendar & notifications** | Calendar (month / week / list) derived from the register; admin, manager-team and employee views; in-app notification centre (nominated, scheduled, schedule/venue changed, postponed, cancelled, reminder, completed, certificate) with read/unread, preferences, configurable reminder offsets and deduplication; scheduled reminder job for an OS scheduler (the scheduled task itself must still be set up) | Outlook / Teams (needs IT, D-13) — clearly shown as *not connected* |

## 3. Out of scope for this release

AI tutor / AI-generated content, course marketplace, e-learning authoring and delivery,
assessments engine, gamification, compliance matrix and certification register, kiosk / QR
check-in, HRMS integration (boundary documented), certificate generation.

## 4. Access model (reuses Stage B roles; no new roles)

| Capability | Permission | Granted to (migration `0011`) |
|---|---|---|
| Manage programmes, events, sessions, participation, run reminders | `training_events.manage` (Stage B) | HR Admin, Super Admin |
| View every employee's training records | `training.records.view` (new) | HR Admin, Super Admin |
| View team training & skills | `team.learning.view` (Stage B) | Supervisor, HOD, HR Admin |
| View own training & skills | `learning.own.view` (Stage B) | every standard role |
| View all skill matrices / assessments | `competency.view` (new) | HR Admin, Super Admin |
| Maintain scales, library, matrices | `competency.manage` (new) | HR Admin, Super Admin |
| Record assessments | `competency.assess` (new) | HR Admin, Super Admin |
| Organisation-unit import | `imports.organisation.run` / `.commit` (new) + `organisation.manage` | HR Admin, Super Admin |

"Team" = employees reporting (directly or indirectly) to the signed-in user's linked
employee through LINE_MANAGER relationships. Being a manager grants nothing without the
permission. Limited users receive 404 for records outside their scope.

## 5. Database change and approval

All tables are created by **migration `0011`** (15 new tables, 26 indexes, 53 foreign keys;
no alteration of existing tables; inserts 6 permissions and 12 role grants into the
existing access tables, and seeds the two source scales).

- Rehearsed on `crescent_lms_test`: upgrade, downgrade (refused while data exists),
  re-upgrade, model/migration drift check, constraint tests.
- SQL preview: [`docs/database/migration-previews/0011_upgrade.sql`](../database/migration-previews/0011_upgrade.sql)
  and [`0011_downgrade.sql`](../database/migration-previews/0011_downgrade.sql).
- **Applied to `crescent_lms_dev` on 2026-11-23**, after a backup and an isolated restore test
  both passed.
- Verified afterwards:
  - Integrity checks: 148 foreign keys, 0 orphaned records.
  - HR Admin application smoke test.
  - The owner's manual browser verification (2026-11-24).
  - All of these passed.
- Record: [execution report](../database/verification/MIGRATION_0011_EXECUTION_REPORT_20261123.md).
- On any database where `0011` has not been applied, the new modules answer
  `503 schema_migration_pending` and the portal shows an "awaiting database update" notice;
  all existing screens keep working.

**Approval package:** [`MIGRATION_0011_APPROVAL_PACKAGE.md`](../database/MIGRATION_0011_APPROVAL_PACKAGE.md)
— operation inventory, safety properties, the rehearsal on `crescent_lms_test`, and the
exact step-by-step commands (backup, verification, restore test, apply, before/after
comparison, smoke test, rollback). *(2026-11-23 review: the earlier two-line backup
command here was replaced because `mysqldump` is not on PATH on the development PC and
PowerShell 5.1 `>` redirection writes UTF-16, which does not restore reliably.)*

## 5a. Post-implementation review (2026-11-23)

Corrected or completed in the review (details in the review report; all covered by tests):

| Area | Change |
|---|---|
| Migration 0011 | Competency `status` (draft/approved) + approval columns; pre-flight refusal when tables already exist; downgrade also refuses edited seeded scales and existing organisation import jobs; SQL previews regenerated (the old ones omitted 2 permissions and 4 grants) |
| Training register | Separated employees can be recorded for training that started on or before their last working day (historical records); still refused afterwards |
| Calendar | Calendar labels limited to the caller's scope; a cancelled session of a running event is shown as cancelled |
| Reminders | Scheduled job `python -m app.jobs training-reminders` (OS scheduler) creates reminders for everyone, signed in or not; reminder text in IST, not UTC |
| Skill matrix | Designation and functional-role scope selectors; staffing-risk explanation per competency (e.g. "5 skilled ≤ 5 required") |
| Competency library | Draft/approved governance with audited approve / return-to-draft; grade-band requirement editor (codes as written, e.g. `L6–L5`) with audited before/after |
| Organisation import | Existing units with different values become `update` rows applied only on explicit approval (audited correction; effective-dated move) |

Still open (business input needed): D-01…D-14; band-to-grade mapping (D-04) so no
employee gap is derived from bands; who approves library entries and whether edits to an
approved entry must return it to draft (proposed addition to D-04/D-09).

## 6. Implementation sequence followed

1. Baseline inspection and reference analysis (docs `00`–`05`).
2. Backend: models, migration `0011`, services (register, timeframe, notifications, scope,
   competency, gap/risk), routes, organisation import profile; unit + integration tests.
3. Frontend: register, event detail, calendar, notification centre and bell, skill matrix,
   competency library, dashboard widgets, org chart, import profile picker.
4. Verification and local servers (LMS backend `8010`, frontend `4180`).

## 7. Next steps (priority order)

1. Approve and apply migration `0011` to `crescent_lms_dev` (section 5). **Done.** Applied
   2026-11-23; technical verification completed 2026-11-24.
2. Decide D-02/D-03 and load the organisation units through the new import.
3. Approve D-04 and add a competency-library import profile; then skill-matrix and
   calendar import profiles (D-05, D-06).
4. Training-need nominations from Dev Plans (D-08), nomination approvals (D-11).
5. Microsoft 365 channel once IT provides the app registration (D-13).
