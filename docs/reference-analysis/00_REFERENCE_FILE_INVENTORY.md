# 00 — Reference File Inventory

| | |
|---|---|
| **Scope** | `D:\OneDrive - CRESCENT FOUNDRY CO. PVT. LTD\Desktop\CF Projects\LMS Data Reference` (the approved reference directory), plus the repository's own `docs/business-data-readiness/` workbooks for comparison |
| **Date** | 2026-11-23 |
| **Method** | Recursive listing; every file opened read-only and its file signature checked (ZIP `PK..` for Office files, `%PDF` for PDFs, JPEG `FFD8` for images). All 27 files were readable (OneDrive files were downloaded, not cloud-only placeholders). No source file was modified. |
| **Confidentiality** | The workbooks contain real employee data (names, codes, CTC in some skill matrices). None of it is reproduced in these documents, in code, in seed data or in test fixtures. |

## 1. Folder tree

```text
LMS Data Reference/                              4 folders, 27 files
├── CF Technical Competency Library.xlsx         competency library (3 sheets)
├── Organization Hierarchy Template Filled.xlsx  filled organisation template (1 sheet)
├── Certificate Designs/                         2 JPEG certificate designs
├── Existing LMS Details/                        8 .docx + 2 .pdf (current LMS = UpsideLMS)
└── Training Calendar/                           13 .xlsx calendars + skill matrices
```

## 2. Files and their purposes

| # | File | Type | Purpose (detail in) |
|---|---|---|---|
| 1 | `Organization Hierarchy Template Filled.xlsx` | xlsx, 1 sheet (`03 Org & Employee`, A1:L540) | PMS-style template: plants, department list, plant–department map, designations with grade/level, a few employee rows ([01](01_ORGANISATION_STRUCTURE_ANALYSIS.md)) |
| 2 | `CF Technical Competency Library.xlsx` | xlsx: Read Me, TC Library, Coverage | 168 technical competencies across the 5 functions, 1–4 scale, required level by grade band ([03](03_SKILL_MATRIX_AND_COMPETENCY_ANALYSIS.md)) |
| 3–15 | `Training Calendar/*.xlsx` (Bagnan_Safety, Bagnan, FARO, Fettling, Forklift, Machine Shop, Maintenance, Melting, Moulding, NPD, Paint Shop, Process, Quality — all `_2026-27`) | 13 xlsx, 61 sheets | Training calendars (staff and OJT), safety calendar, skill matrices (1–5 scale), development-plan nominations ([02](02_TRAINING_CALENDAR_AND_RECORDS_ANALYSIS.md), [03](03_SKILL_MATRIX_AND_COMPETENCY_ANALYSIS.md)) |
| 16–23 | `Existing LMS Details/*.docx` (Classroom training, Competency Module, Curriculum and learning path, E-learning contents, EVENT, LMS Implementation CF, Miscellaneous, Reports) | docx | How the current third-party LMS (**UpsideLMS**) works ([04](04_LMS_DOCUMENTATION_AND_CERTIFICATE_ANALYSIS.md)) |
| 24 | `Existing LMS Details/USER MANUAL LMS.pdf` | pdf | UpsideLMS learner & manager manual ([04](04_LMS_DOCUMENTATION_AND_CERTIFICATE_ANALYSIS.md)) |
| 25 | `Existing LMS Details/Crescent LMS — Initial Layouts.pdf` | pdf | Crescent's own proposed screens (compliance-first) ([04](04_LMS_DOCUMENTATION_AND_CERTIFICATE_ANALYSIS.md)) |
| 26–27 | `Certificate Designs/CF Certificate Design 1.jpg`, `…Design 2.jpg` | jpeg, 2000×1414 | Certificate of appreciation designs ([04](04_LMS_DOCUMENTATION_AND_CERTIFICATE_ANALYSIS.md)) |
| B | *Outside the reference folder:* `Desktop\CF Files\PMS Portal Docs\Organization Structure.xlsx` | xlsx, 1 sheet (`Sheet1`, A1:I442) | **Authorised supplemental company reference** (the user authorised this file only, 2026-11-23). Flat HR extract: 441 employees with location, department, designation, level, grade, joining date and reporting manager. See §3 and [01 §10](01_ORGANISATION_STRUCTURE_ANALYSIS.md). |

## 3. The "two filled organisation templates"

Only **one** filled organisation template exists inside the approved reference folder
(file 1). The repository's `docs/business-data-readiness/02_Excel_Templates/01_Crescent_LMS_Organisation_and_Employee_Master_Template.xlsx`
is a **blank** template (instructions and example rows only).

The organisation-analysis tool also opened a flat HR extract located **outside** the
approved workspace (`Desktop\CF Files\PMS Portal Docs\Organization Structure.xlsx`). This
was not authorised; nothing from it is used in code or data, and the findings that depend
on it are marked *Pending confirmation* in [01](01_ORGANISATION_STRUCTURE_ANALYSIS.md).
**Decision needed (D-01):** place the intended second template in `LMS Data Reference`, or
confirm that the HR extract is an authorised source.

> **Update 2026-11-23: access subsequently authorised.** The paragraph above is kept as history.
> On 2026-11-23 the user authorised exactly one file as an **authorised supplemental company
> reference**:
>
> | | |
> |---|---|
> | Path | `D:\OneDrive - CRESCENT FOUNDRY CO. PVT. LTD\Desktop\CF Files\PMS Portal Docs\Organization Structure.xlsx` ("Source B" / S2) |
> | Provenance | HR employee extract kept with the PMS portal documents. One sheet `Sheet1`, A1:I442, 441 employee rows. No formulas, validations or defined names. File properties: created 2026-10-27, modified 2026-11-10, 41,793 bytes. |
> | Scope of authorisation | This named file only. No other file or folder under `CF Files` or any PMS folder is authorised. They were not listed or opened during re-verification. |
> | Handling | Read-only. Contains personal data (names, joining dates, reporting managers), none of which is reproduced in the repository. |
>
> The A-vs-B reconciliation is in [01 §10](01_ORGANISATION_STRUCTURE_ANALYSIS.md). D-01 is now
> narrowed to *which file is authoritative*.

### 3.1 Re-verified counts (2026-11-23)

Recursive count of `LMS Data Reference`: **4 folders** (the root plus `Certificate Designs`,
`Existing LMS Details` and `Training Calendar`) and **27 files**, as stated in §1.

| Type | Count |
|---|---|
| .xlsx | 15 |
| .docx | 8 |
| .pdf | 2 |
| .jpg | 2 |

There are no skill-matrix workbooks as separate files. The 23 skill-matrix sheets are inside the
`Training Calendar` workbooks.

## 4. Readability limitations

- PDF pages could not be rendered as images (no `pdftoppm`); text was extracted and the
  embedded layout images were viewed directly. Mobile layout pages other than "Today" were
  analysed from text only.
- Several workbook formulas have stale or broken cached results (`#REF!`, ranges that stop
  short) — listed in [02](02_TRAINING_CALENDAR_AND_RECORDS_ANALYSIS.md) and [03](03_SKILL_MATRIX_AND_COMPETENCY_ANALYSIS.md).
  The Machine Shop workbook references an external file on a personal OneDrive that was not
  available; its dependent values were not recomputed.
