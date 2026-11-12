# Training Operations Requirements

| | |
|---|---|
| **Status** | Stage A.1 requirements. **Nothing in this document is implemented.** |
| **Owns** | Financial-year calendars, planned activities, training programmes, events, batches, sessions, venues, platforms, trainers, vendors, nominations, participation, attendance, finalisation, recurrence, notifications, training hours/manhours, feedback, training requests, historical training records. |
| **Labels** | **[C]** confirmed · **[P]** proposed · **[A]** assumption (register `Q-xx` in [product requirements §13](LMS_PRODUCT_REQUIREMENTS.md)) · **[F]** future |
| **Related** | [Product requirements](LMS_PRODUCT_REQUIREMENTS.md) (reports FR-RPT-002, -009, -010, -011, -012) · [System architecture §6](../architecture/LMS_SYSTEM_ARCHITECTURE.md) · [Database design §10](../database/LMS_DATABASE_DESIGN.md) · [Import profiles 4–6](../database/EXCEL_IMPORT_PROFILES.md) |

---

## 1. Principles

1. **Training operations is a dedicated domain**, separate from the learning catalogue. It plans and runs instructor-led, online, hybrid and on-the-job training. **[C]**
2. **Planned and actual are separate records.** **[C]**
   - A **calendar entry (planned training activity) is never a completed event.**
   - A **planned participant count is never individual attendance.**
   - Reports compare plan and actual; they never merge them.
3. **Individual attendance is the only basis** for an employee's training hours, event completion and any downstream learning, competency or compliance effect. **[C]** / downstream effects **[P]**
4. **Finalisation locks an event.** After finalisation, attendance changes require an authorised, audited correction. **[C]** / lock **[P]**
5. **Provenance is kept** for every imported calendar line and attendance record. **[C]**

## 2. Concepts

| Concept | Definition | Label |
|---|---|---|
| **Financial year (FY)** | Configurable planning year; default 1 April – 31 March. | [C]; dates [A] Q-13 |
| **Training calendar** | A plan for an FY with a **scope**: company, location/plant, or department (org unit), and a type (e.g. general, safety). Versioned and approved. | [C] |
| **Planned training activity** | One calendar line: topic, programme (if known), planned period, mode, planned hours, **planned participant count**, target audience, planned trainer/vendor. | [C] |
| **Training programme** | A reusable definition of an instructor-led or OJT training (title, objectives, standard duration, default mode), linking calendar lines, events and curricula across years. | [P] |
| **Training event** | An **actual** training occurrence, optionally linked to the planned activity it fulfils. | [C] |
| **Batch** | A cohort within an event (e.g. shift-wise batches). | [C] |
| **Training session** | A dated, timed slot of a batch at a venue and/or on an online platform. Attendance is per session. | [C] |
| **Delivery mode** | Classroom, online, hybrid, on-the-job (OJT). | [C] |
| **Venue** | A physical training location (room, shop-floor area) at a location, with capacity. | [C] |
| **Online platform** | A virtual delivery tool (e.g. Teams, Zoom) with per-session join details. | [C] |
| **Trainer** | Internal (an employee) or external (person from a vendor or independent). | [C] |
| **Vendor** | An external training provider. | [C] |
| **Event plan** | The event's objectives, agenda, materials, prerequisites and logistics. | [C] |
| **Nomination** | A proposal that an employee attends an event/batch (by self, manager, coordinator, plan or allocation), with approval status. | [C] |
| **Participant** | A confirmed participant of a batch. | [C] |
| **Attendance record** | One employee's attendance for one session: status, times, minutes, capture method. | [C] |
| **Check-in** | Self or assisted attendance capture by QR (session QR or badge QR). | [C] |
| **Attendance correction** | An authorised, reasoned change to an attendance record, with before/after values. | [C] |
| **Finalisation** | Closing an event: attendance locked, hours computed, downstream effects triggered. | [C] |
| **Event series** | Recurring events generated from a recurrence rule. | [C] |
| **Training hours / manhours** | Per-employee attended hours; manhours = sum of attended hours across participants. | [C]; definition [A] Q-14 |
| **Training feedback** | Participant feedback (survey) for an event. | [C] |
| **Training request** | A request for training raised by an employee or manager, with approval. | [C] (report FR-RPT-012) |
| **Historical training record** | An imported past training fact for an employee where the original event cannot be reconstructed. | [P] |

## 3. Lifecycles **[P]**

```text
Training calendar:   draft ─► submitted ─► approved ─► published ─► closed (FY end)
Planned activity:    planned ─► scheduled (≥1 event linked) ─► delivered (≥1 event finalised)
                        └──► postponed / cancelled                (planned record is never deleted)
Training event:      draft ─► scheduled ─► in progress ─► completed ─► finalised
                        └──► postponed / cancelled                      └─► reopened (authorised) ─► finalised
Nomination:          proposed ─► approved ─► confirmed (participant) ─► attended / no-show
                        ├──► rejected      └──► withdrawn / waitlisted
Attendance record:   expected ─► present / partial / absent / excused   (corrections create audited revisions)
```

## 4. Functional requirements

### 4.1 Calendars and planned activities
| ID | Requirement | Label |
|---|---|---|
| FR-TOP-001 | **Financial-year training calendars**. | [C] |
| FR-TOP-002 | **Location-specific** and **department-specific** calendars, plus a company/consolidated view. | [C] |
| FR-TOP-003 | **Planned training activities** with planned period (month or dates), mode, hours, planned participant count, target audience, planned trainer/vendor, owner department. | [C] / fields [P] |
| FR-TOP-004 | Calendar approval workflow; published calendars are visible according to scope. | [P] |
| FR-TOP-005 | A consolidated view combines location and department calendars **without duplicating** activities that appear in both; overlaps are resolved as duplicate candidates with recorded decisions (see import profile 4). | [C] / mechanism [P]; authority [A] Q-04 |
| FR-TOP-006 | Safety training calendars as a calendar type, linkable to compliance skills. | [C] / link [P]; [A] Q-05 |
| FR-TOP-007 | Planned activities can be linked to a training programme, curriculum or compliance skill; unlinked imported lines remain valid. | [P] |

### 4.2 Programmes, events, batches and sessions
| ID | Requirement | Label |
|---|---|---|
| FR-TOP-010 | Training programmes as reusable definitions. | [P] |
| FR-TOP-011 | **Training events** with mode (**classroom, online, hybrid, OJT**), organising unit, location, status and **event plan**. | [C] |
| FR-TOP-012 | Events may fulfil a planned activity (one activity → zero or more events) or be unplanned (ad hoc); unplanned events are flagged in Calendar vs Actual. | [C] / cardinality [P] |
| FR-TOP-013 | **Batches** within events and **sessions** within batches, each session with start/end time, venue and/or online platform and trainers. | [C] |
| FR-TOP-014 | **Venues** (with capacity) and **online platforms** as managed records; venue double-booking warnings. | [C] / warnings [P] |
| FR-TOP-015 | **Internal and external trainers**, and **vendors**. | [C] |
| FR-TOP-016 | **Recurring events** from a recurrence rule (e.g. monthly safety induction); each occurrence is an independent event. | [C] / [P] |

### 4.3 Nominations and participation
| ID | Requirement | Label |
|---|---|---|
| FR-TOP-020 | **Nominations** by self, manager, coordinator, development plan or learning allocation. | [C] / sources [P] |
| FR-TOP-021 | Nomination approval where configured; capacity limits and waitlists. | [P]; approvals [A] Q-18 |
| FR-TOP-022 | **Confirmed participation** per batch, separate from nominations and from planned counts. | [C] |

### 4.4 Attendance
| ID | Requirement | Label |
|---|---|---|
| FR-TOP-030 | **Individual attendance** per participant per session: present, partial (minutes), absent, excused. | [C] |
| FR-TOP-031 | Capture methods: trainer/coordinator entry, **attendance upload** (import profile 6), **QR self-check-in**, badge scan at a kiosk or trainer device. | [C] |
| FR-TOP-032 | Session QR codes are time-limited and rotate; check-in requires the employee to be signed in (or badge + PIN at a kiosk). | [P]; self-service acceptance [A] Q-25 |
| FR-TOP-033 | Walk-in attendees (not nominated) can be added by the trainer/coordinator and are flagged. | [P] |
| FR-TOP-034 | **Attendance correction by authorised administrators** only, with reason; before/after values audited. | [C] |
| FR-TOP-035 | Attendance uploads are validated (unknown employee codes, duplicates, sessions outside event dates) and previewed before commit. | [C] |

### 4.5 Finalisation, hours and feedback
| ID | Requirement | Label |
|---|---|---|
| FR-TOP-040 | **Event finalisation** by an authorised user: locks attendance, records participant count and manhours, marks the linked planned activity as delivered. | [C] / effects [P] |
| FR-TOP-041 | On finalisation, eligible participants (meeting minimum attendance) are marked as having completed linked curriculum items (classroom/OJT), which may trigger competency/compliance/certificate rules. | [P]; threshold [A] Q-15 |
| FR-TOP-042 | Reopening a finalised event requires elevated permission and a reason; downstream effects are recalculated and audited. | [P] |
| FR-TOP-043 | **Training hours** per employee and **manhours** per event, unit, location and FY. | [C]; definition [A] Q-14 |
| FR-TOP-044 | **CPD hours** classification of activities. | [C]; definition [A] Q-12 |
| FR-TOP-045 | **Training feedback** surveys sent to participants after the event; results visible to trainers and coordinators. | [C] / [P] |

### 4.6 Notifications and calendars
| ID | Requirement | Label |
|---|---|---|
| FR-TOP-050 | **Calendar notifications** to nominees, participants and trainers on scheduling, changes and cancellation, with `.ics` attachments. | [C] / `.ics` [P] |
| FR-TOP-051 | Learners see their sessions in the learning calendar (learner portal). | [C] |
| FR-TOP-052 | Microsoft 365 calendar integration. | [F] F-03 |

### 4.7 Training requests and history
| ID | Requirement | Label |
|---|---|---|
| FR-TOP-060 | **Training requests** by employees or managers (topic/programme, justification, employees), with approval and linkage to the planned activity or event that fulfils them. | [C] (report) / workflow [P]; [A] Q-19 |
| FR-TOP-061 | **Historical training records** imported where events cannot be reconstructed; read-only, with provenance; included in Employee Training History. | [C] (import) / entity [P]; [A] Q-06 |
| FR-TOP-062 | Imported historical attendance with sufficient event detail is loaded as finalised historical events with attendance, flagged as imported. | [P] |

## 5. Calculations **[P]** (to be confirmed)

| Metric | Proposed definition | Confirm |
|---|---|---|
| Session minutes | `ends_at − starts_at` of the session | — |
| Employee attended minutes | Recorded minutes for *present*/*partial* sessions (full session minutes when *present*) | — |
| Employee training hours | Σ attended minutes ÷ 60, finalised events only | Q-14 |
| Event manhours | Σ employee training hours over participants | Q-14 |
| Completion eligibility | Attended minutes ≥ X % of scheduled minutes (default 80 %) | Q-15 |
| Calendar vs Actual | Per planned activity: planned count/hours vs finalised events' participant count/manhours; plus unplanned events | Q-04 |

## 6. Related reports and imports

- Reports ([product requirements §8](LMS_PRODUCT_REQUIREMENTS.md)): Event Attendance (FR-RPT-002), Employee Training History (FR-RPT-009), Training Calendar vs Actual (FR-RPT-010), Training Hours & CPD (FR-RPT-011), Training Requests (FR-RPT-012).
- Imports ([profiles](../database/EXCEL_IMPORT_PROFILES.md)): profile 4 (annual calendars), profile 5 (safety calendars), profile 6 (attendance and historical records).
- Open questions: Q-04, Q-05, Q-06, Q-12, Q-13, Q-14, Q-15, Q-18, Q-19, Q-25.
