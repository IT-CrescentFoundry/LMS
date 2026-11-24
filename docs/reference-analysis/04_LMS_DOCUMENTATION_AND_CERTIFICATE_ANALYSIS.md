# 04 – Existing LMS Documentation and Certificate Design Analysis

Analysis date: 2026-11-23. Analyst: Claude (read-only analysis; sources were not modified).

Sources (folder `LMS Data Reference/`):

| # | Source | Type | What it is |
|---|--------|------|------------|
| S1 | Existing LMS Details/Learning Management System (LMS) Implementation CF.docx | Use-case note | Business justification for the **UpsideLMS** implementation at CF |
| S2 | Classroom training,Event and others.docx | Admin how-to | UpsideLMS ILT: sessions, events (batches), venues, nomination, attendance, bulk upload, vendors, trainers |
| S3 | EVENT.docx | Admin how-to | UpsideLMS attendance upload, nomination (single/bulk), attendance statuses, recurring events, compliance skills |
| S4 | Competency Module.docx | Admin how-to + 2 diagrams | UpsideLMS skill levels, level sets, competency skills, roles, designations, curriculum-skill mapping |
| S5 | Curriculum and learning path.docx | Admin how-to | UpsideLMS curriculum creation/assignment, LM feedback, evaluation, learning paths |
| S6 | E-learning contents.docx | Admin how-to | UpsideLMS content types: reference material, SCORM courses, media, assignments, assessments, surveys |
| S7 | Existing LMS Details/Miscellaneous.docx | Admin how-to | Content scheduling (lock), role/designation creation, evaluation |
| S8 | Reports.docx | Admin how-to | UpsideLMS reports, scheduling, exemptions, communities, user creation, branding |
| S9 | USER MANUAL LMS.pdf (15 pp) | Learner & manager manual | "UpsideLMS Learner & Manager Manual" – learner and line-manager screens |
| S10 | Crescent LMS — Initial Layouts.pdf (9 pp) | UI mock-ups | **Proposed new Crescent LMS** screens (kiosk, mobile learner, desktop "Control Room") |
| S11 | Certificate Designs/CF Certificate Design 1.jpg, 2.jpg | Artwork | Two certificate templates |

Key finding: **S1–S9 describe the incumbent third-party product UpsideLMS** (named explicitly in S1 title and S9 title). They document *how that tool is operated*, not CF-specific business rules; many items are product features. **S10 is the only CF-specific forward design** and is compliance/safety-certification centred. Sample people/IDs in S10 and names in S11 are illustrative placeholders and are not reproduced here.

---

## 1. Per-source summaries

### S1 – Implementation use case (UpsideLMS)
- Problem: manual processes, e-mails and offline records across multiple plants (Kulgachia, Salap, Bagnan named).
- Goals: centralised content (policies, SOPs, safety, technical, soft skills); standard training across plants/departments/shifts; Day-1 onboarding assignment (HR policies, POSH, safety, code of conduct) with defined completion timelines; automatic tracking of **completion, assessment scores, certification status, pending trainings**; instant mandatory-compliance reports for audits; online refreshers to avoid stopping production; employee self-view of assigned courses, deadlines, learning history; **version-wise** SOP/process content (Process & FARO, Quality, Maintenance, Safety); analytics on skill gaps, low completion areas, department-wise needs.

### S2 – Classroom / online / hybrid training (UpsideLMS ILT)
- **Training modes**: Classroom (face-to-face), Online (Google Meet, Webex, MS Teams), Hybrid.
- **Session** fields: name, auto-create curriculum, objective, tags, learning hours, CPD points. Session is built into a **curriculum**; curriculum updates applied *prospectively* (no change to history/status) or *retrospectively* (Incomplete -> In Progress); optional "curriculum update e-mail".
- **Event = a batch** of learners for a programme. A learner in one batch cannot be nominated to another; admin can move learners between batches.
- Event lists: **Ongoing / Future / Completed** (completed shown for last 90 days). Future auto-moves to Ongoing on start date.
- Event fields: curriculum, session, start/end dates, start time, **nomination cut-off date**, **cancellation cut-off date**, holidays within event, recurrence (every weekday / weekly / monthly). Manual or bulk (template) creation.
- **Venue** (ILT setup): name, description, site location, facility type Internal/External, **seat limit (mandatory)**; inventory items linkable to venue.
- **Online venue** settings: licences, attendance **threshold** (minimum minutes attended), **approval process**, "collect manager expected" (approving manager answers 2 mandatory questions), cost, e-mail notification toggle, **self-mark attendance**, **QR-code attendance**, **auto-finalise after N days**, allow event shifting, description, reference document.
- **Event Plan** (agenda): per time slot – topic, methodology (lecture, practical, activity…), description.
- **Nomination**: select learners -> type **Nominate** (learner accepts/rejects) or **Confirmed Nomination** (admin confirms; no accept/reject). Learners receive an **automatic calendar invite**.
- Learner view: event name/date/time, details, event plan; **Change Event** (switch batch) or **Decline** if only one batch.
- **Attendance**: per learner per day – Present / Absent (others product-dependent); admin may override QR/self check-in. **Finalize Event** -> choose **Absence e-mail** and/or **Thank-you e-mail** -> event moves to Completed.
- **Bulk upload** (.xlsx): past records = Events + Attendance; future = Events + Plan + Nomination; venue = venue name (classroom) or VC licence name (online).
- Master data: Inventory, Vendor Types (training categories), Vendors (name, type), **Trainers** (name, vendor).

### S3 – EVENT
- Upload attendance to an ongoing event via template; learner identified by **Unique ID, e-mail or username** (at least one).
- Bulk nomination template pre-lists learners already assigned to the curriculum; action codes per learner.
- **Nominate** vs **Confirmed** restated (Confirmed = must complete; no accept/reject).
- Individual attendance statuses: **Present, Absent, Release from the event**.
- Recurring events (past or future) via bulk template with a "Reference Notes" sheet.
- **Compliance skill**: name + optional **expiry date**; attached to a curriculum; completing the curriculum **auto-awards** the compliance skill.

### S4 – Competency module
- Entities: **Skill Level** (Beginner, Intermediate, Expert); **Skill Level Set** (ordered set with numeric value per level: **Beginner = 1, Intermediate = 2, Expert = 3**, numeric values configurable "as per choice"); **Competency Skill** (linked to one level set).
- **Designation** = job title/level; **Role** = responsibilities under a designation. **One designation -> many roles.**
- Role defines required skills with **exactly one level per skill**. If the highest level is required, the learner must complete training for all levels to achieve it.
- Curriculum maps skills with **one level per skill**; completing a curriculum mapped at a higher level **also grants all lower levels**.
- Achievement = completion of mapped curriculum (no separate assessor rating described). Gap logic is shown only via the Competency Skill Finder report (Yes/No achieved).
- Diagram 2 shows a role x skill matrix (e.g., Skill A: Role 1 Beginner, Role 2 Expert, Role 3 Intermediate) – i.e., required level per role.
- Bulk upload for roles (role + skill + level) and designations (designation + roles + description).
- No proficiency descriptors (behavioural statements per level) are given.

### S5 – Curriculum and learning path
- Curriculum = stitched learning materials; Learning Path = stitched curriculums.
- Curriculum fields: title, referenced title, description, tags, type, **retraining (periodic reassignment)**, starts/ends on, duration (days), **expiry/grace with "extend expiry by"**, learning hours, **certificate template upload**, admin access rights, **skills mapping (competency/compliance)**, community, visibility Private (with approval process)/Public, status Available/Active/Inactive, featured window. Optional media and "learning reinforcement" campaign (send content N days after completion).
- Content types in a curriculum: e-learning, assessments (mandatory/optional), assignments, surveys/feedback, offline content, external links.
- Access link sharing with e-mail + OTP; e-mail notification templates (enable per template); announcements to selected learners.
- **Line Manager feedback form** attached into curriculum; LM completes under My Team -> Manager Feedback.
- Catalogue visibility: All / No / Specific users.
- **Assignment methods**: bulk assign/unassign (xlsx), assign multiple, **auto-assignment rules** (name, enable from/disable on, recurrence, all or specific learners by criteria e.g. department, role, location; items = curriculums, learning paths, external certifications), assign single. Learners receive e-mail + in-app notification.
- Evaluation: learner uploads assignment (allowed formats listed); admin evaluates assignment (marks; Resubmit/Fail if below pass; feedback) and short answers; bulk evaluation; learner notified by e-mail.
- Support Center (queries, Open/Close); bulk extra assessment attempts (1–10 attempts, up to 1000 rows).
- Learning path: name, Public/Private, status Active/Inactive/Unavailable, learner access, distribution, freeze status, image, short link, certificate; content settings: maintain sequence, complete minimum, complete within N days, specific end date; notifications (enrolment, reminders, completion); manual enrolment filtered by **Designation, Role, Grade**; bulk enrolment.

### S6 – E-learning contents
- Login with Learner ID + password; profile switch to Admin.
- Public requests need no approval; **Private requests must be approved by an Admin**.
- Content categories: Reference Materials (Word/PPT/PDF/link, ~10–15 MB, view vs view & download), Courses (**SCORM** only; authoring in Articulate/Camtasia; languages per upload), Media (MP3/MP4 up to 2 GB, YouTube, podcast; anti-skip playback control), Assignments (**Online** upload or **Face-to-face: practical demonstration, OJT, role play**; submit within N days, max/pass score, instructor), Assessments (question bank by template; "AI creation – not available"; MCQ, multiple response, fill blanks, match, subjective; practice/final mode; attempts; request extra attempt; negative marking; feedback; hide score), Surveys/Feedback (type Feedback or Survey).
- Common fields: status Active/Inactive/Unavailable, expiry date, tags, CPD points, learning hours, mobile-friendly, instructor.

### S7 – Miscellaneous
- Lock curriculum content until a specific date/time.
- Role and designation creation; "mapping the role and designation is very important".
- Evaluation by **instructor** (notified on submission; pending-evaluation section) or **administrator**; feedback history with timestamps on resubmission; learner e-mailed after evaluation.

### S8 – Reports and admin settings
- Reports (all exportable to XLSX; see section 4). Reports can be **favourited** and **scheduled by e-mail** (subject, recipient).
- **Exemption**: exempt learners from up to 5 curriculums/learning paths; all or specific learners; filter by **organisation tree/department**; bulk via Unique ID, Content ID, Content Name.
- Communities (title, description, type, image, topics, member invitations by e-mail).
- User creation: manual or bulk template; **welcome e-mail** only if "User Creation Email" enabled.
- Branding (colours, logo, header, login background, promotions), SMTP (pre-configured), time zone (affects time-based notifications).

### S9 – USER MANUAL LMS (UpsideLMS Learner & Manager Manual)
Identified system: **UpsideLMS**. Screens/fields:

| Screen | Fields / actions |
|--------|------------------|
| Login | username/password via e-mailed credentials; forgot password (e-mail code, security question); account lock; login-page announcements |
| Profile menu | Dashboard, App login QR, Switch to Admin, Exit |
| Learner dashboard | Overall progress (Completed, Started/Assigned, Not Started), CPD points, training hours (self-paced, ILT/VILT) |
| Notifications | bell; assigned batches, approved requests, certifications |
| Gamification | points, leaderboard |
| My Learning | AI catalogue, ongoing, completed & archived (certificates), hero content, search/filter (keyword, category, skills, status), most popular, recommended, skill-based recommendations |
| Curriculum details | contents, Start/Resume/Retake/View report, CPD, completion %, rating/review, instructor, seat time, score, dates |
| Training Calendar | daily view of enrolled events; **Plan events** (assigned) and **Catalog events** (self-enrol) |
| External certification | upload certificates earned outside; track assigned/completed |
| Transcript | enrolled, completed, in progress, not started; scores, CPD, status |
| My Queries / Support | questions to experts; report issues |
| Training Requests | request external training; approve/reject **with reason**; track status |
| Compliance Skills & Competencies | role-based skills via curriculums; skill levels; recommended curriculums |
| Knowledge | announcements, polls, documents, FAQs |
| Collaboration | communities, discussion board |
| Settings | password, photo, time zone, **language**, org details, notification preferences, diagnostics |
| **Line Manager** | Progress (team curriculum, CPD, compliance); Team Catalog (nominate members); Manager Feedback; Curriculum Requests (approve/reject, reason on reject); Batch & Training Requests (approve/reject, reason required); **Team Calendar**; team announcements; support |

### S10 – Crescent LMS Initial Layouts (proposed new system)
Brand: "Crescent LMS"; dark-navy sidebar, orange accent. Plants in header filter: **All plants, Salap, Kulgachia, Bagnan, Baroda, Head Office**.

| Page | Screen | Content |
|------|--------|---------|
| 1 | Shop-floor **kiosk sign-in** (e.g. "Salap · Kiosk 2") | language selector (EN); **scan ID badge** or Employee ID + **PIN** keypad; "Forgot PIN? Ask your supervisor to reset it"; auto sign-out when idle |
| 2 | Mobile **Today** | date · shift · department, plant; greeting; **safety status ring** (n/6 valid, expired, expiring); expired alert with booked renewal class (date, time, venue); **Do next** list (course progress + due date, renewal "refresher + test, expires in N days", practical "waiting for supervisor sign-off"); bottom nav Today / Learn / Scan / Passport / Me |
| 3 | Mobile **renewal test** | attempt x of 3; progress saved per answer; question n of 10; flag; **Listen** (audio); photo in question; MCQ |
| 4 | Mobile **Skill Passport** | name, job, department, plant, employment type (Permanent), employee ID, "Show to verify", Certificates PDF, n required; list of certificates with status Expired (renewal booked) / expiring in N days / Valid until date |
| 5 | **Practical sign-off** | checklist name + version (e.g. "checklist v2"); worker, ID, dept/plant; attempt; assessor; items scored **Pass / Needs work**; remark; **photo evidence**; worker acknowledgement; **Sign with PIN**; "Score every item to sign. Signing locks this record." |
| 6 | Public **certificate check** (QR) | VALID banner; certificate, holder (abbreviated name), plant, certificate no., issued, valid until, issued by [signatory, role]; timestamp of check; "shows only the details needed"; report a problem |
| 7 | Desktop **Control Room – Overview** (Corporate L&D, all plants) | KPIs: Compliance %, Overdue items (n past Day-14 escalation), Expiring in 30 days (n renewals already scheduled), New joiners onboarding (avg % of Day-1 path); **Compliance by plant** grid (Safety & EHS, Quality ISO/IATF, Machine & process, POSH & statutory, Overall) with thresholds **≥95% green, 85–94% amber, <85% red "!" – "Thresholds to be confirmed"**; **Escalations** ladder; New joiners last 30 days (name, plant·role, joined, Day-1 path %, next item) |
| 8 | **Compliance Matrix** (Plant HR, Salap) | filters Department, Employment type, Status, Saved view (e.g. "Melting · Shift A"); status chips Valid / Expiring / Expired / In progress / Not started; person rows x required trainings; cell shows expiry date (valid), lapse date (expired), % (in progress) or Not started; Valid n/6; **Export**; **Nudge N overdue** |
| 9 | **Certification Register** | "issued certificates are never edited, only renewed, suspended or revoked"; tabs All/Valid/Expiring/Expired/Suspended/Revoked; columns cert no., holder, certification · version, plant, valid until, status; detail panel: holder, employee ID, plant·department, **course version** (published date), issued, valid until, issued by; **Components met** (course completed n/n lessons + date; post-test passed % + attempt + "question set saved"; practical passed – signed with PIN + photos; supervisor validation – on-the-job check); latest activity (checked via public QR; issued automatically); actions **Renew, Suspend, Revoke, Download PDF**; "Issue certificate" button |

Sidebar IA: MONITOR (Overview, Compliance Matrix, Renewals) · PLAN (Training Calendar, Assignment Rules, Approvals) · BUILD (Content Library, Assessments, Certifications) · GOVERN (People, Audit & Evidence, Admin). Personas shown: **Corporate L&D (all plants)**, **Plant HR (single plant)**, worker, assessor/supervisor.

Escalation ladder shown (example data, but structure is explicit): **Day 7 -> line manager; Day 14 -> Department Head; Day 21 -> Plant HR; Day 30 -> Business Head and Corporate L&D**.

Certificate number format shown: `CFL-XXXX-XXXX` (alphanumeric). Employee ID format shown: `CF-NNNNNN`. Employment types shown: Permanent, Contract, Trainee (NATS), Trainee (NAPS).

### S11 – Certificate designs
See section 6.

---

## 2. Consolidated requirement table

Module codes: **REC** Training Records register · **SKL** Skill Matrix/Competency · **CAL** Training Calendar & sessions · **NOT** Notifications · **ORG** Organisation management · **CERT** Certificates · **RPT** Reports · **CNT** Content/e-learning · **ASM** Assessment · **SEC** Access/identity · **OOS** out of scope (first release).

Confidence: **Confirmed (source)** = stated as CF need or current CF practice; **Inferred** = derived from how CF uses UpsideLMS (current practice, but product-driven); **Proposed** = from S10 mock-ups (design intent, not yet approved); **Pending confirmation** = ambiguous or conflicting.

| # | Requirement | Source | Module | Confidence | First release? |
|---|-------------|--------|--------|------------|----------------|
| 1 | Central training record per employee: completion, assessment score, certification status, pending trainings | S1 | REC | Confirmed (S1) | Yes |
| 2 | Employee views assigned trainings, deadlines, learning history (transcript) | S1, S9 | REC | Confirmed (S1) | Yes |
| 3 | Mandatory-training compliance report on demand for audits | S1 | RPT | Confirmed (S1) | Yes |
| 4 | Multi-plant, department and shift standardisation (Salap, Kulgachia, Bagnan, Baroda, Head Office) | S1, S10 | ORG | Confirmed (S1); Baroda/HO Proposed (S10) | Yes |
| 5 | Day-1 onboarding assignment (HR policies, POSH, safety, code of conduct) with completion timeline | S1, S10 | REC/CAL | Confirmed (S1) | Yes (assignment + tracking) |
| 6 | Training modes: Classroom, Online (Teams/Meet/Webex), Hybrid | S2 | CAL | Inferred | Yes |
| 7 | Session/programme master: name, objective, learning hours, tags (CPD optional) | S2 | CAL | Inferred | Yes (CPD Pending) |
| 8 | Event = batch with start/end date, start time, nomination cut-off, cancellation cut-off, holidays, recurrence | S2, S3 | CAL | Inferred | Yes (recurrence: Pending) |
| 9 | One learner per batch of a programme; admin may move learner between batches | S2 | CAL | Inferred | Yes |
| 10 | Event states Future -> Ongoing -> Completed (auto on dates; completed on finalise) | S2 | CAL | Inferred | Yes |
| 11 | Venue master with Internal/External facility type and mandatory seat limit | S2 | CAL | Inferred | Yes |
| 12 | Online venue: attendance threshold (min duration), approval process, cost | S2 | CAL | Inferred | Partial (threshold Pending; Teams integration No) |
| 13 | Event plan/agenda per time slot: topic, methodology, description | S2 | CAL | Inferred | Pending confirmation |
| 14 | Nomination types: Nominate (accept/reject) and Confirmed | S2, S3 | CAL | Inferred | Yes |
| 15 | Manager nominates team members and approves/rejects batch & training requests with mandatory rejection reason | S9 | CAL/SEC | Inferred | Yes |
| 16 | Automatic calendar invite on nomination | S2 | NOT | Inferred | Pending (Outlook/ICS integration) |
| 17 | Learner can change batch or decline (if allowed) | S2 | CAL | Inferred | Pending confirmation |
| 18 | Attendance per learner per day: Present, Absent, Release from event; admin override of self/QR check-in | S2, S3 | REC | Inferred | Yes |
| 19 | QR-code / self check-in attendance | S2, S10 | REC | Inferred | No (later) |
| 20 | Finalise event (manual or auto after N days) locks attendance and completes event | S2 | REC | Inferred | Yes (manual); auto Pending |
| 21 | Bulk xlsx upload: past events + attendance; future events + plan + nomination; learner key = Unique ID/e-mail/username | S2, S3 | REC | Inferred | Yes (past records import is key for migration) |
| 22 | Trainer master linked to vendor; vendor types (training categories); vendors | S2 | CAL | Inferred | Yes (trainer, vendor); inventory No |
| 23 | Line Manager feedback form on a curriculum; LM completes under My Team | S5, S9 | REC | Inferred | Pending confirmation |
| 24 | Learner feedback/survey forms (type Feedback or Survey) | S6 | REC | Inferred | Pending confirmation |
| 25 | Skill levels and level sets with numeric values (Beginner 1, Intermediate 2, Expert 3; configurable) | S4 | SKL | Inferred | Yes (configurable scale) |
| 26 | Competency skill linked to one level set | S4 | SKL | Inferred | Yes |
| 27 | Required level per skill per role (one level per skill); designation -> many roles | S4 | SKL/ORG | Inferred | Yes (map to position/job role in CF org model) |
| 28 | Curriculum mapped to skill at one level; completion grants that level and all lower levels | S4 | SKL | Inferred | Pending confirmation |
| 29 | Skill gap = required level vs achieved (Yes/No per skill) | S4, S8 | SKL/RPT | Inferred | Yes |
| 30 | Compliance skill with optional expiry, auto-awarded on curriculum completion | S3 | SKL/CERT | Inferred | Yes |
| 31 | Curriculum: retraining (periodic reassignment), duration, expiry/grace with extension | S5 | REC | Inferred | Yes (validity/renewal) |
| 32 | Assignment: single, multiple, bulk xlsx, auto-assignment rules by department/role/location | S5, S10 | REC | Inferred; rules Proposed (S10) | Yes (manual + bulk); rules Pending |
| 33 | Learning path (sequence of curriculums, min to complete, complete within N days) | S5 | CNT | Inferred | No |
| 34 | Exemption of learners from curriculums (all/specific, by org tree) | S8 | REC | Inferred | Pending confirmation |
| 35 | Assignment evaluation: marks, Resubmit/Fail, feedback history; instructor notified | S5, S7 | ASM | Inferred | No |
| 36 | Assessments: question banks, MCQ etc., attempts, practice/final | S6 | ASM | Inferred | No (record score only) |
| 37 | Face-to-face assignment for practical demo / **OJT** / role play | S6 | ASM/REC | Inferred | Pending (record OJT completion: Yes) |
| 38 | E-learning content library (reference docs, SCORM, media) with versioning | S1, S6 | CNT | Confirmed (S1) for versioned SOPs | No (except document links Pending) |
| 39 | Reports (see section 4), XLSX export, favourites, scheduled e-mail | S8 | RPT | Inferred | Core reports Yes; scheduling Pending |
| 40 | External certification upload by learner | S9 | REC/CERT | Inferred | Pending confirmation |
| 41 | External training request by learner -> approve/reject with reason | S9, S8 | CAL | Inferred | Pending confirmation |
| 42 | Training calendar: learner daily view, plan vs catalogue events; manager team calendar | S9, S10 | CAL | Inferred | Yes |
| 43 | Certificate template per curriculum / learning path | S5, S11 | CERT | Inferred | Yes |
| 44 | Certificate register: number, holder, certification+version, plant, valid until, status Valid/Expiring/Expired/Suspended/Revoked; never edited, only renewed/suspended/revoked | S10 | CERT | Proposed | Yes (if certificates in scope) |
| 45 | Public QR certificate verification showing minimal data | S10 | CERT | Proposed | Pending confirmation |
| 46 | Compliance matrix (people x required trainings) with filters dept/employment type/status/saved view, export, nudge | S10 | SKL/RPT | Proposed | Yes |
| 47 | Overview KPIs and compliance-by-plant grid with RAG thresholds (95/85, to be confirmed) | S10 | RPT | Proposed | Yes |
| 48 | Overdue escalation ladder Day 7/14/21/30 to LM / Dept Head / Plant HR / Business Head + Corporate L&D | S10 | NOT | Proposed | Pending confirmation |
| 49 | Renewal management: expiring in 30 days, renewal scheduled | S10 | REC/NOT | Proposed | Yes |
| 50 | Practical sign-off checklist (versioned), Pass/Needs work, remarks, photo evidence, PIN sign, record lock, worker acknowledgement | S10 | ASM/REC | Proposed | Pending confirmation |
| 51 | Kiosk login by badge or Employee ID + PIN; supervisor PIN reset; idle sign-out | S10 | SEC | Proposed | No (later) |
| 52 | Mobile learner app (Today, Learn, Scan, Passport, Me) | S10 | CNT/REC | Proposed | No (responsive web first: Pending) |
| 53 | Employment types Permanent, Contract, Trainee NATS/NAPS as filter | S10 | ORG | Proposed | Yes |
| 54 | Multilingual UI with language switch | S9, S10, CLAUDE.md | SEC | Confirmed (CLAUDE.md) | Yes (i18n framework) |
| 55 | Audit & Evidence area | S10 | SEC | Proposed; also CLAUDE.md | Yes |
| 56 | Welcome e-mail on user creation (toggle) | S8 | NOT | Inferred | Pending |
| 57 | Gamification, CPD points leaderboard, communities, polls, AI catalogue/recommendations, SCORM, support center | S6, S8, S9 | OOS | Inferred | No |
| 58 | Login/logout activity report | S8 | RPT/SEC | Inferred | No (audit log covers) |

---

## 3. Roles and actions matrix

Legend: **C** confirmed in UpsideLMS docs (S2–S9), **P** proposed in S10, blank = not described.

| Action | Admin / L&D (Corporate) | Plant HR | Line Manager | Department / Business Head | Trainer / Instructor / Assessor | Employee (learner) |
|--------|--------------------------|----------|--------------|----------------------------|-------------------------------|--------------------|
| Create sessions, events, venues, trainers, vendors | C | | | | | |
| Bulk upload events/attendance/nominations | C | | | | | |
| Nominate learners | C | | C (Team Catalog) | | | |
| Accept/reject nomination; change batch / decline | | | | | | C |
| Approve/reject batch, training, curriculum requests (reason on reject) | C (private curriculum approval) | | C | | | |
| Raise training request (external) | | | C (team) | | | C |
| Mark / override attendance; finalise event | C | | | | | C (self/QR check-in) |
| Provide LM feedback on curriculum | | | C | | | |
| Fill feedback/survey | | | | | | C |
| Evaluate assignments/short answers | C | | | | C (instructor notified) | |
| Practical sign-off with PIN | | | | | P (assessor/supervisor) | P (acknowledge) |
| Supervisor validation (on-the-job check) | | | P | | P | |
| Create skills, level sets, roles, designations, skill mapping | C | | | | | |
| View team progress, compliance, team calendar | | P | C | | | |
| View own transcript, calendar, skills, certificates | | | | | | C |
| Upload external certification | | | | | | C |
| Exempt learners | C | | | | | |
| Issue / renew / suspend / revoke certificates | P | | | | | |
| View compliance matrix & nudge overdue | P (all plants) | P (own plant) | | | | |
| Receive escalations | P (Day 30) | P (Day 21) | P (Day 7) | P (Day 14 Dept Head; Day 30 Business Head) | | |
| Reset kiosk PIN | | | | | P (supervisor) | |
| Run / schedule reports | C | P | | | | |

---

## 4. Reports list

| Report | Source | Content / fields named | Filters named | First release? |
|--------|--------|------------------------|---------------|----------------|
| Event Details Report (attendance) | S8 | attendance per batch, online and classroom | Curriculum, Session, multiple Batches | Yes |
| Curriculum Master Report | S5 | all curriculums (export) | — | Yes (programme master) |
| Content Masterfile | S6 | all contents | Name | No |
| User Details Report | S8 | all users enrolled | — | Yes (employee list exists) |
| Competency Skill Finder Report | S8 | per learner per skill, Skill Gap section: Yes = achieved, No = not achieved | — | Yes |
| Compliance Report | S8 | each learner's compliance skills and compliance status | — | Yes |
| External Certifications Report | S8 | Summary: category-wise completion; Data: learner-wise | — | Pending |
| Training Request Report | S8 | requests from learners and managers | — | Pending |
| CPD Report | S8 | CPD points per learner per curriculum | — | No (CPD Pending) |
| Login/Logout Report | S8 | login/logout events per learner (logout only if signed out) | — | No |
| Gamification Progress Report | S8 | points and badges | — | No |
| Transcript (learner) | S9 | enrolled, completed, in progress, not started; scores, CPD, status | — | Yes |
| Manager Progress view | S9 | team curriculum, CPD, compliance | team | Yes |
| Overview dashboard | S10 | Compliance %, overdue, expiring 30 days, new joiners onboarding %, compliance by plant x category, escalations, new joiners list | plant | Yes |
| Compliance Matrix | S10 | person, employee ID, position, required trainings with expiry/lapse/%, valid n/m | plant, department, employment type, status, saved view | Yes |
| Certification Register | S10 | cert no., holder, certification+version, plant, valid until, status | status tabs, plant | Yes (if certificates in scope) |
| Renewals | S10 (menu only) | not designed | — | Pending |
| Report scheduling & favourites | S8 | subject, recipient e-mail | — | Pending |

All UpsideLMS reports are exported as XLSX.

---

## 5. Notification events

| Event | Recipient | Channel | Source | Confidence |
|-------|-----------|---------|--------|------------|
| Nomination / batch assigned | learner | calendar invite (auto) + in-app bell | S2, S9 | Inferred |
| Curriculum assigned | learner | e-mail + in-app | S5 | Inferred |
| Curriculum content updated | learners | optional e-mail | S2 | Inferred |
| Event attendance finalised – absent | absentees | Absence e-mail | S2 | Inferred |
| Event attendance finalised – attended | attendees | Thank-you e-mail | S2 | Inferred |
| Session e-mail alerts (toggle per online venue) | participants | e-mail | S2 | Inferred |
| Request approved/rejected | requester | in-app (+ reason) | S9 | Inferred |
| Certification issued | learner | in-app | S9 | Inferred |
| Assignment submitted | instructor | notification | S7 | Inferred |
| Assignment evaluated | learner | e-mail | S5, S7 | Inferred |
| Learning path enrolment / reminders / completion | learner | configurable | S5 | Inferred |
| Learning reinforcement content N days after completion | learner | e-mail | S5 | Inferred |
| Announcement | selected learners / team | in-app/e-mail | S5, S9 | Inferred |
| Community invitation | learner | e-mail | S8 | Inferred |
| User created (welcome) | new user | e-mail (toggle) | S8 | Inferred |
| Scheduled report | configured e-mail | e-mail | S8 | Inferred |
| Certificate expiring / renewal due (expires in N days) | worker | in-app Today | S10 | Proposed |
| Renewal class booked | worker | in-app Today | S10 | Proposed |
| Manual "nudge" of overdue people | overdue employees | not specified | S10 | Proposed |
| Overdue escalation Day 7 / 14 / 21 / 30 | LM / Dept Head / Plant HR / Business Head + Corporate L&D | not specified | S10 | Proposed |
| Pending approvals count | approver | badge | S10 | Proposed |

---

## 6. Certificate design specification (S11)

| Attribute | Design 1 | Design 2 |
|-----------|----------|----------|
| Pixel size | 2000 x 1414 px (JPEG) | 2000 x 1414 px (JPEG) |
| Orientation / aspect | Landscape, 1.414:1 = **A4 landscape** | same |
| Frame | White inner panel inside a navy outer border; double thin gold rule frame with stepped/notched corner ornaments | Navy and gold flowing **curved wave bands** at left and right edges; single thin orange-gold rectangular rule; light grey silk/swoosh background |
| Accent shapes | Orange + gold diagonal stripes at top-centre-right, left edge, bottom-centre-right and right edge | Gold/orange ribbon lines inside the waves |
| Logo | "CRESCENT" wordmark (navy, orange accent on the second C) top centre | same position |
| Title | "CERTIFICATE" – large bold navy uppercase, centred | same |
| Subtitle | "OF APPRECIATION" – gold, letter-spaced uppercase, thin grey rule below | same |
| Body | "This is to certify that" / **[Employee Name]** (bold, large, black) / "has successfully completed the Curriculum" / **[Training Name]** (placeholder "Crescent Foundry Training Name") / "on [DD/MM/YYYY]" | identical text |
| Seal | Gold rosette with ribbons, bottom centre between signatures | Larger gold rosette, **top right** corner |
| Signatures | Two signature lines, bottom left and bottom right: [Signatory name] bold grey + "Position Here" | identical |
| Fonts (apparent) | Geometric sans (Montserrat-like) for title/signatories; humanist sans (Open Sans-like) for body | same |

Approximate brand colours (visual estimate, confirm with brand guide): navy **#1D3E6F**, gold/amber **#FBB424**, light gold frame **#F7C95C**, orange **#F37021**, body text **#111111**, signatory grey **#4A4A4A**, rule grey **#B0B0B0**.

Placeholders present: employee name, training/curriculum name, completion date, two signatories with position.
Placeholders **absent** (needed by S10 register/verification): certificate number, employee ID, plant/department, training hours, training dates range, trainer, validity/expiry date, course version, QR verification code, issue date distinct from completion date.

Recommendation (Proposed): treat both as selectable templates rendered server-side to A4-landscape PDF; add an unobtrusive footer band for certificate number, employee ID, valid-until and QR code; signatory slots configurable by role (e.g., Head of HR/L&D, Plant Head) – names not taken from samples.

---

## 7. Conflicts and gaps between sources

| # | Conflict / gap | Sources | Impact |
|---|----------------|---------|--------|
| 1 | S1–S9 describe UpsideLMS product behaviour; S10 proposes a different, compliance-first CF system. Unclear which UpsideLMS behaviours CF actually relies on vs. merely available | S1–S9 vs S10 | Scope of first release |
| 2 | UpsideLMS "Role/Designation" (designation -> many roles) vs CF architecture (org units, positions, job families separate) | S4, S7 vs CLAUDE.md | Map role/designation to position/job role; do not hardcode |
| 3 | Competency achievement is binary via curriculum completion (S4) vs. S10 evidence-based certification (course + test + practical + supervisor validation) | S4 vs S10 | Skill-matrix rating model |
| 4 | Proficiency scale: S4 uses 3 levels (Beginner/Intermediate/Expert = 1/2/3) without descriptors; S10 shows no levels, only valid/expired status | S4 vs S10 | Need CF-approved scale and descriptors |
| 5 | Certificate artwork says "Certificate of Appreciation" and "completed the Curriculum"; S10 needs compliance certificates with number, validity, version, QR | S11 vs S10 | Template wording/fields |
| 6 | Completed events kept only 90 days in list (S2) vs permanent audit-grade training register (S1, S10) | S2 vs S1/S10 | Register must retain history indefinitely |
| 7 | Date format "06/02/2017" ambiguous (DD/MM vs MM/DD) | S11 | Fix locale format (e.g., 06 Feb 2017) |
| 8 | Attendance statuses: S2 Present/Absent "(other options depending on system)"; S3 adds "Release from the event" | S2, S3 | Confirm full status list |
| 9 | Plants: S1 names 3 plants; S10 shows 5 locations incl. Baroda and Head Office | S1 vs S10 | Org data must be configurable anyway |
| 10 | S2 "Nomination Still / Cancellation Still" labels (likely "till") | S2 | Interpretation: cut-off dates |
| 11 | Escalation days and RAG thresholds in S10 are labelled example/"to be confirmed" | S10 | Do not hardcode; make configurable |
| 12 | S10 certificate-check text extraction places dates under shifted labels (Issued/Valid until/Issued by); mock-up only | S10 p6 | No action; confirm field order in UI |
| 13 | Manager approval of nominations: S2 "approval process" per venue/session vs S9 manager approves batch requests – exact approval chain undefined | S2, S9 | Approval workflow design |

---

## 8. Open questions

1. Which UpsideLMS features are actively used today (ILT events, competency module, compliance skills, LM feedback, CPD)? Will UpsideLMS data (events, attendance, skills) be migrated, and in what export format?
2. Approved proficiency scale: keep Beginner/Intermediate/Expert (1–3), or a different number of levels? Are behavioural descriptors per level required? Is the achieved level set by curriculum completion, assessor rating, or both?
3. Is OJT recorded as a training type in the register (S6 treats it as a face-to-face assignment)? Which training types should the register list (Classroom, Online, Hybrid, OJT, External, Induction…)?
4. Training effectiveness: S5 has LM feedback forms but no defined effectiveness evaluation (e.g., post-training review after N days). Is effectiveness evaluation required, by whom and when?
5. Nomination approval chain: does a manager approve before HR confirms? Is self-nomination from catalogue allowed for classroom sessions?
6. Calendar integration: is an Outlook/Teams calendar invite (ICS or Microsoft Graph) required in release 1, or LMS-internal calendar only?
7. Certificates: which template is preferred (1 or 2)? Change "Certificate of Appreciation" to "Certificate of Completion/Competence" for compliance trainings? Which signatory roles? Is QR verification required?
8. Escalation ladder (Day 7/14/21/30) and RAG thresholds (95/85): confirm values and recipients.
9. Is kiosk/badge + PIN login and practical sign-off with photo evidence in scope for the first release?
10. Retention: how long must attendance and training records be kept (audit/IATF requirements)?
11. Exemptions: which roles can exempt employees, and must a reason be recorded?
12. Does an HRMS feed exist (no source mentions HRMS integration explicitly)? S8 only describes manual/bulk user creation.

---

## 9. Scope classification summary

| First release (records, skill matrix, calendar, notifications, org) | Later / out of scope |
|----------------------------------------------------------------------|----------------------|
| Training programme/session master, batches/events, venues, trainers, vendors | E-learning authoring, SCORM player, media hosting |
| Nomination (Nominate/Confirmed), manager approval with reason, batch change | Question banks, online assessments, assignment evaluation |
| Attendance (Present/Absent/Released), finalise, bulk import incl. historical records | Learning paths, learning reinforcement, communities, polls, FAQs |
| Training records register, transcript, validity/expiry and renewal tracking | Gamification, leaderboard, CPD points (pending) |
| Configurable proficiency scale, skills, required level per position/role, gap view | AI catalogue/recommendations, AI question generation |
| Compliance matrix, overview dashboard, core reports with XLSX export | Kiosk badge/PIN login, mobile app, QR attendance |
| In-app + e-mail notifications for nomination, assignment, approval, attendance, expiry | Practical sign-off with photos (pending), public QR verification (pending) |
| Certificate generation from approved template (A4 landscape) | Support center, login/logout report, branding UI |
