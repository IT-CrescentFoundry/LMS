# 03 – Skill Matrix and Competency Library Analysis

| Item | Value |
|---|---|
| Sources | 11 department workbooks `Training Calendar_<Dept>_2026-27.xlsx` (skill matrix and Dev. Plan sheets); `CF Technical Competency Library.xlsx` (Read Me, TC Library, Coverage) |
| Related | `02_TRAINING_CALENDAR_AND_RECORDS_ANALYSIS.md` |
| Method | Read-only openpyxl (formulas and cached values) plus raw XML. Nothing was saved to the sources. |
| Confidentiality | No employee names, codes, pay or contractor names are reproduced. Examples are anonymised ("Employee A"). |

Labels: **Confirmed (source)**, **Inferred**, **Proposed**, **Pending confirmation**.

---

## 1. Skill matrix inventory

There are 23 skill matrix sheets. Variant B workbooks have an "ALL" consolidated sheet plus `- CF` (staff) and `- Workers` sheets; see doc 02 §1.

| Workbook | Sheet | State | Skill columns (items) | Groups | Behav/EHS items | Employee rows | Blank grid cells | Extra score columns |
|---|---|---|---|---|---|---|---|---|
| FARO | Skill Matrix - Faro | visible | L:AS (34) | 9 | 10 | 4 | 0 | – |
| Fettling | Fettling-ALL | visible | M:AW (37) | 8 | 13 | 46 | 12 | – |
| Fettling | Fettling - CF | visible | M:AI (23) | 4 | 10 | 5 | 0 | – |
| Fettling | Fettling - Workers | visible | M:AI (23) | 6 | 7 | 41 | 357 / 943 | – |
| Forklift | Forklift | visible | M:AP (30) | 5 | 7 | 12 | 0 | – |
| Machine Shop | Mach. Shop | visible | M:BA (41) | 7 | 12 | 36 | 0 | – |
| Machine Shop | Mach. Shop - CF | visible | M:AW (37) | 7 | 9 | 3 | 0 | – |
| Machine Shop | Mach. Shop - Workers | visible | M:AT (34) | 8 | 8 | 32 | 467 / 1,088 | – |
| Maintenance | Skill Matrix-Maintenance | visible | M:CC (69) | 19 | 12 | 15 | 0 | – |
| Melting | Melting | visible | M:AZ (40) | 6 | 12 | 22 | 0 | – |
| Melting | Melting - CF | visible | M:AM (27) | 6 | 9 | 4 | 0 | – |
| Melting | Melting - Workers | visible | M:AL (26) | 5 | 8 | 22 | 244 / 572 | – |
| Moulding | Moulding | visible | J:BE (48) | 7 | 12 | 48 | 0 | – |
| Moulding | Moulding-CF | visible | M:AQ (31) | 6 | 10 | 5 | 0 | – |
| Moulding | Moulding-Workers | visible | M:AX (38) | 10 | 8 | 42 | 884 / 1,596 | Average |
| NPD | NPD | visible | M:AO (29) | 2 | 12 | 31 | some | Average |
| NPD | NPD - CF | visible | M:AK (25) | 4 | 9 | 10 | some | Average |
| NPD | NPD - Workers | visible | M:AA (15) | 4 | 7 | 21 | many | Average |
| Paint Shop | Paint | **hidden** | M:BF (46) | 8 | 13 | 73 | 0 | – |
| Paint Shop | Paint - CF | visible | M:AY (39) | 9 | 8 | 5 | 0 | Avg Score, Proficiency %, Band |
| Paint Shop | Paint - Workers | visible | M:AG (21) | 4 | 7 | 60 | 393 / 1,260 | – |
| Process | Skill Matrix - Process | visible | M:BJ (50) | 8 | 9 | 2 | 0 | – |
| Quality | Skill Matrix - Quality | visible | M:BC (43) | 8 | 11 | 15 | 0 (119 cells are "-") | – |

Employee-row counts are approximate (non-empty grid rows). The "ALL" sheets are separate snapshots, not formula unions. For example, Melting-ALL has 22 rows while CF + Workers have 26, and Paint-ALL has 73 rows while CF + Workers have 65. **Confirmed.**

## 2. Matrix layout (common template)

| Rows / columns | Content | Confidence |
|---|---|---|
| Rows 1–5, A:B | **Legend**: `5 Can Train Others`, `4 Expert`, `3 Can Work Independently`, `2 Can Work Under Supervision`, `1 Beginner`. FARO adds a second label column: Highly Skilled (4), Skilled (3), "Ssemi Skilled" (2), "Unskill" (1). | Confirmed |
| Row 7 | Department title in A. In NPD, row 7 holds the skill-group headers instead. | Confirmed |
| Row 8 (row 7 in Maintenance and Process) | Identity headers A:L plus **skill-group headers** (merged across their items), e.g. "Grinding Operation", "Behavioural and EHS" | Confirmed |
| Row 9 (row 8 in Maintenance, Process and NPD) | **Skill item names**, one column per item | Confirmed |
| Data rows | One row per employee. Each grid cell holds an integer score. | Confirmed |
| Right of the grid | `Scores 1 - 2`, `Scores 3`, `Scores 4 - 5` counts per employee, sometimes followed by Average, Proficiency % and Band | Confirmed |
| Below the grid | Six rows: `Scores 1 - 2`, `Scores 3`, `Scores 4 - 5`, `Required Skilled Manpower`, `Available Skilled Manpower`, `Risk Level` | Confirmed |

- **Identity columns** (A:L, typical): Sl. · EMP (code) · Employee · Location · DOJ · Company / Payroll · **CTC** · Designation · Qualification · Certification · Primary Focus Area · Secondary Focus Area.
- **Variants:** FARO has no Sl.
  - Maintenance and Process use "Employee Code", "Payroll" and "CTC Per Month (Including Variables)".
  - Moulding-ALL uses "Company", has a single "Focus Area", and starts its skills at J.
- **Fill rates across 484 employee rows (all sheets):**

  | Field | Fill rate |
  |---|---|
  | Location | 100% (single value: "Bagnan", i.e. one plant) |
  | Designation | 87% (65 distinct raw values; 64 after normalisation, 17 matching HR titles — re-verified 2026-11-23, §11.1) |
  | Primary Focus Area | 89% |
  | Secondary Focus Area | 62% |
  | DOJ | 50% |
  | Qualification | 5% |
  | Certification | about 0% |
  | CTC | 15 rows filled (Maintenance) |

- **Payroll values** are CF, PCI and labour-contractor names.
- **Skill grouping (Confirmed):** a two-level header, group then item, in 2–19 groups per sheet. Every sheet ends with a **"Behavioural and EHS"** group drawn from:
  - Team Management, Core Values, 5S Awareness, Kaizen, Accountability & Ownership, Problem Solving
  - Waste Disposal, Fire Safety, HIRA, Usage of PPEs, Attendance & Regularity, Documentation
  - Several sheets repeat "5S Awareness" twice.
- **Mapping skills to people (Confirmed / Inferred):**
  - Skills map to a **department** (one workbook per department) and to a **population** (CF staff vs Workers).
  - There is no designation-level template.
  - Within Workers sheets, **blank cells** (30–55% of cells) mark items that do not apply to that worker's Primary/Secondary Focus Area (e.g. a "Grinding" worker is blank on Shot-Blast items). This is **Inferred**.
  - Quality uses `-` for not applicable (119 cells). **Confirmed.**
- **Cell comments (Confirmed)** hold item descriptions. Examples:
  - Paint: "Paint Specification & TDS Knowledge" is described as "Mixing ratio, Pot life, Thinner type, Recommended DFT…".
  - Forklift: "Oil Checking" is described as "Engine oil, Transmission oil, …".
  - Melting, Moulding and Quality items have similar notes.
  - These are candidate item descriptions or assessment criteria.

## 3. Proficiency scales

### 3.1 Skill-matrix scale (Confirmed: legend rows 1–5 and conditional formatting)

| Value | Legend label (rows 1–5) | FARO alt label | Paint-CF 2nd legend (B19:C23) | CF fill colour |
|---|---|---|---|---|
| 5 | Can Train Others | – | Can train others | `00B050` green. Omitted or `92D050` on some ranges. |
| 4 | Expert | Highly Skilled | Expert | `92D050` light green |
| 3 | Can Work Independently | Skilled | "Indipendently can Work" | `FFFF00` yellow |
| 2 | Can Work Under Supervision | "Ssemi Skilled" | Can work under supervision | `FFC000` amber |
| 1 | Beginner | "Unskill" | "Beginnier" | `FF0000` red |
| blank / `-` | not applicable (Inferred) | | | none |
| 0 | appears in 2 cells (Machine Shop ALL) | | | none (out of scale) |

- **Value distribution** in skill-score cells (visible sheets) is heavily skewed to 1–2 in worker populations.
  - For example, Melting-ALL has 567 ones and 229 twos out of about 880 cells.
- **CF inconsistencies (Confirmed):**
  - Behavioural-group ranges often lack a rule for 5.
  - Paint sheets have no rule for 5.
  - In Melting and Moulding, the rules on the header area colour 4 yellow and 5 light green.
  - CF uses `containsText` (SEARCH) on some sheets, so "1" also matches "10". Harmless for single digits.

### 3.2 Competency Library scale (Confirmed: Read Me §2 and TC Library F4:I4)

| Level | Meaning | Evidence expected |
|---|---|---|
| 1 Foundation | Knows the basics; does the task under guidance. | Passes a written test on the basics; supervised work record. |
| 2 Practitioner | Does the task independently, to standard, every time. | Practical demonstration or work sample signed off; KPI in range. |
| 3 Advanced | Solves non-routine problems; improves cost, quality or output; reviews others' work. | Completed RCA, project or improvement with measured result. |
| 4 Expert | Sets the standard or system for the company; trains others; is the go-to person. | Standard, SOP or system written and adopted; people trained. |
| `–` | Not required for that band (TC Library J:M) | |

### 3.3 Scale conflict (Confirmed conflict; mapping is Inferred and Pending confirmation)

| Matrix | Closest library level | Note |
|---|---|---|
| 1 Beginner | (below 1) | The library has no "no capability" level |
| 2 Under supervision | 1 Foundation ("under guidance") | |
| 3 Independent | 2 Practitioner ("independently, to standard") | |
| 4 **Expert** | 3 Advanced | **The label "Expert" means different levels in the two scales** |
| 5 Can train others | 4 Expert ("trains others") | |

- The scales differ in range (1–5 vs 1–4), in labels and in evidence. The matrix has no evidence requirement.
- The library's "required level by band" uses its own 1–4 scale. Matrix scores cannot be compared to it without a confirmed mapping.

## 4. Required vs achieved

| Concept | How the matrix represents it | Confidence |
|---|---|---|
| Achieved level | The integer in the employee × item cell | Confirmed |
| Assessment date, assessor, method, history | **Not stored.** One snapshot per file. | Confirmed |
| Required level per employee/item | **Not stored** | Confirmed |
| Applicability | Blank or `-` cell. Focus Area columns. | Inferred |
| Required capacity per item | Row `Required Skilled Manpower`: a **typed headcount** of people needed at score ≥ 3 for that item | Confirmed (value); Inferred (≥ 3 meaning, from the Available formula) |
| Training need per employee/item | Dev. Plan marker `Y` / `US` / blank, typed by hand | Confirmed |
| Required level per role band (library) | TC Library J:M: L7, L6–L5, L4–L3, L2–L (values 1–4 or `–`) | Confirmed |

- **Required Skilled Manpower values (Confirmed):**
  - FARO, Maintenance and Process use 1 for every item.
  - Worker sheets often use the full headcount (e.g. 33, 41, 42, 59), meaning "everyone must be independent".
  - CF sheets use 2–5.
  - All "ALL" sheets except Moulding have the row empty. Moulding-ALL has no such row at all.

### 4.1 Dev. Plan marker rule (Inferred from 4,787 matched cells, 3,812 of them scored)

| Matrix score | `Y` | `US` | blank | Interpretation |
|---|---|---|---|---|
| 1 | 963 | 5 | 0 | Training required |
| 2 | 1,315 | 0 | 0 | Training required |
| 3 | 29 | 776 | 0 | Upskilling |
| 4 | 12 | 637 | 0 | Upskilling |
| 5 | 2 | 18 | 55 | No need (can train others) |
| blank / `-` | 0 | 8 | 967 | Not applicable |

- **Rule:** score ≤ 2 gives `Y` (training); score 3–4 gives `US` (upskilling; the column header is "Upskilling Participants"); score 5 or N/A gives blank. About 98% of scored cells follow it.
- The rule is applied only to items whose matrix **Risk Level** is High or Medium. Risk is copied into the Dev. Plan; the hidden Maintenance `Sheet1` holds a skill → risk list with the Low rows hidden.
- **Dev. Plan layouts (Confirmed):**
  - (a) `Sl. | Competency (one row per session) | Risk Level | <one column per employee code; names in row 2> | Total Planned Participants | Upskilling Participants`, used in FARO, Fettling, Maintenance, Process and Quality. FARO adds a total, `=H+I`.
  - (b) The same layout with `No. of Sessions` before `Risk Level`, used in Forklift, Machine Shop, Melting, Moulding, NPD and Paint.
- Dev. Plan conditional formatting: `US` is yellow, `Y` is white and blank is grey.

## 5. Formula catalogue

Every distinct pattern is shown with its exact text (example cell) and its meaning. All cached values are present. One `#REF!` was found (see §6).

| # | Formula (exact, example) | Where | Plain-English meaning |
|---|---|---|---|
| F1 | `=COUNTIF(L10:AS10, 1)+COUNTIF(L10:AS10, 2)` | Per employee row, every matrix | Number of items where the employee is 1–2 (needs training) |
| F2 | `=COUNTIF(L10:AS10, 3)` | Per employee | Number of items at 3 (independent) |
| F3 | `=COUNTIF(L10:AS10, 4)+COUNTIF(L10:AS10, 5)` | Per employee | Number of items at 4–5 (expert / trainer) |
| F4 | `=COUNTIF(L10:L13, 1)+COUNTIF(L10:L13, 2)` | Per item, row "Scores 1 - 2" | People at 1–2 on this item |
| F5 | `=COUNTIF(L10:L13, 3)` | Per item, row "Scores 3" | People at 3 |
| F6 | `=COUNTIF(L10:L13, 4)+COUNTIF(L10:L13, 5)` | Per item, row "Scores 4 - 5" | People at 4–5 |
| F7 | `=L15+L16` | Row "Available Skilled Manpower" | **Available = people scoring ≥ 3** on the item |
| F8 | `=IF(L18<=L17, "High", IF(L18<=(L17+1), "Medium", "Low"))` | Row "Risk Level" | **High** if Available ≤ Required. **Medium** if Available = Required + 1. **Low** if Available ≥ Required + 2. Meeting the requirement exactly is still "High" risk, so a buffer of 2 is needed for "Low". |
| F9 | `=COUNTIF(L19:AS19, "High")`, `=COUNTIF(L19:AS19, "Medium")` | Next to the Risk row | Number of High-risk and Medium-risk items |
| F10 | `=COUNTIF(J10:BE10, 3)+COUNTIF(J10:BE10, 4)` and `=COUNTIF(J10:BE10, 5)` | Moulding-ALL rows and columns; NPD-ALL rows 10–39 | Alternative banding: 1–2 / **3–4** / **5** |
| F11 | `=AVERAGE(M9:AO9)` | NPD sheets | Mean score per employee. Blanks are ignored. Returns #DIV/0! if the row is empty. |
| F12 | `=IF(COUNTA(M10:AX10)=0,"",AVERAGE(M10:AX10))` | Moulding-Workers | Mean score; empty if nothing is assessed |
| F13 | `=IFERROR(AVERAGE(M10:AY10),"")` | Paint - CF | Avg Score |
| F14 | `=IF(BC10="","",BC10/5)` | Paint - CF | Proficiency % = average / 5 |
| F15 | `=IF(BD10="","",IF(BD10>=75%,"🟢 High Performer",IF(BD10>=60%,"🟡 Proficient",IF(BD10>=40%,"🟠 Developing","🔴 Beginner"))))` | Paint - CF | Band: ≥ 75% High Performer, ≥ 60% Proficient, ≥ 40% Developing, otherwise Beginner. **CF looks for "High", "Mid" and "Low", so only "High Performer" is ever coloured.** |
| F16 | `=COUNTIF(M15:BJ15, "1")` | Process BK15 | Counts the text "1" in the Available row. Appears to be an error and has no meaning. |
| F17 | `=SUM(A32:BC32)` | Quality BE32 (unlabelled row 32) | Sum of per-item session counts = 44, the number of Quality calendar rows (Inferred: "sessions per item"). Paint-CF has a typed "Repeatation" row with the same role. |
| F18 | `=SUM(G9:G23)` | Maintenance G24 | **Sum of the CTC column** (sensitive pay data) |
| F19 | `=VLOOKUP(B10, '[1]MPP BAGNAN LIVE'!$D$67:$I$88, 6, 0)` | Machine Shop (3 sheets), column F | Payroll looked up from an external manpower-plan workbook |
| F20 | `=A10+1` | Serial | – |
| D1 | `=COUNTIF(D3:G3, "Y")` | Dev. Plan "Total Planned Participants" | Number of employees nominated for training |
| D2 | `=COUNTIF(D3:G3, "US")` | Dev. Plan "Upskilling Participants" | Number nominated for upskilling |
| D3 | `=H3+I3` | FARO Dev. Plan J | Total participants (copied into calendar K) |

**Worked example (anonymised, FARO, 4 employees):**
- On item "Preparing Reports & Analytical Knowledge", Employee A scores 4 and Employees B, C and D score 2.
- F4 gives 3, F5 gives 0 and F6 gives 1, so Available = 1.
- Required = 1, so Risk = High (1 ≤ 1).
- In the Dev. Plan, Employee A is marked `US` and B, C and D are marked `Y`. Total = 4, which matches calendar K = 4.

**Gap calculation (Confirmed):** the matrices compute **no per-person gap** (required − achieved). The only gap logic is the item-level capacity gap (F7 vs Required, giving F8). The library's Read Me defines the intended gap: "Gap = required level minus current level. Any gap goes into the TNI and the training calendar; gaps of 2 or more need an individual plan."

## 6. Inconsistencies and data-quality issues (skill matrices)

| # | Issue | Evidence | Confidence |
|---|---|---|---|
| 1 | Banding header contradicts the formula | Melting, Melting-CF and Melting-Workers headers read "Score 1-2 / Score- 3-4 / Score 5" but the formulas compute 1–2 / 3 / 4–5 | Confirmed |
| 2 | Two banding schemes | Most sheets use 1–2 / 3 / 4–5. Moulding-ALL and NPD-ALL (rows 10–39) use 1–2 / 3–4 / 5. NPD-ALL row 9 uses the first scheme, so the same sheet mixes both. | Confirmed |
| 3 | Hard-coded "Available" overriding the formula | Fettling-CF M19:S19 and Fettling-Workers X55:Z55 are typed, equal to Required, which forces "High" | Confirmed |
| 4 | Broken reference | Melting-ALL A15 `='Melting - CF'!#REF!+1`, with 22 dependent `#REF!` serials | Confirmed |
| 5 | Inconsistent Required rows | Empty on the ALL sheets. Moulding-ALL has no Required, Available or Risk rows. | Confirmed |
| 6 | Same item names repeated within a sheet | "5S Awareness" twice. "Setting & Operating", "Tooling & Cutting knowledge" and "SOP / Work Instruction" repeated under each machine group (Machine Shop). Items are identified by **group + name**, not by name. | Confirmed |
| 7 | Typos and inconsistent names across sheets | "Knolwedge", "Laddle", "Reparing", "Vissual", "Cosumption", "KNOWLADGE"; the same skill is worded differently in CF and Workers sheets | Confirmed |
| 8 | Out-of-scale values | `0` (2 cells), `-` (119 cells, Quality only) | Confirmed |
| 9 | ALL sheets are snapshots, not unions | Headcounts and item lists differ from CF + Workers | Confirmed |
| 10 | Personal and pay data in the training files | CTC, payroll contractor, DOJ columns; CTC SUM (F18) | Confirmed. **Do not import pay data.** |
| 11 | External dependency | Machine Shop VLOOKUP to a personal-OneDrive MPP workbook | Confirmed |
| 12 | Snapshot only | No assessment date or assessor, so re-assessment overwrites history | Confirmed |
| 13 | Hidden data | `Paint` matrix and Maintenance `Sheet1` (69 skills → High/Medium/Low, Low rows hidden) | Confirmed |

## 7. Technical Competency Library

### 7.1 Sheets

| Sheet | Purpose | Key formulas |
|---|---|---|
| Read Me | Draft v1 dated 26-10-2026, "Built from the KRAs of 445 employees (2,530 KRA lines)". Covers: summary by function; levels and evidence; required level by band; assessment methods; usage steps; notes. | `=COUNTIF('TC Library'!$B$5:$B$167,A6)` (TCs per function); `=SUMIF(Coverage!$A$5:$A$43,A6,Coverage!$H$5:$H$43)` (employees per function); `=SUM(...)` |
| TC Library | The catalogue: one row per TC (rows 5–172). Auto-filter on A4:P172, frozen at E5. | No formulas. **Data validation J5:M167 list `1,2,3,4,–`** |
| Coverage | TCs per sub-function, and KRA-file employees per sub-function × band (L7, L6–L5, L4–L3, L2–L) | `=COUNTIFS('TC Library'!$B$5:$B$167,A5,'TC Library'!$C$5:$C$167,B5)`; `=SUM(D5:G5)`; `=COUNTIFS('TC Library'!$A$5:$A$167,"AC-0*")`; `=COUNTA('TC Library'!$A$5:$A$167)`; check `=IF(H44=445,"OK","Check")` gives "OK" |

### 7.2 TC Library columns (Confirmed)

| Col | Header | Notes |
|---|---|---|
| A | Code | `XX-nn`, unique; 20 prefixes (HR, AC, SB, PU, OP, ME, MO, CO, FE, PA, MS, PT, PD, PC, QA, LB, MA, PP, SA, SP) |
| B | Function | 5 values (fill-coloured per function) |
| C | Sub-function | 35 values. This is the **department / role applicability field**; there is no explicit department or designation list. |
| D | Technical competency | Name |
| E | Scope (what it covers) | Free text. Lists sub-skills in the draft rows. |
| F | 1 Foundation descriptor | **Column hidden** |
| G | 2 Practitioner descriptor | |
| H | 3 Advanced descriptor | |
| I | 4 Expert descriptor | |
| J | Required level L7 (A1–A6: operators, assistants, technicians) | **Hidden**; yellow; DV 1–4 / – |
| K | Required level L6–L5 (E1–E5: executives, supervisors, engineers) | yellow; DV |
| L | Required level L4–L3 (M1–M5: managers) | yellow; DV |
| M | Required level L2–L (G, V, C: senior leaders) | yellow; DV |
| N | How assessed | **Hidden**. Codes WT, PD, WS, CR, RR plus the KPI in brackets. |
| O | Linked KRA (from KRA file) | **Hidden** |
| P | Check | "Done" on 148 rows. Blank on HR-01..14 and OP-01..06. Meaning **Pending confirmation** (review status?). |

### 7.3 Counts (Confirmed from rows 5–172)

| Function | TCs | Sub-functions (TC count) |
|---|---|---|
| HR, Admin & IT | 14 | HR Ops & Payroll 2 · IR & Labour Law 2 · Talent Acquisition & MPP 2 · Talent Mgmt & L&D 3 · Admin & Facilities 2 · IT & Digital 3 |
| Accounts & Commercial | 26 | Fin. Accounting 3 · Taxation 6 · Treasury/Banking/Forex 4 · Costing 3 · Stores 2 · Export Docs & Logistics 8 |
| Sales & BD | 15 | Key Account 5 · BD & Market Expansion 5 · Sales Ops 5 |
| Purchase | 7 | Strategic Sourcing 2 · Vendor Dev 1 · Technical & NPD Purchase 1 · Purchase Ops 3 |
| Operation | 106 | Common to all 6 · Melting 9 · Moulding 11 · Core Shop 7 · Fettling & Finishing 5 · Paint Shop 10 · Machine Shop 6 · Pattern & Tool Room 2 · Product Dev & Design 8 · Process Control 10 · Quality – Inspection & QA 8 · Lab & Metrology 8 · Maintenance 6 · PPC, Dispatch & MH 3 · Safety & EHS 2 · Sand Plant 5 |
| **Total** | **168** | 35 sub-functions |

- **Completeness:** 100 TCs are complete, with descriptors F–I, required levels J–M and an assessment method.
- **68 TCs are drafts:** they have only a name and scope, with no descriptors, required levels, method or KRA. These are AC×11, SB×5, ME-04..08, MO-04..10, CO-02..06, FE-04, PA-02..09, MS-04/05, PD-05..07, PC-03..09, QA-02/03/06/07, LB-04..07, MA-03 and SP-01..05.
- **Required-level distribution** (complete TCs):

  | Band | Distribution |
  |---|---|
  | L7 | 2 ×33, 1 ×7, – ×60 |
  | L6–L5 | 2 ×59, 3 ×27, 1 ×14 |
  | L4–L3 | 3 ×99, – ×1 |
  | L2–L | 3 ×62, 4 ×36, – ×2 |

- **Assessment methods** (count of mentions): RR 88, PD 44, WS 39, WT 23, CR 6. Their meanings are Written test, Practical demonstration, Work sample, Certificate/licence and Record/KPI review (12 months).
- **Read Me rules (Confirmed text):**
  - Each role takes the TCs of its sub-function.
  - Every Operation role also takes OP-01..OP-06.
  - Assessors are the function head plus a subject expert, with HR coordinating.
  - Gap = required − current. Gaps of 2 or more need an individual plan.
  - **Promotion:** the person must meet the next band's required level on at least 80% of TCs, with no TC more than 1 level below.
  - L7 uses the library as the shop-floor skill matrix, reviewed every 6 months.
  - Validation workshop: 2 hours per sub-function.
- **Library defects (Confirmed):**
  - (a) Read Me, Coverage and DV ranges stop at row 167, so the 5 Sand Plant TCs (rows 168–172) are excluded. Read Me says 163 TCs (Operation 101); the actual figure is 168 (Operation 106).
  - (b) The sub-function value is `"Moulding "` with a trailing space, and Coverage looks up "Moulding & Sand Plant", so Coverage shows **0** TCs for Moulding.
  - (c) Coverage's "TCs applied" column is text guidance, not data.

### 7.4 Coverage sheet meaning (Confirmed)

- For each sub-function or generalist group, the sheet shows:
  - the number of library TCs (live formula)
  - typed KRA-file headcounts per band (L7, L6–L5, L4–L3, L2–L)
  - the total
  - a rule describing which TCs apply
- Totals are 93 / 214 / 109 / 29, giving 445 employees.
- Generalist rows (e.g. "HR generalist", "Accounts generalist (AC-01 to AC-07)", "Plant & operations management") reuse TCs from their function.
- Coverage is a sizing and applicability aid. It is not an employee assignment.

## 8. Comparison: library vs skill matrices

| Aspect | Skill matrices | Competency Library | Confidence |
|---|---|---|---|
| Identifier | None (column position only) | Code `XX-nn` | Confirmed |
| Granularity | Fine-grained items (about 806 item columns across 23 sheets) inside groups | Coarse TCs (168) | Confirmed |
| Scale | 1–5, behaviour-anchored labels, no evidence | 1–4, descriptor per TC per level, evidence and method | Confirmed (conflict) |
| Requirement | Headcount per item (≥ 3) | Level per TC per grade band | Confirmed |
| Applicability | Department workbook, CF/Workers sheet, blank cells, focus area | Function / sub-function, grade band | Confirmed |
| Behavioural / EHS | Present on every sheet | Out of scope ("Technical"). Only OP-03 (TPM, 5S & Kaizen) and OP-05 (Foundry safety practices) overlap partially. | Confirmed / Inferred |

**Match evidence:**
- **Confirmed, strong:** draft library rows are **roll-ups of matrix groups**. Their name equals a matrix group header and their Scope lists that group's items:
  - PA-02 "Incoming Material Inspection & Hanging": scope lists the 4 Paint items (Visual inspection; I-bolt, Belt, Thread hole inspection as per SOP; Trolley, hanging chain, hook condition; Transfer trolley and hanging SOP).
  - PA-04..PA-08 correspond to the Paint groups Paint Storage & Mixing, Paint Application, Putty Application, Sanding Operation and Finished Material Inspection.
  - PC-03..PC-09 correspond to the 7 Process groups (Pattern, Moulding, Core, Melting, Pouring and Operational Inspection, and System Requirements). Their scopes paraphrase the Process items.
  - MO-04 "Core making": scope lists the Moulding "Core making" items.
  - ME-04: scope "Laddle New lining, Gear Box Health" matches the Melting "Laddle" group items.
  - MO-10 "Accessories preparation & Rework" matches the Moulding groups "Accessories preparation" and "1st Line rework".
  - ME-05 "Crane Operation" and ME-08 / MO-09 "Manpower handling" equal matrix item names.
- **Candidate only (name or keyword overlap, not confirmed):**
  - FE-02 "Grinding & auto-fettling" vs the Fettling "Grinding Operation" group
  - FE-01 vs "Shot Blast Machine Operation"
  - FE-03 vs "Knowledge of Casting Welding Operation"
  - MS-01/02/03/06 vs the Machine Shop machine groups, Programming and GD&T
  - MA-01/02/03 vs the Maintenance Electrical, Mechanical and Automation groups
  - PP-03 "Forklift & material movement" vs the Forklift matrix
  - LB-08 "3D scanning & dimensional metrology" vs the FARO matrix
  - PD-02 "Casting simulation" vs NPD "Procast software"
  - PD-03 vs "3D Modeling / Creo"
  - PT-01/02 vs the NPD-Workers pattern and jig groups
- **Not represented in the library:** most matrix items at item level, for example individual Maintenance equipment (Vacuum Pump, HT VCB, PLC…), Forklift tonnage classes and the Behavioural/EHS items. FARO and Forklift have no dedicated sub-function.
- **Not represented in the matrices:** Core Shop (only as a Moulding group), Lab & Metrology, PPC, Safety & EHS, Sand Plant, and every non-Operation function.

**Conclusion (Inferred):** the library is evolving into the parent layer: TC = matrix group. The matrices hold the assessable child items. The two are not yet linked by code, and their scales conflict.

## 9. Data model implications (Proposed)

| Entity | Purpose / key fields | Source mapping |
|---|---|---|
| `proficiency_scale` | Configurable scale: name, code, is_active | Two seeds: "Shop-floor 1–5" (matrix) and "TC 1–4" (library) |
| `proficiency_level` | scale_id, ordinal (1..n), code, label, description, evidence_expected, colour, counts_as_competent (bool) | Matrix legend rows 1–5 and CF colours; Read Me §2 |
| `scale_level_mapping` | from_level → to_level (optional crosswalk) | §3.3, **Pending confirmation** |
| `competency` | code (unique), name, scope, function, sub-function → org taxonomy, type (technical / behavioural / EHS), status (draft, validated), scale_id, parent_id | TC Library A–E, P. Parent/child allows TC → matrix item. |
| `competency_level_descriptor` | competency_id, level_id, descriptor text | TC Library F–I |
| `competency_assessment_method` | competency_id, method (WT, PD, WS, CR, RR), KPI text | TC Library N |
| `skill_matrix_template` | name, scope by org unit (department), audience (CF staff / Workers), optional designation / job family / grade band, version, effective dates | One per matrix sheet (CF / Workers) |
| `skill_matrix_template_item` | template_id, competency_id (item), group label / sort order, **required_level_id** (nullable), **required_headcount_at_or_above** (nullable), risk thresholds, applicable focus areas | Groups and items from rows 8–9; "Required Skilled Manpower"; library J–M |
| `employee_competency_assessment` | employee_id, competency_id, level_id or not-applicable flag, assessed_on, assessor_id, method, evidence, comments, template_id, status. **Append-only history**; the current level is the latest approved row. | Matrix cells imported as one baseline assessment dated at import time |
| `competency_requirement` (role-based) | job family / position / grade band → competency_id, required_level_id | TC Library J:M by band |
| `training_need` | employee_id, competency_id, need_type (TRAINING, UPSKILLING), source (gap, risk, manual), risk level, sessions required, status | Dev. Plan `Y`/`US`, F8 risk |
| Derived (views, not stored) | Per-employee band counts (F1–F3), averages / proficiency % (F11–F15), per-item available headcount (F7), risk (F8), personal gap = required − current, promotion readiness (80% rule) | Formulas in §5 and the Read Me |

- **Rules to make configurable** (do not hard-code):
  - the competent threshold (≥ 3 today)
  - the band boundaries (1–2 / 3 / 4–5 vs 1–2 / 3–4 / 5)
  - the risk margin (+1 Medium, +2 Low)
  - the Proficiency-band percentages (75 / 60 / 40)
  - the need-type rule (≤ 2 gives TRAINING; 3–4 gives UPSKILLING; 5 gives none)
- **Import rules:**
  - Ignore CTC and payroll columns.
  - Map blank or `-` to "not applicable", not to 0.
  - Reject 0.
  - Identify items by (sheet, group, item name).
  - Fuzzy-match names and route them for human review.
  - Never treat similar names as the same competency without approval.

## 10. Open questions

1. Confirm the matrix legend meanings, and whether 1–5 or the library's 1–4 becomes the company standard, or both with a mapping.
2. Is "≥ 3 = skilled" the official threshold? Is "Risk High when Available = Required" intended?
3. What exactly do `Y` and `US` mean? Does "US" trigger a different (advanced) course?
4. Do blank cells mean "not applicable", "not yet assessed" or "not required"?
5. Should behavioural/EHS items live in the same catalogue (as a type) or in a separate behavioural library?
6. Who assesses, how often (Read Me says 6 months for L7), and what evidence is required?
7. Will each matrix item be assigned a library TC code (parent) during the validation workshops?
8. What does the TC Library "Check = Done" column mean? When will the 68 draft TCs receive descriptors and required levels?
9. How do grade bands (A1–A6, E1–E5, M1–M5, G/V/C) map to existing designations in the HR master?
10. Should consolidated "ALL" sheets be discarded in favour of CF + Workers sheets as the import source?

---

## 11. Re-verified 2026-11-23

**Method.** All matrix, Dev. Plan and library sheets were re-opened read-only with openpyxl,
both as formulas (`data_only=False`) and as cached values. Visible and hidden sheets were
included, and validations, hidden columns and fills were checked. Old figures and new figures
are given wherever they differ.

### 11.1 Skill matrices

| Claim | Re-verified result | Status |
|---|---|---|
| Scale 1–5 | The legend in A1:B5 (`5 Can Train Others` … `1 Beginner`) is the same on all 22 visible and hidden matrix sheets; FARO adds alternate labels. In-grid values: 1 = 7,420; 2 = 4,738; 3 = 2,761; 4 = 1,907; 5 = 250; `-` = 119 (Quality only); `0` = 2 (Mach. Shop R29, W45). No other values occur. | Confirmed |
| "Skilled" = score ≥ 3 | Not stated as text anywhere. It is defined by formula: `Available Skilled Manpower` = `Scores 3` + `Scores 4 - 5`. Example: FARO L18 `=L15+L16`, where L15 is `=COUNTIF(L10:L13, 3)` and L16 is `=COUNTIF(L10:L13, 4)+COUNTIF(L10:L13, 5)`. | Confirmed (by formula) |
| Risk formula `=IF(avail<=req,"High",IF(avail<=req+1,"Medium","Low"))` | The **exact text** differs only in spacing and parentheses: `=IF(L18<=L17, "High", IF(L18<=(L17+1), "Medium", "Low"))` in `Skill Matrix - Faro`!L19. Row 17 is `Required Skilled Manpower` and row 18 is `Available Skilled Manpower`. The same pattern occurs in **758 cells on 22 of 23 matrix sheets**, identical after normalisation. | Confirmed. The logic is identical; doc 05 quotes a normalised form. |
| Workbooks that differ | (1) Moulding `Moulding` (ALL) has **no** Required, Available or Risk rows, and its bands are 1–2 / 3–4 / 5 (BF–BH). (2) Fettling-CF M19:S19 (7 cells) and Fettling-Workers X55:Z55 (3 cells) hold **typed** Available values instead of the formula. (3) Process BK15 `=COUNTIF(M15:BJ15,"1")` is an anomaly. (4) Every "ALL" sheet except Moulding has an empty Required row. | Confirmed (as in §6) |
| Matrix designations usable as LMS designation references | The `Designation` column (H; G on Moulding-ALL) has **64 distinct normalised values** (previously reported as 65 raw) across about 490 rows. Only **17** of them, covering about 106 rows, match a Source A/B designation title exactly after normalisation. The rest are: (a) trade or role labels (WELDER, FITTER, HELPER, PAINTER, CRANE OPERATOR…); (b) bare ranks (SUPERVISOR, SR. SUPERVISOR, ASSISTANT MANAGER); (c) process or area names (CHARGING, POURING, CORE JAM, SIMULATION, FURNACE); (d) `CONTRACTOR`. | **Not directly usable.** Treat them as candidate *functional roles*, or map them through a reviewed alias table to the HR designation master. |

### 11.2 Technical Competency Library

| Claim | Re-verified result | Status |
|---|---|---|
| Scale 1–4 | Read Me A15:A18 and TC Library F4:I4 list `1 Foundation`, `2 Practitioner`, `3 Advanced`, `4 Expert`. The validation on J5:M167 is the list `1,2,3,4,–`, where the en dash (U+2013) means "not required". | Confirmed |
| 168 competencies | 168 rows (rows 5–172) with 168 unique codes: Operation 106, Accounts & Commercial 26, Sales & BD 15, HR, Admin & IT 14, Purchase 7. | Confirmed |
| 68 drafts | 68 rows have columns F–O (descriptors, required levels, method, KRA) entirely blank. The other 100 rows are fully populated; none is partial. | Confirmed |
| How draft is indicated | **There is no status column.** A draft is recognisable only by its empty F–O. Column P `Check` reads `Done` on all 68 drafts and is blank on HR-01..14 and OP-01..06, so it does **not** mark draft status. Yellow fill on D/E marks most drafts but not reliably: 1 draft has no fill, and some complete rows are yellow. The whole library is labelled "Draft v1" (Read Me A2, TC Library A2). | New detail |
| Gap = required − assessed | **Text only**, in Read Me B38: "Gap = required level minus current level. Any gap goes into the TNI and the training calendar; gaps of 2 or more need an individual plan." The TC Library contains **0 formulas**. | Confirmed (as a rule, not a formula) |
| IDP trigger: gap ≥ 2 | The same cell, B38: "gaps of 2 or more need an individual plan" | Confirmed |
| Grade-band columns J–M | Columns J–M sit under the merged caption J3 "Required level by band". J is hidden, as are F, N and O. | Confirmed |

**Exact band codes** (row 4 headers, written with the en dash U+2013):

| Column | Band code | Grades shown in header |
|---|---|---|
| J | `L7` | A1–A6 |
| K | `L6–L5` | E1–E5 |
| L | `L4–L3` | M1–M5 |
| M | `L2–L` | G, V, C |

The claim wrote "L6-L5" with a hyphen; the source uses an en dash.

**Band → grade mapping.** It exists only as text, in Read Me A22:B25:

| Band | Grades | Read Me description |
|---|---|---|
| L7 | A1–A6 | operators, assistants, technicians |
| L6–L5 | E1–E5 | executives, supervisors, engineers |
| L4–L3 | M1–M5 | managers |
| L2–L | G1–G4, V1–V4, C1–C4 | senior leaders |

**Nothing maps bands to designations.** In the HR files, the band implied by level and the band
implied by grade disagree on 17 of 441 Source B rows; E4/L7 accounts for 10 of them (see
[01 §10.6](01_ORGANISATION_STRUCTURE_ANALYSIS.md)). The band for each assignment must therefore
be decided by grade or by level, not both (Q-45).

### 11.3 Import column specifications (proposed)

**A. Skill-matrix sheet.** One header block; one employee per data row.

| Location | Content | Target | Rule |
|---|---|---|---|
| Sheet name, A7 | Department, plus audience from the `- CF` / `- Workers` suffix | `skill_matrix` scope (org unit) and audience | Map the department through an HR-confirmed alias table. Prefer the CF and Workers sheets: the ALL sheets are snapshots. |
| Header row 8 (row 7 in Maintenance and Process) | `Sl.` · `EMP` / `Employee Code` / `EMP. CODE` · `Employee` · `Location` · `DOJ` · `Company / Payroll` · `CTC` · `Designation` · `Qualification` · `Certification` · `Primary Focus Area` · `Secondary Focus Area` | Member: employee code (resolved against the master) and focus areas | **Never import** `CTC` or `Company / Payroll`. Take DOJ, name and location from the employee master, not from this sheet. |
| Row 8, from column M (merged cells) | Skill **group** | Item group and sort order | — |
| Row 9, from column M (row 8 in Maintenance, Process and NPD) | Skill **item** | `skill_matrix_item`, keyed by (sheet, group, item) | Fuzzy-match each item to the catalogue and send matches for review. Cell comments hold item descriptions. |
| Grid from M10 (from L in FARO, from J in Moulding-ALL) | Score | `competency_assessment` (baseline, dated at import) | Accept 1–5. Blank or `-` = not assessed / N/A. Reject 0. |
| Right-hand count columns; `Average`, `Avg Score`, `Proficiency %`, `Band` | Derived values | — | Do not import |
| Row `Required Skilled Manpower` | Headcount required at score ≥ 3 | `skill_matrix_item.required_headcount` | Integer; blank → null |
| Rows `Scores …`, `Available Skilled Manpower`, `Risk Level` | Derived values | — | Recompute. Flag the typed Available cells (Fettling). |

**B. Dev. Plan sheet** (training-need nominations; deferred under D-08).

| Column | Content | Rule |
|---|---|---|
| `Sl.` | Serial number | — |
| `Competency` | Item and session | — |
| `No. of Sessions` | Session count | Present on some sheets only |
| `Risk Level` | Copied risk | — |
| One column per employee code | `Y` → TRAINING; `US` → UPSKILLING; blank → none | Names in row 2 are not imported |
| `Total Planned Participants`, `Upskilling Participants` | Derived totals | Do not import |

**C. TC Library** (sheet `TC Library`, header row 4, data rows 5–172).

| Col | Header | Target | Rule |
|---|---|---|---|
| A | `Code` | `competency.code` | Unique; format `XX-nn` |
| B | `Function` | Function | Required; must exactly match one of the five seeded names |
| C | `Sub-function` | Sub-function | Trim whitespace (`"Moulding "`). Mapping to org units is pending (Q-47). |
| D | `Technical competency` | Name | Required |
| E | `Scope (what it covers)` | Scope / description | — |
| F–I | `1 Foundation …` to `4 Expert …` | `competency_level_descriptor` (levels 1–4) | If all four are blank, set status to *draft* |
| J–M | `L7`, `L6–L5`, `L4–L3`, `L2–L` | `competency_band_requirement` | Values `1`–`4`, or `–` = not required. Keep band codes verbatim. Band → grade follows Read Me A22:B25, pending confirmation. |
| N | `How assessed` | Assessment method(s) plus KPI text | Parse the codes WT, PD, WS, CR, RR |
| O | `Linked KRA (from KRA file)` | Reference text | Optional |
| P | `Check` | — | Not a status field; its meaning is pending |
