# Organisation Architecture

| | |
|---|---|
| **Status** | Design document. Implemented so far: organisation structure and reference data (C1, C2) and the employee master with its screens (C3a, C3b); see §12. The Stage D import framework is complete (profile `employees` v1; organisation units are imported through profile `organisation` v1 from the first release). Positions and scoped permissions (C4) are not implemented. Revised in Stage A.1 (functional roles, responsibilities, access-role separation; import design moved to the import-profiles document). |
| **Stage** | Organisation core: Stage C. Organisation import (profile 1): Stage D. See [roadmap](../LMS_IMPLEMENTATION_ROADMAP.md). |
| **Labels** | **[C]** confirmed · **[P]** proposed · **[A]** assumption (register `Q-xx` in [product requirements §13](../product/LMS_PRODUCT_REQUIREMENTS.md)) · **[F]** future |
| **Related** | [Database design §5](../database/LMS_DATABASE_DESIGN.md) · [Import profiles](../database/EXCEL_IMPORT_PROFILES.md) (profile 1) · [System architecture](LMS_SYSTEM_ARCHITECTURE.md) · [Decisions](../decisions/ARCHITECTURAL_DECISIONS.md) (ADR-013, ADR-023, ADR-029) |

---

## 1. Purpose

Almost every LMS capability depends on knowing *who* an employee is, *where* they work and *what* they do:

- learning is allocated by department, position, designation, **functional role**, job family or **responsibility**;
- competency requirements attach to **functional roles**; compliance requirements attach to roles, responsibilities and locations;
- managers approve, monitor and assess their teams;
- plant and department administrators see only their own scope;
- reports aggregate by plant, department and section.

Crescent Foundry's structure is not fixed, will change over time, and is **not guaranteed to be complete** when first loaded. **[C]**

## 2. Design principles

1. **Configuration, not code.** No unit type, level count, department, plant, designation, functional role or reporting hierarchy is hardcoded. **[C]**
2. **Separate concepts stay separate**: organisational units and unit types; plants and locations; employees; designations and positions; job families; functional roles; responsibilities; reporting relationships; historical employee assignments. **[C]**
3. **Application access is not job function.** An employee's *access role* (what they may do in the LMS) is separate from their *functional role* (the work they do). **[C]**
4. **Incomplete data is normal.** The system records what is known and highlights gaps; it never invents placeholder data. **[C]** / approach **[P]**
5. **History is preserved** through effective dating; nothing is overwritten or hard-deleted. **[C]**
6. **Imports are safe** — validated, previewed, confirmed, transactional, repeatable and audited ([import profiles](../database/EXCEL_IMPORT_PROFILES.md)). **[C]**
7. **Security follows structure.** Plant/department scopes derive from the hierarchy (§9). **[C]**

## 3. Concept model **[P]**

```text
 OrgUnitType (+ type rules)                       Location (physical site)
        │ types                                        ▲ located at
        ▼                                              │
     OrgUnit ◄──── parent link (effective-dated) ── OrgUnit      e.g. Company › Plant › Department › Section
        ▲   ▲
        │   └──────────── Position ──► Designation ──► JobFamily ;  Designation ──► Grade (optional)
        │                    │              │
        │                    │              └──(designation→role mapping, optionally unit-scoped)──┐
        │                    └──(position→role mapping, optional)────────────────────────────────┐ │
        │                                                                                         ▼ ▼
        │   EmployeeAssignment (effective-dated)                                       FunctionalRole
        └──────────────┬───────────────────────────────────────────────────────────────▲
                       │                                                               │ EmployeeFunctionalRole
                    Employee ── EmployeeResponsibility (effective-dated) ──► Responsibility
                       │   │
                       │   └── ReportingRelationship (typed, effective-dated) ──► Employee (manager)
                       │
                       └── 0..1 ── UserAccount ── AccessRoleAssignment (scoped to OrgUnit) ──► AccessRole
                                    (identity domain)
```

## 4. Entities

### 4.1 Organisation unit types **[C]**

Types classify units and are created by administrators. Examples (illustrative, not seeded as fixed values): *Company, Business Unit, Location, Plant, Department, Sub-department, Section, Shop, Production Line, Cell, Team, Office*.

| Attribute | Notes |
|---|---|
| `code` | Stable unique identifier used by imports (e.g. `PLANT`). |
| `name` + translations | Display name in all supported languages. |
| `sort_order`, `is_active` | Ordering; inactive types cannot be used for new units. |
| `allows_employee_assignment` | Advisory flag (e.g. a "Company" may hold no direct assignments). |

**Hierarchy rules** (optional) restrict which type may sit under which (*(parent type, child type)* pairs; `NULL` parent = may be a root), with an enforcement mode: **advisory** (default while loading data; violations are warnings) or **strict** (violations rejected). **[P]** There is **no maximum depth**. **[C]**

### 4.2 Organisation units **[C]**

| Attribute | Notes |
|---|---|
| `code` | Unique business key (e.g. `P1-MELT`). |
| `name`, `short_name` + translations | |
| `unit_type_id` | Required. |
| `location_id` | Optional physical location. |
| `status` | `active` / `archived`. |
| `effective_from` / `effective_to` | The unit's lifetime. |
| `external_ref` | Identifier in a source system (HR export, PMS). |

Operations **[P]**: create/edit (as *correction* or effective-dated *change* — the UI asks which); **archive** (never delete; blocked while active children/assignments exist, with the blockers listed); **move** (close current parent link, open a new one); merge/split later as archive + create with a lineage link **[F]**.

### 4.3 Hierarchy **[C]** / storage **[P]**

Parent-child structure is stored as **effective-dated parent links**, so past structures can be reconstructed. Rules: at most one structural parent per unit at any time; multiple roots allowed; unplaced units valid and listed for resolution; cycles rejected (checked in the write transaction under row locks); type rules per enforcement mode. Queries use MySQL 8 recursive CTEs; a closure-table cache may be added only if profiling requires it (ADR-013).

### 4.4 Plants and locations **[C]** / modelling **[P]**

A **location** is a physical site (address, city, state, PIN code, country, time zone). A **plant** is an **org unit of a "Plant" type linked to a location**. Keeping them separate allows one location to host several units, one unit to span locations, and an employee's work location to differ from their unit's.

### 4.5 Job families, grades, designations and positions **[C]**

| Concept | Meaning | Example (illustrative) |
|---|---|---|
| **Job family** | Group of related work, independent of the org chart; optional parent. | *Melting & Pouring*, *Quality Assurance* |
| **Grade** (optional) | Pay/seniority band with a rank. [A] Q-30 | *G3* |
| **Designation** | Title / rank held by an employee; optional job family and grade. | *Senior Technician*, *Engineer* |
| **Position** | A specific role in a specific org unit, with designation, optional reporting position and headcount (can be pooled). | *Furnace Operator – Plant 1 Melting Shop* |

### 4.6 Functional roles **[C]**

A **functional role** describes the *work an employee performs* — and is what **competency requirements attach to** ([competency requirements](../product/COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md)). Illustrative examples: *Furnace Operator, Core Maker, Moulding Line Operator, Fettling Operator, Quality Inspector, Maintenance Electrician, Shift Supervisor*.

| Attribute | Notes |
|---|---|
| `code`, `name` + translations, `description` | |
| `job_family_id` | Optional grouping. |
| `owner_org_unit_id` | Department that owns the role definition (its SMEs maintain requirements). **[P]** |
| `status` | `active` / `retired`. |

Why separate from designation **[P]**: a designation (e.g. *Senior Technician*) is a rank that spans different kinds of work; the same designation means *Furnace Operator* in Melting and *Maintenance Electrician* in Maintenance. Functional roles express the work precisely; designations stay what HR records.

**Mappings** **[C]** / scoping **[P]**:

- **Designation → functional role** (effective-dated), optionally **scoped** to an org-unit subtree or unit type, so the same designation maps differently per department.
- **Position → functional role** (optional, more precise than designation).

**An employee's effective functional roles** (rule **[P]**) = explicit assignments ∪ roles derived from the current primary position mapping ∪ roles derived from the designation mapping within the employee's unit scope − explicit exclusions. Derived roles are recalculated when mappings or assignments change; manual assignments and exclusions persist. Source of the initial role catalogue and mappings: **[A] Q-23**.

### 4.7 Responsibilities **[C]**

A **responsibility** is a discrete duty assigned to an employee independently of their role — illustrative: *Fire Warden, First Aider, Permit-to-Work Issuer, Shift In-charge, Crane Operation*.

| Attribute | Notes |
|---|---|
| `code`, `name` + translations, `description` | |
| `category` | e.g. safety, statutory, operational. **[P]** |
| `status` | |

Responsibilities can drive **compliance requirements** and **learning allocations** (e.g. a First Aider must hold a valid first-aid certification). **Holding a responsibility never grants an authorisation**: if a required certification is missing, the employee shows as non-compliant. **[P]** (follows [C] authorisation rules)

### 4.8 Employees **[C]**

| Attribute | Notes |
|---|---|
| `employee_code` | Company employee number; unique business key; used for **Employee ID login**. |
| Names | Given, family, display name (as printed on certificates). |
| `preferred_language` | en / bn / hi / gu. |
| `employment_type`, `employment_status` | Configurable lists; active / on leave / separated. |
| `date_of_joining`, `date_of_separation` | Drive induction and history. |
| Contact (optional) | Work email / mobile only if needed. |

Rules: **employee ≠ user account** (identity domain, §4.12); **data minimisation** — no salary/**CTC**, bank, Aadhaar, health or family data **[C]**; **no deletion** — separated employees keep their records. **[C]**

### 4.9 Employee assignments **[C]**

Places an employee in the structure for a period: `employee_id`, **`org_unit_id` (required)**, `position_id` (optional), `designation_id` (optional; defaults from position), `location_id` (optional override), `assignment_type` (configurable: primary, additional, acting, temporary/deputation), `is_primary` (exactly one current primary), effective dates, `source` (manual / import batch). Multiple concurrent assignments are allowed; rules evaluate all current assignments; reports aggregate by the primary one. **[P]** (details)

### 4.10 Functional-role and responsibility assignments **[C]** / fields **[P]**

- `employee_functional_role`: employee, functional role, `source` (*derived-designation*, *derived-position*, *manual*, *import*, *exclusion*), `is_primary`, effective dates.
- `employee_responsibility`: employee, responsibility, optional org-unit/location context (e.g. fire warden *for* Plant 2), assigned by, effective dates.

Both preserve history like all effective-dated facts (§5).

### 4.11 Reporting relationships **[C]**

Employee-to-employee, **typed** and **effective-dated**. Types are configurable, for example:

| Type (illustrative) | `allows_multiple` | `is_hierarchical` | Typical use |
|---|---|---|---|
| Line manager (solid line) | no | yes | Approvals, team views |
| Functional manager (dotted line) | yes | yes | Matrix structures |
| Head of department | no | no | Departmental sign-off |
| Training coordinator | yes | no | Nominations, scheduling |
| Mentor / buddy | yes | no | Induction support |
| Practical assessor | yes | no | Shop-floor sign-off |

Rules: no self-reporting; one current relationship per employee and single-valued type; no cycles for hierarchical types. Position-to-position reporting may describe intended structure **[F]**; the employee-level relationship is operative.

### 4.12 Access roles vs functional roles **[C]**

| | **Access role** (identity domain) | **Functional role** (organisation domain) |
|---|---|---|
| Describes | What a person may *do in the LMS* | What work an employee *does at Crescent* |
| Examples | Learner, Line Manager, Training Coordinator, HR Administrator, Assessor, SME Reviewer, Auditor | Furnace Operator, Quality Inspector |
| Assigned to | **User account**, optionally scoped to an org unit (+ descendants) | **Employee**, effective-dated |
| Drives | Permissions, visible portals and data scope | Competency requirements, compliance requirements, learning allocations |

Rules **[P]**: functional roles **never grant permissions directly**. Default access provisioning may use explicit, configurable, audited rules on organisation facts (e.g. every active employee with a user account gets *Learner*; employees with current direct reports get *Line Manager* scoped to their team). Being a practical *assessor* (reporting/assessor relationship or qualification) and holding the *Assessor* access role are both required to sign off practical evaluations.

## 5. Effective dating and history **[C]** / convention **[P]**

All time-varying facts — unit lifetime, parent links, assignments, functional-role and responsibility assignments, mappings, reporting relationships, positions — use:

- `effective_from` (DATE, required), `effective_to` (DATE, nullable), half-open **`[effective_from, effective_to)`**; `NULL` = open-ended;
- check constraint `effective_to > effective_from`;
- "one current row" rules enforced with a generated column (`IF(effective_to IS NULL, 1, NULL)`) in a unique index.

| Action | What happens | Example |
|---|---|---|
| **Change** (business event) | Close the current row; insert a new one. | Transfer from Melting to Moulding on 1 July. |
| **Correction** (data was wrong) | Update in place; audit entry with before/after. | Mistyped employee code. |

| employee | org unit | from | to | meaning |
|---|---|---|---|---|
| E-0001 | Plant 1 / Melting | 2024-04-01 | 2026-07-01 | Original assignment |
| E-0001 | Plant 1 / Moulding | 2026-07-01 | *(null)* | Transfer, current |

Future-dated changes are allowed; "as-of" queries answer historical questions; system time (who changed what, when) is in the audit log.

## 6. Incomplete and evolving data **[C]** / approach **[P]**

Supported explicitly: units without parents or locations; employees without position, designation, functional role or line manager; designations without job families or role mappings. No fake "Unknown" units. A **data-quality view** lists gaps (unplaced units, employees without primary assignment, without functional role, without line manager; designations without role mapping). Rules depending on missing data simply do not match until data is completed.

## 7. Manual organisation builder **[C]** / capabilities **[P]**

Administrators (within scope) can: manage unit types and rules; create, edit, archive and move units (tree view with drag-and-drop plus an accessible form alternative); manage locations; manage job families, grades, designations, positions; **manage functional roles and responsibilities and their mappings**; manage employees; assign employees to units/positions, functional roles and responsibilities with effective dates; maintain reporting relationships; view any structure "as of" a date and any record's history. Every write is audited.

## 8. Organisation import

Organisation and employee data are imported through **import profile 1** of the shared import framework: [EXCEL_IMPORT_PROFILES.md](../database/EXCEL_IMPORT_PROFILES.md). Organisation-specific validation (hierarchy cycles on the combined existing + incoming graph, type rules, one primary assignment, reporting cycles, designation→role mapping resolution) and the exclusion of CTC/compensation columns are specified there. **[C]** / rules **[P]**

## 9. Scope-based permissions **[C]**

Access-role assignments carry an optional **scope**: an org unit plus *include descendants* (ADR-012). Example: *Training Coordinator* scoped to *Plant 2 (including descendants)* manages events and attendance only for Plant 2 employees. Scope is evaluated against **current** assignments and hierarchy; historical records are visible if the employee is in the user's current scope. **[P]** (evaluation rule)

## 10. Future PMS integration **[C]**

The LMS and PMS are **separate applications and databases**. Any future exchange of employee or organisation data uses an explicit, versioned API or file interface ([system architecture §13](LMS_SYSTEM_ARCHITECTURE.md)), never direct database access; `external_ref` fields hold source identifiers; inbound data passes the same validation, preview and audit as imports. Not implemented. What the PMS is and who owns which data: **[A] Q-20**.

## 11. Open questions

Tracked in the [register](../product/LMS_PRODUCT_REQUIREMENTS.md): **Q-20** (PMS), **Q-23** (functional roles and responsibilities catalogue), **Q-27** (unit types per plant), **Q-28** (HR master-data source), **Q-30** (grades), **Q-31** (import approvers), **Q-21** (retention).

## 12. Implementation status (Stages C1–C3)

What exists in code differs from the design above in these places (API: [API reference §7–9](API_REFERENCE.md); screens: [frontend README](../../LMS_Frontend/README.md#employee-area-stage-c3)):

| Topic | Implemented behaviour |
|---|---|
| Employees | Code (letters, digits, `/ . _ -`, ≤ 30, stored in capitals, leading zeros kept), full and display name, preferred language, work email, joining date, last working day, external reference. Status `active` / `on_leave` / `separated` or **not recorded** (never treated as active). No positions, employment type or personal/financial data. Records are never deleted. |
| Assignments | Types primary, additional, acting, deputation; half-open periods; at most one primary per day; unit required; changes from a date keep history; corrections need a reason. Non-assignable unit types give a warning (Q-55). |
| Functional roles | Derived from designation mappings over all current assignments, plus manual roles, minus exclusions — computed by the server. Functional roles never grant permissions (§4.12). |
| Responsibilities | Effective-dated, with optional unit or location context; grant no permissions. |
| Reporting | Only `LINE_MANAGER` is seeded (Q-52): one current line manager, no self-reporting, no cycles, no separated manager; a new manager from a date replaces the current one. Being a manager grants no access. |
| Separation | Last working day stored as entered; open records end the following day. Own records and direct reports' lines are ended only with separate explicit confirmations; records starting later block separation. A read-only preview shows the impact first. |
| Accounts | Login accounts are linked separately (`employees.manage` + `user_accounts.manage`), never automatically; at most one non-disabled account per employee. |
| Data quality (§6) | Eight server checks on an as-of date: status not recorded, no primary assignment, location missing, designation missing, separated with an active account, line manager not active, no line manager, joining date not recorded. Report only. |
| Permissions | Global until C4: `employees.view`, `employees.history.view`, `employees.manage`, `reporting_lines.manage` — HR Admin and Super Admin only (Q-51, Q-57). |

Still open: Q-45 (grade and level), Q-47 (sub-functions and departments), Q-48 (plants and functions), Q-53 (designations and job families).
