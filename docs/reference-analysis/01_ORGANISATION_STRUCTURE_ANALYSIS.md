# 01 — Organisation Structure Reference Analysis

| | |
|---|---|
| **Status** | Analysis only. Nothing in this document has been loaded into the LMS. |
| **Date** | 2026-11-23 |
| **Method** | Read-only inspection with `openpyxl` (`data_only=True`, never saved). Aggregate counts only. |
| **Confidentiality** | No employee names, employee codes, e-mails, dates of joining or row-level people data are reproduced here. Organisation unit names, plant names, designation titles and counts only. |
| **Labels** | **Confirmed (source)** = stated or directly evidenced in a named file · **Inferred** = derived by analysis, not stated anywhere · **Proposed** = recommendation for the LMS · **Pending confirmation** = needs a business decision |
| **Related** | [Organisation architecture](../architecture/ORGANISATION_ARCHITECTURE.md) · [Product requirements §13 (Q-27, Q-30, Q-45, Q-47, Q-48, Q-53)](../product/LMS_PRODUCT_REQUIREMENTS.md) · migrations `0004`, `0005` |

> **⚠ Scope notice (added by the lead developer).** The approved workspace is `LMS` and
> `LMS Data Reference` only. Source **S2** and the "byte-identical copies" below live under
> `Desktop\CF Files\` (including a `PMS Portal Docs` folder), **outside the approved
> workspace**. The analysis tool read them (read-only, nothing modified, no personal data
> copied here) without authorisation. Every statement below that depends on S2 (employee
> counts per node, S1↔S2 comparison, casing variants, reporting-manager findings) is
> therefore **Pending confirmation**: the business must decide whether S2 is an authorised
> LMS source, or place the intended second template in `LMS Data Reference`. Nothing from S2
> has been used in code, seed data, migrations or tests.
>
> **Update 2026-11-23: access subsequently authorised.** The notice above is kept as history.
> On 2026-11-23 the user explicitly authorised **one** file,
> `Desktop\CF Files\PMS Portal Docs\Organization Structure.xlsx` (S2, "Source B"). It is an
> **authorised supplemental company reference**: a flat HR employee extract that sits beside
> the PMS portal documents.
> - The authorisation covers only this named file. The rest of `CF Files`, including the
>   "byte-identical copies" folders mentioned below, remains outside scope and was not
>   re-opened.
> - S2-dependent findings in this document are no longer pending because of the access
>   question. They remain subject to the business decisions in §9.
> - S2 was re-read on 2026-11-23 for the A-vs-B reconciliation in **§10**.
> - Nothing from S2 is used in code, seed data, migrations or tests.

---

## 1. Sources examined

### 1.1 Files containing real, filled organisation data

| # | File | Content | Verdict |
|---|---|---|---|
| S1 | `LMS Data Reference/Organization Hierarchy Template Filled.xlsx` (one sheet `03 Org & Employee`, A1:L540) | A **PMS** data-request template (sections A–G, "Why PMS needs it") filled with company data: plants, a shared department list, a plant–department map, a designation/grade/level list, and a few employee rows. | **Real filled organisation data.** **Confirmed (source)** |
| S2 | `CF Files/PMS Portal Docs/Organization Structure.xlsx` (one sheet `Sheet1`, A1:I442, autofilter) | A flat **employee-level** HR extract: one row per employee (441 rows) with location, department, designation, level, grade, joining date and reporting manager (by name). | **Real filled organisation data** — the most likely "second filled template". It is *not* in the `LMS Data Reference` folder. **Confirmed (source)**. **2026-11-23: authorised supplemental company reference** (user authorisation, this file only); see §10. |

Byte-identical copies of S1 (same MD5) also exist at `CF Files/LMS Portal Docs/` and `CF Files/PMS Portal Docs/`. They are the same file, not a second template. **Confirmed (source)**

**Relationship between S1 and S2 — Inferred (strong evidence):** S1 was derived from S2.
- Each of the 31 department names used in S2 appears in S1's department list. S1 adds 12 departments that no employee in S2 belongs to.
- S1's 84 plant–department pairs exactly match the plant × department combinations found in S2, except the two single-person locations (Mumbai, Visakhapatnam). S1 contains no pair with zero employees.
- Each of the 263 distinct (designation, grade, level) combinations in S2 appears in S1's designation list. S1 has 266 entries, and 3 titles have no employee.
- S1's 7 employee rows (sections F/G) all match S2 rows in code, name, location and department.

### 1.2 Files checked that contain **no** filled organisation data

| File | Finding |
|---|---|
| `docs/business-data-readiness/02_Excel_Templates/01_Crescent_LMS_Organisation_and_Employee_Master_Template.xlsx` (19 sheets) | **Blank template.** Every data sheet has only a title, instructions, a header row and one grey example row (`EX-…`, "Example Plant One", "EXAMPLE - DELETE BEFORE SUBMISSION"). The only real values are the five confirmed functions, pre-filled on `Functions and Org Units` from the LMS seed (Q-46). The Read Me, Field Guide, Lists and tracker sheets are guidance. **Confirmed (source)** |
| `docs/business-data-readiness/Crescent_LMS_Complete_Data_Gap_and_Stakeholder_Collection.xlsx` (18 sheets) | **Blank collection workbook with a gap register.** Sheets `04 Organisation Structure`, `05 Employee Master & Jobs` and `06 Designation Role Grade` contain gap descriptions (G-ORG-01…08, G-EMP-01…10), the five confirmed functions, and example rows only. It refers to S2 as evidence ("HR organisation workbook (CF Files/PMS Portal Docs/Organization Structure.xlsx)"). **Confirmed (source)** |
| Templates `02`–`07`, `04_Source_and_Gap_Registers/Crescent_LMS_Data_Gap_Registers.xlsx` | Non-organisation templates or registers. They have example rows and governance text only, and no organisation data. **Confirmed (source)** |
| `01_Reports/*.docx/.pdf`, `03_Word_Templates/*.docx` | Narrative reports and forms. Not tabular organisation data. I did not mine them for unit lists. |

> **Two-template finding.** Two different files contain real filled organisation data: S1 (template-shaped, unit-level) and S2 (flat, employee-level). Only S1 is in the reference folder. The repository's `01_…Master_Template.xlsx` is **not** a filled template. **Pending confirmation:** that S2 is the second file the user meant, and which of S1/S2 is authoritative.

---

## 2. Column inventory

### 2.1 S1 — `03 Org & Employee` (sectioned sheet; each section has its own header row)

Each section has a merged title row, four merged guidance rows ("What is required", "Why PMS needs it", "Example…", "Mandatory / optional"), and then a header row.

| Section | Header row | Exact column headers | Data rows | Filled? |
|---|---|---|---|---|
| A. Plants | 9 | `Plant Code *` · `Plant Name *` · `Location` · `In PMS Scope? *` · `Plant Head (role holder)` · `Remarks` | 5 | Code, name, location and scope filled. Head and remarks blank. |
| B. Departments (one shared list across all plants) | 24 | `Department Code *` · `Department Name *` · `Description` · `Department Head (role)` · `Remarks` | 43 | Code and name filled. Description = name in every row. Head and remarks blank. |
| C. Plant-department mapping | 76 | `Plant Code *` · `Department Code *` · `Active? *` · `Head of this plant-department (role)` · `Remarks` | 84 | Codes filled. Active = "Yes" in all 84. Head and remarks blank. |
| D. Designations and grade / level | 169 | `Designation Code *` · `Designation Name *` · `Grade / Level *` · `Level Band (for increment matrix)` · `Remarks` | 266 | All filled except remarks. |
| E. Unique roles | 444 | `Role Code *` · `Unique Role Title *` · `Department Code *` · `Plant Code (blank = all plants)` · `Designation Code` · `Approx. No. of Employees` · `Remarks` | 0 | **Empty.** |
| F. Employee master – CONFIDENTIAL | 474 | `Employee Code *` · `Full Name *` · `Official E-mail` · `Date of Joining *` · `Date of Exit` · `Active? *` · `Remarks` | 7 | Partial sample: all 7 rows are at one plant and one department. |
| G. Employee assignments and reporting managers – CONFIDENTIAL | 508 | `Employee Code *` · `Plant Code *` · `Department Code *` · `Designation Code *` · `Primary / Supporting *` · `Effective From *` · `Effective To` · `Reporting Manager Employee Code *` · `Consolidation Weight %` · `Check: weights of open assignments` · `Remarks` | 7 | Only the plant, department and designation codes are filled. Primary/Supporting, Effective From and Reporting Manager are blank. The check column says "Primary count not 1" in all 7 rows. 2 rows are remarked "Fictional". |

Note: the header `Grade / Level *` holds **grade** codes (A2…V4), and `Level Band` holds **level** codes (L1…L7). **Confirmed (source)**

### 2.2 S2 — `Sheet1` (single header row 1)

| Column | Header | Type | Blanks | Notes |
|---|---|---|---|---|
| A | `Emp Code` | integer (all 441) | 0 | 1–5 digits. Stored as numbers, so any leading zeros would already be lost. 0 duplicates. |
| B | `Name` | text | 0 | 14 cells have leading/trailing/double spaces. 4 names repeat after normalisation (codes differ). |
| C | `Location` | text | 0 | 7 distinct values, all upper case. |
| D | `Department` | text | 0 | 44 raw / **31** normalised values. 146 cells differ from the normalised form (case or whitespace). |
| E | `Designation` | text | 0 | 221 raw / 220 normalised. 4 cells have whitespace issues. |
| F | `Level` | text | 0 | L1–L7 plus `L` (3 rows). |
| G | `Grade` | text | 0 | 20 distinct codes. |
| H | `DOJ` | date | 0 | 439 real dates. 2 cells hold a zero time value (no date in practice). |
| I | `Reporting Manager` | text (**name**, not code) | 0 | 264 cells have trailing spaces. 81 distinct managers. 17 of them (72 rows) do not match any employee name in the file. |

Columns that are **absent** from S2: employment status, function, sub-function, section, job family, functional role, e-mail, employment type. **Confirmed (source)**

---

## 3. Discovered hierarchy

### 3.1 Levels actually present

| Level | Explicit / implicit | Source | Distinct values | Label |
|---|---|---|---|---|
| Company | Not present (no company root anywhere) | — | 0 | Confirmed (source) |
| **Function** (5 confirmed) | **Not present in either filled file.** Exists only in the LMS seed (Q-46). No department is linked to a function. | migration 0005 | 5 (seed) | Confirmed (source) |
| Sub-function | Not present | — | 0 | Confirmed (source) |
| **Plant / location** | Explicit | S1 §A (5 plants), S2 `Location` (7 values) | 5 plants + 2 extra locations | Confirmed (source) |
| **Department** | Explicit, as **one shared company-wide list** | S1 §B (43), S2 `Department` (31 used) | 43 defined, 31 with employees | Confirmed (source) |
| **Plant-department** | Implicit unit: S1 §C maps plant × department; S2 rows put each employee in a location + department pair | S1 §C, S2 | 84 (S1); 86 in S2 incl. Mumbai/Visakhapatnam | Confirmed (source) |
| Section / shop / line / team / shift | Not present as a column. Some "departments" look like shops (see §4.3). | — | 0 | Confirmed (source) / Inferred |

The only hierarchy the data shows is two levels: **Plant/Location → Department**. S1's design puts departments in a shared list, linked to plants through a many-to-many matrix. That is a matrix, not a strict tree. **Confirmed (source)**

### 3.2 Plants and locations

| Plant code (S1) | Plant name | S1 "Location" | In PMS scope | Employees (S2) | Departments mapped (S1 §C) |
|---|---|---|---|---|---|
| HO | KOLKATA | KOLKATA | Yes | 63 | 8 |
| SAL | SALAP | SALAP | Yes | 130 | 19 |
| KUL | KULGACHIA | KULGACHIA | Yes | 87 | 20 |
| BAG | BAGNAN | BAGNAN | Yes | 73 | 18 |
| GUJ | GUJARAT | GUJARAT | Yes | 86 | 19 |
| — | MUMBAI (S2 only) | — | — | 1 | — (not in S1) |
| — | VISAKHAPATNAM (S2 only) | — | — | 1 | — (not in S1) |
| | **Total** | | | **441** | **84** |

- "HO" (head office) is listed as a plant. Plant Name and Location are always identical. "GUJARAT" is a state name, not a site name. **Confirmed (source)**
- No addresses, site types, plant heads or effective dates are given. **Confirmed (source)**

### 3.3 Discovered tree (unit names only; employee counts from S2)

```text
(no company root in source)
├── KOLKATA [HO] (63)
│   ├── ACCOUNTS (14)        ├── EXPORT (10)        ├── GENERAL (2)       ├── HR-ADMIN (8)
│   ├── IT (3)               ├── MARKETING (22)     ├── PURCHASE (3)      └── SYSTEM SAP (1)
├── SALAP [SAL] (130)
│   ├── ACCOUNTS (7)   ├── CI (6)           ├── DI (26)          ├── DISPATCH (2)    ├── EXCELLENCE (1)
│   ├── FETTLING (2)   ├── FORKLIFT (7)     ├── GENERAL (2)      ├── HR-ADMIN (3)    ├── MAINTENANCE (19)
│   ├── MS (1)         ├── PAINT (6)        ├── PD (22)          ├── PPC (2)         ├── PROCESS (3)
│   ├── PURCHASE (1)   ├── QUALITY (17)     ├── SAFETY (2)       └── STORE (1)
├── KULGACHIA [KUL] (87)
│   ├── ACCOUNTS (3)   ├── DISPATCH (2)     ├── FARO (3)         ├── FETTLING (3)    ├── FORKLIFT (1)
│   ├── HR-ADMIN (4)   ├── LAB (2)          ├── MACHINESHOP (8)  ├── MAINTENANCE (11)├── MELTING (4)
│   ├── MOULDING (3)   ├── PAINT (5)        ├── PD (7)           ├── PPC (1)         ├── PROCESS (6)
│   ├── PRODUCTION (6) ├── PURCHASE (1)     ├── QUALITY (15)     ├── SAFETY (1)      └── STORE (1)
├── BAGNAN [BAG] (73)
│   ├── ACCOUNTS (2)   ├── DISPATCH (1)     ├── FARO (4)         ├── FETTLING (5)    ├── HR-ADMIN (3)
│   ├── LAB (1)        ├── MACHINESHOP (4)  ├── MAINTENANCE (8)  ├── MOULDING (1)    ├── PAINT (6)
│   ├── PD (8)         ├── PPC (1)          ├── PROCESS (4)      ├── PRODUCTION (7)  ├── PURCHASE (2)
│   ├── QUALITY (14)   ├── SAFETY (1)       └── STORE (1)
├── GUJARAT [GUJ] (86)
│   ├── ACCOUNTS (4)   ├── FETTLING (2)     ├── FORKLIFT (2)     ├── GENERAL (1)     ├── HR-ADMIN (2)
│   ├── IT (1)         ├── LAB (1)          ├── MACHINESHOP (5)  ├── MAINTENANCE (16)├── PATTERN (3)
│   ├── PD (4)         ├── PPC (1)          ├── PROCESS (1)      ├── PRODUCTION (20) ├── PRODUCTION - LFC (6)
│   ├── PURCHASE (1)   ├── QUALITY (14)     ├── SAFETY (1)       └── STORE (1)
├── MUMBAI (1)            [location in S2 only — not a plant in S1]
│   └── MARKETING (1)
├── VISAKHAPATNAM (1)     [location in S2 only — not a plant in S1]
│   └── MARKETING (1)
└── (departments defined in S1 §B with NO plant mapping and NO employees — 12)
    CNC · CORE SHOP · DRIVER · FURNACE · GRINDING · GUEST HOUSE · HOUSEKEEPING ·
    LEGAL · OPERATION · PEON · SHOT BLASTING · WEIGHING BRIDGE
```

The five functions (Accounts & Commercial; HR, Admin & IT; Operation; Purchase; Sales & BD) **cannot be placed in this tree from the source data**. No department-to-function link exists in any file (gap G-ORG-04). **Confirmed (source)**

---

## 4. Level analysis

### 4.1 Departments repeating across plants (S1 §C; every pair has at least one employee in S2)

| Plants | Departments |
|---|---|
| 5 of 5 | ACCOUNTS, HR-ADMIN, PURCHASE |
| 4 (all manufacturing plants: BAG, GUJ, KUL, SAL) | FETTLING, MAINTENANCE, PD, PPC, PROCESS, QUALITY, SAFETY, STORE |
| 3 | DISPATCH (BAG, KUL, SAL) · LAB (BAG, GUJ, KUL) · MACHINESHOP (BAG, GUJ, KUL) · PAINT (BAG, KUL, SAL) · PRODUCTION (BAG, GUJ, KUL) · FORKLIFT (GUJ, KUL, SAL) · GENERAL (GUJ, HO, SAL) |
| 2 | FARO (BAG, KUL) · MOULDING (BAG, KUL) · IT (GUJ, HO) |
| 1 | PATTERN, PRODUCTION - LFC (GUJ) · EXPORT, MARKETING, SYSTEM SAP (HO) · MELTING (KUL) · CI, DI, EXCELLENCE, MS (SAL) |

21 of the 31 used departments exist at two or more plants. **Inferred:** a name such as "MAINTENANCE" probably denotes a *separate unit per plant* (separate staff, separate location) and only shares the name. S1, however, deliberately models it as **one shared department record** ("Every department, once – not once per plant"; PMS reports "Department – Plant X" and "Department – All Plants"). How the LMS should represent this is **Pending confirmation** (G-ORG-05 / Q-48).

### 4.2 Codes and identifiers

| Item | Code present? | Format | Label |
|---|---|---|---|
| Plant | Yes (S1) | 2–3 letters: HO, SAL, KUL, BAG, GUJ | Confirmed (source) |
| Department | Yes (S1 only) | `DEPT001`–`DEPT043`, sequential, alphabetical by name except the last two (HOUSEKEEPING, LEGAL appended). Looks generated for the template, not an HR system code. | Confirmed (source) / Inferred |
| Plant-department | No own code; identified by the (plant code, department code) pair | — | Confirmed (source) |
| Designation | Yes (S1 only) | `DESG001`–`DESG266`. One code per (title, grade, level) **combination**, not per title (see §5). | Confirmed (source) |
| Location (S2) | No codes; names only | — | Confirmed (source) |
| Employee | Yes | Integer, 1–5 digits, unique in S2 | Confirmed (source) |

### 4.3 Department names that are not clearly "departments" (Inferred; all Pending confirmation)

| Pattern | Names | Observation |
|---|---|---|
| Collide with a function name | OPERATION, PURCHASE | OPERATION has no plant and no employees. PURCHASE exists at all 5 plants. Risk of confusing the *function* "Operation"/"Purchase" with a department of the same name. |
| Look like shops or process sections | CORE SHOP, FETTLING, FURNACE, GRINDING, MACHINESHOP, MELTING, MOULDING, PAINT, PATTERN, SHOT BLASTING, CNC | May be sections under PRODUCTION/PD. In S1 they are peers of PRODUCTION. |
| Look like job groups or service pools | DRIVER, PEON, FORKLIFT, WEIGHING BRIDGE, GUEST HOUSE, HOUSEKEEPING | DRIVER, PEON, WEIGHING BRIDGE, GUEST HOUSE and HOUSEKEEPING have no employees. FORKLIFT has 10 employees at 3 plants. |
| Unexplained abbreviations | CI, DI, MS, PD, PPC, FARO, LFC (in "PRODUCTION - LFC"), SYSTEM SAP, EXCELLENCE, GENERAL | Meanings not given in any source (Description = Name). They are not expanded here, so no meaning is invented. |
| Possible product lines | CI, DI (SALAP only) | Designations such as "DEPUTY GENERAL MANAGER – DI OPERATIONS" suggest business lines rather than departments. |

### 4.4 Missing parents, orphans and unclear relationships

- **Function parent missing for all 43 departments.** **Confirmed (source)**
- **12 orphan departments** in S1 §B: no plant mapping and no employees (list in §3.3). **Confirmed (source)**
- **2 locations** in S2 (MUMBAI, VISAKHAPATNAM), each with 1 MARKETING employee, are not plants in S1 and have no plant–department mapping. **Confirmed (source)**
- **No unit heads** anywhere: plant head, department head and plant-department head are all blank. **Confirmed (source)**
- **No effective dates** for any unit. **Confirmed (source)**
- **Reporting lines** are given by manager *name*. 72 rows (17 distinct manager names) cannot be matched to an employee in the file, and duplicate names make name matching ambiguous. **Confirmed (source)**

---

## 5. Occupational data (kept separate from organisation units)

| Attribute | S1 | S2 | Notes |
|---|---|---|---|
| **Designation** | 266 codes; **223 distinct titles** | 221 raw / 220 normalised titles | Each S2 title is in S1. S1 adds 3 titles with no employee: DESIGN ENGINEER, NPD DOCUMENTATION ENGINEER, PROCESS ENGINEER. |
| **Grade** | 20 codes | 20 codes (same set) | A2, A3, A4 · C2 · E1–E5 · G1, G2, G4 · M1–M5 · V1, V2, V4. Six letter families. S2 counts by family: E 217, M 114, A 82, G 18, V 7, C 3. |
| **Level** | 8 values | 8 values (same set) | L1–L7 plus a bare `L` (used only by C2 grade: the CFO, CHRO and COO titles). |
| Job family | — | — | **Absent.** |
| Functional role | §E empty | — | **Absent.** |
| Position | — | — | **Absent.** |
| Employment status | §F "Active?" = Yes ×7 | — | **No status column in S2.** |

**Grade ↔ level (S2, Inferred):** this is not a one-to-one relationship.
- One level: A2/A3/A4→L7; C2→L; E1→L6; G1/G2/G4→L2; V1/V2/V4→L1.
- Two levels: E2/E3→L5 or L6; E4/E5→L5 or L7; M1/M2→L4 or L5; M3/M4→L3 or L4; M5→L2 or L3.
- L1 holds the most senior titles (vice presidents) and L7 holds operators and associates. **Inferred:** L1 = most senior.

This supports keeping Grade and JobLevel as **independent lists** (Q-45).

**Designation code ≠ designation (Confirmed (source)):** 35 titles appear under 2–4 S1 codes that differ only in grade/level. For example, INSPECTOR QUALITY appears 4× with grades E2/E3/E4 and levels L5/L6, and OPERATOR CNC appears 3× with A3/A4/E4. Loading `DESG###` 1:1 as LMS designations would create duplicate titles.

**Same designation used in several departments (S2, Confirmed (source)):** 19 titles appear in more than one department. Examples:
- INSPECTOR QUALITY: QUALITY / PROCESS / CI
- SUPERVISOR MOULDING: MOULDING / DI / PRODUCTION / CI
- OPERATOR CNC: PD / MACHINESHOP
- INCHARGE STORE: STORE / ACCOUNTS

This is consistent with the LMS design: designation is separate from org unit, and functional roles are mapped per unit scope.

---

## 6. Data-quality issues

| # | Issue | Where | Extent | Label |
|---|---|---|---|---|
| DQ-01 | No function / sub-function in any filled source | S1, S2 | All 43 departments | Confirmed (source) |
| DQ-02 | Departments defined but unused/unmapped | S1 §B | 12 | Confirmed (source) |
| DQ-03 | Locations outside the plant list | S2 | MUMBAI, VISAKHAPATNAM (1 employee each) | Confirmed (source) |
| DQ-04 | Department casing/whitespace variants (e.g. "Quality"/"QUALITY", "MAINTENANCE "/"Maintenance", "SAFETY ") | S2 `Department` | 44 raw → 31 distinct; 146 cells affected (69 with whitespace) | Confirmed (source) |
| DQ-05 | Designation near-duplicates differing only by hyphen, en-dash (U+2013), spaces or case. Examples: OPERATOR - VMC / OPERATOR VMC, OPERATOR CORESHOP / OPERATOR CORE SHOP, SUPERVISOR PAINTSHOP / SUPERVISOR-PAINT SHOP, ASSISTANT MANAGER – ACCOUNTS / ASSISTANT MANAGER - ACCOUNTS | S1 §D | 16 pairs; 17 titles contain an en-dash; 5 titles in mixed case | Confirmed (source) |
| DQ-06 | Case variant of one designation | S2 | 1 pair | Confirmed (source) |
| DQ-07 | Designation code = title + grade + level combination | S1 §D | 266 codes vs 223 titles; 35 titles repeated | Confirmed (source) |
| DQ-08 | Incomplete level value `L` | S1 §D, S2 | 3 entries (C2 grade) | Confirmed (source) |
| DQ-09 | Reporting manager by name, not code; trailing spaces | S2 | 441 rows; 264 trailing spaces; 72 rows (17 names) unresolved | Confirmed (source) |
| DQ-10 | Duplicate employee names (different codes) | S2 | 4 names | Confirmed (source) |
| DQ-11 | Employee codes stored as numbers (any leading zeros lost; format not confirmed) | S1 §F, S2 | All | Confirmed (source) / Pending confirmation |
| DQ-12 | Joining date effectively blank (zero time value) | S2 `DOJ` | 2 | Confirmed (source) |
| DQ-13 | No employment status | S2 | All 441 | Confirmed (source) |
| DQ-14 | Name whitespace issues | S2 | 14 names, 4 designations | Confirmed (source) |
| DQ-15 | All heads/owners blank | S1 §A, §B, §C | All | Confirmed (source) |
| DQ-16 | No effective dates for units or assignments | S1, S2 | All | Confirmed (source) |
| DQ-17 | §E Unique roles empty | S1 | 0 rows | Confirmed (source) |
| DQ-18 | §F/§G contain real personal data, yet 2 rows are remarked "Fictional"; §G primary, effective date and manager are blank; the built-in check fails on all rows | S1 | 7 rows | Confirmed (source) |
| DQ-19 | HO listed as a "plant"; "GUJARAT" is a state name used as a site name; Plant Name = Location | S1 §A | — | Confirmed (source) |
| DQ-20 | Department description = name (no definitions); abbreviations unexplained | S1 §B | 43 | Confirmed (source) |
| DQ-21 | Personal data (names, work e-mails, joining dates) stored in a reference workbook | S1 §F, S2 | — | Confirmed (source). Never use these files as test fixtures (CLAUDE.md §5). |

No duplicate employee codes, no duplicate department codes or names, no duplicate plant–department pairs, and no references to undefined plant, department or designation codes were found. **Confirmed (source)**

---

## 7. Comparison with the existing LMS model and seed

### 7.1 Seeded baseline (migration `0005`) — verified

- **Unit types:** `FUNCTION` (Function, sort 10), `SUB_FUNCTION` (Sub-function, 20), `DEPARTMENT` (Department, 30). All have `allows_employee_assignment = true` and mode `advisory`. **Confirmed (source)**
- **Type rules:** root → FUNCTION; FUNCTION → SUB_FUNCTION; SUB_FUNCTION → DEPARTMENT; FUNCTION → DEPARTMENT. **Confirmed (source)**
- **Units:** `ACC_COM` Accounts & Commercial · `HR_ADMIN_IT` HR, Admin & IT · `OPERATION` Operation · `PURCHASE` Purchase · `SALES_BD` Sales & BD. All are roots with no dates. No plants, locations, departments or company root are seeded. **Confirmed (source)**
- The five functions match the previously established list exactly. **They do not appear in S1 or S2.** Their source is the Q-46 business confirmation, not these workbooks. **Confirmed (source)**

### 7.2 What the current model can already represent

| Need from the evidence | Model support | Verdict |
|---|---|---|
| New unit types (e.g. Plant) without code changes | `org_unit_type` is admin-configurable, with translations | Supported |
| Plant → Department or Function → Department rules | `org_unit_type_rule`, advisory/strict per child type | Supported (rules must be added; currently there is no PLANT type and no rule for it) |
| Same department name at several plants | `org_unit.name` is not unique; `code` is unique | Supported (plant-specific units need distinct codes, e.g. `SAL-MAINT`) |
| Physical sites (5 plants + 2 offices) | `location` table (code, name, address, city, state, PIN, country, TZ) | Supported. No site-type / "is plant" field; the design uses a Plant-type unit linked to a location. |
| A unit tied to a site | `org_unit.location_id` | Supported |
| An employee's site independent of the unit | `employee_assignment.location_id` | Supported |
| Effective dates and history | `org_unit` lifetime and effective-dated `org_unit_hierarchy` | Supported (source gives no dates; nullable = "not recorded") |
| Grades (20) and levels (8) as independent lists | `grade`, `job_level`, each with `rank` | Supported. No grade↔level mapping table, which is consistent with Q-45 being open. |
| Designations (≈220 titles) | `designation` (code, title, optional job family) | Supported. No grade on the designation; grade and level sit on the assignment, which fits S2. |
| Reporting lines | `reporting_relationship` (employee → manager employee, typed) | Supported, but the source gives **names**; codes must be resolved first. |
| Status not supplied | `employment_status` nullable ("not recorded") | Supported |
| Unit heads | No head field on units; can be modelled as a `Responsibility` with unit context, or a "Head of department" reporting type | Partially (design choice pending) |

### 7.3 What is missing or does not fit

1. **Matrix vs single parent.** S1 models Plant × Department as a many-to-many matrix with one shared department record. The LMS hierarchy allows **one open structural parent per unit**. The matrix therefore has to be materialised as **plant-specific department units** (84 + 2) under a single chosen parent. Alternatively, departments can be company-wide units with the plant held only in `location_id` on the assignment. Either way a business decision is needed (Q-48 / G-ORG-05). **Confirmed (source)** / **Pending confirmation**
2. **Function placement and plant placement compete.**
   - If plants are units (Plant → Department), the five functions cannot also be structural parents of the same departments.
   - If functions stay the roots (current seed), plants must be expressed through `location_id`, or by building a Function → Plant-department subtree. In that case a plant is not a single subtree.
   - Scope-based permissions (ADR-012) are *org unit + descendants*. A plant administrator scope therefore only works natively if the plant is a subtree. A **location-based scope** does not exist yet, so this is a C4 design gap. **Inferred**
3. **No PLANT (or SITE/OFFICE) unit type** is seeded and there is no rule for one. Adding it is configuration plus data, not a schema change. **Confirmed (source)**
4. **No department → function link** exists in any source. The seeded FUNCTION → DEPARTMENT rule cannot be populated from the evidence. **Confirmed (source)**
5. **No alias/mapping table** is needed for loading S1 department names (they are clean). S2 department and designation variants, however, need the reviewed alias mapping planned for Stage D (ADR-053). **Inferred**

**Conclusion:** The existing schema (configurable unit types, advisory type rules, non-unique names, `location`, `org_unit.location_id`, `assignment.location_id`, effective dating, independent grade/level lists) is **sufficient to store** what the sources contain, with no schema change. What is missing is **decisions and data, not tables**:
- a PLANT-type and/or rules (configuration);
- the plant-vs-function placement (Q-48);
- department→function mapping (G-ORG-04);
- per-plant department representation (G-ORG-05);
- a future location-based permission scope if plants are not subtrees (C4).

---

## 8. Recommended initial unit types and type rules (Proposed — not to be loaded until the decisions in §9 are made)

| Type code | Name | Assignable | Evidence | Label |
|---|---|---|---|---|
| `FUNCTION` | Function | Advisory: no direct assignments expected | Seeded (Q-46); absent from sources | Confirmed (source) — existing |
| `SUB_FUNCTION` | Sub-function | — | No evidence in any source; keep, but do not populate | Confirmed (source) — existing; usage Pending confirmation (Q-47) |
| `DEPARTMENT` | Department | Yes | 43 defined / 31 used, 84 plant pairs | Confirmed (source) — existing |
| `PLANT` | Plant / Site | Optional (head-office staff may sit directly) | 5 plants in S1 §A; HO included | **Proposed** (Pending confirmation Q-48) |
| `OFFICE` (or a location only) | Office / branch | — | MUMBAI, VISAKHAPATNAM (1 employee each) | **Proposed**: hold as `location` only until confirmed |
| `SECTION` / `SHOP` | Section / Shop | Yes | No explicit evidence; shop-like department names (§4.3) | **Do not create yet** — Pending confirmation (Q-27 / G-ORG-06) |

**Rule options (Proposed; choose one under Q-48):**

| Option | Tree shape | Rules to add | Pros | Cons |
|---|---|---|---|---|
| **A. Function-first, plant as attribute** | Function → Department (plant-specific unit, `location_id` = plant) | none beyond the seed; locations for 5 plants + 2 offices | Keeps the confirmed seed; matches the current default in Q-48 | A plant is not a subtree, so plant-scoped admins need location scoping (C4); the department→function map is still missing |
| **B. Plant-first** | Plant → Department (plant-specific) | root → PLANT; PLANT → DEPARTMENT | Mirrors S1 §C and S2 exactly; plant scopes work natively | Functions become a parallel classification, not structural parents |
| **C. Function → Plant → Department** | Function → Plant-in-function → Department | FUNCTION → PLANT; PLANT → DEPARTMENT | Both in one tree | Plant units duplicated per function (up to 5 × 5); unsupported by any source |

Keep `parent_rule_mode = advisory` during the first load, because the evidence has gaps. Switch to strict only after the structure is approved. **Proposed**

**Candidate department → function hints for stakeholder review (Inferred from names only, NOT for loading):**
- MARKETING, EXPORT → Sales & BD *(2026-11-23: the competency library instead places
  "Export Documentation & Logistics" and "Stores & Inventory" under Accounts & Commercial.
  See the classified hierarchy in §10.5, which supersedes these hints.)*
- ACCOUNTS → Accounts & Commercial
- HR-ADMIN, IT, SYSTEM SAP → HR, Admin & IT
- PURCHASE → Purchase
- Production, quality and shop departments → Operation
- No hint: GENERAL, SAFETY, STORE, DISPATCH, LEGAL, EXCELLENCE, PPC, the service pools, and every abbreviation.

---

## 9. Open decisions

| # | Decision needed | Evidence | Options / note | Owner (suggested) | Label |
|---|---|---|---|---|---|
| OD-01 | Which filled file is authoritative: S1 (PMS template) or S2 (HR extract)? Is S2 the user's "second template"? | §1, §10 | S1 derived from S2; S2 has full population. **2026-11-23:** S2 authorised by the user as a supplemental reference; which file is authoritative is still open. | HR / LMS owner | Pending confirmation (authority only) |
| OD-02 | Where plants sit relative to functions | §7.3, §8 | Options A / B / C | Management (Q-48, BD-01) | Pending confirmation |
| OD-03 | Is each plant's department a separate unit, or one company-wide department? | §4.1 | S1 says shared list; LMS needs one parent per unit | HR (G-ORG-05) | Pending confirmation |
| OD-04 | Department → function (and sub-function) mapping for all departments | §3.3, §4.4 | Hints in §8 are inferred only | HR + function heads (G-ORG-04, Q-47) | Pending confirmation |
| OD-05 | Status of the 12 departments with no plant and no employees (incl. OPERATION, LEGAL, HOUSEKEEPING) | §3.3 | Create inactive / omit / map | HR | Pending confirmation |
| OD-06 | Are MUMBAI and VISAKHAPATNAM offices, sales locations, or errors? | §3.2 | Location only vs unit | HR / Sales | Pending confirmation |
| OD-07 | Is HO (KOLKATA) a "plant" or a head-office unit type? | §3.2 | Separate type vs PLANT | HR | Pending confirmation |
| OD-08 | Are shop-like names (MELTING, MOULDING, FETTLING, PAINT, CORE SHOP…) departments or sections? Are DRIVER, PEON, FORKLIFT, WEIGHING BRIDGE departments or job groups? | §4.3 | Section type vs department vs functional role | Plant HR / Operations (Q-27, G-ORG-06) | Pending confirmation |
| OD-09 | Meanings of CI, DI, MS, PD, PPC, FARO, LFC, GENERAL, EXCELLENCE, SYSTEM SAP | §4.3 | Needed for names and translations | HR | Pending confirmation |
| OD-10 | Canonical designation list (merge 16 punctuation/case pairs?) and whether the `DESG###` codes are used anywhere | §5, DQ-05/07 | Titles as designations; grade/level on assignment (Proposed) | HR (Q-53) | Pending confirmation |
| OD-11 | Grade ↔ level relationship, order and names; meaning of bare `L` for C2 | §5 | Keep independent lists (Proposed) | HR (Q-45) | Pending confirmation |
| OD-12 | Employee code format (numeric only? leading zeros? contract series?) | DQ-11 | Store as text | HR (G-EMP-03) | Pending confirmation |
| OD-13 | Reporting manager by employee code, with effective date | DQ-09 | Resolve 17 unmatched names | HR (G-EMP-05) | Pending confirmation |
| OD-14 | Employment status and joining dates for all employees | DQ-12/13 | — | HR (G-EMP-04/07) | Pending confirmation |
| OD-15 | Unit heads (plant, department, plant-department) and how to model them | DQ-15 | Responsibility with unit context vs reporting type | HR (G-ORG-07) | Pending confirmation |
| OD-16 | Baseline effective date for the initial structure load | DQ-16 | One agreed baseline date vs NULL "not recorded" | HR / LMS owner (G-ORG-08) | Pending confirmation |
| OD-17 | Location-based permission scope if plants are not subtrees | §7.3 | C4 design item | LMS architecture | Proposed |
| OD-18 | Handling of personal data in S1 §F/G and S2 (remove from shared reference folders; secure channel) | DQ-21 | — | HR / IT | Proposed |

---

## 10. Source A vs Source B reconciliation (re-verified 2026-11-23)

**Source A** = S1, `LMS Data Reference/Organization Hierarchy Template Filled.xlsx`.
**Source B** = S2, `Desktop\CF Files\PMS Portal Docs\Organization Structure.xlsx`. The user
authorised Source B on 2026-11-23 as an **authorised supplemental company reference**. The
authorisation covers this named file only, not the rest of `CF Files`.

Both files were opened read-only with openpyxl, in both `data_only=False` and `data_only=True`
modes, and were never saved. The scripts are kept in a session scratchpad outside the
repository. No personal data is reproduced here.

### 10.1 Workbook structure (all sheets, including hidden)

| | Source A | Source B |
|---|---|---|
| Sheets | 1: `03 Org & Employee` (visible, A1:L540, 37 merged ranges). No hidden sheets. | 1: `Sheet1` (visible, A1:I442, auto-filter A1:I442). No hidden sheets. |
| Formulas | 32, all the §G check in J509:J540: `=IF(A509="","",IF(COUNTIFS($A$509:$A$540,A509,$E$509:$E$540,"Primary",$G$509:$G$540,"")<>1,"Primary count not 1",…` | None |
| Data validations | 5: list `L_YesNo` (D10:D14, C77:C160, F475:F499); list `L_AssignType` (E509:E540); date ≥ 2000-01-01 (D475:E499, F509:G540); whole ≥ 0 (F445:F465); decimal ≥ 0 (I509:I540) | None |
| Defined names / external links | 20 list names (`L_YesNo`, `L_AssignType`, `L_Dept`, …). Every one points to `[1]Lists!…` in an **external** workbook, `../CF Projects/PMS/docs/data-gap-assessment/PMS Data Gap Assessment.xlsx`. The list validations depend on that file, which was not opened. | None |
| Provenance (file properties) | Created 2026-11-19, modified 2026-11-23, 44,298 bytes | Created 2026-10-27, modified 2026-11-10, 41,793 bytes |
| Codes | Plant codes (HO, SAL, KUL, BAG, GUJ), `DEPT001–043`, `DESG001–266` | **No unit or designation codes.** Names only, plus numeric employee codes. |
| Function / sub-function / section columns | None | None |

### 10.2 Record-level comparison — plants / locations

| Plant (A code) | Source A (`03 Org & Employee`) | Source B (`Sheet1` col C) | Finding |
|---|---|---|---|
| HO | A10: `HO` / `KOLKATA`, Location `KOLKATA`, In scope `Yes`; 8 dept mappings in §C | `KOLKATA` — 63 rows (first C2) | In both (name match; B has no codes) |
| SAL | A11: `SAL` / `SALAP`, Location `SALAP`, In scope `Yes`; 19 dept mappings in §C | `SALAP` — 130 rows (first C6) | In both (name match; B has no codes) |
| KUL | A12: `KUL` / `KULGACHIA`, Location `KULGACHIA`, In scope `Yes`; 20 dept mappings in §C | `KULGACHIA` — 87 rows (first C4) | In both (name match; B has no codes) |
| BAG | A13: `BAG` / `BAGNAN`, Location `BAGNAN`, In scope `Yes`; 18 dept mappings in §C | `BAGNAN` — 73 rows (first C3) | In both (name match; B has no codes) |
| GUJ | A14: `GUJ` / `GUJARAT`, Location `GUJARAT`, In scope `Yes`; 19 dept mappings in §C | `GUJARAT` — 86 rows (first C12) | In both (name match; B has no codes) |
| — | absent | `MUMBAI` — 1 row (C289), dept MARKETING | Only B |
| — | absent | `VISAKHAPATNAM` — 1 row (C190), dept MARKETING | Only B |

### 10.2a Record-level comparison — departments

| Dept code (A) | Name | Source A §B row / §C plants (rows) | Source B: plants (employee rows), raw spelling variants, first row | Finding |
|---|---|---|---|---|
| DEPT001 | ACCOUNTS | A25; BAG, GUJ, HO, KUL, SAL (rows 77,95,114,122,142) | BAG 2, GUJ 4, HO 14, KUL 3, SAL 7; 2 variant(s); first D9 | In both; plant set identical |
| DEPT002 | CI | A26; SAL (rows 143) | SAL 6; 1 variant(s); first D369 | In both; plant set identical |
| DEPT003 | CNC | A27; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT004 | CORE SHOP | A28; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT005 | DI | A29; SAL (rows 144) | SAL 26; 1 variant(s); first D13 | In both; plant set identical |
| DEPT006 | DISPATCH | A30; BAG, KUL, SAL (rows 78,123,145) | BAG 1, KUL 2, SAL 2; 1 variant(s); first D7 | In both; plant set identical |
| DEPT007 | DRIVER | A31; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT008 | EXCELLENCE | A32; SAL (rows 146) | SAL 1; 1 variant(s); first D217 | In both; plant set identical |
| DEPT009 | EXPORT | A33; HO (rows 115) | HO 10; 1 variant(s); first D93 | In both; plant set identical |
| DEPT010 | FARO | A34; BAG, KUL (rows 79,124) | BAG 4, KUL 3; 1 variant(s); first D23 | In both; plant set identical |
| DEPT011 | FETTLING | A35; BAG, GUJ, KUL, SAL (rows 80,96,125,147) | BAG 5, GUJ 2, KUL 3, SAL 2; 2 variant(s); first D12 | In both; plant set identical |
| DEPT012 | FORKLIFT | A36; GUJ, KUL, SAL (rows 97,126,148) | GUJ 2, KUL 1, SAL 7; 2 variant(s); first D96 | In both; plant set identical |
| DEPT013 | FURNACE | A37; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT014 | GENERAL | A38; GUJ, HO, SAL (rows 98,116,149) | GUJ 1, HO 2, SAL 2; 2 variant(s); first D11 | In both; plant set identical |
| DEPT015 | GRINDING | A39; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT016 | GUEST HOUSE | A40; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT017 | HR-ADMIN | A41; BAG, GUJ, HO, KUL, SAL (rows 81,99,117,127,150) | BAG 3, GUJ 2, HO 8, KUL 4, SAL 3; 1 variant(s); first D16 | In both; plant set identical |
| DEPT018 | IT | A42; GUJ, HO (rows 100,118) | GUJ 1, HO 3; 1 variant(s); first D135 | In both; plant set identical |
| DEPT019 | LAB | A43; BAG, GUJ, KUL (rows 82,101,128) | BAG 1, GUJ 1, KUL 2; 2 variant(s); first D45 | In both; plant set identical |
| DEPT020 | MACHINESHOP | A44; BAG, GUJ, KUL (rows 83,102,129) | BAG 4, GUJ 5, KUL 8; 2 variant(s); first D67 | In both; plant set identical |
| DEPT021 | MAINTENANCE | A45; BAG, GUJ, KUL, SAL (rows 84,103,130,151) | BAG 8, GUJ 16, KUL 11, SAL 19; 2 variant(s); first D8 | In both; plant set identical |
| DEPT022 | MARKETING | A46; HO (rows 119) | HO 22, MUMBAI 1, VISAKHAPATNAM 1; 1 variant(s); first D2 | In both; B adds VISAKHAPATNAM,MUMBAI |
| DEPT023 | MELTING | A47; KUL (rows 131) | KUL 4; 1 variant(s); first D4 | In both; plant set identical |
| DEPT024 | MOULDING | A48; BAG, KUL (rows 85,132) | BAG 1, KUL 3; 1 variant(s); first D28 | In both; plant set identical |
| DEPT025 | MS | A49; SAL (rows 152) | SAL 1; 1 variant(s); first D6 | In both; plant set identical |
| DEPT026 | OPERATION | A50; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT027 | PAINT | A51; BAG, KUL, SAL (rows 86,133,153) | BAG 6, KUL 5, SAL 6; 1 variant(s); first D10 | In both; plant set identical |
| DEPT028 | PATTERN | A52; GUJ (rows 104) | GUJ 3; 1 variant(s); first D143 | In both; plant set identical |
| DEPT029 | PD | A53; BAG, GUJ, KUL, SAL (rows 87,105,134,154) | BAG 8, GUJ 4, KUL 7, SAL 22; 1 variant(s); first D22 | In both; plant set identical |
| DEPT030 | PEON | A54; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT031 | PPC | A55; BAG, GUJ, KUL, SAL (rows 88,106,135,155) | BAG 1, GUJ 1, KUL 1, SAL 2; 1 variant(s); first D18 | In both; plant set identical |
| DEPT032 | PROCESS | A56; BAG, GUJ, KUL, SAL (rows 89,107,136,156) | BAG 4, GUJ 1, KUL 6, SAL 3; 2 variant(s); first D21 | In both; plant set identical |
| DEPT033 | PRODUCTION | A57; BAG, GUJ, KUL (rows 90,108,137) | BAG 7, GUJ 20, KUL 6; 2 variant(s); first D46 | In both; plant set identical |
| DEPT034 | PRODUCTION - LFC | A58; GUJ (rows 109) | GUJ 6; 1 variant(s); first D39 | In both; plant set identical |
| DEPT035 | PURCHASE | A59; BAG, GUJ, HO, KUL, SAL (rows 91,110,120,138,157) | BAG 2, GUJ 1, HO 3, KUL 1, SAL 1; 2 variant(s); first D29 | In both; plant set identical |
| DEPT036 | QUALITY | A60; BAG, GUJ, KUL, SAL (rows 92,111,139,158) | BAG 14, GUJ 14, KUL 15, SAL 17; 2 variant(s); first D3 | In both; plant set identical |
| DEPT037 | SAFETY | A61; BAG, GUJ, KUL, SAL (rows 93,112,140,159) | BAG 1, GUJ 1, KUL 1, SAL 2; 2 variant(s); first D90 | In both; plant set identical |
| DEPT038 | SHOT BLASTING | A62; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT039 | STORE | A63; BAG, GUJ, KUL, SAL (rows 94,113,141,160) | BAG 1, GUJ 1, KUL 1, SAL 1; 2 variant(s); first D79 | In both; plant set identical |
| DEPT040 | SYSTEM SAP | A64; HO (rows 121) | HO 1; 1 variant(s); first D368 | In both; plant set identical |
| DEPT041 | WEIGHING BRIDGE | A65; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT042 | HOUSEKEEPING | A66; — (none) | absent | Only A (no plant mapping, no employees) |
| DEPT043 | LEGAL | A67; — (none) | absent | Only A (no plant mapping, no employees) |

**Plant–department pairs.** Source A §C has **84** pairs (rows 77–160, all `Active? = Yes`).
Source B has **86** distinct (location, normalised department) pairs. All 84 Source A pairs
appear in Source B. The extra 2 are MUMBAI–MARKETING and VISAKHAPATNAM–MARKETING. Every Source A
pair has at least one employee in Source B.

**Designations.** Source A §D has 266 codes (rows 170–437) covering 223 normalised titles.
Source B has 263 distinct (title, grade, level) combinations, and **all 263 exist in Source A**.
Source A adds 3 combinations that no Source B employee holds:
- DESIGN ENGINEER E4/L5
- NPD DOCUMENTATION ENGINEER E4/L5
- PROCESS ENGINEER E2/L6

Grades (20 codes) and levels (L1–L7 plus `L`) are the same set in both files. Neither file maps
a designation to a department or a function.

### 10.3 Lists

**In both**
- 5 plants: KOLKATA/HO, SALAP, KULGACHIA, BAGNAN, GUJARAT
- 31 departments
- 84 plant–department pairs
- 263 designation/grade/level combinations
- 20 grades and 8 level values

**Only in A**
- 12 departments with no plant and no employees: CNC, CORE SHOP, DRIVER, FURNACE, GRINDING, GUEST HOUSE, HOUSEKEEPING, LEGAL, OPERATION, PEON, SHOT BLASTING, WEIGHING BRIDGE
- The 3 designation combinations listed above
- Every code (plant, department, designation)
- The §E–§G structures

**Only in B**
- Locations MUMBAI (row 289) and VISAKHAPATNAM (row 190), each with 1 MARKETING row
- 13 case/whitespace spelling variants of department names (44 raw → 31 normalised)
- Reporting-manager names, joining dates, and per-employee grade/level

**Same name, different code**
- Source B carries no unit codes, so no A-vs-B code conflict is possible.
- Within Source A, 35 designation titles have 2–4 `DESG` codes each (one per grade/level).
- Against the seed: the department `PURCHASE` is `DEPT035` but the function `Purchase` is `PURCHASE`. The department `OPERATION` is `DEPT026` but the function `Operation` is `OPERATION`.

**Same name, possibly different entity**
- (a) The departments OPERATION and PURCHASE vs the functions Operation and Purchase.
- (b) 21 department names occur at 2–5 plants (e.g. MAINTENANCE ×4, QUALITY ×4). They are probably separate units per plant (OD-03).
- (c) Plant name = location name, and GUJARAT is a state name (OD-07).
- (d) Training workbooks use different names for some departments:
  - "Production" for the Moulding department;
  - "Process Control" for PROCESS;
  - "NPD", which is not a department in A or B. It may or may not relate to the PD department or to the library prefix `PD-` (Product Development & Design).
- (e) The department MS (SAL) vs the library prefix `MS-` (Machine Shop). The only MS employee holds a fabrication title.

**Departments with unclear parent function:** 35 of 43, i.e. every department except the 8 class-2 links in §10.5. That includes all 13 class-4 departments.

**Plants with unclear parent:** all 5 plants and both extra locations. No source places a plant under a company root or a function (Q-48 / OD-02).

**Plant–department pairs found only in the training workbooks:** BAGNAN–Melting, BAGNAN–Forklift and BAGNAN–NPD.
- The matrix `Location` is "Bagnan" on every row, and the Bagnan consolidated calendar lists these three departments.
- None of the three is a BAG pair in A §C or in B.
- The matrices also include contract workers, who are not among Source B's 441 rows.

### 10.4 The five top-level functions — exact spelling

| Seed `0005` (lines 84–88): code / name | Source A | Source B | TC Library (`CF Technical Competency Library.xlsx`) | Verdict |
|---|---|---|---|---|
| `ACC_COM` / `Accounts & Commercial` | 0 occurrences | 0 | `TC Library`!B (26 rows), `Read Me`!A7, `Coverage`!A12:A18; exact | Seed spelling confirmed by the library; absent from both org files |
| `HR_ADMIN_IT` / `HR, Admin & IT` | 0 | 0 | B (14 rows), `Read Me`!A6, Coverage A5:A11; exact | As above |
| `OPERATION` / `Operation` | Only as **department** `OPERATION` (B50/C50; no plant, no employees) and inside designation titles | Only inside designation titles ("… OPERATIONS") | B (106 rows), `Read Me`!A10, Coverage A28:A43; exact | As above. The department of the same name is a different entity. |
| `PURCHASE` / `Purchase` | Only as **department** `PURCHASE` (B59/C59; 5 plants) | Only as department value `PURCHASE` (some rows with a trailing space) | B (7 rows), `Read Me`!A9, Coverage A23:A27; exact | As above. The department of the same name is a different entity. |
| `SALES_BD` / `Sales & BD` | 0 | 0 | B (15 rows), `Read Me`!A8, Coverage A19:A22; exact | As above |

**Conclusion:**
- The five seeded names are spelled exactly as in the competency library. The library is the only reference file that uses functions.
- Neither organisation file has a function level.
- The seed's evidence therefore remains Q-46 (business confirmation), corroborated by the library.

### 10.5 Recommended hierarchy with classified links

Classes: **1** Directly confirmed · **2** Strongly supported by multiple records · **3** Inferred,
needs confirmation · **4** Unknown.

Nothing below has been loaded. Apart from the five seeded functions, every unit stays proposed
until HR confirms it.

| Link set | Links | Class 1 | Class 2 | Class 3 | Class 4 | Evidence |
|---|---|---|---|---|---|---|
| Root → Function | 5 | 5 | – | – | – | Seed 0005 lines 84–88 (Q-46); TC Library col B |
| Function → Sub-function (library taxonomy) | 34 | 32 | – | 2 | – | TC Library B/C rows 5–172; Read Me E6:E10; Coverage A5:B43 |
| Plant / location → parent | 7 | – | – | – | 7 | None in any source (Q-48) |
| Plant → Department (plant-specific unit) | 89 | 84 | – | 4 | 1 | A §C rows 77–160 plus B employee rows; B rows 190/289; training workbooks |
| Department → Function | 43 | – | 8 | 22 | 13 | Department placement table below |
| Department → Sub-function | 43 | – | 8 | 10 | 25 | Department placement table below |
| **Total** | **221** | **121** | **16** | **38** | **46** | |

**Function → Sub-function**
- **Class 1 (32):** sub-functions named identically in the TC Library and the Read Me.
- **Class 3 (2):** `Moulding` (the TC Library value has a trailing space: `"Moulding "`) and `Sand Plant`. The TC Library lists them separately; Read Me E10 and Coverage A30 combine them as "Moulding & Sand Plant".
- "Operation – common to all" is a competency group, not a unit, and is excluded.
- These sub-functions are competency-library groupings. Whether they become `SUB_FUNCTION` org units is Q-47.

**Department placement** (function and sub-function proposals; plants as in §10.2)

| Department(s) | Proposed function (class) | Proposed sub-function (class) | Evidence |
|---|---|---|---|
| MELTING · MOULDING · PAINT · PROCESS · FETTLING · MACHINESHOP · MAINTENANCE · QUALITY | Operation (**2**) | Melting · Moulding · Paint Shop · Process Control · Fettling & Finishing · Machine Shop · Maintenance · Quality – Inspection & QA (**2**) | Each has an A §B row, a same-name Operation sub-function in TC Library col C, and a Bagnan training workbook for that department. For Paint, Process, Moulding and Melting, the library's draft TCs are roll-ups of the matrix groups (doc 03 §8). The Process calendar's Department column reads "Process Control". |
| LAB · PATTERN · PPC · DISPATCH · SAFETY · CORE SHOP | Operation (3) | Lab & Metrology · Pattern & Tool Room · PPC, Dispatch & Material Handling (PPC and DISPATCH) · Safety & EHS · Core Shop (3) | Name match to a library sub-function only. Source B titles agree, e.g. LAB = chemists and SAFETY = safety officers. CORE SHOP has no plant and no employees. |
| FORKLIFT | Operation (3) | PPC, Dispatch & Material Handling (3) | Library PP-03 "Forklift & material movement" (candidate); Forklift workbook |
| FARO | Operation (3) | unknown (4): Process Control or Lab & Metrology | Source B titles include "INSPECTOR PROCESS CONTROL" and "ASSISTANT MANAGER FARO"; library LB-08 is a candidate |
| PRODUCTION · PRODUCTION - LFC · CI · DI · PD · MS · GENERAL | Operation (3) | unknown (4) | Source B titles only: production, melting and moulding supervisors (CI, DI); CNC, design and pattern (PD); fabrication (MS); COO and VP Operations (GENERAL). Coverage A43 has "Plant & operations management". |
| STORE · EXPORT | **Accounts & Commercial** (3) | Stores & Inventory · Export Documentation & Logistics (3) | The library places both under Accounts & Commercial. This **contradicts** the earlier name-only hint in §8 (EXPORT → Sales & BD). Source B titles for EXPORT include logistics roles. |
| ACCOUNTS | Accounts & Commercial (3) | unknown (4): generalist across AC-01..07 | Name; Coverage A18 "Accounts generalist" |
| HR-ADMIN · IT | HR, Admin & IT (3) | HR-ADMIN: unknown (4). IT: IT & Digital (3) | Name; Coverage A11 "HR generalist" |
| PURCHASE | Purchase (3) | unknown (4) | Name only. Same name as the function, but a different entity. |
| MARKETING | Sales & BD (3) | unknown (4) | Name only. The library has no "Marketing" sub-function. |
| EXCELLENCE · SYSTEM SAP · LEGAL · OPERATION · DRIVER · PEON · GUEST HOUSE · HOUSEKEEPING · WEIGHING BRIDGE · CNC · FURNACE · GRINDING · SHOT BLASTING | unknown (**4**) | unknown (4) | No supporting record. EXCELLENCE and SYSTEM SAP have 1 employee each; the rest have no plant and no employees. |

**Plant → department links**
- **Class 1 (84):** each pair is explicitly mapped in A §C (rows 77–160), and each has at least one Source B employee row. The per-plant lists are in §3.3.
- **Class 3 (4):**
  - MUMBAI → MARKETING (B row 289) and VISAKHAPATNAM → MARKETING (B row 190). Each rests on a single row, and the location is not a plant in A.
  - BAGNAN → Melting and BAGNAN → Forklift. These appear only in the training workbooks, not in A §C or B.
- **Class 4 (1):** BAGNAN → NPD. NPD is not a department in either organisation file.

**Items needing HR confirmation**
1. Where plants sit relative to functions (OD-02 / Q-48).
2. All 35 class-3 and class-4 department → function links. Two need particular attention:
   - STORE and EXPORT under Accounts & Commercial, as the library proposes;
   - the PURCHASE and OPERATION departments vs the functions of the same names.
3. Whether the 8 class-2 links may be loaded as proposed.
4. Whether library sub-functions become org units (Q-47), and whether Moulding and Sand Plant are split.
5. The status of MUMBAI and VISAKHAPATNAM (OD-06).
6. BAGNAN Melting, Forklift and NPD: the training workbooks disagree with the HR files.
7. The meaning of CI, DI, PD, MS, GENERAL, EXCELLENCE, FARO and LFC (OD-09).
8. The fate of the 12 unmapped departments (OD-05).
9. Whether per-plant departments are separate units (OD-03).

### 10.6 Grade bands vs the organisation files

The competency library defines its bands by grade (Read Me A22:B25):

| Band | Grades |
|---|---|
| L7 | A1–A6 |
| L6–L5 | E1–E5 |
| L4–L3 | M1–M5 |
| L2–L | G1–G4, V1–V4, C1–C4 |

The two org files do not always agree with this mapping:
- **Source B:** the band implied by **level** and the band implied by **grade** disagree on 17 of 441 rows: E4/L7 ×10, M1/L5 ×3, M2/L5 ×2, E5/L7 ×1 and M5/L2 ×1.
- **Source A §D:** they disagree on 13 of 266 rows.
- **Unused grades:** A1, A5, A6, G3, V3, C1, C3 and C4 fall within the library ranges but appear in neither org file.
- **Designations:** no file maps bands to designations.
