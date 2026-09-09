**Smart Timetable Generator (PS1)**

Complete Project Document

*Idea, requirements, architecture, and implementation specification*

Version 2.1 (IDE Build-Ready)

Supersedes the earlier SRS, System Design, and Idea Document drafts

**Document control**

This document is the single source of truth for the project. Every open question and inconsistency identified across the earlier drafts has been resolved and is reflected directly in the sections below (resolution log in Section 24). A second review pass, aimed specifically at whether an engineer or coding agent could build directly from this document without inventing unstated decisions, closed a further set of schema, API, and access-control gaps; that pass is logged in Section 32, and its content lives in Sections 27–31. Section 31 lists what intentionally remains normal engineering latitude rather than a gap.

Table of Contents

**PART A — THE IDEA**

1\. Problem Statement (PS1)

*“Smart Timetable Generator — develop an intelligent timetable generation system that creates conflict-free schedules while considering faculty availability, classrooms, laboratories, batches, electives, and scheduling constraints.”*

2\. The Big Idea

A multi-tenant SaaS “scheduling brain.” An institution — school, college, or university — describes its reality once: who can teach what to whom, which rooms and labs exist and what's in them, how cohorts split into batches and electives, and which rules must never be broken. The system hands back a timetable that is mathematically guaranteed conflict-free across regular classes, lab batches, electives, and exams — not “probably correct,” but independently verified correct — and keeps it correct as reality changes, without a human re-checking every cell by hand.

The differentiator is not “it draws a grid.” It is that the grid is provably clash-free at a scale no human scheduler can hold in their head, re-proved cheaply every time something changes.

3\. Users and Roles

| **User**                              | **Role in the workflow**                                                                                                                |
|---------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| Platform operator                     | Onboards a new institution as an isolated tenant. One-time, invisible to the institution afterward.                                     |
| Institution admin                     | Primary hands-on user. Heavy setup once per term, light ongoing maintenance after.                                                      |
| Department head / timetable committee | Scoped setup; performs the mandatory review-and-approve step before every publish (Section 6, Section 8.9).                             |
| Faculty                               | Views own schedule, reports absence, sees substitutions. May hold profiles at more than one tenant under a single login (Section 15.3). |
| Student                               | Views own individualized schedule, reflecting their specific elective enrollment.                                                       |

4\. Complete Workflow

Three time-scales: one-time onboarding, a once-per-term setup-to-publish cycle, and a continuous day-to-day operating loop. The exam module runs the same cycle again, independently, near exam time.

4.1 One-time: onboarding

- Platform operator creates the tenant, provisions isolated data, and creates the institution's first admin account.

- Admin configures institution type, campus structure, period/day template, and which optional modules are enabled for this tenant (Section 8.1, FR-1.5).

4.2 Once per term: the core cycle

**Setup + import** *— master data, constraint rules (structured or natural-language, Section 5), and pre-resolved elective enrollment.*

↓

**Generate** *— solver runs (sync for small tenants, async job for large ones); produces a candidate timetable plus the load-verification report.*

↓

**Review + approve (mandatory)** *— the timetable committee or admin must explicitly review and approve every draft before it can be published — there is no auto-publish path for any tenant, regardless of size (Section 6, resolved item 1).*

↓

**Publish** *— an explicit act, gated on the approval above. Raw solver output is denormalized into per-view read tables; affected faculty/students are notified.*

↓

**Consume + operate** *— faculty/students view their schedule; disruptions are handled as lightweight patches; larger changes loop back to Generate, incrementally.*

4.3 Running in parallel: exam scheduling

The exam module follows the identical cycle, reusing the same rooms/cohorts/faculty data, with its own constraint set (Section 10, H12–H14) and its own outputs (seating charts, invigilator rosters).

5\. How Non-Technical Input Is Understood

Two genuinely different problems, handled differently rather than forced through one mechanism.

5.1 Structured setup data (the majority of all input)

Faculty lists, room capacities, course-hour requirements, batch definitions: entered through guided forms and templated bulk-import spreadsheets with constrained fields (dropdowns, not free text), validated immediately with row-level, specific errors. No interpretation step, no ambiguity risk.

5.2 Natural-language constraint rule builder (in scope for v1)

This ships as part of the hackathon build, not as a future roadmap item — confirmed and reflected as FR-5.5 (Section 8.5) and detailed as a technical pipeline in Section 20. The governing principle stays the same: the system never silently acts on its own interpretation of ambiguous input. What is parsed from a sentence is shown back to the admin as an explicit, deterministically-rendered structured statement before it is applied:

*You said: “no faculty teaches more than 4 periods a day.” I'll apply this as: faculty daily period cap = 4, tenant-wide. Apply this rule? \[Confirm\] \[Edit\]*

If wrong, the admin corrects the structured version directly rather than re-wording the sentence. See Section 20 for exactly how this is built.

5.3 The same discipline runs in the other direction

When the system cannot do something — infeasible configuration, failed generation — the explanation names the specific conflicting faculty/course/cohort in plain language (FR-6.3), not solver internals.

**PART B — REQUIREMENTS**

6\. Scope

6.1 In scope (v1)

- Multi-tenant SaaS platform with isolated data per institution.

- Core timetable generation engine producing provably conflict-free schedules for faculty, rooms, labs, and cohorts.

- A configurable constraint rule engine — both a structured rule builder and a natural-language rule builder with confirm-before-commit (Section 5.2, Section 20).

- Batch and laboratory scheduling, including parallel batch-splitting with shared-resource capacity limits, and optional multi-period (“block”) course scheduling where a course needs it (Section 8.2, FR-2.5).

- Elective-based cohort scheduling from pre-resolved enrollment data (imported or entered directly).

- An integrated exam-timetable module sharing the class-timetable module's data model and constraint engine.

- A mandatory draft → review → publish workflow for every tenant, with no auto-publish bypass.

- Substitution management, multi-view reporting/export, notifications, RBAC, and full audit logging.

- Per-tenant module toggles — electives and exam scheduling can be enabled or disabled per institution (Section 8.1, FR-1.5).

- A single login identity that can be associated with staff profiles at more than one tenant, while each tenant's scheduling data remains fully isolated (Section 15.3, FR-1.6).

6.2 Out of scope (v1)

- Elective preference collection and automated seat-allotment engine — enrollment is treated as a resolved input.

- Finance/fee management, attendance tracking (beyond integration hooks), hostel/mess scheduling.

6.3 Everything previously open is now closed

See Section 24 for the full resolution log. In summary: review-before-publish is mandatory for all tenants; the natural-language rule builder is in v1; both row-level and schema-per-tenant isolation are included; multi-period course blocks are supported where a course needs them; rooms/labs are confirmed hard-constrained resources; elective/exam modules are explicitly toggleable per tenant; and cross-tenant faculty identity is supported at the auth layer.

7\. Core Data Model

| **Entity**                        | **Description**                                                                                                                                                                                                                                       |
|-----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Identity                          | A single person-level login (email/SSO), independent of any tenant. May be linked to staff profiles at multiple tenants (Section 15.3).                                                                                                               |
| Tenant                            | A single institution (or campus); isolated data and configuration; carries an enabled_modules flag set (e.g., electives, exams) per FR-1.5.                                                                                                           |
| Department / Program              | Organizational unit under a tenant; courses and faculty roll up to it.                                                                                                                                                                                |
| Academic Term                     | Year, semester, or term boundary.                                                                                                                                                                                                                     |
| Course / Subject                  | Core, elective, or lab/practical course; carries credit value, contact-hours/week, batch-split flag, and a block_size attribute (default 1; \>1 means the course occupies that many consecutive periods as one atomic unit, per FR-2.5).              |
| Cohort / Class / Section          | Fixed group (school-style) or variable-membership group formed after elective enrollment (college-style).                                                                                                                                             |
| Batch                             | Sub-division of a cohort for parallel lab/practical sessions.                                                                                                                                                                                         |
| Elective Section                  | Schedulable group formed from resolved elective enrollment for one elective offering.                                                                                                                                                                 |
| Staff Profile                     | A tenant-scoped record linking one Identity to one Tenant, carrying eligibility list, employment type, workload cap, availability windows, and reserved non-teaching blocks.                                                                          |
| Faculty-Course-Cohort Eligibility | Explicit mapping of who may teach what to whom, scoped to a Staff Profile.                                                                                                                                                                            |
| Room                              | Classroom, lab (with equipment tags), seminar hall, auditorium, or ground/PT space; capacity and accessibility attributes; confirmed as a hard-constrained resource (Section 24, item 5).                                                             |
| Time Slot / Period Template       | Configurable per tenant/campus; periods per day may vary by weekday; multiple shifts supported.                                                                                                                                                       |
| Constraint Rule                   | A hard or soft rule, scoped to tenant/department/course/faculty/room; carries a weight for soft rules, a source (structured or natural-language), and, if natural-language, the raw input text (Section 20).                                          |
| Enrollment Record                 | Resolved student ↔ elective-section mapping, imported per term.                                                                                                                                                                                       |
| Exception Calendar                | Holidays, exam periods, institution events, half-days.                                                                                                                                                                                                |
| Substitution Log                  | Date, absent staff profile, substitute, affected slot(s).                                                                                                                                                                                             |
| Timetable Version                 | Draft → under-review → published → archived. Every tenant passes through under-review; there is no direct draft-to-published transition (Section 24, item 1).                                                                                         |
| Exam Session                      | A scheduled exam instance for a course/cohort, with assigned room(s), seating, and invigilator(s); grouped under an Exam Timetable Version that follows the same mandatory draft → review → publish states as a class Timetable Version (Section 28). |

8\. Functional Requirements

8.1 Tenant & Institution Management

- FR-1.1: Onboard a new tenant with isolated data, configuration, and admin account(s).

- FR-1.2: Configure institution type (school / college / university / coaching institute).

- FR-1.3: Configure the period/day template per institution or campus, including variable periods per weekday and multiple shifts.

- FR-1.4: Support multiple campuses under a single tenant, each a row in the campus table (Section 28), with rooms scoped to a campus.

- FR-1.5: Enable or disable the elective module and the exam module independently, per tenant, at onboarding or later — both modules exist in the platform for every tenant but are only active where enabled.

- FR-1.6: Support one Identity (login) holding Staff Profiles at more than one tenant; each Staff Profile's scheduling data remains fully isolated to its own tenant (Section 15.3).

8.2 Master Data Management

- FR-2.1: CRUD for departments, courses, faculty, rooms/labs, cohorts/classes, batches.

- FR-2.2: Bulk import/export (CSV/Excel) for all master data entities, against the fixed column templates in Section 29.4.

- FR-2.3: Define faculty–course–cohort eligibility explicitly, independent of general subject qualification.

- FR-2.4: Define required weekly/term contact hours per (course, cohort); validate configuration consistency before generation.

- FR-2.5: Support declaring a course's block_size (default 1). Where block_size \> 1, the solver schedules that course as one atomic assignment spanning that many consecutive periods, in the same room, on the same day; this applies only to courses that declare it — it is not assumed for the general case (Section 24, item 4).

8.3 Elective-Based Cohort Scheduling

- FR-3.1: Import or enter a pre-resolved elective enrollment dataset per term, including cross-department electives.

- FR-3.2: Treat each elective section as a schedulable cohort feeding directly into the generation engine.

- FR-3.3: Generate a correct individual timetable per student once elective enrollment is known.

- FR-3.4: Support re-importing an updated enrollment dataset and re-solving only the affected portion (see FR-6.4).

8.4 Batches & Laboratories

- FR-4.1: Split a cohort into N batches for a lab/practical course, scheduled independently.

- FR-4.2: Support configurable, stable batch-rotation patterns across weeks.

- FR-4.3: Match lab/room assignment to a course's declared equipment/type requirement.

- FR-4.4: Enforce shared-resource capacity limits across batches and cohorts (confirmed hard constraint, Section 24 item 5).

8.5 Constraint Configuration

- FR-5.1: Configurable hard constraints per tenant (Section 10.1).

- FR-5.2: Configurable soft/preference constraints with adjustable weights (Section 10.2).

- FR-5.3: Per-faculty availability windows and reserved non-teaching/admin blocks.

- FR-5.4: Institution-wide blocked slots (assembly, lunch, common breaks).

- FR-5.5: A rule builder with two entry paths into the same underlying rule storage: (a) a structured form (dropdowns/fields), and (b) natural-language input parsed into the same structured schema and shown back for confirmation before it is stored (Section 20). Both are in scope for v1.

8.6 Class-Timetable Generation Engine

- FR-6.1: Generate a complete, conflict-free timetable across all cohorts, batches, and elective sections for a tenant in a single run.

- FR-6.2: Guarantee zero hard-constraint violations, independently re-verified by a conflict-checker decoupled from the solver.

- FR-6.3: On infeasibility, report the specific conflicting constraints in human-readable form.

- FR-6.4: Support incremental regeneration for a single changed input.

- FR-6.5: Support generating multiple candidate solutions scored against a configurable objective.

- FR-6.6: Support what-if simulation without committing changes.

8.7 Exam-Timetable Module

- FR-7.1: Define an exam schedule as a distinct timetable type reusing existing rooms, cohorts, and faculty (as invigilators), grouped under its own Exam Timetable Version so the mandatory review-and-approve step (FR-9.3) applies to exam schedules exactly as it does to class schedules — no tenant publishes an exam schedule without approval either (Section 28).

- FR-7.2: Enforce exam-specific hard constraints (Section 10.1, H12–H14).

- FR-7.3: Support exam-specific soft constraints (Section 10.2, S9).

- FR-7.4: Assign invigilators subject to the same availability/workload constraints as regular teaching.

- FR-7.5: Produce exam-specific views and exports.

8.8 Views, Exports & Reporting

- FR-8.1: Cohort-wise, faculty-wise, room-wise, department-wise views.

- FR-8.2: Individual student-specific views reflecting elective enrollment.

- FR-8.3: Export to PDF, Excel/CSV, ICS.

- FR-8.4: Auto-generated load-verification report, available on demand.

- FR-8.5: Utilization dashboards.

8.9 Manual Editing & Mandatory Approval Workflow

- FR-9.1: Manual drag-and-drop editing with live conflict re-validation against the same hard-constraint set used during generation; concurrent edits are guarded by optimistic concurrency on version_no (Section 29.3), rejecting a stale edit rather than silently overwriting another editor's change.

- FR-9.2: Cell locking so regeneration never overwrites specific manually-fixed slots.

- FR-9.3: A draft → review → publish workflow is mandatory for every tenant, regardless of institution size. A small institution's admin may also act as the reviewer, but the explicit review-and-approve action must still occur — there is no configuration path that skips it (Section 24, item 1).

- FR-9.4: Full audit trail of manual overrides and approvals, persisted to the audit_log table (Section 28).

8.10 Absence & Substitution Management

- FR-10.1: Mark a faculty member absent for a date/period range.

- FR-10.2: Automatically suggest eligible substitutes.

- FR-10.3: Publish substitution changes without triggering a full regeneration.

8.11 Notifications

- FR-11.1: Notify affected faculty/students on schedule changes, via a configurable channel, logged in the notification table (Section 28).

- FR-11.2: Optional digest notifications.

8.12 Access Control & Integration

- FR-12.1: RBAC enforced at the API layer for every user class, against the fixed role and permission matrix in Section 27.

- FR-12.2: API for ERP/LMS/SIS integration.

- FR-12.3: SSO against institutional identity providers.

8.13 Localization & Accessibility

- FR-13.1: Multi-language UI and output content.

- FR-13.2: Accessibility-aware room assignment as a configurable rule.

9\. Non-Functional Requirements

| **Category**                    | **Key requirements**                                                                                                                                                                                                                   |
|---------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Correctness & reliability       | NFR-1: zero hard-constraint violations, independently verified. NFR-2: deterministic reproducibility. NFR-3: atomic publish.                                                                                                           |
| Performance & scalability       | NFR-4: explicit solve-time SLA per scale tier (Section 16). NFR-5: 10–50x entity growth without redesign. NFR-6: incremental regeneration under 10% of full-solve time. NFR-7: exam generation meets the same SLA as class generation. |
| Usability                       | NFR-8: a non-technical admin completes setup → generation → review → publish without engineering support. NFR-9: familiar view conventions. NFR-10: human-readable, actionable infeasibility messages.                                 |
| Availability & operations       | NFR-11: offline/print export. NFR-12: automated backups and version history. NFR-13: defined uptime target with monitoring.                                                                                                            |
| Security & access               | NFR-14: server-side RBAC. NFR-15: full audit logging. NFR-16: strict tenant data isolation. NFR-17: documented data-protection approach.                                                                                               |
| Maintainability & extensibility | NFR-18: pluggable constraint rules. NFR-19: solver testable independently of UI. NFR-20: new scheduling modules addable without changing the core solver contract.                                                                     |
| Portability & interoperability  | NFR-21: web-based, responsive. NFR-22: open API for ERP/LMS and calendar sync.                                                                                                                                                         |

10\. Constraint Taxonomy

10.1 Hard Constraints

- H1: No faculty double-booked across two cohorts/rooms in the same slot.

- H2: No cohort/batch double-booked across two courses in the same slot.

- H3: No room double-booked across two cohorts/batches in the same slot.

- H4: Faculty not scheduled during declared unavailable/admin/reserved blocks.

- H5: Faculty only assigned to (course, cohort) pairs they are eligible for.

- H6: Scheduled hours/week per (course, cohort) exactly match configured required hours.

- H7: Slots scheduled only within the valid period range for that day/shift.

- H8: Faculty weekly/daily workload cap never exceeded.

- H9: Room type/equipment matches the course's declared requirement — confirmed as a hard, always-enforced constraint (Section 24, item 5).

- H10: Shared-resource capacity across batch-splits is never exceeded.

- H11: An individual student's timetable has no double-booking across their specific course combination.

- H12 (exam): No student has two overlapping exam sessions.

- H13 (exam): Exam-room seating capacity is never exceeded.

- H14 (exam): An invigilator is not double-booked, and only assigned within availability and workload cap.

- H15: A course with block_size \> 1 is scheduled as N consecutive periods, same room, same day, treated as one atomic assignment for H1–H10 (Section 24, item 4).

10.2 Soft Constraints

- S1: Minimize idle gaps for faculty and students.

- S2: Balance faculty load evenly across the week.

- S3: Distribute a course's weekly hours across different days.

- S4: Prefer high-focus/core subjects earlier in the day.

- S5: Minimize same-course-twice-in-one-day unless load requires it.

- S6: Prefer parallel batch sessions aligned to the same period slot.

- S7: Maximize room-utilization efficiency.

- S8: Respect individual faculty time-of-day preferences.

- S9 (exam): Spread a student's exams evenly; minimize consecutive-day exams.

11\. External Interface Requirements

- User interfaces: responsive web dashboard; mobile-friendly faculty/student views; drag-and-drop editor with live conflict highlighting; natural-language rule input box with confirm-before-commit card (Section 20).

- Software interfaces: relational database; CP-SAT solver service; ICS calendar export; SSO via SAML/OAuth2.

- Communication interfaces: REST API (Section 18); webhooks for outbound events; email/push/SMS gateway.

**PART C — SYSTEM DESIGN**

12\. High-Level Architecture

Five layers, requests flowing top to bottom, results flowing back up through a cache/read layer rather than through the solver.

**Client apps** *— web (admin, committee) + mobile-responsive (faculty, student)*

↓

**API gateway** *— authentication against Identity, RBAC, tenant routing — branches to Integrations (ERP / LMS / SSO / calendar)*

↓

**Core services** *— master data · constraint rule engine · rule parsing service (Section 20) · generation orchestrator · reporting — independently deployable*

↓

**Solver workers** *— OR-Tools CP-SAT, behind an async job queue*

↓

**Postgres + Redis** *— system of record (multi-tenant) and cache/queue*

13\. Technology Stack

| **Layer**         | **Choice**                                                   | **Rationale**                                                                                                        |
|-------------------|--------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| Frontend          | React + Tailwind                                             | Fast to build the drag-drop timetable grid and the rule-builder confirm card.                                        |
| API layer         | Python (FastAPI)                                             | Same language as the solver — no cross-language overhead passing large constraint models.                            |
| Solver            | OR-Tools CP-SAT (Python)                                     | Fits this constraint class; supports solution hints for incremental regeneration.                                    |
| Rule parsing      | LLM API call with a fixed JSON output schema (Section 20)    | Fastest path to a working natural-language rule builder for the hackathon timeline, without training a custom model. |
| Database          | PostgreSQL                                                   | Relational structure matches the join-heavy constraint model; row-level security for tenant isolation.               |
| Job queue / cache | Celery + Redis                                               | Needed once a solve is long enough to require async handling.                                                        |
| Auth / SSO        | JWT + OAuth2 via Keycloak or Auth0                           | Supports one Identity spanning multiple tenants (Section 15.3) without building identity from scratch.               |
| Containerization  | Docker Compose for demo; Kubernetes as the production target | Keeps the demo simple while the scaling story is explicit.                                                           |

14\. Key Design Decisions

- Warm-started incremental regeneration — CP-SAT solution hints seed re-solves from the previous result.

- CQRS-lite — generation writes to a raw slot-assignment model; publish denormalizes into per-view read tables.

- Decomposition into independent sub-problems — departments sharing no faculty/rooms solved as separate, parallel CSPs.

- Tenant-aware worker pools — solve jobs routed by tenant size/tier.

- Timeout with best-effort fallback — hard constraints always guaranteed; soft-constraint shortfall surfaced, never hidden.

- Deterministic confirmation rendering — the plain-English confirmation shown to the admin for a parsed rule (Section 20) is template-rendered from the structured object, never re-generated by the LLM, so what is shown is guaranteed to match what is stored.

15\. Multi-Tenancy and Identity Approach

15.1 Data isolation (resolved: both mechanisms included)

- Default for every tenant: every table carries a tenant_id column; PostgreSQL row-level security policies enforce that a query can only see rows for the caller's tenant, enforced at the database layer.

- Included as an explicit, supported upgrade path: a large tenant (e.g., a multi-campus university) can be promoted to a dedicated schema for stronger physical isolation, selectable at onboarding or later, without an application-layer rewrite. Both mechanisms are part of this version's design, not just the default (Section 24, item 3).

15.2 Compute isolation

- Solver working-state and job-queue entries are tenant-scoped, so a bug in job dispatch cannot leak one tenant's data into another's solve.

15.3 Cross-tenant identity (resolved: included)

- Authentication is handled at the Identity layer, independent of any tenant. One Identity (one login) may be linked to a Staff Profile at more than one tenant — covering a visiting or part-time faculty member who works at two institutions on the platform.

- Each Staff Profile's scheduling data (eligibility, availability, assignments) remains fully isolated to its own tenant; the shared Identity only provides a single sign-on convenience layer across tenant contexts, and never merges or exposes one tenant's data to another (Section 24, item 8).

16\. Scale and Performance Targets

| **Tier**                            | **Illustrative Profile**                                                         | **Full-Solve Time**         | **Incremental Regeneration** |
|-------------------------------------|----------------------------------------------------------------------------------|-----------------------------|------------------------------|
| Small (single school)               | ≤ 10 sections, ≤ 20 faculty, no electives                                        | ≤ 30 seconds                | ≤ 3 seconds                  |
| Medium (college, demo baseline)     | ≥ 40 sections, ≥ 100 faculty, electives + lab batches + exam data (Section 22.4) | ≤ 3 minutes                 | ≤ 15 seconds                 |
| Large (university, design headroom) | ≥ 200 sections, ≥ 500 faculty, multiple departments/campuses                     | ≤ 15 minutes (or async job) | ≤ 60 seconds                 |

**PART D — IMPLEMENTATION SPECIFICATION**

17\. Database Schema (Core Tables)

Key tables and columns for the core entities in Section 7. Section 28 adds the supporting tables (campus, elective_section, student_profile, audit_log, notification, exception_calendar, exam_timetable_version) needed to make every reference below resolve to a real table.

| **Table**         | **Key columns**                                                                                                                                                     |
|-------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| identity          | id (PK), email, auth_provider_ref, platform_role (nullable — 'super_admin' or null; see Section 27)                                                                 |
| tenant            | id (PK), name, institution_type, timezone, enabled_modules (jsonb), isolation_mode (row \| schema)                                                                  |
| department        | id (PK), tenant_id (FK), name                                                                                                                                       |
| course            | id (PK), tenant_id (FK), department_id (FK), name, type (core\|elective\|lab), credit_value, hours_per_week, block_size (int, default 1)                            |
| cohort            | id (PK), tenant_id (FK), name, type (fixed\|elective_derived)                                                                                                       |
| batch             | id (PK), cohort_id (FK), course_id (FK), label                                                                                                                      |
| room              | id (PK), tenant_id (FK), campus_id (FK), name, type, capacity, equipment_tags (jsonb), accessible (bool)                                                            |
| staff_profile     | id (PK), identity_id (FK), tenant_id (FK), employment_type, workload_cap_week, workload_cap_day, roles (jsonb array — see Section 27)                               |
| eligibility       | staff_profile_id (FK), course_id (FK), cohort_id (FK) — composite key                                                                                               |
| period_template   | id (PK), tenant_id (FK), weekday, period_index, start_time, end_time, shift                                                                                         |
| constraint_rule   | id (PK), tenant_id (FK), rule_type (enumerated in Section 30), scope, target_id, threshold, unit, polarity, weight, source (structured\|nl), raw_input_text, status |
| enrollment_record | id (PK), tenant_id (FK), student_profile_id (FK, see Section 28), elective_section_id (FK, see Section 28)                                                          |
| timetable_version | id (PK), tenant_id (FK), term_id, state (draft\|under_review\|published\|archived), created_by, approved_by, version_no (optimistic concurrency, Section 29)        |
| assignment        | id (PK), timetable_version_id (FK), staff_profile_id (FK), course_id (FK), cohort_id (FK), room_id (FK), slot_start, slot_span                                      |
| exam_session      | id (PK), exam_timetable_version_id (FK, see Section 28), course_id (FK), cohort_id (FK), room_id (FK), invigilator_staff_profile_id (FK), slot_start                |
| substitution_log  | id (PK), tenant_id (FK), original_staff_profile_id (FK), substitute_staff_profile_id (FK), assignment_id (FK), date                                                 |

Example DDL sketch for the two tables most central to correctness — assignment (the solver's write model) and constraint_rule (where Section 20's confirmed rules land):

CREATE TABLE assignment (  
id UUID PRIMARY KEY,  
timetable_version_id UUID REFERENCES timetable_version(id),  
staff_profile_id UUID REFERENCES staff_profile(id),  
course_id UUID REFERENCES course(id),  
cohort_id UUID REFERENCES cohort(id),  
room_id UUID REFERENCES room(id),  
slot_start INT NOT NULL,  
slot_span INT NOT NULL DEFAULT 1  
);  
  
CREATE TABLE constraint_rule (  
id UUID PRIMARY KEY,  
tenant_id UUID REFERENCES tenant(id),  
rule_type TEXT NOT NULL,  
scope TEXT NOT NULL,  
target_id UUID,  
threshold NUMERIC,  
unit TEXT,  
polarity TEXT,  
weight NUMERIC DEFAULT NULL,  
source TEXT CHECK (source IN ('structured','nl')),  
raw_input_text TEXT,  
status TEXT DEFAULT 'confirmed'  
);

18\. API Contract (Core Endpoints)

| **Method & Path**                                 | **Purpose**                                                                                                                  |
|---------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| POST /tenants                                     | Onboard a new tenant (platform operator only).                                                                               |
| POST /tenants/{id}/modules                        | Enable/disable electives or exams for a tenant (FR-1.5).                                                                     |
| POST /tenants/{id}/import/master-data             | Bulk import faculty, rooms, courses, cohorts.                                                                                |
| POST /tenants/{id}/import/enrollment              | Import pre-resolved elective enrollment for a term.                                                                          |
| POST /tenants/{id}/rules                          | Create a rule via structured fields.                                                                                         |
| POST /tenants/{id}/rules/parse                    | Send a natural-language sentence; returns the parsed structured object for confirmation (does not persist yet — Section 20). |
| POST /tenants/{id}/rules/{ruleId}/confirm         | Persist a previously-parsed rule after admin confirmation.                                                                   |
| POST /tenants/{id}/generate                       | Trigger class-timetable generation; returns a job id for async tiers.                                                        |
| GET /jobs/{jobId}                                 | Poll generation job status/progress.                                                                                         |
| GET /tenants/{id}/timetables/{versionId}          | Fetch a timetable version, any view.                                                                                         |
| POST /tenants/{id}/timetables/{versionId}/edit    | Apply a manual edit; re-validated live.                                                                                      |
| POST /tenants/{id}/timetables/{versionId}/approve | Mandatory review-and-approve action (FR-9.3); required before publish.                                                       |
| POST /tenants/{id}/timetables/{versionId}/publish | Publish; rejected if not yet approved.                                                                                       |
| POST /tenants/{id}/exams/generate                 | Trigger exam-timetable generation.                                                                                           |
| POST /tenants/{id}/substitutions                  | Record an absence and request a substitute suggestion.                                                                       |
| GET /tenants/{id}/reports/verification            | Auto-generated load-verification report (FR-8.4).                                                                            |
| GET /me/tenants                                   | For the current Identity, list all tenants it holds a Staff Profile at (FR-1.6).                                             |

19\. CP-SAT Solver Model

The core decision variable and how each hard constraint in Section 10.1 maps onto it:

assign\[f, c, k, r, s\] ∈ {0, 1}  
meaning: staff profile f teaches course c to cohort k  
in room r, in a block starting at slot s.  
Variables are only created for (f,c,k) pairs present  
in the eligibility table (enforces H5 by construction)  
and for (c,r) pairs where room r's equipment_tags  
match course c's requirement (enforces H9).

| **Constraint**                           | **CP-SAT formulation**                                                                                                                                 |
|------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| H1 — no faculty double-booked            | For each f, s: sum over c,k,r of assign\[f,c,k,r,s\] ≤ 1                                                                                               |
| H2 — no cohort double-booked             | For each k, s: sum over f,c,r of assign\[f,c,k,r,s\] ≤ 1                                                                                               |
| H3 — no room double-booked               | For each r, s: sum over f,c,k of assign\[f,c,k,r,s\] ≤ 1                                                                                               |
| H4 — faculty reserved/unavailable blocks | assign\[f,\*,\*,\*,s\] fixed to 0 for every s in f's blocked set                                                                                       |
| H6 — hours match required                | sum over r,s of assign\[f,c,k,r,s\] == required_hours\[c,k\]                                                                                           |
| H7 — valid period range per day/shift    | Variables only created for (s) within that day/shift's valid range                                                                                     |
| H8 — workload cap                        | sum over c,k,r,s of assign\[f,c,k,r,s\] ≤ cap\[f\], evaluated per week and per day                                                                     |
| H10 — shared lab capacity                | For lab type L, slot s: sum of assign\[...\] using a room of type L at s ≤ count(rooms of type L)                                                      |
| H15 — block courses                      | For course c with block_size = n \> 1, assign\[f,c,k,r,s\] implies occupancy of s..s+n−1 in every sum above; s constrained to not cross a day boundary |

Soft constraints (Section 10.2) are added as weighted penalty terms in the objective and minimized alongside the hard-constraint-feasible search. Incremental regeneration calls AddHint() with the previous solution's variable values before re-solving, per the warm-start decision in Section 14.

20\. Natural-Language Rule Builder — Technical Approach

Since this is being built for the hackathon now, here is the concrete pipeline, designed to be buildable quickly without training a custom model:

- 1\. Admin types a sentence into the rule-builder input.

- 2\. The backend calls an LLM with a system prompt constrained to output only JSON matching a fixed schema: rule_type (enum of supported types), scope (tenant \| department \| faculty \| course \| cohort), target_id, threshold, unit, polarity (max \| min \| forbid \| require).

- 3\. The backend validates the JSON structurally (schema check) and semantically (target_id must resolve to a real entity in this tenant); if rule_type is 'unsupported' or fails validation, the admin is shown the list of supported rule types to pick from manually — never a silent failure.

- 4\. If valid, the confirmation text is generated by a deterministic template from the structured object — not re-asked from the LLM — guaranteeing the text shown always matches what gets stored (Section 14).

- 5\. On Confirm: the rule is persisted with source = 'nl' and the original sentence retained for audit. On Edit: the admin adjusts the structured fields directly, bypassing the LLM entirely.

- 6\. At generation time, every constraint_rule row (regardless of source) is compiled into the CP-SAT model identically — the solver never distinguishes how a rule was authored.

21\. UI Wireframe Descriptions (Core Screens)

21.1 Setup wizard

Step-based flow: institution profile → period template → bulk-import master data (with row-level validation feedback) → module toggles (electives/exams) → enrollment import (if electives enabled).

21.2 Rule builder screen

A text input (“type a rule in plain English…”) alongside a structured form; submitting text renders the confirm-before-commit card described in Section 5.2 inline, with Confirm/Edit actions.

21.3 Generation & review screen

A drag-and-drop grid (cohort-wise by default, switchable to faculty/room/student view), a live conflict-highlight overlay on any manual edit, and a persistent “Approve” action that is disabled until the reviewing role has opened and inspected the draft at least once.

21.4 Publish confirmation

A summary of what changed since the last published version, blocked until FR-9.3's approval step is complete.

21.5 Faculty / student view

Read-only, mobile-first, individualized (a student's view reflects their own electives).

21.6 Exam module screens

Mirrors the class-timetable screens, with a seating-chart view and an invigilator-roster view added.

22\. Test and Acceptance Plan

22.1 Correctness tests

For each hard constraint H1–H15, an automated test constructs a synthetic case designed to violate that specific constraint if it weren't enforced, asserts the solver's output satisfies it, and separately asserts the independent conflict-checker flags a manually-corrupted schedule that violates it.

22.2 Performance tests

An automated benchmark harness generates synthetic tenants at each tier in Section 16 and asserts solve time and incremental-regeneration time against that tier's targets.

22.3 Usability acceptance test

A scripted walkthrough (setup → generate → review → approve → publish) performed by someone unfamiliar with the system, timed and observed for confusion points, validating NFR-8.

22.4 Demo dataset specification

The medium-tier synthetic dataset prepared for the hackathon demo must include: at least 40 cohorts/sections and 100 faculty; at least one cross-department elective basket with enrolled students; at least two batch-split lab courses across two or more same-type lab rooms; at least one multi-period (block_size \> 1) course; and a complete exam-period dataset (courses, student enrollment, room seating, invigilator pool) sufficient to run the exam module end to end — this closes the earlier gap where exam and elective data were not explicitly required in the demo dataset.

23\. Build-Order / Milestone Plan

- Phase 1: master data CRUD + single-cohort CP-SAT solver (H1–H9) + one view. This is the smallest slice that proves the core PS1 claim.

- Phase 2: batches/labs (H10) + multi-cohort scale + the load-verification report.

- Phase 3: electives ingestion + individualized student view (H11).

- Phase 4: exam module (H12–H14), reusing the Phase 1–3 engine.

- Phase 5: mandatory review/approve/publish workflow (FR-9.3) + notifications + substitution.

- Phase 6: natural-language rule builder (Section 20). This only touches the constraint_rule storage layer and can be built in parallel with Phases 2–5, since it doesn't depend on the solver's internals until generation time — worth pulling forward if it's already underway, as noted.

- Phase 7: multi-tenancy hardening (schema-per-tenant option) + cross-tenant Identity linking.

- Phase 8: analytics dashboards, what-if simulation, demo-dataset polish.

24\. Resolved Items Log

| **\#** | **Original open item**                                          | **Resolution**                                                                                             | **Reflected in**                                                  |
|--------|-----------------------------------------------------------------|------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| 1      | Is review-before-publish mandatory or optional?                 | Mandatory for every tenant; no auto-publish path exists.                                                   | FR-9.3, Section 4.2, Section 7 (Timetable Version)                |
| 2      | Is the natural-language rule builder v1 or roadmap?             | In v1 — actively being built now.                                                                          | FR-5.5, Section 5.2, Section 20                                   |
| 3      | Row-level vs schema-per-tenant isolation — which one?           | Both included: row-level is the default; schema-per-tenant is an explicit supported upgrade path.          | Section 15.1                                                      |
| 4      | Is double-period/consecutive-block course scheduling supported? | Yes, as an opt-in per-course attribute (block_size), used only where a course needs it.                    | FR-2.5, H15, Section 17 (course table)                            |
| 5      | Is room/lab a real hard-constrained resource?                   | Confirmed yes.                                                                                             | H3, H9, H10                                                       |
| 6      | Are elective/exam modules toggleable per tenant?                | Yes — explicit per-tenant module toggles.                                                                  | FR-1.5, Section 17 (tenant table)                                 |
| 7      | Idea Document's broken internal section cross-reference.        | Fixed by consolidating into this single document with continuous section numbering.                        | This document, throughout                                         |
| 8      | Should cross-tenant faculty identity be supported?              | Yes — one Identity may hold Staff Profiles at multiple tenants; scheduling data stays isolated per tenant. | FR-1.6, Section 15.3, Section 17 (identity, staff_profile tables) |

25\. Future Roadmap (Post-v1)

- Elective preference collection and automated seat-allotment engine.

- Elective-demand forecasting from historical preference data.

- Hostel/mess scheduling and other adjacent institutional scheduling problems, reusing the same constraint-engine architecture.

26\. Appendix: Validation Case Study

A real school timetable (8 sections — 5th through 10th with parallel A/B sections at 9th and 10th; 8 periods Monday through Friday and 5 periods on Saturday; approximately 15 faculty) validated the school-mode configuration of the data model in Section 7: subjects split into parallel halves (Batch entity, H10), variable periods per weekday (Period Template, H7), an administrative role with reserved non-teaching time (H4), strict faculty-course-cohort eligibility (H5), and a standing load-verification report (FR-8.4). The elective, batch, exam-scheduling, block-course, module-toggle, and cross-tenant-identity requirements added since then extend the same model to college- and university-scale scenarios per the PS1 problem statement.

**PART E — IDE BUILD-READINESS PASS**

The sections below were added after a second, deliberately adversarial review: reading Sections 1–26 as if about to generate code from them, and asking where an IDE or coding agent would have to invent an answer rather than find one. New section numbers were used rather than renumbering Sections 1–26, so every existing cross-reference in this document stays valid.

27\. Roles and Permissions

Section 3 names the human user types; this defines the actual access-control model behind FR-12.1.

- platform_super_admin — a flag on identity.platform_role, not tenant-scoped. Only role permitted to call POST /tenants.

- Tenant-scoped roles, stored as an array on staff_profile.roles (a person can hold more than one at the same tenant): institution_admin, department_head, reviewer, faculty.

- student — stored on student_profile, not staff_profile (Section 28); a distinct identity kind with read-only scope over its own data.

*Note: FR-4.2 (batch rotation patterns) and the Section 14 decomposition-into-independent-subproblems optimization are deliberately deferred to a future phase to prioritize core correctness and multi-tenant scaling.*

| **Action category**                                              | **Allowed roles**                                             |
|------------------------------------------------------------------|---------------------------------------------------------------|
| Tenant configuration, module toggles (FR-1.5)                    | institution_admin                                             |
| Master data CRUD / bulk import (Section 8.2)                     | institution_admin, department_head (scoped to own department) |
| Rule authoring, structured or natural-language (Section 8.5, 20) | institution_admin, department_head                            |
| Trigger generation (FR-6.1, FR-7.1)                              | institution_admin, department_head                            |
| Review and approve (FR-9.3)                                      | reviewer (may be the same person as institution_admin)        |
| Publish                                                          | institution_admin — and only once approved by a reviewer      |
| Manual edit (FR-9.1)                                             | institution_admin, department_head                            |
| View own schedule                                                | faculty, student                                              |
| View all schedules / reports (FR-8.1, FR-8.4)                    | institution_admin, department_head, reviewer                  |
| Substitution management (Section 8.10)                           | institution_admin, department_head                            |

This table is the source the API layer's authorization check is built against (Section 29.2); an endpoint not listed here defaults to institution_admin-only.

28\. Data Model — Supporting Tables

These tables are referenced from Section 7 and Section 17 and are defined here in full so every foreign key in this document resolves to something real.

| **Table**              | **Key columns**                                                                                                                          | **Closes**                                                                                                                                                      |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| campus                 | id (PK), tenant_id (FK), name, timezone                                                                                                  | FR-1.4 multi-campus support                                                                                                                                     |
| elective_section       | id (PK), tenant_id (FK), course_id (FK), term_id (FK), capacity                                                                          | enrollment_record's elective_section_id FK (Section 17), Elective Section entity (Section 7)                                                                    |
| student_profile        | id (PK), identity_id (FK, nullable if the tenant doesn't give students logins), tenant_id (FK), external_student_code, cohort_id (FK)    | enrollment_record.student_id now correctly FKs to student_profile.id rather than an unlinked raw value; also the target of the student role (Section 27)        |
| exception_calendar     | id (PK), tenant_id (FK), date, type (holiday\|exam_period\|event\|half_day), description                                                 | Exception Calendar entity (Section 7), listed there but missing from Section 17                                                                                 |
| audit_log              | id (PK), tenant_id (FK), actor_identity_id (FK), action, entity_type, entity_id, before (jsonb), after (jsonb), at (timestamp)           | FR-9.4, NFR-15 full audit logging                                                                                                                               |
| notification           | id (PK), tenant_id (FK), identity_id (FK), channel (email\|push\|sms), subject, body, status (queued\|sent\|failed), created_at, sent_at | FR-11.1, FR-11.2                                                                                                                                                |
| exam_timetable_version | id (PK), tenant_id (FK), term_id (FK), state (draft\|under_review\|published\|archived), created_by, approved_by, version_no             | Gives the exam module the same mandatory review/approve/publish state machine as timetable_version, closing the exam-versioning gap noted against FR-7.1/FR-9.3 |

Two follow-on changes to tables already defined in Section 17: room gains a campus_id (FK to campus); tenant gains a timezone column, with campus.timezone able to override it for a multi-region institution; exam_session gains exam_timetable_version_id (FK) in place of a bare tenant_id.

29\. API Conventions and Multi-Tenant Request Context

29.1 Versioning and base path

All endpoints in Section 18 are served under /api/v1/. A breaking change to any response shape ships as /api/v2/ alongside it, never as a silent change to v1.

29.2 Authentication and tenant context

The JWT issued at login carries only the identity_id claim (sub) — never a tenant_id — because one Identity can hold staff or student profiles at more than one tenant (FR-1.6). Every tenant-scoped request already carries {tenantId} in its path (Section 18); on each such request the API layer looks up whether the calling Identity has a staff_profile or student_profile at that tenant, checks its roles against the Section 27 matrix, and, if authorized, runs the request in a transaction with:

SET LOCAL app.tenant_id = '\<tenantId\>';  
SET LOCAL app.identity_id = '\<identity_id from JWT\>';

Every row-level security policy in the database is of the form below, which is the concrete mechanism behind Section 15.1's “row-level security enforces tenant_id”:

CREATE POLICY tenant_isolation ON \<table\>  
USING (tenant_id = current_setting('app.tenant_id')::uuid);

29.3 Standard error envelope and optimistic concurrency

Every error response has the same shape:

{  
"error": {  
"code": "VALIDATION_ERROR \| NOT_FOUND \| FORBIDDEN \|  
CONFLICT \| INFEASIBLE_CONFIGURATION",  
"message": "human-readable, per FR-6.3 / NFR-10",  
"details": { }  
}  
}

timetable_version, exam_timetable_version, and assignment all carry version_no. A manual edit (FR-9.1) or approval action must include the version_no it last read; a mismatch returns CONFLICT rather than silently overwriting a concurrent change — this is the concrete mechanism behind FR-9.1's concurrency guard.

29.4 Bulk import templates

Exact column headers for the three highest-value imports (FR-2.2); every other master-data import follows the same pattern — one column per required field, one external_id column used in row-level error messages (Section 5.1).

| **File**    | **Columns**                                                                                              |
|-------------|----------------------------------------------------------------------------------------------------------|
| faculty.csv | external_id, full_name, email, department, employment_type, workload_cap_week, workload_cap_day          |
| rooms.csv   | external_id, name, type, capacity, equipment_tags (semicolon-separated), campus, accessible (true/false) |
| courses.csv | external_id, name, department, type (core\|elective\|lab), credit_value, hours_per_week, block_size      |

29.5 Pagination

All list endpoints accept ?cursor=&limit= and return {items: \[...\], next_cursor: string\|null}, rather than a bare array — kept consistent from the first endpoint built, since retrofitting pagination onto an already-shipped bare-array response is a breaking change.

30\. Constraint Rule Type Enumeration

The closed list of values constraint_rule.rule_type may take — both the structured form and the natural-language parser (Section 20) can only ever produce one of these; anything else routes to the 'unsupported' fallback in Section 20 step 3.

| **rule_type**              | **unit**               | **Maps to**                                        | **Example phrasing**                                                |
|----------------------------|------------------------|----------------------------------------------------|---------------------------------------------------------------------|
| max_periods_per_day        | periods                | H8 (tenant/tenant-configured cap)                  | “no faculty teaches more than 4 periods a day”                      |
| max_periods_per_week       | periods                | H8                                                 | “faculty should teach at most 20 periods a week”                    |
| min_gap_between_periods    | periods                | S1                                                 | “give faculty at least one free period between two teaching blocks” |
| no_consecutive_same_course | boolean                | S5                                                 | “don't put the same subject back-to-back for a class”               |
| preferred_time_of_day      | morning \| afternoon   | S4, S8                                             | “science should be scheduled in the morning”                        |
| balance_load_across_week   | boolean, tenant-wide   | S2                                                 | “spread faculty load evenly across the week”                        |
| room_utilization_priority  | weight only            | S7                                                 | “prioritize using all rooms evenly”                                 |
| elective_no_overlap_core   | boolean, scope: cohort | H11 (reinforced as an explicit soft priority)      | “electives should never clash with core classes for a cohort”       |
| exam_min_gap_days          | days                   | S9                                                 | “give students at least one day between exams”                      |
| unsupported                | —                      | none — always routes to the manual structured form | anything the parser can't map to the above                          |

31\. What Remains an Implementation-Time Decision (By Design)

Named explicitly so these are never mistaken for gaps in the spec — they are ordinary engineering judgment calls that don't affect correctness (Section 10) or any resolved decision (Section 24):

- The exact LLM provider/model used for rule parsing (Section 20) — any provider supporting constrained/structured JSON output satisfies the pipeline; swapping providers later changes no other part of this document.

- Default numeric weights for soft constraints S1–S9 — tenants can retune them later; a reasonable starting default is a build-time judgment call, not a design question.

- The specific tie-break rule for ranking eligible substitutes (FR-10.2) beyond “eligible, free, not overloaded” — e.g., least-loaded-first versus most-recently-taught-this-cohort-first; either is valid, document whichever is chosen in code.

- Exact visual spacing/styling of the screens described in Section 21 — those are structural wireframes (required elements and their relationships), not pixel-level design.

- Specific frontend component/icon library choices beyond React + Tailwind (Section 13).

- Exam Module Scope: Exams apply only to `type='core'` and `type='elective'` courses. `type='lab'` courses are excluded from exam scheduling (labs are batch-split/practical and don't fit the seated room+invigilator model).

32\. IDE Build-Readiness Review Log

| **\#** | **Gap found in this pass**                                                                                        | **Closed by**                                       |
|--------|-------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| 1      | constraint_rule.rule_type had no enumerated values                                                                | Section 30                                          |
| 2      | No RBAC role list or permission-to-action matrix existed anywhere                                                 | Section 27                                          |
| 3      | enrollment_record.elective_section_id, and the Elective Section entity, referenced a table that was never defined | Section 28 (elective_section)                       |
| 4      | enrollment_record.student_id was a bare value with no link to an Identity or role                                 | Section 28 (student_profile)                        |
| 5      | FR-1.4 multi-campus had no campus table; room had no campus scoping                                               | Section 28 (campus), room.campus_id                 |
| 6      | FR-9.4 / NFR-15 audit logging had no table                                                                        | Section 28 (audit_log)                              |
| 7      | FR-11.1/11.2 notifications had no table                                                                           | Section 28 (notification)                           |
| 8      | The Exception Calendar entity (Section 7) was missing from the Section 17 schema                                  | Section 28 (exception_calendar)                     |
| 9      | The exam module had no draft/review/publish state machine, contradicting FR-9.3's “mandatory for every tenant”    | Section 28 (exam_timetable_version), FR-7.1 updated |
| 10     | No API versioning, error envelope, or pagination convention was defined                                           | Section 29.1, 29.3, 29.5                            |
| 11     | “Row-level security enforces tenant_id” had no concrete mechanism for how tenant context gets set per request     | Section 29.2                                        |
| 12     | Bulk import (FR-2.2) had no defined column templates                                                              | Section 29.4                                        |
| 13     | No timezone field existed anywhere despite multi-campus/multi-region tenants                                      | Section 28 (tenant.timezone, campus.timezone)       |
| 14     | Concurrent manual edits (FR-9.1) had no conflict-handling mechanism                                               | Section 28 (version_no), Section 29.3 (CONFLICT)    |
| 15     | H9 (Section 10.1) references "course's declared requirement" for room equipment matching, but course table (Section 17) had no equipment column | Added `required_equipment_tags` (jsonb, default `[]`) to `course` table. Phase 1 uses coarse `course.type` ↔ `room.type` matching; full equipment-tag intersection matching activates when tags are populated. |
| 16     | `timetable_version.term_id` (Section 17) referenced no `academic_term` table | Added `academic_term` table: id (PK), tenant_id (FK), name, start_date, end_date. `timetable_version.term_id` and `elective_section.term_id` are real FKs to it. |
| 17     | FR-5.3 "per-faculty availability windows and reserved non-teaching/admin blocks" had no storage mechanism — `constraint_rule` columns (scope/target_id/threshold/unit) have no slot concept and §30's enum has no "unavailable at slot S" type | Added `staff_availability_block` table: id (PK), staff_profile_id (FK), weekday, period_index, block_type (enum: unavailable, admin, reserved). Solver's H4 reads from this table, not from `constraint_rule`. |
| 18     | `assignment`, `eligibility`, and `batch` (Section 17) lack `tenant_id`, forcing non-uniform RLS policies with per-row subquery joins — costly for `assignment` (solver's primary write target) | Added denormalized `tenant_id` column to all three tables, set at insert time from `app.tenant_id` session variable. All three get the identical `tenant_id = current_setting('app.tenant_id')::uuid` RLS policy as every other tenant-scoped table. |
| 19     | `staff_availability_block` (§32 #17) was excluded from RLS in migration 001 because it lacked `tenant_id` — scoped only via `staff_profile_id` FK, which is not directly usable in a `USING` clause without a subquery join. Phase 1 review identified this as a gap; a bare FK is weaker than the DB-layer guarantee invariant #3 requires. | Added denormalized `tenant_id` column to `staff_availability_block` in migration 002, backfilled from `staff_profile.tenant_id`. Applied standard `tenant_isolation` RLS policy identical to all other tenant-scoped tables. |
| 20     | `batch` lacks a mapping to `student_profile`, making it impossible to know which students are in which batch for individualized student views (FR-8.2) and accurate H11 overlap checking. | Added `batch_membership` table: student_profile_id, batch_id, tenant_id. Allows precise student-level validation without over-constraining the solver. |
| 21     | `department_head`'s scope is defined as "own department" per §11, but currently has tenant-wide write access in the CRUD routers. | Explicitly deferred as technical debt. A resource-department match (joining the target resource's `department_id` against the caller's `staff_profile`) needs to be implemented. |
| 22     | API test coverage gap: despite four phases of CRUD routers being built, only `test_reports.py` exists as an API test. | Tracked as technical debt. The Phase 5 Step 2 RBAC enforcement adds `test_auth_rbac.py` to cover authorization paths, but full CRUD functional testing for Phases 1-4 is missing. |
| 23     | `GET /timetables/{versionId}` is currently restricted to `institution_admin`, `department_head`, `reviewer` (§11 "view all schedules/reports"). Faculty have no individualized timetable view endpoint equivalent to `GET /students/{id}/timetable`. | Explicitly deferred as technical debt. A faculty-scoped read endpoint (own assigned slots only, gated on `faculty` role + identity_id match) needs to be implemented. See AGENTS.md §11 TODO #2. |

With Sections 27–32 in place, every foreign key, enum, and cross-tenant request path referenced anywhere in this document resolves to something concretely defined in it.
