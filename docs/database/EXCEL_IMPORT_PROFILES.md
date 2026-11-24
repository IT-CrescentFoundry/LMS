# Excel Import Framework and Profiles

| | |
|---|---|
| **Status** | **Framework and profile 1 version 1 (employees, assignments, reporting lines) implemented in Stage D** — see §0 and §11.1. The rest of profile 1 (organisation and reference data), profiles 4–6 (Stage E) and profiles 2–3 (Stage F) remain design only ([roadmap](../LMS_IMPLEMENTATION_ROADMAP.md)). |
| **Owns** | The reusable import framework (pipeline, validation, duplicate candidates, provenance, preview, commit, history, security) and the six import profiles. Supersedes the import section of the Stage A organisation architecture. |
| **Labels** | **[C]** confirmed · **[P]** proposed · **[A]** assumption (register `Q-xx` in [product requirements §13](../product/LMS_PRODUCT_REQUIREMENTS.md)) · **[F]** future |
| **Requirements** | FR-IMP-001…013 in [product requirements §9](../product/LMS_PRODUCT_REQUIREMENTS.md) |
| **Tables** | [Database design §12](LMS_DATABASE_DESIGN.md) (migration 0010) · **API** [API reference §10](../architecture/API_REFERENCE.md) |

> **Important:** the source workbooks referred to in the Stage A.1 brief (Bagnan skill matrices, development plans, annual and safety calendars, attendance records) are **not in the repository workspace**. Layouts below are therefore **expected** layouts, marked **[A]**, and must be verified against the real files — using synthetic copies, never the originals, for development and tests.

---

## 0. Stage D implementation status

Stage D implemented the **framework** and **profile 1 version 1** (`employees` v1: employees, employee assignments and reporting lines). The code is in `LMS_Backend/app/services/imports/`, the tables are created by migration 0010, and the Import Control Room is at `/imports` in the frontend ([API reference §10](../architecture/API_REFERENCE.md)). Sections 1–10 remain the design for the whole framework; where the implementation differs, this section is authoritative.

| Design concept (§2–§10) | Stage D implementation |
|---|---|
| Import batch (`import_batch`) | `import_job`: profile code and version, status, file name (display only), SHA-256, size, detected workbook structure (header texts only), confirmed column mapping, summary counts, uploader, validator, committer, timestamps. |
| States (§3) | `uploaded` → `mapping_required` → `validating` → `validation_failed` \| `ready_for_approval` → `committing` → `completed` \| `completed_with_skips` \| `failed`; `cancelled` and `expired` close an open job. Inspection happens during upload; the design states *inspected / mapped / validated / matched / previewed* are collapsed into `mapping_required`, `validating` and `ready_for_approval`. The transition table is enforced in code (`jobs.TRANSITIONS`). |
| Mapping profile (saved, versioned) | **Not implemented [F].** Each job carries its own confirmed column mapping. Suggestions come from the profile's built-in header and sheet aliases, matched exactly after label normalisation (case, spacing, punctuation, `&` → `and`); there is no fuzzy header matching. |
| Value mapping (§2) | `import_value_mapping`: one current decision per kind and normalised label (`pending`, `approved`, `rejected`; withdrawn decisions are kept as `superseded`). Used for reference values (organisation unit, designation, location, grade, job level) only. Suggestions are ranked and shown, never applied. |
| Import row / import issue | `import_row` (one per sheet row and section: normalised values, mapped source text, outcome, change set, decision) and `import_issue` (code, severity, sheet, row, column, field, source value, parameters). |
| Duplicate candidate (§6) | No separate table. Exact duplicate keys in a file are errors (`duplicate_in_file`). A **probable duplicate** (different code, same normalised name and joining date, in the file or in the database) is a warning that **requires a decision**: *different person* (`distinct`) or *skip row* (with a reason). It is never merged. |
| Record provenance (§9) | `record_provenance`: target type and public ID, action (`created`, `updated`, `unchanged`), job and staged row; the row carries the section, sheet and row number, and the job the file name and hash. The rows API returns each staged row's `target_public_id`; there is no dedicated provenance screen yet. |
| Protected exclusion list (§4.2) | Built into the code (`profiles.EXCLUDED_HEADER_PATTERNS`); **not yet configurable** by administrators [F]. It covers compensation, bank, government identifiers, date of birth, gender, address, health, family and personal contact data. Excluded columns cannot be mapped. Only mapped cells are ever taken from a row: values of excluded columns are never copied into staging rows, issues, job records, audit events, logs or reports (verified end to end by `test_sensitive_values_never_reach_storage_logs_audit_or_reports`). The XML parser still reads each row (and the workbook's shared-strings table) in memory while streaming; nothing from it is kept. A sensitive column under an innocuous header (for example "Ref No" holding identity numbers) cannot be recognised — the template instructions tell users never to include such data. |
| Header row | Detected automatically in the first 10 rows (the row matching the most field aliases). **Choosing another header row is not supported** [F]: the API accepts only the detected row (`422 import_mapping_header_row`), because a data row chosen as the "header" would bypass the exclusion check on the real headers. |
| Error export (§9) | An `.xlsx` list of every issue (sheet, row, column, field, severity, code, source value), formula-neutralised. The design's "original layout with Status and Issues columns" is not implemented [F]. |
| Stale-preview check (§8) | The preview is valid for 24 hours, and becomes stale when any reference-mapping decision is made after validation (`409 import_revalidation_required`). The commit re-runs every row against current data, in one transaction: if a row now breaks a rule, **nothing is written** and the job ends `failed` with the commit-time issues; if a row would now do something other than the approved preview (for example an employee created on the screens since validation turns a *new* row into an *update*), **nothing is written**, the job stays `ready_for_approval` and must be validated again (`409 import_records_changed`). Approved changes are therefore never replaced by changes nobody reviewed. |
| Commit serialisation (§8) | All import commits are serialised by the `imports` graph lock, and then by the job row. |
| Permissions (§8) | `imports.view`, `imports.employees.run`, `imports.employees.commit` and `imports.mappings.manage` (migration 0010; HR Admin and Super Admin). The commit also requires the domain permissions it writes with (`employees.manage`, `reporting_lines.manage`). |
| Second approver (Q-31) | Not implemented (Q-31 open). The approval is one explicit action (`confirm: true`) by a user holding `imports.<profile>.commit` and the domain permissions; approving and committing are the same request. |
| Retention (Q-21) | Open (full retention rules are deferred). Uploaded files are kept only while a job is open; staging rows, issues and audit records are kept. See *Uploaded-file lifecycle* below. |
| Expiry | A job expires 7 days after upload (`LMS_IMPORT_JOB_EXPIRY_DAYS`). Every state-changing action (mapping, validation, row decisions, commit) refuses an overdue job (`409 import_job_expired`) even before it has been marked expired; viewing a job or the job list marks it `expired` and releases its file. |

**Uploaded-file lifecycle.** The database is the source of truth. When a job completes, fails, is cancelled or expires, its file is *released* (`file_stored = false`) in the same transaction as the new status, and deleted only after that transaction has committed. So a failed save leaves the job open **with** its workbook, never without it. A deletion that fails afterwards (for example a file locked by a virus scanner) leaves an orphan that housekeeping removes later. Housekeeping runs whenever the job list is opened (no background worker): it expires overdue jobs, returns abandoned validations to `mapping_required` (a job left in `validating` for 30 minutes, `LMS_IMPORT_VALIDATION_TIMEOUT_MINUTES`, because its request died), and deletes released files, files without a job and interrupted `.part` writes. Files without a job are deleted only after a one-hour grace period, because their upload may still be in progress; files with other names are never touched. If the database commit of an upload fails, the file just written is deleted at once. `committing` is never visible to other requests (it is set and replaced inside the one commit transaction), so an interrupted commit simply rolls back. These steps make the behaviour predictable and retryable; they do not make the file system and the database one atomic unit.

Safety controls implemented (§10): `.xlsx` only; OLE/encrypted/legacy files, macros (`vbaProject.bin`), unsafe ZIP entry names, too many entries, excessive expansion or compression ratio, and too many sheets, rows or columns are rejected before parsing; malformed workbook XML anywhere (structure, sheet data, merged ranges) is rejected as `422 file_corrupted`, never a server error; `openpyxl` read-only with cached values only (formulas are never evaluated, and a formula without a cached result is read as empty); hidden rows and merged cells are flagged; workbook XML is parsed with `defusedxml`; external links are not loaded. Files are stored outside the repository (`LMS_IMPORT_STORAGE_DIR`, default `%LOCALAPPDATA%\CrescentLMS\imports`), named by job ID, never by the uploaded name. Limits are settings (`LMS_IMPORT_MAX_*`).

**Processing time and limits (measured).** Processing is synchronous: validation and commit run the same domain services as the employee screens, row by row (about 15 SQL statements per row). In the synthetic volume test (2,000 employees, 2,000 assignments and 1,999 reporting lines = 5,999 rows, on the development PC's MySQL) validation took about 155 s and the commit about 178 s — roughly 25–30 ms per row. The browser waits at most 5 minutes for these requests, so one import is limited to **6,000 rows across all sections** (`LMS_IMPORT_MAX_ROWS_TOTAL`, `422 import_too_many_rows`); larger workbooks are split (for example employees first, then assignments and reporting lines). The per-sheet limit (`LMS_IMPORT_MAX_ROWS_PER_SHEET`, 20,000 rows including blanks) still bounds reading. A worker queue is not needed at this size; the state model allows one later if imports grow.

Business rules implemented (Stage D brief):

* **Employee codes** are text. Leading zeros are kept. A numeric cell is accepted only when its number format fixes the width (for example `00000`); otherwise it is an error (`employee_code_numeric`), because the original code cannot be known.
* **A missing employment status stays not recorded** (null); it never defaults to Active.
* **Dates are never guessed**: ISO, day-first (`dd-mm-yyyy`, `dd/mm/yyyy`, `dd.mm.yyyy`) and month names are accepted; two-digit years, bare numbers and date-times are errors.
* **Organisation units, designations and other reference data are never created** by an import. The five functions (Accounts & Commercial; HR, Admin & IT; Operation; Purchase; Sales & BD) are matched exactly. Unfamiliar labels go to the review queue with their original text preserved. Q-53 (the hierarchy below function level) remains open.
* **Missing managers are reported** (`manager_not_found`), never ignored.
* **Status changes and separations are never applied** by an import: they are reported as warnings (`status_change_not_applied`, `separation_not_applied`) and must be made on the employee screen, where the separation checks run.
* **Assignment history is never rewritten**: an assignment row that conflicts with existing history is an error (`assignment_conflicts_existing`).

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

### 11.1 Implemented: `employees` version 1 (Stage D)

Commit mode: **all or nothing, with explicit skips** — every row not explicitly skipped is committed in one transaction, or nothing is. Sections are committed in the order employees → assignments → reporting, so a workbook can create an employee and their assignment and manager together. One worksheet may be mapped as several sections (for example a flat HR export holding both employee and assignment columns).

| Section | Sheet aliases | Natural key | Fields (**required**) |
|---|---|---|---|
| `employees` | Employees, Employee, Employee Master, Employee List | employee_code | **employee_code**, **full_name**, display_name, preferred_language (en, bn, hi, gu or the language name), work_email, employment_status (Active, On Leave, Separated; blank = not recorded), date_of_joining, last_working_day, external_ref |
| `assignments` | Assignments, Assignment | employee_code + unit + assignment_type + effective_from | **employee_code**, assignment_type (primary, additional, acting, deputation; blank = primary), **unit**, designation, grade, level, location, **effective_from**, last_day (the last day in effect, inclusive) |
| `reporting` | Reporting, Reporting Lines, Managers | employee_code + effective_from | **employee_code**, **manager_code**, **effective_from** (line manager only) |

The standard template (`GET /imports/profiles/employees/template`) has these sheets with text-formatted code columns. Header aliases (for example *Emp Code*, *DOJ*, *Department*, *Plant*) are listed by `GET /imports/profiles`.

Validation layers, in order:

1. **File** (§10) and **structure**: header row detected (choosing another row is not supported in v1); required fields mapped; excluded columns refused; at most 6,000 rows per import.
2. **Field**: the normalisation rules above. Issue codes: `required`, `employee_code_invalid`, `employee_code_numeric`, `date_invalid`, `date_ambiguous`, `date_numeric`, `date_has_time`, `status_invalid`, `language_invalid`, `assignment_type_invalid`, `email_invalid`, `text_expected`, `value_too_long`, `last_day_before_start`, `last_working_day_requires_separated`, `separated_requires_last_working_day`; warnings `row_hidden`, `row_merged_cells`.
3. **Within the file**: `duplicate_in_file` (same natural key twice); `probable_duplicate` (warning, needs a decision); `depends_on_invalid_row` (for example an assignment whose employee row has errors).
4. **References**: `reference_unmapped` (the label has no code, exact unique name or approved mapping; a pending mapping is queued); `employee_not_found`; `manager_not_found`.
5. **Domain rules (dry run)**: every row is run through the same services as the manual screens (`create_employee`, `correct_employee`, `create_assignment`, `set_manager`) inside a transaction that is rolled back, so the codes are those of the [employee API](../architecture/API_REFERENCE.md) (for example `primary_overlap`, `outside_employment_period`, `reporting_cycle`, `unit_not_active`). Profile-specific: `assignment_conflicts_existing`, `reporting_conflicts_existing`; warnings `status_change_not_applied`, `separation_not_applied`.

Change classification: `new`, `update` (existing employee with differing correctable fields: name, display name, language, work email, joining date, external reference — applied only when the approver chooses *apply updates*, otherwise counted as skipped), `unchanged`, `error`, `skipped` (explicit decision; blank and repeated header rows are counted separately and not staged).

### 11.1a Implemented: `organisation` version 1 (first release, migration `0011`)

Sheet **Organisation Units** (aliases: Org Units, Units, Organisation Structure); one row per unit:
`Unit Code`* · `Unit Name`* · `Unit Type`* (type code or name) · `Parent Unit Code` · `Location Code` (code or name) · `Short Name` · `Effective From` · `External Reference`.

- New codes are **created** through the same service as the Organisation screens (unique codes, sibling-name rule, parent-type rules, active types/locations, hierarchy lock). Parents may be existing units or rows anywhere in the file (ordered automatically).
- An existing code with identical values is `unchanged` (re-uploading a file is harmless).
- *(Changed in the 2026-11-23 review; previously a blocking `existing_unit_differs` error.)* An existing code whose supplied values differ is an **`update`** row. The preview lists every difference (`from → to`; a parent change also shows its effective date). Updates are applied **only** when the approver ticks "apply the listed corrections" at commit; otherwise those rows are skipped and the units stay unchanged. Name, type, location, short name and external reference changes are audited corrections (`org_unit.corrected`, reason `Excel import <job>`); a different parent is an effective-dated move (`org_unit.moved`) from the commit's business date, so the previous placement stays in the unit's history. Blank optional cells never clear recorded values; start dates are never changed; an import never closes, reopens or deletes a unit (closing obsolete units is done on the Organisation screens, with an effective date and reason). The commit is still one transaction, refused if the data changed after the preview (`import_records_changed`).
- Other blocking issues: `unit_type_unknown`, `location_unknown`, `parent_not_found`, `parent_cycle_in_file`, `parent_row_failed`, `duplicate_in_file`, and any domain rule code. Advisory parent-rule findings are warnings.
- The filled company template (sections A–G in one sheet) cannot be uploaded as-is: an administrator copies the agreed units into the Organisation Units sheet after decisions D-02/D-03 ([open decisions](../reference-analysis/05_SOURCE_TO_SYSTEM_MAPPING_AND_OPEN_DECISIONS.md)).
- Permissions: `imports.organisation.run`; commit needs `imports.organisation.commit` **and** `organisation.manage`.

### 11.2 Not yet implemented

The remaining worksheets below (unit types, locations, organisation units, job families, designations, positions, functional roles, responsibilities, designation–role mappings, employee roles and responsibilities) are **not part of Stage D**. Organisation and reference data are maintained on the Organisation Builder screens; importing them depends on Q-47 and Q-53. Positions are not implemented at all.

### 11.3 Original design

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

Q-01, Q-03, Q-04, Q-05, Q-06, Q-21, Q-28, Q-31, Q-47, Q-53 — see the [register](../product/LMS_PRODUCT_REQUIREMENTS.md).
