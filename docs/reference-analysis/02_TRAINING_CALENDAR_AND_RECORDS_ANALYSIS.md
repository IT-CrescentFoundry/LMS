# 02 – Training Calendar and Training Records Analysis

| Item | Value |
|---|---|
| Source folder | `LMS Data Reference\Training Calendar\` (13 workbooks, FY 2026-27) |
| Related | `03_SKILL_MATRIX_AND_COMPETENCY_ANALYSIS.md` (skill matrices, Dev. Plans, competency library) |
| Method | Read-only. Each workbook was loaded twice with openpyxl (formulas, then cached values) and the raw XML was unzipped and inspected. Nothing was saved back to the source files. |
| Analysis date | 2026-11-23 |
| Confidentiality | The source files hold real employee names, codes, pay (CTC) and contractor names. None of that appears here. Trainer names are reported only as counts. |

Confidence labels: **Confirmed (source)** = seen directly in cells, formulas or XML. **Inferred** = derived from data patterns. **Proposed** = design recommendation. **Pending confirmation** = needs a business owner to answer.

---

## 1. Workbook and worksheet inventory

The 13 workbooks contain **61 worksheets**:

| Sheet type | Count | Notes |
|---|---|---|
| Training calendar (staff, "CF") | 11 | 10 department sheets plus 1 Bagnan consolidated sheet |
| OJT calendar (workers) | 8 | 7 department sheets plus 1 Bagnan consolidated sheet |
| Safety training calendar | 1 | Bagnan, plant-wide |
| Skill matrix | 23 | 1 hidden (`Paint`). See doc 03. |
| Development plan ("Dev. Plan") | 17 | Training-needs nomination grid. See doc 03. |
| Helper sheet (hidden) | 1 | Maintenance `Sheet1`: 69 skills, each with a High/Medium/Low risk value |

| # | Workbook | Sheets (state, used range) | Template variant |
|---|---|---|---|
| 1 | Bagnan_Safety Training Calendar_2026-27 | Safety Training Calendar (A1:N45) | Calendar only |
| 2 | Bagnan_Training Calendar_2026-27 | Training Calendar - CF (A1:N433); OJT Calendar - Workers (A1:N291) | Plant consolidation |
| 3 | Training Calendar_FARO | Skill Matrix - Faro; Dev. Plan; Training Calendar | A (single population) |
| 4 | Training Calendar_Forklift | Forklift (matrix); Dev. Plan; OJT Calendar | A (workers only) |
| 5 | Training Calendar_Maintenance | Skill Matrix-Maintenance; **Sheet1 (hidden)**; Dev. Plan; Training Calendar | A |
| 6 | Training Calendar_Process | Skill Matrix - Process; Training Calendar; Dev. Plan | A |
| 7 | Training Calendar_Quality | Skill Matrix - Quality; Dev. Plan; Training Calendar | A |
| 8 | Training Calendar_Fettling | Fettling-ALL; Fettling - CF; Fettling - Workers; Dev. Plan - CF; Dev. Plan - Workers; Training Calendar - CF; OJT Calendar - Workers | B (CF / Workers split) |
| 9 | Training Calendar_Machine Shop | Mach. Shop; Mach. Shop - CF; Mach. Shop - Workers; Dev. Plan - CF/Workers; Training Calendar - CF; OJT Calendar - Workers | B |
| 10 | Training Calendar_Melting | Melting; Melting - CF; Melting - Workers; Dev. Plan - CF/Workers; Training Calendar - CF; OJT Calendar - "Worekrs" (sic) | B |
| 11 | Training Calendar_Moulding | Moulding; Moulding-CF; Moulding-Workers; Dev. Plan - CF/Workers; Training Calendar - CF; OJT Calendar - Workers | B |
| 12 | Training Calendar_NPD | NPD; NPD - CF; NPD - Workers; Dev. Plan - CF/Workers; Training Calendar - CF; OJT Calendar - Workers | B |
| 13 | Training Calendar_Paint Shop | **Paint (hidden)**; Paint - CF; Paint - Workers; Dev. Plan - CF/Workers; Training Calendar - CF; OJT Calendar - Workers | B |

**Template variants (Confirmed):**
- **Variant A** (FARO, Forklift, Maintenance, Process, Quality): one population, so one matrix, one Dev. Plan and one calendar.
- **Variant B** (Fettling, Machine Shop, Melting, Moulding, NPD, Paint Shop): split into staff (`CF`) and workers.
  - There is an "ALL" consolidated matrix (Paint's is hidden), a `- CF` matrix and a `- Workers` matrix.
  - There are two Dev. Plans.
  - The staff calendar is `Training Calendar - CF` and the worker calendar is `OJT Calendar - Workers`.
- **Inferred:** "CF" means Crescent Foundry company-payroll staff and executives, and "Workers" means operators, including contract labour. Payroll values on the worker sheets are labour-contractor names.

No workbook has defined names except auto-filter and print-title names. Only Machine Shop has external links (see §7).

## 2. Calendar structure

### 2.1 Layout (Confirmed, identical in all 20 calendar sheets)

- **One row = one planned session.** Calendars are row-based lists, not month-column grids.
- There are no month columns, no P/A cells and no Gantt-style colouring.
- Row 1 is the header. There are no merged cells. Panes are frozen at varying positions.
- Row fills alternate between `F9EBEA` and `FADBD8`. This is visual banding only and carries no business meaning.

| Col | Header (exact) | Type found | Fill rate (department sheets) | Meaning |
|---|---|---|---|---|
| A | `Sl.` | int, then formula `=A2+1` | 100% | Serial number |
| B | `Training Subjects` (staff and safety) / `OJT Subjects` (worker sheets) | text | 100% | Topic. Usually `<skill name> - Session n`, sometimes with a sub-topic after a dash. |
| C | `Trainer` | text | 100% | Internal trainer names, initials or pairs `X / Y`. Between 1 and 14 distinct values per sheet. |
| D | `Department` | text | 100% | Fettling, Machine Shop, Melting, NPD, Paint Shop, Production (Moulding), Process Control, Quality, Maintenance, Faro, Forklift |
| E | `Training Location` | text | 0–100% | E.g. "Fettling Office", "M/c Shop Floor", "Packing Area". Blank on every Quality row. |
| F | `Month` | **text** | about 94% | `Apr' 26` … `Mar' 27`. Variants found: `July' 26` and `May, 26`. |
| G | `Training Plan Date` | date, or formula `=G(prev)+7` | about 94% | Planned date, on a weekly cadence |
| H | `Training Executed Date` | date | **1 of 1,532 rows** | Actual date |
| I | `Training Time` | stored as datetime | 1 row | Actual time. The type is wrong (a date-time serial). |
| J | `Training Duration` | number | 1 row | Unit not stated. Hours is inferred from the manhours formula. |
| K | `Total Attendees Planned` | int (typed) | 100% | Planned headcount |
| L | `Total Attended` | int | 1 row | Actual headcount |
| M | `Planned  Training Manhours` | formula `=J*K` | 100% (evaluates to 0) | Planned manhours |
| N | `Actual Training Manhours` | formula `=J*L` | 100% (evaluates to 0) | Actual manhours |

**Fields that do not exist** (Confirmed by their absence):
- status (planned, completed, cancelled or postponed), internal/external faculty flag, trainer organisation, cost or budget
- target designation or role, named participant list, attendance per person
- evaluation, feedback or effectiveness, assessment result, certificate
- link to a competency code, delivery mode, language, plant (only implied by the file name "Bagnan")

### 2.2 Plan vs actual representation

| Aspect | Planned | Actual | Confidence |
|---|---|---|---|
| Date | G `Training Plan Date` | H `Training Executed Date` | Confirmed |
| Headcount | K `Total Attendees Planned` | L `Total Attended` | Confirmed |
| Effort | M `=J*K` | N `=J*L` | Confirmed |
| Duration and time | none | I, J (actual only; M also reuses J) | Confirmed |
| P/A, ✓/✗, or colour status markers | none | none | Confirmed (no data validation, no fill semantics) |

- **Actuals are effectively unused.** Of 1,532 calendar rows, exactly one row has H/I/J/L filled: one Paint Shop CF row whose executed date is one day after its plan date. *(Re-verified 2026-11-23, §10. The 1,532 includes 722 Bagnan consolidated copies, so there are about 810 distinct sessions.)*
- Every M and N formula therefore evaluates to 0.
- This is true even though plan dates from April to November 2026 are already in the past (analysis date 2026-11-23).
- **Inferred:** completion is recorded elsewhere (paper attendance or the existing LMS), or not at all. **Pending confirmation.**

### 2.3 Volumes (Confirmed)

| Workbook | Staff calendar rows (scheduled) | OJT / worker rows (scheduled) | Planned-attendee pattern (K) |
|---|---|---|---|
| FARO | 33 (31) | – | 3–4 |
| Fettling | 44 (41) | 48 (45) | 5 / 3–41 |
| Forklift | – | 46 (43) | 10–12 |
| Machine Shop | 48 (45) | 48 (45) | 2–3 / 5–32 |
| Maintenance | 51 (51) | – | 15 on every row |
| Melting | 44 (41) | 46 (43) | 1–4 / 4–22 |
| Moulding ("Production") | 42 (39) | 46 (43) | 3–5 / 3–42 |
| NPD | 50 (47) | 35 (32) | 10 / 8–21 |
| Paint Shop | 50 (47) | 42 (39) | 5 / 28–60 |
| Process | 49 (49) | – | 2 |
| Quality | 44 (44) | – | 2–14 |
| Bagnan consolidated | 432 | 290 | copy of the above |
| Bagnan Safety | 44 (0 dated) | – | 2–60 |

- Most department sheets have **2–3 rows with no Month or Plan Date**. These are unscheduled sessions.
- The **Bagnan consolidated sheets contain only the dated rows**, typed as values with no links.
- Department row counts in the consolidation match the dated rows exactly, except Process (47 vs 49) and Maintenance (50 vs 51). **Inferred:** the consolidation is a manual copy that has drifted.
- **Safety calendar:**
  - 44 rows covering three topics only (HIRA ×16, Fire Safety ×15, Usage of PPEs ×13) across 10 departments, with one trainer.
  - Month, plan date and every actual field are blank.
  - Planned attendees match department headcount sizes.
  - **Inferred:** a needs list, not yet scheduled.
- **Session cadence (Inferred):** each department trains on a fixed weekday each week. The sessions of a topic ("Session 1/2/3") are spread across months.
- **Duplicate detection (Confirmed):** Moulding calendars apply a `duplicateValues` conditional format (yellow) on the plan-date column, which flags two sessions booked on the same date.

### 2.4 How calendar rows are generated (Inferred, strong evidence)

1. **Skill matrix.** Each employee is scored 1–5 per skill. Each skill gets a Risk Level (doc 03).
2. **Dev. Plan.** Each skill and session is a row and each employee is a column. The marker is `Y` (score 1–2: training) or `US` (score 3–4: upskilling); blank means not needed or not applicable.
3. **Calendar.** One row per Dev. Plan row and session. **K equals the Dev. Plan `Total Planned Participants` + `Upskilling Participants`.**
   - Confirmed for every exact-name match: FARO 33/33, Maintenance 51/51, Process 32/32, Fettling 15/15, Machine 46/46, Melting 19/19, Moulding 29/29, NPD 10/10, Paint 20/20, Forklift 11/12.
   - Quality does not match (9 rows differ by 1–4).
   - K is typed, not formula-linked.
4. The Bagnan consolidated calendar is a values-only union of department calendars, filtered to dated rows.

## 3. Formula inventory (calendar sheets)

Every calendar formula fits one of 4 patterns. Normalised forms below; all cached values are present and none are errors.

| Formula (row r) | Column | Sheets | Meaning |
|---|---|---|---|
| `=A{r-1}+1` | A | all 20 | Running serial |
| `=J{r}*K{r}` | M | all 20 | Planned manhours = duration × planned attendees |
| `=J{r}*L{r}` | N | all 20 | Actual manhours = duration × attended |
| `=G{r-1}+7` | G | Bagnan OJT (42 cells), Melting OJT (42 cells) | Next session one week later |

- There are no cross-sheet links between a calendar and its matrix or Dev. Plan.
- M and N are **stale by design**: they show 0 because J and L are empty.

## 4. Data validation and conditional formatting

| Workbook / sheet | Data validation | Conditional formatting | Business meaning |
|---|---|---|---|
| All 20 calendar sheets | **None** | None (except below) | Free text everywhere. Month, department and trainer drift as a result. |
| Moulding: Training Calendar - CF, OJT Calendar - Workers | – | `duplicateValues` on G, yellow | Clash warning for two sessions on the same date |
| Melting: OJT Calendar - Worekrs | – | B2:B20 `=1..5`, coloured red, amber, yellow, green | Leftover copied from the matrix. Never triggers on text subjects. |
| Dev. Plan sheets (17) | None | `US`: yellow; `Y`: white; blank: grey | Upskilling vs training nomination (doc 03) |

## 5. Data-quality issues

| # | Issue | Evidence | Impact | Confidence |
|---|---|---|---|---|
| 1 | Actuals not maintained | 1 of 1,532 rows has an executed date or attendance | No completion history to migrate from these files | Confirmed |
| 2 | Month stored as text with variants | `July' 26`, `May, 26` alongside `Mon' YY` | Derive the month from the plan date instead | Confirmed |
| 3 | Training Time typed as a datetime | One value stored as a 2026-11-10 date-time serial | Needs a separate time field | Confirmed |
| 4 | Duration has no unit | Header "Training Duration" | Hours assumed (Inferred) | Pending confirmation |
| 5 | Department names inconsistent | "Production" for Moulding; "Faro"; "Process Control"; locations misspelt ("Mainteannce Office") | Map to org-unit master data | Confirmed |
| 6 | Topic text inconsistent | Typos ("Knolwedge", "Partling", "Machinine"); `- - Polyworks`; trailing spaces | Normalise topics against the skill catalogue | Confirmed |
| 7 | Consolidated calendar is a manual copy | Process −2 rows, Maintenance −1 row vs department sheets | Single source needed | Confirmed |
| 8 | Unscheduled rows | 2–3 rows per department sheet with no month or date. The safety calendar is fully undated. | Need a "Planned – unscheduled" state | Confirmed |
| 9 | Trainer is free text with pairs and initials | e.g. `<initials> / <initials>` | Needs a trainer master and many-to-many co-trainers | Confirmed |
| 10 | Planned attendees typed, not linked | Equals Dev. Plan totals except Quality | Should be derived from nominations | Confirmed / Inferred |
| 11 | No participant identity | Only counts | Per-employee records are impossible from calendars alone | Confirmed |
| 12 | Sheet-name typo | `OJT Calendar - Worekrs` | Import mapping must allow aliases | Confirmed |
| 13 | Staff vs worker distinction exists only in sheet names | `Training Calendar - CF` vs `OJT Calendar - Workers` | Needs a programme/audience type field | Confirmed |
| 14 | Sensitive data next to training data | The matrix sheets in the same workbooks contain CTC and payroll-contractor columns | Do not import pay data. Restrict file handling. | Confirmed |

## 6. Mapping table

| Workbook | Worksheet | Business purpose | Information maintained | Formula / calculation | Proposed portal module | Outstanding clarification |
|---|---|---|---|---|---|---|
| Bagnan_Safety Training Calendar | Safety Training Calendar | Plant-wide EHS training need (Fire Safety, HIRA, PPE) | Topic, trainer, department, location, planned headcount | `=A+1`, `=J*K`, `=J*L` | Training Calendar → Mandatory/EHS programmes | Who schedules these? Is EHS training a recurring compliance item with a validity period? |
| Bagnan_Training Calendar | Training Calendar - CF | Plant-level view of all staff sessions | Union of department staff calendars (dated rows only) | Same as above | Calendar → plant/period view (derived, not stored) | Is this the master or a report? Who keeps it in sync? |
| Bagnan_Training Calendar | OJT Calendar - Workers | Plant-level view of worker OJT | Union of department OJT calendars | Same, plus `=G+7` | Calendar → OJT view (derived) | Same as above |
| Dept workbooks (10) | Training Calendar / Training Calendar - CF | Department staff session plan | Session per skill, trainer, location, month, plan date, planned headcount; empty actual columns | `=A+1`, `=J*K`, `=J*L` | Training Calendar → Session scheduling; Attendance | Who records actuals, when, and where today? Duration unit? |
| Dept workbooks (7) | OJT Calendar / OJT Calendar - Workers | Shop-floor on-the-job training plan | As above, at the work location (floor or area) | As above; `=G+7` (Melting) | Calendar → OJT sessions (type = OJT) | Is OJT signed off by a supervisor? Is there a practical assessment after OJT? |
| Dept workbooks (11) | Dev. Plan(s) | Training-need nomination (TNI) per skill and session | `Y` / `US` per employee, risk level, sessions, totals | `COUNTIF(...,"Y")`, `COUNTIF(...,"US")` | Training Needs (TNI) → Nominations → Session participants | Confirm Y = training, US = upskilling; is "US" a different course level? |
| Dept workbooks (11) | Skill matrix sheets | Source of needs (doc 03) | Scores 1–5 | Bands, risk | Competency Assessment | See doc 03 |
| Moulding | Calendars (both) | Clash check | – | CF `duplicateValues` on G | Scheduling rule: warn on trainer, venue or date clash | Is one session per department per day the rule? |

## 7. External links

- **Machine Shop** (3 matrix sheets, column F "Company / Payroll") uses `=VLOOKUP(B{r}, '[1]MPP BAGNAN LIVE'!$D$67:$I$88, 6, 0)`.
- `[1]` points to an external manpower-plan workbook, `MPP SHEET BAGNAN UNIT 24-02-2026.xlsx`, on a personal OneDrive.
- The cached values are present, but the link breaks for anyone else. **Confirmed.**
- **Proposed:** source payroll and contractor data from the LMS employee master (already built) instead of copying it.

## 8. Implications for the portal (Proposed)

- **Training Session** (one row per calendar row):
  - programme type (Classroom-CF, OJT-Worker, EHS), org unit (department), plant
  - topic linked to a skill / competency item, session number of N, trainers (many), venue
  - planned date/time, planned duration (hours), status (Unscheduled, Scheduled, Completed, Cancelled, Postponed)
  - actual date/time and duration
- **Nomination / Participant:** one employee per session, with need type (`TRAINING` from Y, `UPSKILLING` from US) and source (skill gap, mandatory, manual). Planned headcount is the count of nominations; it is not typed.
- **Attendance:** present/absent per participant. Actual manhours = actual duration × present count, or the sum of individual hours.
- **Derived views** replace the Bagnan consolidated sheets.
- **Import:** department calendar rows can be imported as Scheduled or Unscheduled sessions with no participants. Participants come from Dev. Plan imports (doc 03).

## 9. Outstanding questions

1. Where are training completions and attendance recorded today? Is there paper attendance or the existing LMS?
2. Unit of "Training Duration" (hours or minutes). Is a standard session length assumed?
3. Are all trainers internal? Is external faculty ever used, and with what details (agency, cost)?
4. Does "CF" mean company-payroll staff? Are contract workers always on the OJT calendars?
5. Should EHS topics (Fire Safety, HIRA, PPE) recur at a fixed frequency with expiry?
6. Should the Bagnan consolidated calendar be retired in favour of a portal report?
7. Why do the Quality calendar's planned headcounts differ from its Dev. Plan totals?
8. Approval workflow: who approves the annual calendar, and who may reschedule?

---

## 10. Re-verified 2026-11-23

**Method.** The 13 workbooks were re-opened read-only with openpyxl, with `data_only=True` for
values and `data_only=False` for formulas and validations. A calendar sheet is one whose row 1
contains `Trainer`. A data row is a row whose column B (subject) is non-blank.

### 10.1 Results

| Claim | Re-verified result | Status |
|---|---|---|
| 61 worksheets, 2 hidden | 61 sheets: 59 visible, 2 hidden (`Paint`, Maintenance `Sheet1`) | Confirmed |
| 20 calendar sheets, identical 14-column layout | 20 sheets, all A–N. The headers are identical except B: `Training Subjects` on 12 sheets, `OJT Subjects` on 8. | Confirmed |
| ≈1,532 calendar data rows | **1,532** exactly | Confirmed (see note below) |
| 1 row with an actual (executed) date | **1**: `Training Calendar_Paint Shop` → `Training Calendar - CF` row 2. Plan date 2026-05-06, executed 2026-05-07. The same row is the only one with Training Time, Duration and Total Attended. The Bagnan consolidated copy of this session does **not** carry the actual values. | Confirmed |
| No individual attendance | **Confirmed.** No sheet has a participant or attendance list, P/A marks, or per-person completion. Employee-level data exists only as skill scores (matrix sheets) and Y/US nominations (Dev. Plan sheets, one column per employee code). These are training needs, not attendance. | Confirmed |
| No data validation on calendars | 0 validations on all 20 calendar sheets | Confirmed |

**Correction: what the 1,532 rows contain.** The total includes the **722** rows of the two
Bagnan consolidated sheets (432 CF + 290 OJT). Those rows are values-only copies of the dated
department rows. Distinct planned sessions are therefore about **810**:
- 766 department-sheet rows
- 44 safety rows

Use 810, not 1,532, when sizing a calendar import. The consolidated sheets should not be imported
(§2.3).

**Rows with a plan date:**
- Every department sheet except Maintenance, Process and Quality has 2–3 rows with no plan date.
- The safety calendar has none of its 44 rows dated.
- Both Bagnan consolidated sheets have all rows dated.

### 10.2 Import column specification (proposed calendar import profile)

| Source col | Header (exact) | Target field | Type / rule | Required |
|---|---|---|---|---|
| A | `Sl.` | — (ignored; formula `=A{r-1}+1`) | — | No |
| B | `Training Subjects` / `OJT Subjects` | programme / session title; session number parsed from `Session n` | text, trimmed; fuzzy-match to the skill/competency catalogue and route to review | Yes |
| — (sheet name) | `Training Calendar…` / `OJT Calendar…` / `Safety Training Calendar` | programme type (Classroom-CF / OJT-Worker / EHS) | derived from the sheet name, with alias `Worekrs` | Yes |
| — (file name) | `Bagnan_…` or the department workbook | plant | Bagnan for every current file; to be confirmed | Yes |
| C | `Trainer` | trainer(s) | split on `/`; resolve against a trainer master; unresolved → review | Yes |
| D | `Department` | org unit | alias map (Production → Moulding?, Process Control → PROCESS, Faro → FARO, NPD → ?) — HR confirmation required | Yes |
| E | `Training Location` | venue | free text | No |
| F | `Month` | planned month | text `Mon' YY`, with variants `July' 26` and `May, 26`. Use only when G is blank; otherwise derive the month from G. | No |
| G | `Training Plan Date` | planned date | date, or formula `=G{r-1}+7` (use the cached value); blank → status Unscheduled | No |
| H | `Training Executed Date` | actual date | date; must not be in the future | No |
| I | `Training Time` | actual start time | stored as datetime; take the time part only | No |
| J | `Training Duration` | duration | number, unit unconfirmed (hours assumed; D-05) | No |
| K | `Total Attendees Planned` | planned headcount | integer ≥ 0 | Yes |
| L | `Total Attended` | reported attendance count (headcount only) | integer ≥ 0, ≤ K is not enforced | No |
| M | `Planned  Training Manhours` (two spaces) | — (derived = J×K; do not import) | — | No |
| N | `Actual Training Manhours` | — (derived = J×L; do not import) | — | No |

Exclusions: both `Bagnan_Training Calendar` sheets are duplicates; there are no participant
columns to import.
