# 05 — Source-to-System Mapping and Open Decisions

| | |
|---|---|
| **Date** | 2026-11-23 |
| **Labels** | **C** = confirmed by a source · **I** = inferred from several sources · **P** = proposed application behaviour · **Q** = pending business confirmation |
| **Implementation** | Migration `0011` and the first-release modules (see [revised scope](../product/REVISED_FIRST_RELEASE_SCOPE.md)) |

## 1. Source → portal mapping

| Source | What it holds | Business logic | Portal module / entity | Status |
|---|---|---|---|---|
| Training Calendar workbooks — calendar sheets (20) | One row per planned session: subject, trainer, department, location, month, plan date, executed date, time, duration, planned attendees, attended | Planned manhours `=J*K`, actual manhours `=J*L` (C) | **Training Records** → `training_event` (planned month / planned dates / actual dates kept apart; `planned_participant_count`, `reported_attendance_count`, `planned_duration_minutes`; `planned_manhours` and `reported_manhours` derived) + `training_session` | Implemented. Bulk calendar import: **deferred** (D-05) |
| Calendar "Training Executed Date" / "Total Attended" | Actuals (1 of 1,532 rows filled) | — | `actual_start_date`, `reported_attendance_count` (headcount only, never individual attendance) | Implemented |
| Individual attendance | **Not in any workbook** | — | `training_participation` (nomination ≠ attendance ≠ completion) | Implemented (manual entry); attendance import deferred |
| Skill-matrix sheets (23) | Employees × items, scores 1–5, legend, "Required Skilled Manpower" row | Per-employee and per-item counts by score; available skilled = score ≥ 3; risk `=IF(avail<=req,"High",IF(avail<=req+1,"Medium","Low"))` (C) | **Skill Matrix** → `skill_matrix`, `skill_matrix_item.required_headcount`, `skill_matrix_member`, `competency_assessment`; scale `CF_SKILL_MATRIX_1_5` with `competent_rank = 3`; `risk_medium_margin = 1`; per-item counts by rank, skilled count and risk in the grid | Implemented (formula preserved exactly, incl. "High when equal" — Q) |
| Skill-matrix banding variants | Moulding/NPD band 1–2 / 3–4 / 5; Paint-CF averages and % bands | Sheet-specific (C) | Counts per individual level are shown (a superset of every banding); the variant bands are **not** implemented | Q (D-07) |
| Dev. Plan sheets (17) | Y / US markers per employee × item | Y ≈ score 1–2, US ≈ score 3–4 (I, ~98 %) | Not implemented (training-need nominations) | Deferred (D-08) |
| Competency library — TC Library | 168 TCs: code, function, sub-function, name, scope, level descriptors 1–4, required level by grade band, assessment method, KRA link | Gap = required − current; gap ≥ 2 needs an individual plan; promotion ≥ 80 % at next band (C, Read Me) | **Competency Library** → `competency` (+ `competency_level_descriptor`, `competency_band_requirement`), scale `CF_TC_LIBRARY_1_4` (`gap_method = numeric`, `plan_gap_steps = 2`); gap and `needs_plan` computed per cell | Library entity and rules implemented; **library import deferred** (D-04); promotion rule not implemented |
| Competency library — Coverage | TC counts per sub-function; 445 employees per band | Contains counting-range defects | Not migrated (reporting) | — |
| Organisation template (S1) | Plants, 43 departments, 84 plant–department pairs, 266 designation codes (title+grade+level), grades, levels | Plant × department matrix (C) | **Organisation** → existing configurable `org_unit_type` / `org_unit` / `location` / `designation` / `grade` / `job_level`; **new import profile `organisation` v1** (units with type, parent, location) | Implemented (import creates units; existing units are never silently moved) |
| UpsideLMS documents | Current product behaviour (events = batches, nominate/confirmed, present/absent/release, finalise, 90-day completed list, 1–3 skill levels) | Product behaviour, not company rules (C) | Used as evidence only; no workflow copied without a company source | — |
| Initial Layouts PDF | Crescent's forward design: compliance matrix, certification register, kiosk, practical sign-off, escalation ladder | Thresholds "to be confirmed" (C) | Out of the first release (compliance/certification stages) | Deferred |
| Certificate designs | 2000×1414 landscape, navy #1D3E6F, gold #FBB424, orange #F37021, "Certificate of Appreciation" | No number / QR / hours (C) | `training_participation.certificate_number` (recorded, not generated); generation deferred | Deferred (D-10) |

## 2. Rules implemented, with their evidence

| Rule | Label | Where |
|---|---|---|
| A planned event is not a delivered event; planned and actual dates are separate | C (calendar columns G/H) | `training_event`, `records.change_status` |
| `completed` requires an actual start date that is not in the future | P | DB CHECK + service |
| Attendance only for scheduled/completed events that have started | P | `records.update_participation` |
| Completion requires present/partial attendance; certificate requires completion | P | DB CHECKs + service |
| Unrecorded employment status is never treated as active; separated employees can be recorded only for training that started on or before their last working day (historical records kept; corrected in the 2026-11-23 review — previously refused outright) | C (CLAUDE.md, Stage C3) | `records.add_participants` |
| Manhours = duration × headcount | C (workbook formula) | `records.manhours` (duration in minutes — unit is Q) |
| Proficiency scales are configurable; different sources keep different scales | C (1–5 matrix vs 1–4 library vs 1–3 UpsideLMS) | `proficiency_scale` / `proficiency_level` |
| Ordinal gap = rank difference; numeric value difference only for numeric scales | P | `competency/gap.py` |
| Blank = not assessed (never level 0/1) | P (Q whether blank means "not applicable") | `compute_gap` |
| Library gap ≥ 2 → individual plan needed | C (library Read Me) | `needs_development_plan` |
| Skilled = score ≥ 3; staffing risk formula | C (matrix formulas) | `staffing_risk`, `item_stats` |
| Notifications only from real business events; each at most once | P | `services/notifications.py` (UNIQUE `dedupe_key`) |
| Reminders are generated by a scheduled job (`python -m app.jobs training-reminders`, OS scheduler), by an administrator, or when a user opens their notification centre; times shown in IST (fixed offset, no DST) | P | `app/jobs.py`, `generate_due_reminders` |
| New library competencies are drafts until an explicit, audited approval; drafts are never published silently | C (library: 68 drafts, blank columns F–O) / P (workflow) | `competency.status`, `change_competency_status` |
| Grade-band required levels are configuration (codes as written, e.g. `L6–L5`); edits audited; recorded assessments never changed; no employee gap from bands until D-04 | C (library J–M) / Q (band→grade map) | `set_band_requirements` |
| Outlook / Teams not connected until IT provides an app registration | P | `/notifications/channels` reports *not connected* |

## 3. Open decisions (business / HR / IT)

| ID | Decision needed | Owner | Effect while open |
|---|---|---|---|
| D-01 | Which file is the second organisation template? Is the HR extract outside the reference folder an authorised source? *(2026-11-23 note: the user subsequently authorised `CF Files\PMS Portal Docs\Organization Structure.xlsx`, and only that file, as a supplemental company reference. Reconciliation in [01 §10](01_ORGANISATION_STRUCTURE_ANALYSIS.md). Still open: which file is authoritative.)* | HR | S1 and the authorised HR extract (S2) are both used as references. Neither is loaded. |
| D-02 | Where do plants sit relative to the five functions (Q-48)? Plant → Function → Department, Function → Plant → Department, or plants as locations only? | HR / Management | Import supports any choice: administrators create unit types and parent rules first |
| D-03 | Department → function mapping (absent from every source); 12 departments with no plant | HR | Not inferred; departments are not placed under functions automatically |
| D-04 | Approve loading the competency library (168 TCs, 68 drafts) and how grade bands map to grades/designations | L&D / HR | Library entity ready; data not loaded. *(2026-11-23: draft/approved governance and the band editor now exist; also needed — who approves entries, and whether editing an approved entry returns it to draft. Re-verification found Read Me band→grade text and Source B band/level disagreeing on 17 of 441 rows; see [03 §11](03_SKILL_MATRIX_AND_COMPETENCY_ANALYSIS.md).)* |
| D-05 | Calendar import: duration unit, month-text formats, trainer initials, duplicate Bagnan consolidated copy | L&D | Events entered manually or via a future calendar import profile |
| D-06 | Official skill-matrix scale and "skilled = ≥ 3" threshold; should risk be "High" when headcount equals requirement? | Plant heads / L&D | Seeded as found in the workbooks; both are configurable |
| D-07 | Keep the sheet-specific banding variants (Moulding, NPD, Paint) or standardise? | L&D | Per-level counts shown instead |
| D-08 | Meaning of Dev. Plan markers Y / US; blank = not applicable or not assessed? | L&D | Training-need nominations not implemented |
| D-09 | Who may record assessments (assessor role per plant)? Manager self-service? | HR | Only `competency.assess` holders (HR Admin, Super Admin) |
| D-10 | Certificate template, wording ("Appreciation" vs completion), number format, signatories, QR verification | HR / Management | Certificate number recorded manually only |
| D-11 | Nomination approval chain and capacity/waitlist rules | HR | Nominate / confirm by training administrators only |
| D-12 | Reminder intervals (default 7 and 1 days before a session) | HR | `LMS_TRAINING_REMINDER_OFFSETS_DAYS`. *(2026-11-23: also decide how often the scheduled job runs — 15 minutes proposed — and who owns the Windows scheduled task on the server.)* |
| D-13 | Microsoft 365 integration go-ahead | IT | In-app only |
| D-14 | Matrices contain CTC and payroll-contractor columns — confirm these must never be imported | HR | The import exclusion list already blocks salary/CTC headers |

## 4. Microsoft 365 (Outlook / Teams) — future dependency

Not built. Requirements for IT before it can be:

1. Microsoft Entra ID **app registration** for the LMS (single tenant), with a client secret
   or certificate stored in the server's secret store — never in the repository.
2. Admin-consented Microsoft Graph **application permissions** (least privilege, to be
   confirmed by IT): `Calendars.ReadWrite` (create/update/cancel training invitations in a
   dedicated training mailbox, ideally restricted with an *Application Access Policy*), and
   for Teams either `TeamsActivity.Send` (activity-feed notifications) or a bot / channel
   webhook approved by IT.
3. A sending mailbox / Teams app identity, and a decision on whether invitations come from a
   shared "Training" mailbox.
4. Integration point: a new channel class beside `IN_APP_CHANNEL` in
   `app/services/notifications.py`; core training logic does not change. Until configured,
   `/api/v1/notifications/channels` reports Outlook and Teams as **not connected**.

## 5. HRMS — future dependency

Not built. The organisation and employee masters already carry `external_ref` columns and
record provenance; an HRMS feed can be added as another import source behind the same
validate → preview → approve → commit pipeline, without changing the core tables.
