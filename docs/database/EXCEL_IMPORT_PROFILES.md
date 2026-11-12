# Excel Import Framework and Profiles

| | |
|---|---|
| **Status** | Design only (Stage A.1). **Nothing is implemented.** Framework and profile 1: Stage D; profiles 4–6: Stage E; profiles 2–3: Stage F ([roadmap](../LMS_IMPLEMENTATION_ROADMAP.md)). |
| **Owns** | The reusable import framework (pipeline, validation, duplicate candidates, provenance, preview, commit, history, security) and the six import profiles. Supersedes the import section of the Stage A organisation architecture. |
| **Labels** | **[C]** confirmed · **[P]** proposed · **[A]** assumption (register `Q-xx` in [product requirements §13](../product/LMS_PRODUCT_REQUIREMENTS.md)) · **[F]** future |
| **Requirements** | FR-IMP-001…013 in [product requirements §9](../product/LMS_PRODUCT_REQUIREMENTS.md) |
| **Tables** | [Database design §12](LMS_DATABASE_DESIGN.md) |

> **Important:** the source workbooks referred to in the Stage A.1 brief (Bagnan skill matrices, development plans, annual and safety calendars, attendance records) are **not in the repository workspace**. Layouts below are therefore **expected** layouts, marked **[A]**, and must be verified against the real files — using synthetic copies, never the originals, for development and tests.

---

## 1. Principles

1. **One framework, many profiles.** All Excel imports share one pipeline; each data type is a **profile** with its own mapping, validation and commit logic. **[C]**
2. **Nothing is written until an administrator confirms** a validated preview. **[C]**
3. **All or nothing.** A confirmed batch commits in one transaction. **[C]**
4. **Safe re-imports.** Importing the same file again changes nothing; importing an updated file changes only what changed. **[C]**
5. **Never discard potentially valid records** because they look similar to others; similar records become **duplicate candidates** for a human decision. **[C]**
6. **Provenance for every record**: file, sheet, row (and column for matrix cells). **[C]**
7. **Original values are preserved** where they carry meaning not yet confirmed (e.g. "Y", "US"). **[C]**
8. **Irrelevant and sensitive data is excluded at the door**: CTC and all compensation data are never stored — not in staging, not in logs. **[C]**
9. **Absence is not deletion.** Records missing from a file are never deleted or deactivated by default. **[C]** / default **[P]**

## 2. Framework concepts **[P]**

| Concept | Description |
|---|---|
| **Import profile** | A built-in import type (profiles 1–6) defining target entities, required fields, validation and commit order. |
| **Mapping profile** | A saved, versioned configuration for a source layout: sheet selection, header row, column → field mapping, wide-matrix settings, transforms, value mappings, excluded columns. Reusable across batches. |
| **Value mapping** | Maps source values to LMS values (e.g. `"Perm." → permanent`, `"4" → level 4`). Each mapping has a *confirmed* flag; unconfirmed mappings never change business meaning. |
| **Import batch** | One upload + its processing state, parameters (e.g. FY, as-of date, calendar scope), results and audit. |
| **Import row** | One parsed source row (or one unpivoted matrix cell) with normalised values and classification. |
| **Import issue** | A row/cell-level error or warning (code, severity, column, translated message). |
| **Duplicate candidate** | A suspected match between an incoming row and another row or an existing record, with similarity reasons and an administrator decision. |
| **Record provenance** | Link from a business record to the import row(s) that created, updated or confirmed it. |

## 3. Pipeline and states **[C]** / states **[P]**

```text
Upload ─► Inspect ─► Map ─► Parse & normalise ─► Validate ─► Match & detect duplicates ─► Diff
                                                                                             │
                                                    Resolve duplicate candidates (admin) ◄───┤
                                                                                             ▼
                                         Preview (dry run) ─► Administrator confirmation ─► Commit (one transaction) ─► Report
                                              │                                                 │
                                              └──► cancelled / expired                         ├──► committed
                                                                                                └──► failed (rolled back)
```

| State | Meaning |
|---|---|
| `uploaded` | File stored in protected storage; SHA-256 recorded; batch parameters captured. |
| `inspected` | Sheets, header rows and column headers detected; excluded columns identified. |
| `mapped` | Mapping profile applied/confirmed. |
| `validated` | Rows parsed, normalised and validated; issues recorded. |
| `matched` | Natural keys resolved; duplicate candidates generated. |
| `previewed` | Diff computed; summary available. **No business table has been written.** |
| `committing` → `committed` / `failed` | Single-transaction commit. |
| `cancelled` / `expired` | Cancelled, or preview stale/expired. |

A **dry run** is a batch taken to `previewed` and then cancelled; the preview and error report remain available in history. **[P]**

## 4. Mapping

### 4.1 Column mapping **[C]**

Users pick a saved mapping profile or map interactively; the system suggests matches from header names and saved **header aliases**. Transforms: trim, case, whitespace normalisation, date parsing (Excel serial dates, `dd-mm-yyyy`, `dd.mm.yy`, month names), number parsing, value mapping. **[P]**

### 4.2 Excluded and unmapped columns **[C]** / mechanism **[P]**

- **Unmapped columns are discarded at parse time.** Only mapped fields are stored in staging; for unmapped columns only the **header text** is recorded (never cell values), so administrators can see what was ignored.
- A **protected exclusion list** blocks compensation and other irrelevant sensitive data **even if someone tries to map it**: headers matching patterns such as *CTC, salary, gross, net pay, basic, HRA, allowance, wage, compensation, increment, bonus, bank, account no, IFSC, PAN, Aadhaar, UAN, PF no, ESI no* are dropped and flagged in the preview ("excluded: sensitive"). The list is configurable by system administrators only (additions freely; removals require an audited change).
- Personal data not needed by the LMS (e.g. date of birth, home address, personal phone) is excluded by default unless a documented purpose is approved. **[P]**; [A] Q-21

### 4.3 Wide matrices (unpivot) **[C]** / mechanism **[P]**

Some sources are **wide**: one row per employee and one column per skill (skill matrices), or one row per competency and one column per employee (development plans). A mapping profile declares:

- orientation (*entities in rows, attributes in columns* or the reverse);
- **identity columns/rows** (e.g. employee code, name) and **value columns/rows** (e.g. one per skill);
- header rows (including multi-row headers, e.g. a category row above skill names) and how merged header cells propagate;
- how header text maps to LMS entities (header aliases → competency skill).

Parsing **unpivots** each value cell into one import row `(employee, skill, raw value, sheet, row, column)`, so validation, provenance and errors work per cell.

### 4.4 Raw value preservation **[C]**

For fields whose source meaning is not yet confirmed, the raw source value is stored verbatim **on the business record** (not only in staging), alongside the optional mapped value. Current case: development-plan indicators such as "Y" and "US" (profile 3, [A] Q-01).

## 5. Validation layers **[C]** / layers **[P]**

Each issue records sheet, row, column, code, **severity** (`error` blocks commit, `warning` does not) and a translated message.

1. **Field** — required values, formats, dates, lengths, known enumerations, numeric ranges, period logic (`effective_to > effective_from`).
2. **Within file** — duplicate natural keys; conflicting rows; overlapping periods.
3. **Cross-sheet / cross-file** — references resolve to rows in the same workbook or to existing records.
4. **Against the database** — referenced records exist and are active; history rules respected.
5. **Profile rules** — specified per profile (§11–16).

## 6. Duplicate-candidate detection **[C]** / method **[P]**

| Kind | Example | Handling |
|---|---|---|
| **Exact key duplicate within a sheet** | Same employee code twice | Error (blocks commit) |
| **Conflict across files** | Same employee/skill with different levels in two departmental matrices | Duplicate candidate; admin chooses |
| **Probable duplicate record** | Different employee codes, same normalised name and joining date | Warning + candidate; never auto-merged |
| **Probable duplicate activity** | "Fire Safety Training" in the consolidated calendar and "Fire safety trg." in the Melting calendar, same month | Duplicate candidate; never auto-discarded |

Similarity uses several attributes together (normalised text with configurable synonyms/abbreviations, unit, period, duration, trainer, date) and records the **reasons** shown to the administrator. **Text similarity alone never removes a record.**

Administrator decisions per candidate: **same record** (link: one business record, multiple provenance links), **different records** (keep both), or **skip row** (with reason; the row stays in batch history). The default is *keep both*. Decisions are audited and can be **remembered** for future batches of the same source (e.g. this departmental line always equals that consolidated line). **[P]**

## 7. Change classification

| Class | Meaning |
|---|---|
| **New** | No matching record exists. |
| **Updated** | Matching record exists and at least one mapped field differs; preview shows *field: old → new*. |
| **Unchanged** | Matching record exists; all mapped fields equal. Re-importing an identical file yields only *unchanged* (and previously decided candidates). |
| **Duplicate candidate** | Awaiting or resolved administrator decision. |
| **Error** | Blocking issues. |
| **Skipped** | Blank/instruction rows, or skipped by decision. |

## 8. Preview, confirmation and commit **[C]** / mechanics **[P]**

- The preview shows counts per sheet and class, distinct unmapped values (e.g. all indicator values found, with counts), excluded columns, and row issues, in the user's language.
- **Commit is impossible** while blocking errors or unresolved duplicate candidates exist.
- Confirmation is an explicit action by a user with the profile's commit permission (`import.<profile>.commit`), separate from preview permission. Second approver: **[A] Q-31**.
- **Stale-preview check** before commit: target data unchanged since preview (record versions / data fingerprint) and preview not expired (default 24 h).
- **One transaction** per batch, in profile-defined dependency order; any failure rolls everything back and marks the batch `failed`.
- Effective-dated targets follow the change-vs-correction rules ([organisation architecture §5](../architecture/ORGANISATION_ARCHITECTURE.md)).
- Commits for the same profile and target scope are serialised.

## 9. Provenance, history, audit and error export **[C]** / mechanics **[P]**

- `import_batch`: uploader, confirmer, timestamps, file name, SHA-256, profile, mapping-profile version, parameters, counts, status.
- `import_row` / `import_issue` / `import_duplicate_candidate` retained per retention policy ([A] Q-21).
- **`record_provenance`** links every created/updated/confirmed business record to its import row(s) — so any value can be traced to file, sheet, row and column, and a record confirmed by two workbooks shows both.
- Every business change is also an audit-log entry referencing the batch.
- **Error export**: the original sheet layout (mapped columns only — never excluded columns) with added *Status* and *Issues* columns, for correction and re-upload. Cells beginning with `=`, `+`, `-`, `@` are neutralised to prevent formula injection.

## 10. Safety, security and repository policy **[C]** / controls **[P]**

- `.xlsx` only; reject macro-enabled (`.xlsm`), legacy `.xls` and content/extension mismatches. CSV may be added later for attendance devices. **[F]**
- Limits on file size, sheet count, rows and cells; `openpyxl` in read-only mode with hardened XML parsing (`defusedxml`) against zip bombs and XML attacks.
- Uploaded files are stored outside the web root with restricted access and deleted after the retention period.
- **Original workbooks and real employee data are never committed to Git.** Developers use synthetic workbooks that mimic layouts. Local copies of real files, if ever needed for layout analysis, stay in git-ignored folders (`private-data/`, `data/private/`, `data/imports/`) and are never used as test fixtures.
- Processing is synchronous for expected sizes; the state model allows moving validation/commit to background jobs later.

---

## 11. Profile 1 — Organisation and employees

| | |
|---|---|
| **Purpose** | Load and refresh organisation structure, roles and employees. **[C]** |
| **Targets** | Unit types, locations, org units, hierarchy links, job families, grades, designations, positions, **functional roles**, **responsibilities**, **designation→role mappings**, employees, employee assignments, employee functional roles, employee responsibilities, reporting relationships. |
| **Sources** | Standard LMS template or HR exports via mapping profiles. Source system: [A] Q-28. |

Standard template worksheets (any subset may be present) **[P]**:

| Worksheet | Natural key | Key columns (illustrative) |
|---|---|---|
| `UnitTypes` | type_code | name_en/bn/hi/gu, allowed_parent_type_codes |
| `Locations` | location_code | name, address, city, state, pin_code, country |
| `OrgUnits` | unit_code | name, type_code, parent_unit_code, location_code, effective_from |
| `JobFamilies` | job_family_code | name, parent_job_family_code |
| `Designations` | designation_code | title, job_family_code, grade_code |
| `Positions` | position_code | title, unit_code, designation_code, headcount |
| `FunctionalRoles` | role_code | name, job_family_code, owner_unit_code |
| `Responsibilities` | responsibility_code | name, category |
| `DesignationRoleMap` | designation_code + role_code + scope_unit_code + effective_from | scope_unit_code optional |
| `Employees` | employee_code | given_name, family_name, preferred_language, employment_type, date_of_joining |
| `Assignments` | employee_code + unit_code + effective_from | position_code, assignment_type, is_primary, effective_to |
| `EmployeeRoles` | employee_code + role_code + effective_from | is_primary |
| `EmployeeResponsibilities` | employee_code + responsibility_code + effective_from | context_unit_code |
| `Reporting` | employee_code + relationship_type + manager_code + effective_from | |

Profile rules **[P]**: hierarchy cycles checked on the **combined** existing + incoming graph; type rules per enforcement mode; one current primary assignment; no reporting cycles for hierarchical types; references resolvable within the workbook or database; probable-duplicate employees flagged (§6). Commit order: unit types → locations → units → hierarchy → job families → grades → designations → positions → functional roles → responsibilities → mappings → employees → assignments → employee roles/responsibilities → reporting.
**Excluded**: CTC and all compensation and banking/identity-number columns (§4.2). **[C]**

## 12. Profile 2 — Skill matrices (employee × skill)

| | |
|---|---|
| **Purpose** | Load employees' assessed competency levels from wide matrices (initially the Bagnan workbooks). **[C]** |
| **Targets** | Employee skill assessments (method *imported matrix*); optionally functional-role requirements if matrices carry required levels ([A] Q-03). |
| **Parameters** | Skill-level set (e.g. Bagnan 5-level), **as-of date**, source department/plant. |

Expected layout **[A] Q-03**: one row per employee (employee code, name, designation, department, …); one column per skill; possibly a category header row above skill names; cells contain numeric levels 1–5 (possibly with labels such as "3 - Can Work Independently").

Processing **[P]**:
- Identity columns + skill columns declared in the mapping profile; matrix unpivoted per cell (§4.3).
- Skill headers resolved via **header aliases → competency skill**. Unknown headers are errors for that column: an administrator maps them to an existing skill or creates the skill in the Control Room and re-runs — **skills are never created silently**.
- Cell values resolved against the skill's level set by numeric value or label. **Blank = not assessed.** Invalid values ("6", "NA", "-") produce issues; the raw value is retained in the import row.
- Employee code is required; a name mismatch against the employee record is a warning.

Re-import **[P]**: same employee + skill + as-of date + same level → unchanged; same as-of date, different level → update (correction, audited); new as-of date → a new assessment (history). Conflicting levels for the same employee/skill/as-of date across departmental files → duplicate candidate.

## 13. Profile 3 — Individual development plans (competency × employee)

| | |
|---|---|
| **Purpose** | Load development-plan matrices into employee development plans. **[C]** |
| **Targets** | Development plans (per employee and period) and plan items. |
| **Parameters** | Plan period (FY), source department/plant, skill-level set if levels are present. |

Expected layout **[A] Q-01, Q-03**: competencies in rows, employees in columns (or the reverse — orientation is a mapping setting); cells contain indicators such as **"Y"** and **"US"**; possibly current/target level columns.

Processing **[C]** / **[P]**:
- **Every indicator is stored verbatim** on the plan item (`source_indicator_raw`). Blank = no plan item.
- The preview lists **all distinct indicator values with counts**. A value mapping (indicator → intervention type/status) may be configured **only after the business confirms meanings**; until then items are *unclassified*. Unmapped values are never dropped.
- Competency headers resolved via aliases as in profile 2.

Re-import **[P]**: same employee + period + skill → update the raw indicator if changed (old value kept in provenance/audit); items absent from a new file are not deleted.

## 14. Profile 4 — Annual training calendars

| | |
|---|---|
| **Purpose** | Load FY training plans from consolidated and departmental workbooks. **[C]** |
| **Targets** | Training calendar (draft version) and planned training activities. **Never events or attendance.** **[C]** |
| **Parameters** | FY, calendar scope (company / location / department), source role (*consolidated* or *departmental*). |

Expected layout **[A] Q-04**: one row per programme/topic with department/target audience, trainer/faculty (internal/external), duration, planned participants, venue, and either planned dates or **month columns (April…March)** holding planned counts or marks. If month columns are used, each marked month becomes one planned activity occurrence.

Overlap handling **[C]** / **[P]**: consolidated and departmental workbooks overlap substantially. Each incoming line is matched against lines in the same batch, other batches for the same FY and existing activities using normalised title (with a configurable synonym/abbreviation list), department/unit, planned month, duration and trainer. Matches become **duplicate candidates** (§6) — *same activity* (one activity, provenance from both workbooks), *different activities*, or *skip*. **Similar names alone never discard a line.** Which workbook is authoritative is **[A] Q-04**; proposed default: departmental workbooks provide detail, the consolidated workbook defines the approved company view, and the administrator decides per FY.

Re-import **[P]**: lines matched by remembered decisions and keys are unchanged/updated; removed lines are reported, not deleted; publishing a calendar is a separate action.

## 15. Profile 5 — Safety training calendars

| | |
|---|---|
| **Purpose** | Load safety training plans. **[C]** |
| **Targets** | Calendar of type *safety* and planned activities; optional link of topics to **compliance skills**. |
| **Why separate** | Different layout and rules from general calendars; links to compliance. **[P]** |

Expected layout **[A] Q-05**: as profile 4, possibly with mandatory audience, statutory reference and frequency columns. Processing, overlap handling and re-import as profile 4. Topic → compliance-skill mapping is a confirmed value mapping; unmapped topics are imported unlinked.

## 16. Profile 6 — Event attendance and historical training records

| | |
|---|---|
| **Purpose** | (a) Upload attendance for LMS events; (b) load historical training records. **[C]** |
| **Targets** | (a) Attendance records (or attendance corrections if the event is finalised); (b) historical finalised events with attendance, or historical training records. |
| **Parameters** | (a) Target event (and session mapping); (b) period, source, grouping mode. |

**(a) Attendance upload** **[P]**: rows contain employee code, session date/time or session code, present/absent mark or status, optional in/out times or hours. Rules: employee must exist; session must belong to the event; duplicate employee/session rows are errors; attendees not nominated are flagged *walk-in*; uploads to a **finalised** event require correction permission and create audited correction records.

**(b) Historical records** **[P]**; layout **[A] Q-06**: rows with employee code, name, training title, date(s), hours, trainer/provider, location, internal/external, optional certificate number.
- If rows share title, date(s), location and trainer, the administrator may group them into **historical events** (status *finalised*, flagged *imported*) with attendance; otherwise each row becomes a **historical training record**. Grouping is a preview decision.
- Rows **without an employee code** are *unresolved*; the system may suggest matches, but **name-only matches always need administrator confirmation**.
- Possible duplicates of existing attendance or records (same employee, similar title, same date) are duplicate candidates — never auto-discarded.
- Source hours are preserved as given alongside computed hours.

## 17. Open questions

Q-01, Q-03, Q-04, Q-05, Q-06, Q-21, Q-28, Q-31 — see the [register](../product/LMS_PRODUCT_REQUIREMENTS.md).
