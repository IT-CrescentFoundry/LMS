# First Release — Gap and Dependency Register

| | |
|---|---|
| **Date** | 24 November 2026 |
| **Status source** | [Master completion matrix](FIRST_RELEASE_MASTER_COMPLETION_MATRIX.md) (authoritative). This register adds the **business impact**, **dependencies** and **next action** for each incomplete requirement. It also holds the **decision register** and the **data-readiness assessment**. Acceptance criteria stay in the matrix. |
| **Related** | [Execution plan](FIRST_RELEASE_EXECUTION_PLAN_TO_20261215.md) (task IDs E-x.y) · [Acceptance checklist](FIRST_RELEASE_ACCEPTANCE_CHECKLIST.md) · [Open decisions D-01…D-14](../reference-analysis/05_SOURCE_TO_SYSTEM_MAPPING_AND_OPEN_DECISIONS.md) |

## 1. Gaps in first-release mandatory requirements

| Gap | Matrix IDs | What is missing | Business impact | Dependencies | Next action | Task |
|---|---|---|---|---|---|---|
| G-01 Function list | ORG-04 | HR confirmation of five vs six top-level functions | Every department placement and every function-level report depends on it | D-15 | Owner raises D-15 with HR; record the signed list | E-2.1 |
| G-02 Organisation hierarchy | ORG-05, ORG-09, ORG-10, ORG-11 | Approved plant placement, department→function map; real load through the existing import | Without it there is no plant- or department-wise view, team scope or report | D-01, D-02, D-03, D-15 | HR decision session; HR fills the hierarchy sheet of template 01; dry run, then approval | E-2.1, E-2.7 |
| G-03 Designation reference data | ORG-07 (+ ORG-08 conditional) | Canonical designation / grade / level list; load route | The employee import cannot resolve designations, so the employee master cannot be loaded | D-01, Q-45, Q-53, SC-03 | HR validates S1's 266 codes (16 near-duplicate pairs, 17 band conflicts); approve SC-03 or plan manual keying | E-2.4, E-2.8 |
| G-04 Employee master | EMP-08 | Corrected extract with manager **codes**, employment status and text-format codes | No learners, no team scope, no notifications, no UAT on real data | D-01, D-16, G-02, G-03 | HR corrects S2 (17 unmatched managers, numeric codes, missing status); dry run with the data-quality review | E-2.9 |
| G-05 Account provisioning | ADM-05, ADM-06 | Account admin UI; bulk provisioning; credential handover | Nobody outside HR can sign in; learner, manager and notification features cannot be used | D-16 | Build the UI over the existing API; bulk-provision from linked employees once D-16 is decided | E-2.2, E-2.3 |
| G-06 Role boundaries | ADM-07, TRS-04, MGR-07 | Who approves library entries, who assesses, whether trainer or coordinator roles exist | Assessments and approvals are restricted to HR Admin; plant operations bottleneck | D-04, D-09 | HR/L&D decide; implement grants (a migration if new roles; needs approval) | E-3.3, E-3.8 |
| G-07 Competency governance enforcement | CMP-03 | Draft competencies are usable in matrices and assessments; edit-after-approval rule undecided | Unapproved content can drive official gaps | D-04 | Decide the rule; enforce it with tests | E-3.3 |
| G-08 Competency library data | CMP-06 | Approved library (68 of 168 TCs are blank drafts; whole file "Draft v1") | The library is empty in the portal; no competency-based matrices | D-04, CMP-05 | L&D approval; load through E-3.1 or manually | E-3.2 |
| G-09 Scale and risk thresholds | CMP-01, SKM-05 | Official confirmation of the 1–5 matrix and 1–4 library scales, "skilled ≥ 3", "High when equal" | Risk results may be disputed in UAT | D-06 | Plant heads / L&D confirm (values are configurable; no code change) | E-2.1 |
| G-10 Real-data verification of 0011 modules | TRN-01, 04–08, 10–13 · LRN-01–04 · MGR-01, 02, 05 · CMP-02, 04, 07, 08 · SKM-01–04 · NTF-01–04 · RPT-01, 10 · ADM-03 | Verified only on empty data and synthetic fixtures; no E2E; no UAT | Undetected workflow defects at rollout | G-04, G-05, OPS-04 | E2E suite, expanded tests, UAT scripts per journey | E-2.10, E-2.11, E-3.10, E-5.6, E-5.7 |
| G-11 Reminder scheduling | NTF-05 | Scheduled task on the server; owner; interval | Reminders appear only when a user opens the notification centre | D-12, OPS-01 | Configure Windows Task Scheduler on the production host; name the owner | E-5.4 |
| G-12 Translations | X-01 | Native-speaker review of bn/hi/gu (1,934 keys each) | Learner-facing text may be wrong or confusing | D-19 | Nominate reviewers; review learner-facing screens first | E-5.9 |
| G-13 Device verification | X-04 | First-release screens not tested at phone or tablet widths | Shop-floor mobile use may fail | OPS-04 | E2E at 360 / 768 / 1280 px | E-2.10 |
| G-14 Navigation placeholders | ADM-10, LRN-03 | Six "Coming soon" modules visible to everyone | UAT users expect features that are out of scope | Owner | Owner decides: hide for release, or keep labelled | E-2.6, E-3.5 |
| G-15 Production environment | OPS-01, OPS-02, OPS-03, OPS-12 | Host, HTTPS, production database, DBA trigger privilege, backups, security review | No deployment possible | D-17 | IT and DBA request now (lead time); deployment runbook | E-5.1…E-5.5 |
| G-16 Test depth and E2E | OPS-04, OPS-05 | Browser E2E; workflow-level tests | Regressions undetected during intensive change | DEP-01 | Approve the dev dependency; build the suite | E-2.10, E-2.11, E-3.10 |
| G-17 Operations and guides | OPS-08, OPS-09 | Runbooks, named owners, HR and learner guides | No operational ownership after go-live | D-12, D-17, X-01 | Draft from existing fragments; owners rehearse | E-5.8 |
| G-18 UAT | OPS-10 | UAT plan, participants, sign-off authority | The release cannot be accepted | D-18, G-04 | Name UAT participants per domain by 1 Dec | E-5.7 |

## 2. Gaps in first-release conditional requirements

| Gap | Matrix IDs | What is missing | Business impact | Dependencies | Next action | Task |
|---|---|---|---|---|---|---|
| C-01 Reference-data import | ORG-08 | Designation, grade, level and location import profile | Without it HR keys 266 designations by hand (about 1–2 days of HR effort, error-prone) | SC-03 | Owner decides SC-03 | E-2.4 |
| C-02 Calendar import (planned only) | TRN-14 | Import profile for FY 2026-27 planned sessions | Without it the calendar and register stay nearly empty at rollout | D-05, SC-05 | L&D answers D-05 (duration unit, month formats, trainer initials, consolidated copy) | E-2.5 |
| C-03 Competency-library import | CMP-05 | Profile for the TC Library layout | 168 TCs × (4 descriptors + 4 bands) keyed by hand | SC-05 (build), D-04 (load) | Approve SC-05; build in parallel with the D-04 decision | E-3.1 |
| C-04 Skill-matrix import | SKM-07 | Wide-matrix profile with CTC exclusion | Bagnan matrices keyed by hand | D-06, D-14, SC-05 | Decide D-06 and D-14 | E-3.4 |
| C-05 Nomination approval | TRN-09, NTF-06 | Approval states, approver, notifications | Nominations are confirmed directly by HR; no manager control | D-11, SC-02 | HR defines the approval chain | E-3.6 |
| C-06 Trainer access | TRS-01, TRS-02 | Trainer scope; attendance capture by trainer | Attendance must be entered by HR Admin | SC-02, D-09 | Decide whether trainers record attendance | E-3.7 |
| C-07 Mandatory training and certification validity | CPL-01…05, NTF-07, RPT-07 | Requirement rules, compliance status, validity, expiry, evidence | No compliance or expiry visibility (milestone 4 expectation) | SC-01, Q-11, Q-34, **compliance source data (none exists)** | HR supplies the mandatory-training and validity matrix by 3 Dec, or the item is deferred | E-4.4, E-4.5, E-4.6 |
| C-08 Reports and export | RPT-02, 03, 05, 08 | Aggregated reports; audited Excel export | Management still relies on Excel | SC-01, G-02 | Approve SC-01 (reduced M4) | E-4.1, E-4.2 |
| C-09 Management dashboard | RPT-09 | Approved KPI definitions | No KPI dashboard | SC-01, Q-29 | HR/management approve KPIs (template 07 has 18 drafts) by 3 Dec | E-4.3 |

P2 items (TRN-02, TRN-03, EMP-10, LRN-05, MGR-03, MGR-07, ORG-13, ORG-15, SKM-06, SKM-08, SKM-09, NTF-09, RPT-06, X-02, X-03, X-05, OPS-06, OPS-07, OPS-11) are listed in the matrix with their missing work and dependencies. Their business impact is limited to convenience or post-rollout capability. Each needs the owner's explicit acceptance to remain after rollout (checklist AC-SCOPE-02).

## 3. Decision register

**Reading the columns:**
* **Can dev continue?** Can development work proceed while the decision is open?
* **Blocks release?** Does it block release acceptance?

D-01…D-14 are unchanged from [doc 05 §3](../reference-analysis/05_SOURCE_TO_SYSTEM_MAPPING_AND_OPEN_DECISIONS.md). D-15…D-19, SC-01…SC-06 and DEP-01 are **new from this audit**.

| ID | Decision required | Why it matters | Available evidence | Responsible stakeholder | Can dev continue? | Blocks release? | Needed by |
|---|---|---|---|---|---|---|---|
| D-01 | Which organisation source is authoritative: S1 template or S2 HR extract (`Organization Structure.xlsx`)? | Departments, designations and the employee master differ between them | S1: 43 departments, 266 designations, 7 employee rows. S2: 441 employees, 7 locations, 44 raw / 31 normalised departments | HR | Yes | **Yes** (EMP-08, ORG-05) | 27 Nov |
| D-02 | Placement of plants relative to functions (Plant→Function→Dept, Function→Plant→Dept, or plants as locations only) | Determines the tree, team scope and plant-wise reports | No source states it (Q-48) | HR / Management | Yes (import supports any choice) | **Yes** | 27 Nov |
| D-03 | Department → function mapping; 12 departments without a plant | Departments cannot be placed; nothing will be inferred | Absent from every source (G-ORG-04) | HR | Yes | **Yes** | 27 Nov |
| D-04 | Approve loading the competency library; band→grade mapping; who approves entries; does editing an approved entry return it to draft? | Library data, governance enforcement (CMP-03), personal gaps (LRN-05) | 168 TCs, 68 blank drafts; band text conflicts on 17 rows | L&D / HR | Yes (CMP-05 can be built) | **Yes** for CMP-06 and TRS-04 | 1 Dec |
| D-05 | Calendar import rules: duration unit, month formats, trainer initials, duplicate Bagnan consolidated copy | Calendar import (TRN-14) | 1,532 rows, 722 consolidated copies, 1 executed row | L&D | Partly (the profile skeleton can be built) | Only if SC-05 is approved | 27 Nov |
| D-06 | Official skill-matrix scale; skilled ≥ 3; "High" risk when equal | Risk results; matrix import | Workbook formulas (C) | Plant heads / L&D | Yes (configurable) | **Yes** (UAT acceptance of SKM-05) | 1 Dec |
| D-07 | Keep sheet-specific banding variants or standardise | Moulding/NPD/Paint reports | Sheet formulas | L&D | Yes | No (P2) | Post-rollout |
| D-08 | Meaning of Dev-Plan markers Y / US; blank = N/A or not assessed | Training-need nominations (deferred) | About 98 % correlation inferred, not confirmed | L&D | Yes | No (deferred) | Post-rollout |
| D-09 | Who may record assessments (assessor per plant)? Manager self-service? Trainer attendance? | Role boundaries (ADM-07), TRS-01/02, MGR-07 | Only HR Admin / Super Admin today | HR | Yes | **Yes** (ADM-07) | 1 Dec |
| D-10 | Certificate template, wording, number format, signatories, QR | Certificate generation (deferred); certificate number format | 2 JPG appreciation designs only | HR / Management | Yes | No (CPL-06 deferred); number format needed if CPL-03 proceeds | 3 Dec if SC-01 |
| D-11 | Nomination approval chain; capacity and waitlist rules | TRN-09 | Q-18 open | HR | Yes | Only if SC-02 is approved | 1 Dec |
| D-12 | Reminder offsets (default 7 and 1 days); job interval (15 min proposed); owner of the scheduled task | NTF-04, NTF-05 | Config `LMS_TRAINING_REMINDER_OFFSETS_DAYS` | HR + IT | Yes | **Yes** (NTF-05 owner) | 5 Dec |
| D-13 | Microsoft 365 integration go-ahead | Outlook / Teams (deferred) | IT prerequisites in doc 05 §4 | IT | Yes | No | Post-rollout |
| D-14 | Confirm CTC and payroll-contractor matrix columns must never be imported | Matrix import privacy | CTC on at least 22 of 23 matrix sheets | HR | Yes | Only if SKM-07 proceeds | 1 Dec |
| **D-15** | **Top-level functions: five (seed: "HR, Admin & IT" combined) or six (brief: "HR" and "Admin & IT" separate)?** | Organisation tree, function-level reports, TC Library function mapping | Seed `0005`, TC Library and template 01 have five; the 24 Nov brief lists six | HR / Management | Yes (names and units are editable in the UI; no migration) | **Yes** | 27 Nov |
| **D-16** | **Rollout audience and accounts:**<ul><li>who gets accounts in the first release (all ~441 employees, staff only, or a pilot plant)?</li><li>login ID (employee code?);</li><li>initial-password handover;</li><li>which managers get Supervisor/HOD roles?</li></ul>(Q-07, Q-44, Q-50) | ADM-06, MGR-01, notifications, UAT scope | No accounts exist except admins; S2 has no e-mail column | HR + IT | Yes (UI build) | **Yes** | 27 Nov |
| **D-17** | **Production hosting:** server, HTTPS certificate, DNS name, DBA for database creation and audit-trigger privilege, backup storage | OPS-01…03 | No deployment artefacts; the restore test needed a DBA | IT / DBA | Yes | **Yes** | Server by 5 Dec |
| **D-18** | **UAT participants and sign-off authority** per domain (HR, L&D, plant manager, sample learners) | OPS-10 | — | Owner / HR Head | Yes | **Yes** | 1 Dec |
| **D-19** | **Native-speaker reviewers** for bn/hi/gu; must review finish before learner rollout? (Q-58) | X-01 | All three languages are machine drafts | HR | Yes | **Yes** for learner-facing rollout | 1 Dec (names) |
| **SC-01** | Approve the reduced Milestone 4 (reports + export; compliance/certification register only if source data arrives by 3 Dec) | Approved scope §3 excludes the compliance matrix and certification register | [Matrix §2](FIRST_RELEASE_MASTER_COMPLETION_MATRIX.md) | Owner | Yes | Defines release content | 27 Nov |
| **SC-02** | Include nomination approval and trainer access in M3? | Scope has no trainer role or approval | Matrix §2 | Owner + HR | Yes | Defines release content | 27 Nov |
| **SC-03** | Reference-data import profile or manual keying | Critical path to the employee load | Matrix §2 | Owner | Yes | Indirectly (EMP-08) | 26 Nov |
| **SC-04** | Accept global (not plant-scoped) HR Admin access for the first release | `CLAUDE.md` §5 vs scope deferral of C4 | Matrix §2 | Owner | Yes | **Yes** (security acceptance) | 1 Dec |
| **SC-05** | Bring forward the calendar, library and matrix imports | Data onboarding feasibility | Matrix §2, §5 below | Owner | Yes | Indirectly (UAT realism) | 26 Nov |
| **SC-06** | Approve the recommended baseline and confirm development capacity | Effort vs available days | [Plan §2](FIRST_RELEASE_EXECUTION_PLAN_TO_20261215.md) | Owner | — | Yes | 26 Nov |
| **DEP-01** | Approve adding a browser-automation dev dependency (e.g. Playwright) to `LMS_Frontend` | OPS-04; `CLAUDE.md` restricts dependency changes without approval | No E2E in the repository | Owner | Yes | **Yes** (AC-TEST-02) | 26 Nov |

## 4. Critical dependencies (critical path)

```text
D-15 + D-01 + D-02 + D-03 ──► ORG-05 org hierarchy load ─┐
D-01 + Q-53 (+ SC-03) ──────► ORG-07 designations load ──┼─► EMP-08 employee master load ─► ADM-06 accounts (D-16)
                                                         │        │                            │
                                                         │        ▼                            ▼
                                                         │   reporting lines ─► team scope (MGR-01, TRN-12, ADM-03)
                                                         │                                     │
D-05 (+ SC-05) ─► TRN-14 calendar import ────────────────┤                                     ▼
D-04 (+ SC-05) ─► CMP-06 library load ───────────────────┴──────────────────────► UAT on real data (OPS-10, D-18) ─► sign-off 15 Dec
D-17 ─► OPS-01/02/03 production host + DB + backups ─► deployment rehearsal ─────────────────────────────────┘
```

* **Latest safe dates.** If D-01, D-02, D-03, D-15 and D-16 are not decided by **27 Nov** and the corrected employee extract is not received by **28 Nov**, there will be no real employee data before 1 Dec. UAT (11–14 Dec) would then have to use synthetic data, which cannot count as business acceptance.
* **Production host.** If the production host (D-17) is not available by **5 Dec**, there is no time to rehearse a deployment before 15 Dec.

## 5. Data-readiness assessment

The assessment was read-only (workbooks opened read-only). No data was imported and no source file was modified. All counts are aggregates; no personal data is shown.

| Data area | Source | Verdict | Findings | Needs |
|---|---|---|---|---|
| Organisation structure | S1 `Organization Hierarchy Template Filled.xlsx`; S2 `Organization Structure.xlsx` (authorised) | **Needs HR validation**; department→function map **not available** | <ul><li>S1: 5 plants, 43 departments, 84 plant–department pairs; 12 departments with no plant or employees.</li><li>S2: 7 locations, adding Mumbai and Visakhapatnam with 1 employee each.</li><li>No function or sub-function column in either file.</li><li>Unit heads and effective dates are blank.</li><li>The names OPERATION and PURCHASE are used for both functions and departments.</li><li>Three departments (Bagnan Melting, Forklift, NPD) appear only in the training workbooks.</li></ul> | D-01, D-02, D-03, D-15 |
| Employee master | S2 (441 rows); S1 §F (7 rows, 2 marked "Fictional") | **Needs HR validation** | <ul><li>S2 has 0 blank or duplicate codes.</li><li>Reporting manager is stored **by name**: 81 managers, 17 of them (72 rows) unmatched.</li><li>264 manager cells have trailing spaces.</li><li>Codes are stored as numbers.</li><li>No status, e-mail or employment type.</li><li>4 repeated names, 2 non-date joining dates, 3 incomplete levels "L".</li></ul> | Corrected extract with manager codes and status; D-16 |
| Designations and functional roles | S1 (266 codes / 223 titles); S2 (220 titles) | Designations **need HR validation**; functional roles **not available** | <ul><li>16 near-duplicate designation pairs.</li><li>Grade band vs level band disagree on 17 of 441 (S2) and 13 of 266 (S1) rows.</li><li>The functional-role section has 0 rows.</li><li>Only 17 of 64 matrix designation labels match HR titles.</li></ul> | Q-53 canonical list; Q-23 |
| Competency library | `CF Technical Competency Library.xlsx` | **Incomplete, not approved** | <ul><li>168 unique TCs: Operation 106, Accounts & Commercial 26, Sales & BD 15, HR/Admin/IT 14, Purchase 7.</li><li>68 drafts have columns F–O blank.</li><li>The whole library is labelled "Draft v1".</li><li>Read Me/Coverage ranges omit 5 Sand Plant TCs.</li><li>"Moulding " has a trailing space.</li></ul> | D-04 |
| Skill-matrix templates | 23 sheets (Bagnan only, 1 hidden) | **Needs L&D validation** | <ul><li>Scores 1–5; 119 "-" cells; 2 zeros.</li><li>10 typed overrides of formulas.</li><li>One `#REF!`.</li><li>No assessment date or assessor.</li><li>**CTC column on at least 22 sheets (must never be imported).**</li></ul> | D-06, D-07, D-14 |
| Training calendars | 20 calendar sheets in 13 workbooks | **Ready as plans only** | <ul><li>1,532 rows, of which 722 are values-only consolidated copies (about 810 distinct).</li><li>1,447 rows have a plan date; all 44 safety rows are undated.</li><li>**Only 1 row has an executed date or attendance.**</li><li>Duration unit unknown.</li><li>Consolidated copy has drifted from department sheets.</li></ul> | D-05. **Planned dates must not be treated as actual training.** |
| Historical training records | — | **Not available** | No records before FY 2026-27 | Deferred (TRN-15) |
| Attendance / completion | — | **Not available** | Headcounts only. The 17 Dev-Plan sheets hold Y/US needs markers, not attendance | Deferred |
| Certification information | — | **Not available** | No certification register, validity or compliance matrix | Blocks C-07 (SC-01) |
| Course and training content | `Existing LMS Details/` (UpsideLMS documentation only) | **Not available** | No content inventory, materials, SCORM or question bank | Deferred |
| Certificate templates | `Certificate Designs/` (2 JPG, 2000×1414) | **Incomplete** | "Certificate of Appreciation" only; no completion wording, number format, signatories, QR or editable source | D-10 |
| Business-data-readiness templates | `docs/business-data-readiness/` (7 Excel, 2 Word, gap registers) | **Blank** (example rows only) | <ul><li>Only the 5 functions are pre-filled.</li><li>Gap register: 103 gaps, all "Not started" (P0 20, P1 56, P2 22, P3 5); the collection workbook has 109.</li><li>56 business decisions (BD-xx), all open.</li><li>16 expected sources not supplied.</li><li>The Summary sheet's formulas are not recalculated.</li></ul> | Stakeholder submissions |

**Rules applied in this assessment:**
* No department-function relationship has been inferred.
* No calendar row has been treated as completed training.
* No planned date has been treated as an actual date.
* Automated tests continue to use synthetic data only.
