# LMS Product Requirements

| | |
|---|---|
| **Status** | Requirements baseline, revised in **Stage A.1** (architecture alignment). Only the Stage A foundation is implemented (FR-PLT-001…004). **Everything else is planned.** |
| **Owns** | Vision, users, user experiences, glossary, cross-cutting functional requirements, report catalogue, non-functional requirements, the **assumptions & open-questions register** (§13) and the **future-enhancements register** (§14). |
| **Related** | [Competency & compliance requirements](COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md) · [Training operations requirements](TRAINING_OPERATIONS_REQUIREMENTS.md) · [System architecture](../architecture/LMS_SYSTEM_ARCHITECTURE.md) · [Organisation architecture](../architecture/ORGANISATION_ARCHITECTURE.md) · [Database design](../database/LMS_DATABASE_DESIGN.md) · [Excel import profiles](../database/EXCEL_IMPORT_PROFILES.md) · [Decisions](../decisions/ARCHITECTURAL_DECISIONS.md) · [Roadmap](../LMS_IMPLEMENTATION_ROADMAP.md) |

---

## 0. How to read the LMS documents

### 0.1 Labels

Every requirement and significant design statement across the documentation carries one of these labels:

| Label | Meaning |
|---|---|
| **[C]** Confirmed | Stated by Crescent Foundry (project brief, Stage A / A.1 instructions, `CLAUDE.md`). |
| **[P]** Proposed | A design decision proposed by the architecture team. Reasoned and recorded (often as an ADR), but open to review. |
| **[A]** Assumption | Not yet verified. Must be confirmed before the dependent feature is built. Each has an ID in the register (§13), e.g. `Q-01`. |
| **[F]** Future | Desired, but outside initial delivery. Listed in §14 (`F-01`…). |

### 0.2 Which document owns what

To avoid duplication, each topic has one owning document; others link to it.

| Topic | Owning document |
|---|---|
| Vision, users, portals, glossary, learning catalogue & delivery, assessments, reports, AI, NFRs, open questions | **This document** |
| Competency framework, development plans, compliance skills, certification, Skill Passport | [COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md](COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md) |
| Calendars, planned activities, events, sessions, nominations, attendance, hours, feedback, training requests | [TRAINING_OPERATIONS_REQUIREMENTS.md](TRAINING_OPERATIONS_REQUIREMENTS.md) |
| Modules, domain model, cross-domain rules, security, AI architecture, integrations | [LMS_SYSTEM_ARCHITECTURE.md](../architecture/LMS_SYSTEM_ARCHITECTURE.md) |
| Organisation and employee model | [ORGANISATION_ARCHITECTURE.md](../architecture/ORGANISATION_ARCHITECTURE.md) |
| Tables, constraints, conventions | [LMS_DATABASE_DESIGN.md](../database/LMS_DATABASE_DESIGN.md) |
| Import framework and the six import profiles | [EXCEL_IMPORT_PROFILES.md](../database/EXCEL_IMPORT_PROFILES.md) |
| Decisions and their rationale | [ARCHITECTURAL_DECISIONS.md](../decisions/ARCHITECTURAL_DECISIONS.md) |
| Delivery stages and dependencies | [LMS_IMPLEMENTATION_ROADMAP.md](../LMS_IMPLEMENTATION_ROADMAP.md) |

## 1. Vision

Crescent Foundry LMS develops every employee's capabilities continuously — from their first day through each role they grow into — in the language they are most comfortable with, on whatever device is at hand: a phone on the shop floor, a shared kiosk, a tablet in a training room, or a desktop in an office. **[C]**

## 2. Goals

1. Every new employee completes a consistent, trackable induction and foundation programme. **[C]**
2. Every employee knows what they must learn for their role, and managers can see where their teams stand. **[C]**
3. Foundry process knowledge and safety practice are captured, standardised, validated by department experts and refreshed. **[C]**
4. Skills are verified through theoretical **and** practical assessment; operational authorisation is never granted on online completion alone. **[C]**
5. Training operations (calendars, events, attendance, hours) move from spreadsheets into one system that keeps *planned* and *actual* separate. **[C]**
6. Compliance and certification status is visible per employee (Skill Passport) and per plant (Certification Register). **[C]**
7. Employees can prepare for their next role using competency gaps and recommendations. **[C]**
8. AI assists learners and content authors, grounded in approved company material and subject to human approval. **[C]**

## 3. User categories

| Category | Description | Key needs | Label |
|---|---|---|---|
| **Learner — shop floor** | Operators, technicians, helpers, apprentices; may share devices; varying literacy. | Mobile-first UI, local language, short modules, kiosk access, Skill Passport. | [C] |
| **Learner — staff** | Engineers, supervisors, office staff. | Paths, self-paced learning, certificates, calendar. | [C] |
| **Line manager** | Leads a team, shift or section. | Team status, nominations and approvals, gaps, development plans, practical sign-off. | [C] |
| **Head of department** | Accountable for department capability. | Department learning, competency and compliance status. | [C] |
| **Department SME** | Subject-matter expert in a department. | Validate technical content; author and review questions and checklists. | [C] |
| **HR / L&D administrator** | Owns learning administration. **Final course approval and publishing authority.** | Control Room: catalogue, calendars, events, imports, certificates, reports. | [C] |
| **Training coordinator** | Plant- or department-level operations. | Calendars, events, nominations, attendance, finalisation (within scope). | [C] |
| **Trainer — internal / external** | Delivers classroom, online or OJT training. | Sessions, attendance capture, materials, feedback results. | [C] |
| **Practical assessor** | Validates practical competence. | Versioned checklists, evidence, remarks, employee acknowledgement. | [C] |
| **Content author** | Creates learning assets (may be an SME or HR). | Authoring, AI drafting, translation workflow. | [P] |
| **System administrator** | Technical administration. | Configuration, access roles, kiosks, integrations, audit. | [C] |
| **Senior management** | Oversight. | Plant- and company-level dashboards. | [C] |
| **Auditor** | Internal/external audit. | Read-only registers and audit trails. | [P] |
| **Vendor (external training provider)** | Supplies trainers/programmes. | Recorded as data; no portal access initially. | [P] / portal [F] |

Categories map to configurable **access roles** with **scopes** (e.g. one plant). Access roles are **separate from functional job roles** (§5, ADR-023). **[C]**

## 4. User experiences

Three distinct experiences in one web application, plus a kiosk mode. **[C]** Implemented as route areas of one SPA with separate layouts (ADR-031). **[P]**

### 4.1 Employee / Learner Portal — mobile-first **[C]**

| Capability | Label |
|---|---|
| Learning dashboard with **upcoming learning actions** (due items, scheduled sessions, assessments, acknowledgements) | [C] |
| Safety and certification status (valid / due soon / expired / missing) | [C] |
| Skill Passport (competencies, compliance, certificates, authorisations, training history) | [C] |
| Course (curriculum) progress and resume | [C] |
| Learning calendar (own sessions and deadlines) | [C] |
| Practical sign-off: view and acknowledge practical evaluations | [C] |
| Catalogue browsing and self-enrolment where visible | [P] |
| Training feedback and surveys | [C] |
| Language selection (en/bn/hi/gu) at any time | [C] |

### 4.2 Line Manager Portal **[C]**

Team dashboard; team compliance, certification expiry and skill gaps; nominations and approvals; development plans; training requests; practical assessments (when the manager is an assessor); team calendar. **[P]** (feature list) — exact manager permissions **[A] Q-18**.

### 4.3 HR / Administrator Control Room **[C]**

Organisation and employee data; imports; learning catalogue management with SME validation and **HR approval/publishing**; training calendars and events; attendance and finalisation; certification register and templates; compliance configuration; reports; access-role and kiosk administration; audit. Desktop-first but responsive. **[P]**

### 4.4 Devices, kiosks and sign-in

| Requirement | Label |
|---|---|
| Smartphones, tablets, laptops, desktops and **shared kiosks** | [C] |
| **Employee ID login** | [C] |
| **PIN access on configured (registered) kiosks** | [C] |
| **QR badge scanning** (kiosk sign-in and attendance) | [C] |
| **Automatic idle logout**, shorter on kiosks | [C] |
| Badge QR identifies; PIN authenticates — a badge alone never opens an account | [P] (ADR-032) |
| Credential on personal devices (password, OTP, SSO for staff) | [A] Q-07 |
| Badge format and issuance | [A] Q-08 |

## 5. Glossary

| Term | Meaning |
|---|---|
| **Learning Academy** | Top-level grouping of learning by domain or department (e.g. Safety Academy). Contains learning paths. |
| **Learning Path** | A structured programme made of **sections**, each containing curricula, with sequence, minimum-completion and deadline rules. |
| **Curriculum** | A unit of learning (what people commonly call a "course") made of **curriculum items**, mandatory or optional. Has validity, retraining and certificate rules. |
| **Curriculum item** | A slot in a curriculum that refers to one learning asset, with mandatory/optional flag and order. |
| **Learning Asset** | Reusable content or activity: reference material, PDF, presentation, video, podcast, SCORM package, assessment, assignment, survey, classroom session, OJT/practical activity, external resource. |
| **Learning allocation** | A requirement that an employee (or audience) completes a path or curriculum by a deadline. *(Avoids confusion with "assignment".)* |
| **Assignment** | A learning-asset type: a task submitted online or evaluated face-to-face. |
| **Employee assignment** | Organisation term: an employee's placement in a unit/position over a period. |
| **Enrolment** | An employee's participation record in a path or curriculum, with progress and completion. |
| **Access role** | Application permission role (e.g. Training Coordinator). |
| **Functional role** | The work an employee performs (e.g. Furnace Operator); drives competency requirements. |
| **Responsibility** | A discrete duty assigned to an employee (e.g. First Aider); may drive compliance requirements. |
| **Competency skill** | A skill measured on a proficiency scale (skill-level set). |
| **Compliance skill** | A binary, validity-based requirement (e.g. fire-safety training); separate from competency skills. |
| **Planned training activity** | A calendar line. **Not** an event and **not** evidence of training. |
| **Training event** | An actual training occurrence, delivered in batches and sessions. |
| **Training session** | A dated time slot of an event batch; attendance is recorded per session. |
| **Login session** | A signed-in application session (security term). |
| **Certificate issuance** | One immutable issued certificate with its own number; renewals create new issuances. |
| **Skill Passport** | An employee's consolidated view of competencies, compliance, certificates and training history. |

## 6. Module overview

| Module | Requirements | Label |
|---|---|---|
| Platform & portals | §4, §7.1 | [C] |
| Identity & access | §7.2 | [C] |
| Organisation & employees | §7.3, [organisation architecture](../architecture/ORGANISATION_ARCHITECTURE.md) | [C] |
| Learning catalogue & content governance | §7.4, §7.5 | [C] |
| Learning delivery | §7.6 | [C] |
| Assessments & practical evaluation | §7.7 | [C] |
| Competency & development | [Competency & compliance](COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md) | [C] |
| Compliance, certification & Skill Passport | [Competency & compliance](COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md) | [C] |
| Training operations | [Training operations](TRAINING_OPERATIONS_REQUIREMENTS.md) | [C] |
| Career development | §7.8 | [C] |
| Reports & analytics | §8 | [C] |
| Data import | §9, [import profiles](../database/EXCEL_IMPORT_PROFILES.md) | [C] |
| AI services | §10 | [C] |
| Integrations (PMS boundary) | §7.9 | [C] |

## 7. Functional requirements

IDs are stable. Requirements revised in Stage A.1 keep their IDs; replaced IDs are listed in §13.

### 7.1 Platform foundation
| ID | Requirement | Label | Status |
|---|---|---|---|
| FR-PLT-001 | Responsive application shell usable on phones, tablets, laptops and desktops. | [C] | **Implemented** (shell) |
| FR-PLT-002 | UI in English, Bengali, Hindi and Gujarati; switch at any time; choice remembered on the device. | [C] | **Implemented** (strings pending native review) |
| FR-PLT-003 | Visible API connectivity and readiness indication. | [P] | **Implemented** |
| FR-PLT-004 | Consistent error and loading feedback. | [P] | **Implemented** |
| FR-PLT-005 | Preferred language stored per employee and applied at sign-in. | [C] | Planned |
| FR-PLT-006 | Three experiences (Learner Portal, Manager Portal, Control Room) with role-based navigation. | [C] | Planned |
| FR-PLT-007 | Kiosk mode: touch-optimised layout, badge scan + PIN sign-in, short idle timeout, no persistent personal data on the device. | [C] / details [P] | Planned |

### 7.2 Identity and access
| ID | Requirement | Label |
|---|---|---|
| FR-IAM-001 | Sign-in with **employee ID** plus a credential. | [C]; credential type [A] Q-07 |
| FR-IAM-002 | Server-side login sessions with **automatic idle logout** and absolute timeout; shorter on kiosks. | [C] |
| FR-IAM-003 | Configurable **access roles** and permissions, independent of functional job roles. | [C] |
| FR-IAM-004 | Access-role assignments scoped to organisation units (e.g. a plant) including descendants. | [C] |
| FR-IAM-005 | Audit trail of sensitive operations, viewable by authorised users. | [C] |
| FR-IAM-006 | **PIN** sign-in accepted only on administrator-registered kiosk devices; PINs hashed, rate-limited, lockable. | [C] / controls [P] |
| FR-IAM-007 | **QR badge** scanning identifies an employee at kiosks and for attendance; badge tokens are revocable and re-issuable. | [C] / tokens [P] |
| FR-IAM-008 | Re-authentication (e.g. PIN) for acknowledgements and sign-offs. | [P]; acceptability [A] Q-24 |

### 7.3 Organisation and employees
Detailed model: [organisation architecture](../architecture/ORGANISATION_ARCHITECTURE.md).

| ID | Requirement | Label |
|---|---|---|
| FR-ORG-001 | Administrators manage organisation unit types and optional parent/child type rules. | [C] |
| FR-ORG-002 | Create, edit, archive and move units in a hierarchy of any depth, including multiple roots and unplaced units. | [C] |
| FR-ORG-003 | Manage multiple plants and locations. | [C] |
| FR-ORG-004 | Manage job families, grades, designations and positions. | [C] (grades [A] Q-30) |
| FR-ORG-005 | Manage employee records with minimal personal data; **no compensation data (e.g. CTC)**. | [C] |
| FR-ORG-006 | Effective-dated employee assignments; multiple concurrent, one primary. | [C] |
| FR-ORG-007 | Typed, effective-dated reporting relationships. | [C] |
| FR-ORG-008 | As-of views and change history. | [C] |
| FR-ORG-009 | Data-quality view of incomplete organisation data. | [P] |
| FR-ORG-010 | Manage **functional roles**; map designations (and optionally positions) to functional roles; assign functional roles to employees with effective dates. | [C] |
| FR-ORG-011 | Manage **responsibilities** and assign them to employees with effective dates. | [C] |
| FR-ORG-012 | An employee's **access role** is managed separately from their **functional role**. | [C] |

### 7.4 Learning catalogue
| ID | Requirement | Label |
|---|---|---|
| FR-CNT-001 | Learning is organised as **Learning Academy → Learning Path → Curriculum → Learning Asset**, each a separate entity. *(Revised in A.1.)* | [C] |
| FR-CNT-002 | Content in up to four languages per item, with translation status per language. | [C] |
| FR-CNT-003 | Versioning of assets, curricula and paths; learners keep records against the version they completed. | [C] / mechanism [P] |
| FR-CNT-004 | Review and approval before publication — see §7.5. *(Revised.)* | [C] |
| FR-CNT-005 | Department-specific academies, each with an owning department. | [C] |
| FR-CNT-006 | Asset types: reference material, PDF, presentation, video, podcast, **SCORM package**, assessment, assignment, survey/feedback, classroom session, OJT/practical activity, external resource. | [C]; SCORM versions [A] Q-16 |
| FR-CNT-007 | Assets are reusable across curricula; curricula are reusable across paths. | [P] |
| FR-CNT-008 | A curriculum contains **mandatory and optional** items, ordered, with a minimum number of optional items where configured. | [C] |
| FR-CNT-009 | A path contains **sections** and curricula with **sequence requirements** (free, sequential, prerequisite), **minimum completion rules** (all mandatory / at least N) and **deadlines** (relative or fixed). | [C] |
| FR-CNT-010 | **Curriculum validity** (e.g. 12 months) and **retraining** rules (re-allocation before expiry; optional refresher curriculum). | [C] |
| FR-CNT-011 | **Access visibility** rules: who can see/self-enrol, by unit, location, designation, functional role, job family, responsibility or employment type. | [C] |
| FR-CNT-012 | Completion **certificates** configurable per curriculum or path (completion template). | [C] |
| FR-CNT-013 | **Learning reinforcement**: scheduled follow-up activities after completion (e.g. short quizzes at set intervals). | [C]; pattern [A] Q-26 |
| FR-CNT-014 | Classroom and OJT items are fulfilled through training operations (attended, finalised events; practical evaluations), not by self-marking. | [P] |

### 7.5 Content governance
| ID | Requirement | Label |
|---|---|---|
| FR-GOV-001 | **Department SMEs validate technical content** before approval. | [C] |
| FR-GOV-002 | **HR is the final approval and publishing authority** for curricula, paths, assets and official assessments. | [C] |
| FR-GOV-003 | Workflow: Draft → SME validation → HR approval → Published → Retired; rejections return to Draft with comments. | [P] |
| FR-GOV-004 | AI-generated content is marked as such and follows the same workflow; it can never be published without recorded human approval. | [C] |
| FR-GOV-005 | Safety-critical content requires a designated safety reviewer in addition to the department SME. | [P] |
| FR-GOV-006 | Every governance decision is audited (who, when, version, comments). | [C] |

### 7.6 Learning delivery
| ID | Requirement | Label |
|---|---|---|
| FR-LRN-001 | Company-wide induction and foundation programme allocated automatically to new joiners. | [C] |
| FR-LRN-002 | Foundry manufacturing and process education catalogue. | [C] |
| FR-LRN-003 | **Learning allocations** by rules on unit, position, designation, functional role, job family, responsibility, employment type; and manually by managers/HR. *(Revised.)* | [C] |
| FR-LRN-004 | Enrolment (self where visible, manager nomination, coordinator, rule-based), deadlines and reminders. | [C] |
| FR-LRN-005 | Progress tracking and resume on any device. | [C] |
| FR-LRN-006 | Classroom/OJT participation — see [training operations](TRAINING_OPERATIONS_REQUIREMENTS.md). *(Revised.)* | [C] |
| FR-LRN-007 | Learner dashboard and manager team view (§4). | [C] |
| FR-LRN-008 | **Enrolment approvals** where configured (e.g. manager approval for self-enrolment). | [C]; which cases [A] Q-18 |
| FR-LRN-009 | Completion expires at the end of curriculum validity; status shows "due for retraining" before expiry. | [C] |
| FR-LRN-010 | Curriculum completion is a learning record only; it does **not** by itself grant competency levels above configured limits or any operational authorisation. | [C] |

### 7.7 Assessments and practical evaluation
| ID | Requirement | Label |
|---|---|---|
| FR-ASM-001 | Question banks with question types: **MCQ**, **multiple response**, **fill-in-the-blanks**, **match-the-following**, **subjective**. Multilingual. *(Revised.)* | [C] |
| FR-ASM-002 | **Practice** and **final examination** modes; pass marks; **configurable attempts**; result history. *(Revised.)* | [C] |
| FR-ASM-003 | **OJT/practical assessments** using **versioned checklists**, **assessor remarks**, **evidence attachments** and **employee acknowledgement**; usable on tablets on the shop floor. *(Revised.)* | [C] |
| FR-ASM-004 | Results feed competency achievement and certification rules. | [C] |
| FR-ASM-005 | **Manual evaluation** of subjective answers by authorised evaluators. | [C] |
| FR-ASM-006 | **Assignments**: online (submission) and face-to-face (evaluated and recorded by the trainer/assessor). | [C] |
| FR-ASM-007 | Random selection from banks by tag/difficulty; question and option shuffling. | [P] |
| FR-ASM-008 | **Human oversight**: official (final) results with subjective components and all practical validations are confirmed by an authorised human; AI may only suggest. | [C] |
| FR-ASM-009 | Attempts record the exact question versions shown and answers given. | [P] |
| FR-ASM-010 | Re-evaluation / dispute process for final results. | [A] Q-17 |

### 7.8 Career development
| ID | Requirement | Label |
|---|---|---|
| FR-CAR-001 | Career paths linking current and next functional roles/designations. | [C] |
| FR-CAR-002 | Next-role readiness from competency gaps; development plan linkage. | [C] |

### 7.9 Integration
| ID | Requirement | Label |
|---|---|---|
| FR-INT-001 | LMS and PMS remain **separate applications and databases**. | [C] |
| FR-INT-002 | Documented API integration boundaries are prepared for future PMS integration; **no PMS integration is implemented** until scoped. | [C] |
| FR-INT-003 | Integration uses service credentials and versioned contracts; never direct database access. | [P] |

## 8. Reports and management analytics

All reports are **permission-controlled** and **scope-filtered** (e.g. a plant coordinator sees only their plant); exports are audited. **[C]**

| ID | Report | Purpose / key content | Primary sources | Label |
|---|---|---|---|---|
| FR-RPT-001 | **Training Completion** | Completion of allocated paths/curricula by unit, period, status | Enrolments, allocations | [C] |
| FR-RPT-002 | **Event Attendance** | Per event/session attendance, no-shows | Attendance records | [C] |
| FR-RPT-003 | **Department & Plant Learning Status** | Overdue, due soon, completed, by department/plant | Enrolments, org | [C] |
| FR-RPT-004 | **Competency Skill Finder** | Find employees with skill X at ≥ level N, by plant/department | Competency status | [C] |
| FR-RPT-005 | **Skill Gap Report** | Required (role) vs current level per employee/team | Role requirements, competency status | [C] |
| FR-RPT-006 | **Compliance Report** | Plant-wise compliance by compliance skill | Compliance status | [C] |
| FR-RPT-007 | **Certification Register** | All certificate issuances with status | Certificate issuances | [C] |
| FR-RPT-008 | **Certification Expiry** | Expiring / expired certificates in a window | Certificate issuances | [C] |
| FR-RPT-009 | **Employee Training History** | Complete history: online completions, attended events, historical records | Enrolments, attendance, historical records | [C] |
| FR-RPT-010 | **Training Calendar vs Actual** | Planned activities vs finalised events, by FY/location/department | Planned activities, events | [C] |
| FR-RPT-011 | **Training Hours & CPD** | Hours per employee, manhours per unit/FY, CPD hours | Finalised attendance, completions | [C]; CPD definition [A] Q-12 |
| FR-RPT-012 | **Training Requests** | Requests by status, unit, topic | Training requests | [C] |
| FR-RPT-013 | Management dashboards across plants | KPIs | All | [C]; KPIs [A] Q-29 |

Former FR-ADM-001/003/004 are covered by FR-RPT-001…013; FR-ADM-002 moved to training operations (§13).

## 9. Data import

Framework and profile details: [Excel import profiles](../database/EXCEL_IMPORT_PROFILES.md).

| ID | Requirement | Label |
|---|---|---|
| FR-IMP-001 | Import `.xlsx` workbooks with multiple worksheets through a **reusable import framework with separate profiles**: (1) organisation & employees, (2) skill matrices, (3) individual development plans, (4) annual training calendars, (5) safety training calendars, (6) event attendance & historical training records. *(Revised.)* | [C] |
| FR-IMP-002 | Standard templates and saved, reusable column-mapping profiles. | [C] |
| FR-IMP-003 | Row-level validation; **duplicate-candidate detection**. | [C] |
| FR-IMP-004 | **Preview / dry run** with new / updated / unchanged / error / duplicate-candidate counts. | [C] |
| FR-IMP-005 | **Administrator confirmation** before any data is written. | [C] |
| FR-IMP-006 | **Transactional** commit; **safe re-imports**; no implicit deletion. | [C] |
| FR-IMP-007 | **Import history** and audit; **source provenance** (file, sheet, row, column) kept for every imported record. | [C] |
| FR-IMP-008 | **Error exports** for correction and re-upload. | [C] |
| FR-IMP-009 | Wide **employee-by-skill matrices** and **competency-by-employee development-plan matrices** are supported. | [C] |
| FR-IMP-010 | Records are **never discarded automatically** because training names are similar; similar records become duplicate candidates for an administrator to resolve. | [C] |
| FR-IMP-011 | **CTC and other compensation data are excluded** and never stored, not even in staging. | [C] |
| FR-IMP-012 | Original values (e.g. development-plan indicators "Y", "US") are preserved verbatim. | [C] |
| FR-IMP-013 | Real employee records and original workbooks are never added to the Git repository. | [C] |

## 10. AI services

Architecture: [system architecture §12](../architecture/LMS_SYSTEM_ARCHITECTURE.md).

| ID | Requirement | Label |
|---|---|---|
| FR-AI-001 | AI learning tutor answering from **approved company learning material**, with references, in the learner's language. | [C] |
| FR-AI-002 | Personalised learning recommendations. | [C] |
| FR-AI-003 | AI-assisted question generation — drafts only; **authorised human approval** required. | [C] |
| FR-AI-004 | AI-assisted course (curriculum/asset) drafting — drafts only; HR publishing authority applies. | [C] |
| FR-AI-005 | AI-assisted skill-gap analysis; the gap itself is computed deterministically by the LMS, AI explains and suggests. | [C] / split [P] |
| FR-AI-006 | Administrators enable/disable AI features and set usage limits. | [P] |
| FR-AI-007 | AI **learning-path recommendations**. | [C] |
| FR-AI-008 | AI never decides official results, competency levels, compliance status, attendance or certificate issuance. | [P] (follows [C] human-oversight rules) |
| FR-AI-009 | Claude is the initial provider behind provider-independent interfaces. | [C] |

## 11. Non-functional requirements

| ID | Requirement | Label |
|---|---|---|
| NFR-001 | Devices: 360 px phones to desktops, tablets and shared kiosks; touch-friendly; learner portal mobile-first. | [C] |
| NFR-002 | Languages: en, bn, hi, gu for UI and content; correct Indic rendering. | [C] |
| NFR-003 | Accessibility: WCAG 2.2 AA for learner-facing pages; low-literacy friendly (icons, audio/video). | [P] |
| NFR-004 | Security: server-side sessions, idle logout, CSRF protection, scoped RBAC, audit trail, protected files, no secrets in source. | [C] |
| NFR-005 | Privacy: data minimisation; no compensation data; alignment with the Digital Personal Data Protection Act, 2023; synthetic test data only. | [C] / DPDP alignment [P] |
| NFR-006 | Reliability: transactional changes; immutable evidence records (attempts, evaluations, issuances); tested backups. | [C] / [P] |
| NFR-007 | Performance: typical API responses < 300 ms; usable on modest plant Wi-Fi. | [P] |
| NFR-008 | Maintainability: modular monolith, normalised schema, automated tests, documented decisions. | [C] |
| NFR-009 | AI governance: provider-independent, grounded, cost-controlled, human-approved. | [C] |
| NFR-010 | Kiosks: no personal data persisted on the device after logout; sessions bound to the registered device. | [P] |

## 12. Constraints

- Technology stack as defined in `CLAUDE.md`. **[C]**
- LMS and PMS are separate applications with separate databases. **[C]**
- Organisation structure and competency scales are configurable; nothing hardcoded. **[C]**

## 13. Assumptions and open questions register

Each item blocks only the features that reference it. "Origin" shows where the question arose.

| ID | Question / assumption | Affects | Origin |
|---|---|---|---|
| Q-01 | Meaning of development-plan indicators such as **"Y"** and **"US"**, and the full list of indicator values used. Values are preserved verbatim until confirmed. | Development plans, import profile 3 | A.1 |
| Q-02 | Do all plants use the Bagnan 5-level proficiency scale? Are there other scales or per-skill level descriptions? | Competency framework | A.1 |
| Q-03 | Exact layouts of the Bagnan skill matrices (header rows, required-level rows, multiple sheets, as-of dates, merged cells). Workbooks are not in the repository workspace. | Import profile 2 | A.1 |
| Q-04 | Layout of the annual training calendars (month columns vs dates, planned counts, hours), and **which workbook is authoritative** where consolidated and departmental workbooks overlap. | Import profile 4, calendar vs actual | A.1 |
| Q-05 | Safety calendar specifics: links to statutory requirements, mandatory audiences, validity. | Import profile 5, compliance | A.1 |
| Q-06 | Format and time span of historical attendance/training records to import. | Import profile 6 | A.1 |
| Q-07 | Credential for personal-device sign-in (password, OTP) and whether staff need corporate SSO. | Identity | A, A.1 |
| Q-08 | Existing ID badges: do they carry a QR/barcode, what does it encode, can badges be re-issued with LMS tokens? | Kiosk sign-in, attendance | A.1 |
| Q-09 | Kiosk locations, supervision, PIN length and reset process. | Kiosks | A.1 |
| Q-10 | Certificate numbering format, authorised signatories, digital-signature needs; supply the Crescent certificate designs (completion, appreciation) in editable/vector form — they are **not** in the repository workspace. | Certification | A.1 |
| Q-11 | Which certifications are **operational authorisations** (e.g. crane, forklift, furnace), statutory requirements and validity periods. | Compliance, certification | A, A.1 |
| Q-12 | Definition of **CPD hours** (which activities count, caps, per-year targets). | Reports | A.1 |
| Q-13 | Financial year assumed **1 April – 31 March**. | Training operations | A.1 |
| Q-14 | Definition of **manhours** (attended hours × participants vs scheduled hours). | Training operations, reports | A.1 |
| Q-15 | Minimum attendance percentage for an event to count as completed. | Training operations, learning | A.1 |
| Q-16 | SCORM versions required (1.2 / 2004) and existing SCORM content. | Learning catalogue | A.1 |
| Q-17 | Subjective evaluation: evaluator assignment, moderation, re-evaluation/dispute process. | Assessments | A.1 |
| Q-18 | Which enrolments and nominations need manager approval; manager portal permissions. | Delivery, training operations | A.1 |
| Q-19 | Training-request workflow and approvers. | Training operations | A.1 |
| Q-20 | What the PMS is, data ownership, and integration direction. | Integration | A |
| Q-21 | Retention periods: import files and staging rows, audit log, AI logs, separated-employee records, attendance evidence. | All | A |
| Q-22 | Business priority of stages (e.g. training operations and competency before the learning catalogue). | Roadmap | A.1 |
| Q-23 | Does a catalogue of functional roles and responsibilities exist? Source of designation→role mapping. | Organisation, competency | A.1 |
| Q-24 | Is PIN re-entry acceptable as the employee's acknowledgement of a practical evaluation? | Assessments | A.1 |
| Q-25 | Is a self-service check-in by scanning a session QR acceptable without trainer confirmation? | Attendance | A.1 |
| Q-26 | Expected learning-reinforcement pattern (intervals, formats). | Learning delivery | A.1 |
| Q-27 | Unit types and levels per plant; plants structured differently? | Organisation | A |
| Q-28 | HR master-data source system and refresh frequency. | Import profile 1 | A |
| Q-29 | Management KPIs and dashboard frequency. | Reports | A |
| Q-30 | Are grades used, and relevant to learning rules? | Organisation | A |
| Q-31 | Who may commit imports; is a second approver required? | Imports | A |
| Q-32 | Official brand guidelines for the application (colours, logo files). | Frontend | A |
| Q-33 | Existing induction and safety courses and their languages. | Catalogue | A |
| Q-34 | Which compliance skills apply to which functional roles, responsibilities and locations. | Compliance | A.1 |

## 14. Future enhancements register

| ID | Enhancement |
|---|---|
| F-01 | xAPI / cmi5 content and a learning record store. |
| F-02 | Vendor / external-trainer portal access. |
| F-03 | Microsoft 365 calendar integration (beyond `.ics` invitations). |
| F-04 | SMS / WhatsApp notifications. |
| F-05 | Offline-capable learner app (PWA) for low-connectivity areas. |
| F-06 | Skill Passport export with verification QR. |
| F-07 | "Deactivate records not present in this file" import mode (separately permissioned). |
| F-08 | Cross-listing a learning path in several academies. |
| F-09 | Proctoring for final examinations. |
| F-10 | Budget and cost tracking for training events. |
| F-11 | AI-assisted grading suggestions for subjective answers (suggestions only). |
| F-12 | Digital signatures on certificates. |

## 15. Requirement ID changes in Stage A.1

| Old ID | Change |
|---|---|
| FR-CNT-001 | Revised: from "courses, modules, lessons" to the Academy → Path → Curriculum → Asset model. |
| FR-CNT-004, FR-LRN-003, FR-LRN-006, FR-ASM-001…003, FR-IMP-001 | Revised in place (scope widened). |
| FR-CMP-001…004, FR-CRT-001…003 | Moved to [competency & compliance requirements](COMPETENCY_AND_COMPLIANCE_REQUIREMENTS.md) (IDs kept, text revised). |
| FR-ADM-001, -003, -004 | Replaced by FR-RPT-001…013. |
| FR-ADM-002 | Replaced by FR-TOP-* in [training operations requirements](TRAINING_OPERATIONS_REQUIREMENTS.md). |
