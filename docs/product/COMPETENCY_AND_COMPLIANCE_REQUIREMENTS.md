# Competency and Compliance Requirements

| | |
|---|---|
| **Status** | Stage A.1 requirements. **Nothing in this document is implemented.** |
| **Owns** | Competency framework, employee skill assessment, competency achievement, development plans, compliance skills, certification, Skill Passport. |
| **Labels** | **[C]** confirmed · **[P]** proposed · **[A]** assumption (see register `Q-xx` in [product requirements §13](LMS_PRODUCT_REQUIREMENTS.md)) · **[F]** future |
| **Related** | [Product requirements](LMS_PRODUCT_REQUIREMENTS.md) (reports FR-RPT-004…009) · [System architecture §6](../architecture/LMS_SYSTEM_ARCHITECTURE.md) (evidence chain) · [Database design §6–7](../database/LMS_DATABASE_DESIGN.md) · [Import profiles 2 & 3](../database/EXCEL_IMPORT_PROFILES.md) |

---

## 1. Principles

1. **Scales are configuration.** Proficiency scales (skill-level sets) are data, not code. The Bagnan scale is the first configured scale, not a hardcoded standard. **[C]**
2. **Competency ≠ compliance ≠ authorisation.** Competency skills are measured on a proficiency scale; compliance skills are binary and validity-based; operational authorisations are certifications requiring practical validation. They are separate entities with separate records. **[C]**
3. **Evidence-based.** A competency level is achieved through configured combinations of course completion, theoretical assessment and practical validation — each recorded as evidence. **[C]**
4. **Online completion never grants operational authorisation.** **[C]**
5. **Human oversight** of official assessments and practical validations. **[C]**
6. **History is preserved.** Assessments, achievements and certificate issuances are never overwritten; corrections are new, audited records. **[C]** / mechanism **[P]**
7. **Source values are preserved.** Imported values (e.g. development-plan indicators "Y", "US") are stored verbatim; their meaning is not assumed. **[C]**

## 2. Concepts

| Concept | Definition | Label |
|---|---|---|
| **Skill-level set** | A named, configurable proficiency scale (e.g. "Bagnan 5-level scale"). | [C] |
| **Skill level** | One level in a set: a **numeric proficiency value**, a label (translated) and a description. | [C] |
| **Competency skill** | A skill measured against one skill-level set, grouped by category (e.g. technical, process, behavioural). | [C] |
| **Functional role requirement** | The level a functional role requires for a competency skill, with importance (mandatory/desirable). | [C] |
| **Designation-to-role mapping** | Which functional roles a designation normally implies (defaults; employees can also be assigned roles directly). | [C] |
| **Role-to-competency mapping** | The set of functional role requirements for a role. | [C] |
| **Curriculum-to-competency mapping** | Which competency skills a curriculum develops, and the highest level it can contribute to. | [C] |
| **Competency achievement rule** | For a skill and level: which evidence is required (curriculum completion, theory assessment result, practical validation, assessor rating). | [C] / structure [P] |
| **Employee skill assessment** | A dated rating of an employee on a skill (by an assessor, manager, practical evaluation or import), with status and provenance. | [C] |
| **Competency achievement** | A recorded award of a level when a rule is satisfied, with links to its evidence. | [C] / [P] |
| **Current competency level** | The employee's latest valid level per skill, derived from approved assessments and achievements. | [P] |
| **Employee development plan** | A plan for an employee (per period) listing competencies, target levels, interventions and dates. | [C] |
| **Compliance skill** | A binary, validity-based requirement (e.g. fire-safety training, permit-to-work awareness). | [C] |
| **Certification** | A definition of something that can be certified (completion, appreciation, compliance, operational authorisation, external). | [C] / kinds [P] |
| **Certificate issuance** | One immutable issued certificate: number, employee, dates, status, document, verification token. | [C] |
| **Skill Passport** | An employee's consolidated, read-only view of competencies, compliance, certificates, authorisations and training history. | [C] |

## 3. Competency framework

| ID | Requirement | Label |
|---|---|---|
| FR-CMP-001 | Administrators configure **skill-level sets**, each with ordered **skill levels** having a numeric value, translated label and description. *(Revised.)* | [C] |
| FR-CMP-002 | **Functional role requirements**: required level per competency skill per functional role, with importance and effective dates. *(Revised: requirements attach to functional roles; designations map to roles.)* | [C] |
| FR-CMP-003 | Evidence-based employee proficiency with full history. | [C] |
| FR-CMP-004 | Gap view (required vs current) for employees, managers and departments. | [C] |
| FR-CMP-005 | Catalogue of **competency skills** with category, owning department, skill-level set, translations and status. | [C] |
| FR-CMP-006 | **Designation-to-role mapping** (effective-dated), producing default functional roles for employees with that designation. | [C] |
| FR-CMP-007 | **Curriculum-to-competency mapping**, including the maximum level a curriculum can contribute to. | [C] / max-level rule [P] |
| FR-CMP-008 | A skill's levels may carry level-specific descriptions (what "Can Work Independently" means for that skill). | [P]; need [A] Q-02 |
| FR-CMP-009 | Scales can differ by skill or plant; reports compare levels only within the same skill-level set. | [P]; need [A] Q-02 |

### 3.1 Initial scale: Bagnan workbooks **[C]**

The initial Bagnan workbooks use this scale. It will be loaded as **configuration data** (a skill-level set), not as code:

| Numeric value | Label |
|---|---|
| 1 | Beginner |
| 2 | Can Work Under Supervision |
| 3 | Can Work Independently |
| 4 | Expert |
| 5 | Can Train Others |

Whether other plants use the same scale is **[A] Q-02**. Translations of the labels into bn/hi/gu require native review. **[P]**

## 4. Employee skill assessment

| ID | Requirement | Label |
|---|---|---|
| FR-CMP-010 | Record **employee skill assessments**: employee, skill, level, date, method (assessor rating, manager rating, practical evaluation, imported matrix), assessor, remarks, status. | [C] / methods [P] |
| FR-CMP-011 | Ratings from assessors or managers follow draft → submitted → approved; only approved ratings affect the current level. | [P] |
| FR-CMP-012 | Imported matrix values are recorded as assessments with method *imported*, the as-of date stated at import, and full source provenance. | [C] / [P] |
| FR-CMP-013 | A blank matrix cell means **not assessed**, never level 0 or level 1. | [P] |
| FR-CMP-014 | Current level per employee and skill is derived from the latest approved assessment or achievement; history remains queryable as of any date. | [P] |
| FR-CMP-015 | Self-assessment as an input that never changes the official level on its own. | [F] |

## 5. Competency achievement

| ID | Requirement | Label |
|---|---|---|
| FR-CMP-016 | **Achievement rules** per skill and level define required evidence: curriculum completion, theory assessment (minimum score), practical validation (checklist outcome by an authorised assessor), assessor rating — combined with *all of*. | [C] / combination [P] |
| FR-CMP-017 | When all required evidence exists, the LMS records a **competency achievement** linking each piece of evidence. | [C] / [P] |
| FR-CMP-018 | Rules for levels that imply **independent operational work** (by default level 3 and above on the Bagnan scale) must include practical validation. | [P]; threshold [A] Q-02 |
| FR-CMP-019 | Curriculum completion alone can raise a level only up to the curriculum's configured maximum contribution. | [P] |
| FR-CMP-020 | Achievements can be withdrawn by authorised users with a reason (audited); the withdrawal is a new record. | [P] |

## 6. Development plans

| ID | Requirement | Label |
|---|---|---|
| FR-DEV-001 | **Employee development plans** per employee and period (financial year by default), owned by the line manager. | [C] / ownership [P] |
| FR-DEV-002 | Plan items: competency skill, current level, target level, intervention (curriculum, training programme, OJT, mentoring), target date, status. | [C] / fields [P] |
| FR-DEV-003 | **Source indicators** in development-plan files (e.g. "Y", "US") are stored verbatim on the plan item. | [C] |
| FR-DEV-004 | Indicator meanings are mapped through a configurable value mapping **only after business confirmation**; unmapped indicators remain "unclassified" and are never dropped. | [C] / mechanism [P]; meanings [A] Q-01 |
| FR-DEV-005 | Plan items can generate learning allocations or training nominations once approved. | [P] |
| FR-DEV-006 | Plan progress reflects linked enrolments, attendance and achievements. | [P] |
| FR-DEV-007 | Plans are imported from competency-by-employee matrices (import profile 3). | [C] |

## 7. Compliance skills

| ID | Requirement | Label |
|---|---|---|
| FR-CPL-001 | **Compliance skills are separate from competency skills**: binary (held/not held), validity-based, with their own catalogue. | [C] |
| FR-CPL-002 | **Requirement rules**: who must hold a compliance skill — by functional role, responsibility, location/plant, org unit, designation, employment type or everyone — with effective dates. | [C] / audiences [P]; mappings [A] Q-34 |
| FR-CPL-003 | **Fulfilment rules**: how a compliance skill is satisfied — a valid certificate issuance of a certification, completion of a curriculum within its validity, or a verified external certification. | [P] |
| FR-CPL-004 | Employee compliance status per skill: *compliant*, *due soon*, *expired*, *missing*, *not applicable*, *exempt*. | [P] |
| FR-CPL-005 | Exemptions require an authorised approver, reason and end date. | [P] |
| FR-CPL-006 | Grace periods for new joiners and role changes. | [P] |
| FR-CPL-007 | Plant-wise compliance reporting (FR-RPT-006). | [C] |

## 8. Certification

| ID | Requirement | Label |
|---|---|---|
| FR-CRT-001 | **Certification definitions** with kind, validity period, renewal/refresher rule, template and issuing requirements. *(Revised.)* | [C] |
| FR-CRT-002 | **Certificate issuance** on rule satisfaction (e.g. curriculum completion) or by authorised manual issuance. *(Revised.)* | [C] |
| FR-CRT-003 | Expiry tracking, reminders and automatic refresher allocation. | [C] |
| FR-CRT-004 | Unique **certificate number** per issuance. | [C]; format [A] Q-10 |
| FR-CRT-005 | **QR verification**: each certificate carries a QR code for a public verification page showing only certificate number, holder name, certification, issue/expiry date and current status. | [C] / content [P] |
| FR-CRT-006 | **Issue date** and **expiry date** on every issuance (expiry optional for non-expiring kinds). | [C] |
| FR-CRT-007 | **Renewal creates a new issuance** linked to the previous one; historical issuances are never changed. Renewal history is visible. | [C] |
| FR-CRT-008 | **Suspension** and reinstatement with reason, approver and dates. | [C] |
| FR-CRT-009 | **Revocation** with reason and approver; revoked certificates verify as revoked. | [C] |
| FR-CRT-010 | **External certifications**: record certificates from external bodies (issuer, number, dates, document) with verification status (pending, verified, rejected). | [C] |
| FR-CRT-011 | **Certificate templates**: separate templates for **completion** and **appreciation** certificates, using the supplied Crescent certificate designs as the branding reference; versioned; issuances record the template version used. | [C]; designs to be supplied [A] Q-10 |
| FR-CRT-012 | The issued document (PDF) is generated once, stored immutably with its hash, and re-downloadable. | [P] |
| FR-CRT-013 | **Certification Register**: all issuances with status, filterable by plant, department, certification and period (FR-RPT-007). | [C] |
| FR-CRT-014 | **Operational authorisations** (certification kind *authorisation*) require a recorded practical validation by an authorised assessor and approval by an authorised signatory; online completion alone can never issue them. | [C] / mechanism [P]; list [A] Q-11 |
| FR-CRT-015 | Appreciation certificates are issued manually by HR and are not evidence of competence or compliance. | [P] |
| FR-CRT-016 | Certificate languages: English by default; additional languages per template. | [A] Q-10 |

## 9. Skill Passport

| ID | Requirement | Label |
|---|---|---|
| FR-SKP-001 | Each employee has a **Skill Passport** showing current competency levels (with role requirements), compliance status, certificates (internal and external), operational authorisations and training history. | [C] |
| FR-SKP-002 | Available to the employee (learner portal, mobile), their managers (within scope) and HR. | [C] / access [P] |
| FR-SKP-003 | The passport is a **view** over the source records, not a separate copy of data. | [P] |
| FR-SKP-004 | Printable summary; export with verification QR. | Print [P]; export [F] F-06 |

## 10. Related reports and imports

- Reports (defined once in [product requirements §8](LMS_PRODUCT_REQUIREMENTS.md)): Competency Skill Finder (FR-RPT-004), Skill Gap (FR-RPT-005), Compliance (FR-RPT-006), Certification Register (FR-RPT-007), Certification Expiry (FR-RPT-008).
- Imports ([profiles](../database/EXCEL_IMPORT_PROFILES.md)): profile 2 (skill matrices), profile 3 (individual development plans).
- Open questions: Q-01, Q-02, Q-03, Q-10, Q-11, Q-23, Q-24, Q-34.
