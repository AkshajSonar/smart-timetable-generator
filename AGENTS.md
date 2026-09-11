# AGENTS.md — Smart Timetable Generator (PS1)

This file is the operating manual for any AI coding agent (Antigravity, or
anything else that reads `AGENTS.md`) working in this repository. It is a
**build companion**, not a replacement for the spec. The complete,
authoritative requirements live in [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md)
(Version 2.1, IDE Build-Ready — converted from the original Word doc). This
file exists so the agent doesn't have to re-read and re-derive 1,400 lines of
spec before every task; it distills the parts that drive code structure,
plus the parts most likely to be silently gotten wrong.

**If this file and `docs/PROJECT_SPEC.md` ever disagree, the spec wins.**
Fix this file, don't route around the spec.

Section numbers below (e.g. "§10.1") refer to `docs/PROJECT_SPEC.md`.

---

## 0. How the agent should operate in this repo

- **Don't silently invent unstated decisions.** That's not a style
  preference — it's this product's own design principle turned back on its
  own build process. The system's rule for itself is: *never silently act
  on an ambiguous interpretation; show the interpretation back and ask*
  (§5.2). Hold the agent's own work to the same bar. §31 is the explicit
  list of things that are genuinely open (LLM provider, default soft-constraint
  weights, tie-break rules, visual styling, component library) — decide
  those freely and document the choice in code/commit message. Anything
  *not* on that list that looks underspecified should be flagged to the
  developer, not guessed.
- **Read §3 (Non-Negotiable Invariants) before writing code that touches
  publishing, tenant isolation, RLS, or the solver.** These are the things
  most likely to be "quietly" broken by a reasonable-looking shortcut.
- **Follow the phase order in §13 (Build Order).** Each phase is scoped so
  its own tests can pass before the next phase starts. Don't jump ahead to
  Phase 4 (exams) before Phase 1's solver core is green — later phases
  reuse it.
- **Keep this file current.** When a §31-style open decision gets locked
  in (e.g. infra choice, LLM provider), update the relevant section here in
  the same PR.

---
### 0.1 Agent Execution Protocol — Mandatory

The agent must work in small, independently verifiable checkpoints.

For every implementation task:

1. Identify the smallest meaningful checkpoint that can be completed independently.
2. Implement only that checkpoint.
3. Run the relevant tests, type checks, linting, build checks, or other verification required for that checkpoint.
4. Inspect `git status` and `git diff`.
5. If verification passes, immediately create a focused Git commit for that checkpoint.
6. Verify the commit with `git status` and `git log -1 --oneline`.
7. Only then continue to the next checkpoint.

**Do not accumulate multiple completed checkpoints in an uncommitted working tree.**

A checkpoint should represent one coherent piece of functionality, infrastructure, correctness, testing, configuration, or documentation. Do not create meaningless commits for trivial intermediate edits.

The required workflow is:

`Plan → Implement → Test → Review diff → Commit → Verify commit → Continue`

If a checkpoint's required tests fail, do not commit it as complete. Fix the failure, re-run verification, and commit only after the checkpoint is valid.

Before switching to an unrelated workstream, commit the completed work first.
---
## 1. Project Snapshot

**Problem statement (PS1):** *"Smart Timetable Generator — develop an
intelligent timetable generation system that creates conflict-free
schedules while considering faculty availability, classrooms, laboratories,
batches, electives, and scheduling constraints."*

**What it actually is:** a multi-tenant SaaS scheduling engine. An
institution describes its reality once — who can teach what to whom, what
rooms/labs exist, how cohorts split into batches and electives, what rules
must never be broken — and the system returns a timetable that is
**mathematically guaranteed conflict-free**, independently re-verified (not
just trusted from the solver), and stays correct as reality changes without
a human re-checking every cell.

**The actual differentiator** is not "it draws a grid." It's that the grid
is provably clash-free at a scale no human scheduler can hold in their
head, and it's re-proved cheaply every time something changes. Every
architectural decision in this doc exists in service of that claim —
optimize for correctness and verifiability first, UI polish second.

**Context:** built for a hackathon, but specified to IDE/agent
build-readiness (every FK, enum, and cross-tenant request path resolves to
something concretely defined — see §32 for the gap-closure log).

---

## 2. Doc Map

| Need | Where |
|---|---|
| Full requirements, data model, API, solver math | `docs/PROJECT_SPEC.md` |
| Quick reference while coding | This file |
| Roles/users overview | Spec §3 |
| Workflow (onboarding → setup → generate → review → publish) | Spec §4 |
| Functional requirements (FR-x.x) | Spec §8 |
| Non-functional requirements (NFR-x) | Spec §9 |
| Hard/soft constraints (H1–H15, S1–S9) | Spec §10, condensed in §9 below |
| Full DB schema | Spec §17, §28 |
| API contract | Spec §18, conventions in §29 |
| CP-SAT solver model | Spec §19 |
| NL rule builder pipeline | Spec §20 |
| Wireframe descriptions | Spec §21 |
| Test/acceptance plan | Spec §22 |
| Build phases | Spec §23 |
| RBAC matrix | Spec §27 |

---

## 3. Non-Negotiable Invariants

These hold regardless of hackathon time pressure. Violating one of these
isn't a shortcut, it's a wrong implementation of a requirement that's
already been explicitly resolved (see spec §24 resolution log).

1. **No auto-publish, ever.** Every tenant, regardless of size, must pass
   through an explicit review-and-approve action before publish. A small
   institution's admin can *be* the reviewer, but the action itself cannot
   be skipped or defaulted (FR-9.3).
2. **Zero hard-constraint violations, independently re-verified.** Solver
   output is not trusted on its own — a decoupled conflict-checker
   re-validates H1–H15 against the same rules the solver used (FR-6.2,
   NFR-1). Build the conflict-checker as a separate code path from the
   solver's own constraint construction, not a re-run of the same function.
3. **Tenant isolation is enforced at the database layer**, via Postgres
   row-level security keyed on `tenant_id` — not just an application-layer
   `WHERE tenant_id = ...` that a future query could forget to add
   (NFR-16, §15.1, §29.2).
4. **The JWT carries only `identity_id`, never `tenant_id`.** One Identity
   can hold staff/student profiles at multiple tenants (FR-1.6); tenant
   context is resolved per-request from the `{tenantId}` path param, not
   from the token (§29.2).
5. **A parsed natural-language rule is never auto-applied.** It's always
   shown back as a deterministic, template-rendered confirmation
   ("You said: '...'. I'll apply this as: ...") and requires an explicit
   Confirm before it's persisted (§5.2, §20 step 4–5).
6. **The confirmation text is template-rendered from the structured
   object — never re-generated by the LLM.** This is what guarantees what's
   shown always matches what's stored (§14, §20 step 4). If you catch
   yourself piping the LLM's own phrasing back to the user, that's the bug.
7. **Manual edits and approvals carry `version_no`; a stale write returns
   `CONFLICT`, never a silent overwrite** (FR-9.1, §29.3).
8. **`constraint_rule.rule_type` is restricted to the enum in §30.**
   Anything the NL parser can't map to it routes to `unsupported` → manual
   structured form. Never let the parser invent a new rule_type.
9. **`block_size > 1` is opt-in per course, not a general behavior.** Only
   courses that declare it get scheduled as one atomic multi-period block
   (H15, spec §24 item 4). Don't generalize multi-period logic to courses
   that didn't ask for it.
10. **All list endpoints paginate**: `?cursor=&limit=` →
    `{items: [...], next_cursor: string|null}`. Never a bare array (§29.5).
11. **All endpoints live under `/api/v1/`.** A breaking response-shape
    change ships as `/api/v2/` alongside the old one, never as a silent
    modification (§29.1).

---

## 4. Locked Technology Stack (spec §13 — do not substitute without updating this file)

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Tailwind | Fast to build the drag-drop timetable grid and the rule-builder confirm card |
| API layer | Python (FastAPI) | Same language as the solver — no cross-language overhead passing large constraint models |
| Solver | OR-Tools CP-SAT (Python) | Fits this constraint class; supports solution hints for incremental regeneration |
| Rule parsing | LLM API call, fixed JSON output schema | Fastest path to a working NL rule builder on a hackathon timeline, no custom model training |
| Database | PostgreSQL | Join-heavy relational model; native row-level security for tenant isolation |
| Job queue / cache | Celery + Redis | Needed once a solve is long enough to require async handling |
| Auth / SSO | JWT + OAuth2 via Keycloak or Auth0 | Supports one Identity spanning multiple tenants (§15.3) without building identity from scratch |
| Containerization | Docker Compose (demo) → Kubernetes (production target) | Simple demo, explicit scaling story |

Spec §31 leaves the exact LLM provider, and frontend component/icon library
beyond React+Tailwind, as free implementation choices — pick and document,
don't ask.

---

## 5. Infra Decision (Locked)

The spec locks *Postgres + RLS* and *Keycloak/Auth0* as the auth approach (§13). 
This project has locked in **Option C — Pure local**, augmented with Keycloak, as the deployment architecture. 
The demo environment relies entirely on Docker Compose for Postgres, Redis, and Keycloak, avoiding cloud dependency for the demo. Keycloak serves standard OIDC flows for Auth.

---

## 6. Repository Layout (target structure)

Proposed monorepo shape. Names can flex, but keep the *separation* — the
solver must stay testable independently of the API and UI (NFR-19), and new
scheduling modules (e.g. exams) must slot in without changing the solver's
core contract (NFR-20).

```
smart-timetable-generator/
├── AGENTS.md
├── README.md
├── docker-compose.yml
├── .env.example
├── docs/
│   └── PROJECT_SPEC.md              # full spec — source of truth
├── apps/
│   └── web/                         # React + Tailwind (Vite)
│       └── src/
│           ├── features/
│           │   ├── setup-wizard/       # §21.1
│           │   ├── rule-builder/       # §21.2 — confirm-before-commit card
│           │   ├── generation-review/  # §21.3 — drag-drop grid, conflict overlay
│           │   ├── publish/            # §21.4
│           │   ├── faculty-student-view/ # §21.5
│           │   └── exam-module/        # §21.6
│           ├── api/                 # typed API client
│           └── lib/
├── services/
│   ├── api/                         # FastAPI core services
│   │   └── app/
│   │       ├── main.py
│   │       ├── core/                 # config, DB session, tenant-context middleware (§29.2)
│   │       ├── models/               # SQLAlchemy models mirroring §17 / §28, 1:1
│   │       ├── schemas/              # Pydantic request/response models
│   │       ├── routers/              # one per §18 resource group
│   │       ├── services/             # rule engine, publish workflow, substitution logic
│   │       ├── rbac/                 # §27 matrix as code, not scattered checks
│   │       └── rule_parser/          # §20 pipeline: LLM call → schema validate → template render
│   │   ├── alembic/                  # migrations
│   │   └── tests/
│   └── solver/                      # OR-Tools CP-SAT worker, deployable independently
│       └── solver/
│           ├── model.py             # assign[f,c,k,r,s] + one builder fn per H1–H15
│           ├── objective.py         # S1–S9 as weighted penalty terms
│           ├── worker.py            # Celery task entrypoint
│           └── conflict_checker.py  # independent re-verification (FR-6.2, invariant #2)
│       └── tests/
│           └── constraints/         # one synthetic violate-then-assert test per H1–H15 (§22.1)
├── packages/
│   └── shared-types/                # OpenAPI-generated types for FE; rule_type enum (§30) as a single source
└── infra/
    ├── docker/
    └── k8s/                         # production target (§13)
```

---

## 7. Architecture (spec §12)

Five layers, requests flowing down, results flowing back up through a
cache/read layer — **not back through the solver**:

```
Client apps (web admin/committee + mobile-responsive faculty/student)
        ↓
API gateway  — auth against Identity, RBAC, tenant routing
        ↓  (branches to Integrations: ERP / LMS / SSO / calendar)
Core services — master data · constraint rule engine · rule parsing (§20)
              · generation orchestrator · reporting — independently deployable
        ↓
Solver workers — OR-Tools CP-SAT, behind an async job queue
        ↓
Postgres + Redis — system of record (multi-tenant) and cache/queue
```

**Key design decisions (§14) to bake into the implementation, not bolt on later:**

- **Warm-started incremental regeneration** — CP-SAT `AddHint()` seeds
  re-solves from the previous solution's variable values.
- **CQRS-lite** — generation writes to a raw slot-assignment model
  (`assignment` table); *publish* is the step that denormalizes into
  per-view read tables. Don't read from raw assignments in the UI paths.
- **Decomposition into independent sub-problems** — departments sharing no
  faculty/rooms are solved as separate, parallel CSPs.
- **Tenant-aware worker pools** — solve jobs routed by tenant size/tier
  (§16).
- **Timeout with best-effort fallback** — hard constraints are always
  guaranteed; if a soft-constraint target can't be met in time, that
  shortfall is surfaced to the user, never silently dropped.

---

## 8. Data Model — entity & table index

Full column lists: spec §17 (core tables) + §28 (supporting tables, added
in the build-readiness pass to close FK gaps — §32). Model these as a 1:1
SQLAlchemy mirror; don't reshape during ORM modeling.

| Table | Key columns | Notes |
|---|---|---|
| `identity` | id, email, auth_provider_ref, platform_role (nullable) | Person-level login, tenant-independent |
| `tenant` | id, name, institution_type, timezone, enabled_modules (jsonb), isolation_mode (row\|schema) | |
| `campus` | id, tenant_id, name, timezone | Closes FR-1.4 multi-campus gap (§32 #5) |
| `department` | id, tenant_id, name | |
| `course` | id, tenant_id, department_id, name, type (core\|elective\|lab), credit_value, hours_per_week, block_size (default 1) | |
| `cohort` | id, tenant_id, name, type (fixed\|elective_derived) | |
| `batch` | id, cohort_id, course_id, label | |
| `elective_section` | id, tenant_id, course_id, term_id, capacity | Closes §32 #3 |
| `room` | id, tenant_id, campus_id, name, type, capacity, equipment_tags (jsonb), accessible (bool) | |
| `staff_profile` | id, identity_id, tenant_id, employment_type, workload_cap_week, workload_cap_day, roles (jsonb array) | |
| `student_profile` | id, identity_id (nullable), tenant_id, external_student_code, cohort_id | Closes §32 #4 |
| `eligibility` | staff_profile_id, course_id, cohort_id (composite key) | |
| `period_template` | id, tenant_id, weekday, period_index, start_time, end_time, shift | |
| `constraint_rule` | id, tenant_id, rule_type (enum §30), scope, target_id, threshold, unit, polarity, weight, source (structured\|nl), raw_input_text, status | |
| `enrollment_record` | id, tenant_id, student_profile_id, elective_section_id | |
| `exception_calendar` | id, tenant_id, date, type (holiday\|exam_period\|event\|half_day), description | Closes §32 #8 |
| `timetable_version` | id, tenant_id, term_id, state (draft\|under_review\|published\|archived), created_by, approved_by, version_no | |
| `assignment` | id, timetable_version_id, staff_profile_id, course_id, cohort_id, room_id, slot_start, slot_span | Solver's write model |
| `exam_timetable_version` | id, tenant_id, term_id, state, created_by, approved_by, version_no | Closes §32 #9 — same state machine as `timetable_version` |
| `exam_session` | id, exam_timetable_version_id, course_id, cohort_id, room_id, invigilator_staff_profile_id, slot_start | |
| `substitution_log` | id, tenant_id, original_staff_profile_id, substitute_staff_profile_id, assignment_id, date | |
| `audit_log` | id, tenant_id, actor_identity_id, action, entity_type, entity_id, before (jsonb), after (jsonb), at | Closes §32 #6 |
| `notification` | id, tenant_id, identity_id, channel (email\|push\|sms), subject, body, status (queued\|sent\|failed), created_at, sent_at | Closes §32 #7 |

**DDL reference** (spec §17) for the two tables most central to
correctness:

```sql
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
```

---

## 9. Constraint Taxonomy — this is the actual product

Everything else is scaffolding around these two lists (spec §10). Get these
right before polishing anything else.

### 9.1 Hard constraints (zero violations, always)

| ID | Constraint |
|---|---|
| H1 | No faculty double-booked across two cohorts/rooms in the same slot |
| H2 | No cohort/batch double-booked across two courses in the same slot |
| H3 | No room double-booked across two cohorts/batches in the same slot |
| H4 | Faculty not scheduled during declared unavailable/admin/reserved blocks |
| H5 | Faculty only assigned to (course, cohort) pairs they're eligible for |
| H6 | Scheduled hours/week per (course, cohort) exactly match required hours |
| H7 | Slots scheduled only within the valid period range for that day/shift |
| H8 | Faculty weekly/daily workload cap never exceeded |
| H9 | Room type/equipment matches the course's declared requirement |
| H10 | Shared-resource capacity across batch-splits never exceeded |
| H11 | An individual student's timetable has no double-booking across their course combination |
| H12 (exam) | No student has two overlapping exam sessions |
| H13 (exam) | Exam-room seating capacity never exceeded |
| H14 (exam) | Invigilator not double-booked; only assigned within availability/workload cap |
| H15 | `block_size > 1` course scheduled as N consecutive periods, same room, same day, one atomic assignment for H1–H10 |

### 9.2 Soft constraints (weighted objective terms)

| ID | Constraint |
|---|---|
| S1 | Minimize idle gaps for faculty and students |
| S2 | Balance faculty load evenly across the week |
| S3 | Distribute a course's weekly hours across different days |
| S4 | Prefer high-focus/core subjects earlier in the day |
| S5 | Minimize same-course-twice-in-one-day unless load requires it |
| S6 | Prefer parallel batch sessions aligned to the same period slot |
| S7 | Maximize room-utilization efficiency |
| S8 | Respect individual faculty time-of-day preferences |
| S9 (exam) | Spread a student's exams evenly; minimize consecutive-day exams |

### 9.3 CP-SAT model (spec §19)

Decision variable: `assign[f, c, k, r, s] ∈ {0, 1}` — staff `f` teaches
course `c` to cohort `k` in room `r`, block starting at slot `s`. Variables
are only *created* for `(f,c,k)` pairs present in `eligibility` (enforces H5
by construction) and for `(c,r)` pairs where `r.equipment_tags` matches
`c`'s requirement (enforces H9 by construction).

| Constraint | CP-SAT formulation |
|---|---|
| H1 | ∀ f,s: Σ over c,k,r of assign[f,c,k,r,s] ≤ 1 |
| H2 | ∀ k,s: Σ over f,c,r of assign[f,c,k,r,s] ≤ 1 |
| H3 | ∀ r,s: Σ over f,c,k of assign[f,c,k,r,s] ≤ 1 |
| H4 | assign[f,*,*,*,s] fixed to 0 for every s in f's blocked set |
| H6 | Σ over r,s of assign[f,c,k,r,s] == required_hours[c,k] |
| H7 | Variables only created for s within that day/shift's valid range |
| H8 | Σ over c,k,r,s of assign[f,c,k,r,s] ≤ cap[f], evaluated per week and per day |
| H10 | For lab type L, slot s: Σ of assign[...] using a room of type L at s ≤ count(rooms of type L) |
| H15 | For course c with block_size = n > 1: assign[f,c,k,r,s] implies occupancy of s..s+n−1 in every sum above; s constrained to not cross a day boundary |

Soft constraints (S1–S9) are weighted penalty terms in the objective,
minimized alongside the hard-constraint-feasible search. Incremental
regeneration calls `AddHint()` with the previous solution's variable values
before re-solving.

**Implementation convention:** one builder function per H-code
(`build_h1_no_faculty_double_booking(model, ...)`, etc.) in `model.py`, so
each has a direct, greppable link to its test in
`solver/tests/constraints/`.

---

## 10. API Conventions (spec §29)

- **Base path:** everything under `/api/v1/`. A breaking response-shape
  change ships as `/api/v2/` alongside, never a silent change to v1.
- **Auth & tenant context:** the JWT carries only `identity_id` (`sub`) —
  never `tenant_id`. Every tenant-scoped request already has `{tenantId}`
  in its path. On each request: look up whether the calling Identity has a
  `staff_profile` or `student_profile` at that tenant → check its roles
  against the §27 matrix → if authorized, run the request in a transaction
  with:

  ```sql
  SET LOCAL app.tenant_id = '<tenantId>';
  SET LOCAL app.identity_id = '<identity_id from JWT>';
  ```

  Every RLS policy follows this pattern:

  ```sql
  CREATE POLICY tenant_isolation ON <table>
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
  ```

- **Error envelope**, identical shape everywhere:

  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR | NOT_FOUND | FORBIDDEN | CONFLICT | INFEASIBLE_CONFIGURATION",
      "message": "human-readable, per FR-6.3 / NFR-10",
      "details": {}
    }
  }
  ```

- **Optimistic concurrency:** `timetable_version`, `exam_timetable_version`,
  and `assignment` all carry `version_no`. A manual edit (FR-9.1) or
  approval action must include the `version_no` it last read; a mismatch
  returns `CONFLICT` rather than silently overwriting a concurrent change.
- **Pagination:** all list endpoints accept `?cursor=&limit=`, return
  `{items: [...], next_cursor: string|null}` — never a bare array.
- **Bulk import templates** (exact column headers, spec §29.4):

  | File | Columns |
  |---|---|
  | `faculty.csv` | external_id, full_name, email, department, employment_type, workload_cap_week, workload_cap_day |
  | `rooms.csv` | external_id, name, type, capacity, equipment_tags (semicolon-separated), campus, accessible (true/false) |
  | `courses.csv` | external_id, name, department, type (core\|elective\|lab), credit_value, hours_per_week, block_size |

  Every other master-data import follows the same pattern: one column per
  required field, one `external_id` column used in row-level error
  messages.

---

## 11. Code Editing Rules (§17)
- **Surgical edits over full-file rewrites:** Always prefer small, targeted updates (e.g., using search/replace tools for specific chunks) over replacing the entire content of an existing file.
- **Diff before commit:** If a full-file rewrite is completely unavoidable, you MUST diff the new file against the prior version before committing to explicitly confirm that nothing (especially untouched imports or helper functions) was unintentionally dropped.

### Core endpoints (spec §18, condensed)

| Method & path | Purpose |
|---|---|
| `POST /tenants` | Onboard a tenant (platform operator only) |
| `POST /tenants/{id}/modules` | Enable/disable electives or exams (FR-1.5) |
| `POST /tenants/{id}/import/master-data` | Bulk import faculty, rooms, courses, cohorts |
| `POST /tenants/{id}/import/enrollment` | Import pre-resolved elective enrollment |
| `POST /tenants/{id}/rules` | Create a rule via structured fields |
| `POST /tenants/{id}/rules/parse` | Parse an NL sentence → structured object, *not persisted yet* |
| `POST /tenants/{id}/rules/{ruleId}/confirm` | Persist a previously-parsed rule after confirm |
| `POST /tenants/{id}/generate` | Trigger generation; returns job id for async tiers |
| `GET /jobs/{jobId}` | Poll generation job status |
| `GET /tenants/{id}/timetables/{versionId}` | Fetch a timetable version, any view |
| `POST /tenants/{id}/timetables/{versionId}/edit` | Manual edit, re-validated live |
| `POST /tenants/{id}/timetables/{versionId}/approve` | Mandatory review-and-approve (FR-9.3) |
| `POST /tenants/{id}/timetables/{versionId}/publish` | Publish; rejected if not yet approved |
| `POST /tenants/{id}/exams/generate` | Trigger exam-timetable generation |
| `POST /tenants/{id}/substitutions` | Record absence, request substitute suggestion |
| `GET /tenants/{id}/reports/verification` | Load-verification report (FR-8.4) |
| `GET /me/tenants` | List all tenants the current Identity holds a Staff Profile at |

---

## 11. RBAC / Permission Matrix (spec §27)

Roles: `platform_super_admin` (flag on `identity.platform_role`, not
tenant-scoped — only role permitted to call `POST /tenants`). Tenant-scoped
roles live as an array on `staff_profile.roles` (a person can hold more
than one at the same tenant): `institution_admin`, `department_head`,
`reviewer`, `faculty`. `student` lives on `student_profile`, not
`staff_profile` — a distinct identity kind, read-only over its own data.

| Action | Allowed roles |
|---|---|
| Tenant configuration, module toggles | institution_admin |
| Master data CRUD / bulk import | institution_admin, department_head (own dept) |
| Rule authoring (structured or NL) | institution_admin, department_head |
| Trigger generation | institution_admin, department_head |
| Review and approve | reviewer (may be same person as institution_admin) |
| Publish | institution_admin — only once approved |
| Manual edit | institution_admin, department_head |
| View own schedule | faculty, student |
| View all schedules / reports | institution_admin, department_head, reviewer |
| Substitution management | institution_admin, department_head |

**An endpoint not listed here defaults to institution_admin-only.** Build
the RBAC check as a single reusable dependency reading this table (put it
in `services/api/app/rbac/`), not ad hoc per-router checks.

*(TODO #1: `department_head` is currently implemented with tenant-wide write access as a tracked gap. A resource-department match against the caller's `staff_profile` is required.)*

*(TODO #2: Individualized faculty schedule view — `GET /timetables/{id}` is currently restricted to `institution_admin`, `department_head`, `reviewer` per §11 "view all schedules/reports". Faculty should eventually have a read-only view of their own assigned slots (mirrors `GET /students/{id}/timetable`). This is tracked debt; implement as a separate endpoint or a role-scoped filter on the existing one. See PROJECT_SPEC.md §32 #23.)*

*(TODO #3: Schema-per-tenant isolation — §15.1 calls for dynamic schema creation and schema-scoped migrations when `tenant.isolation_mode = 'schema'`. This is tracked debt. The column is stored but the system universally enforces Row-Level Security via Postgres `current_setting` as the active mechanism for all tiers. See PROJECT_SPEC.md §32 #25.)*

*(TODO #4: Frontend read-paths currently query raw `Assignment` and `ExamSession` tables, bypassing the CQRS read models. The frontend needs to be repointed to the denormalized `PublishedSchedule` table, which may require adding new read endpoints like `GET /published-schedules`. See PROJECT_SPEC.md §32 #24.)*

---

## 12. Natural-Language Rule Builder Pipeline (spec §20)

Build exactly this sequence — it's the whole reason invariant #5/#6 exist:

1. Admin types a sentence into the rule-builder input.
2. Backend calls an LLM with a system prompt constrained to output **only**
   JSON matching a fixed schema: `rule_type` (enum, §30), `scope`
   (tenant\|department\|faculty\|course\|cohort), `target_id`, `threshold`,
   `unit`, `polarity` (max\|min\|forbid\|require).
3. Backend validates the JSON structurally (schema check) and semantically
   (`target_id` must resolve to a real entity in this tenant). If
   `rule_type` is `unsupported` or validation fails, show the admin the
   list of supported rule types to pick from manually — never a silent
   failure.
4. If valid, generate the confirmation text via a **deterministic
   template** from the structured object — not re-asked from the LLM. This
   is what guarantees the shown text always matches what's stored.
5. On Confirm: persist with `source = 'nl'`, retain the original sentence
   for audit. On Edit: admin adjusts the structured fields directly,
   bypassing the LLM entirely.
6. At generation time, every `constraint_rule` row — regardless of source —
   compiles into the CP-SAT model identically. The solver never
   distinguishes how a rule was authored.

### Step 1 Design Resolutions
- **H8 Override Behavior:** When a `max_periods_per_day` or `max_periods_per_week` rule is scoped to a specific faculty (`target_id` = that `staff_profile`), it OVERRIDES that faculty's `workload_cap_day` / `workload_cap_week` column for H8 purposes during solver compilation.
- **S9 Override Behavior:** When an `exam_min_gap_days` rule is confirmed, it OVERRIDES the hardcoded placeholder default weight for S9. If `constraint_rule.weight` is NULL, it falls back to the existing default (50).
- **elective_no_overlap_core Rationale:** While H11 hard-guarantees no double-booking for an *enrolled* student, `elective_no_overlap_core` scoped to a cohort operates as an explicit soft priority (penalty) during scheduling. It nudges the solver to place electives at entirely different times than the core subjects of that cohort, giving students the maximum possible conflict-free elective options before enrollments are locked. The default weight is 30, overridable via `constraint_rule.weight`.
- **NULL Weight Fallback:** If a soft constraint rule's `weight` column is explicitly NULL, the `compile_constraint_rules` function MUST treat it as "use the default weight" for that rule type (as defined in `DEFAULT_WEIGHTS`), rather than `weight = 0` (which would silently disable the constraint) or throwing a compile-time error. This applies uniformly to every S1-S9-mapped `rule_type`.

### `rule_type` enum (spec §30 — closed list, nothing else is valid)

| rule_type | unit | Maps to | Example phrasing |
|---|---|---|---|
| max_periods_per_day | periods | H8 | "no faculty teaches more than 4 periods a day" |
| max_periods_per_week | periods | H8 | "faculty should teach at most 20 periods a week" |
| min_gap_between_periods | periods | S1 | "give faculty at least one free period between two teaching blocks" |
| no_consecutive_same_course | boolean | S5 | "don't put the same subject back-to-back for a class" |
| preferred_time_of_day | morning\|afternoon | S4, S8 | "science should be scheduled in the morning" |
| balance_load_across_week | boolean, tenant-wide | S2 | "spread faculty load evenly across the week" |
| room_utilization_priority | weight only | S7 | "prioritize using all rooms evenly" |
| elective_no_overlap_core | boolean, scope: cohort | H11 (reinforced as soft priority) | "electives should never clash with core classes for a cohort" |
| exam_min_gap_days | days | S9 | "give students at least one day between exams" |
| unsupported | — | none — routes to manual form | anything the parser can't map |

---

## 13. Build Order / Milestones (spec §23) — follow sequentially

| Phase | Scope | Why this order |
|---|---|---|
| 1 | Master data CRUD + single-cohort CP-SAT solver (H1–H9) + one view | Smallest slice that proves the core PS1 claim |
| 2 | Batches/labs (H10) + multi-cohort scale + load-verification report | |
| 3 | Electives ingestion + individualized student view (H11) | |
| 4 | Exam module (H12–H14) | Reuses the Phase 1–3 engine — don't build a parallel solver |
| 5 | Mandatory review/approve/publish workflow (FR-9.3) + notifications + substitution | |
| 6 | NL rule builder (§20) | Only touches `constraint_rule` storage — can run in parallel with Phases 2–5, doesn't need solver internals until generation time. Pull forward if it's already underway. |
| 7 | Multi-tenancy hardening (schema-per-tenant option) + cross-tenant Identity linking | |
| 8 | Analytics dashboards, what-if simulation, demo-dataset polish | |

---

## 14. Testing & Definition of Done (spec §22)

Don't call a phase done until its tests exist and pass — this is what
"provably conflict-free" actually cashes out to in code:

- **§22.1 Correctness tests:** for **each** hard constraint H1–H15, an
  automated test suite must cover three standard assertions:
  1. **Satisfaction**: The solver's output satisfies the constraint when a valid schedule is feasible.
  2. **Infeasibility**: The solver correctly returns INFEASIBLE when the constraint genuinely cannot be met.
  3. **Violation Reporting**: The independent conflict-checker correctly flags a manually-corrupted schedule that violates the constraint.
  Three assertions per constraint, not just one or two.
- **§22.2 Performance tests:** an automated benchmark harness generates
  synthetic tenants at each tier in §16 and asserts solve time and
  incremental-regeneration time against that tier's targets.
- **§22.3 Usability acceptance test:** a scripted walkthrough (setup →
  generate → review → approve → publish) performed by someone unfamiliar
  with the system, timed and observed for confusion points (validates
  NFR-8). This is a good fit for Playwright MCP (§18 below).
- **§22.4 Demo dataset spec** — the medium-tier synthetic dataset for the
  hackathon demo must include:
  - ≥ 40 cohorts/sections and ≥ 100 faculty
  - ≥ 1 cross-department elective basket with enrolled students
  - ≥ 2 batch-split lab courses across ≥ 2 same-type lab rooms
  - ≥ 1 multi-period (`block_size > 1`) course
  - a complete exam-period dataset (courses, student enrollment, room
    seating, invigilator pool) sufficient to run the exam module end to end

### Scale/performance targets (spec §16)

| Tier | Profile | Full-solve time | Incremental regen |
|---|---|---|---|
| Small (single school) | ≤10 sections, ≤20 faculty, no electives | ≤ 30s | ≤ 3s |
| Medium (demo baseline) | ≥40 sections, ≥100 faculty, electives+labs+exams | ≤ 3 min | ≤ 15s |
| Large (design headroom) | ≥200 sections, ≥500 faculty, multi-dept/campus | ≤ 15 min (or async) | ≤ 60s |

---

## 15. Local Dev Environment

Docker Compose services (demo target per §13):

- `postgres` — with RLS policies applied via migrations, per §10 above
- `redis` — Celery broker/result backend
- `keycloak` — Identity Provider for Auth/JWT
- `api` — FastAPI app
- `solver-worker` — Celery worker running the CP-SAT solve tasks
- `web` — Vite dev server for the React app
- (optional) a mail-catcher for notification testing (FR-11.1)

Suggested `.env` keys — fill in real values once §5's infra decision is
locked:

```
DATABASE_URL=
REDIS_URL=
JWT_ISSUER_URL=            # Keycloak/Auth0 (or Supabase Auth if Option B)
LLM_API_KEY=                # rule parser, §20 — provider is a free choice per §31
SOLVER_TIMEOUT_SECONDS=
```

Seed data should satisfy the §22.4 demo dataset checklist above — build
the seed script once in Phase 1 and extend it as later phases add
electives/exams, rather than writing a new one per phase.

---

## 16. Coding Conventions by Layer

**Backend (FastAPI):**
- SQLAlchemy models mirror §17/§28 tables 1:1 — no speculative extra
  columns.
- Tenant context is set via a FastAPI dependency wrapping every
  tenant-scoped request in the `SET LOCAL app.tenant_id` transaction
  pattern from §10 above — implement this once, reuse everywhere, don't
  inline it per router.
- Migrations via Alembic; every migration that adds a tenant-scoped table
  also adds its RLS policy in the same migration, not a follow-up.
- RBAC checks read from the single §27-matrix module (§11 above).
- **Postgres RLS and Session Context**: Postgres reverts `set_config` GUC
  variables (like `app.tenant_id`) at transaction end. Always call
  `await db.flush()` to send changes to the database, followed by
  `await db.refresh(instance)`, and strictly call `await db.commit()`
  *last* to prevent RLS context from clearing before the row is refreshed.

**Solver (OR-Tools CP-SAT):**
- One function per H-code in `model.py` (see §9.3's implementation
  convention).
- `conflict_checker.py` is a genuinely separate implementation path from
  the solver's constraint construction — re-deriving "is this schedule
  valid" from the raw `assignment` rows, not re-running the solver's own
  builder functions.
- Soft constraints live in `objective.py` as weighted terms; default
  weights are a documented, changeable constant set (§31 — free choice,
  but write down the rationale).

**Frontend (React + Tailwind):**
- Feature-folder structure aligned to the §21 wireframe screens (see §6's
  layout above).
- Drag-drop library and exact visual styling are open choices (§31) — the
  wireframes in §21 are structural requirements (required elements and
  their relationships), not pixel specs.
- The rule-builder confirm card (§21.2) must render the backend's
  template-generated text verbatim — don't reformat or re-derive it
  client-side, or invariant #6 breaks silently.

**Rule parser (§20):**
- Keep the LLM call, schema validation, and template-rendering as three
  distinct functions, in that order, so each is independently testable.
- Log `raw_input_text` alongside every persisted `nl`-sourced rule (audit
  requirement, §20 step 5).

---
## 17. Git / PR Workflow

Git history is part of the engineering workflow, not an afterthought. The agent MUST maintain small, meaningful, recoverable commits throughout implementation.

### 17.1 Branching

* Branch naming: `phase-<n>/<short-description>`, matching the §13 phase table.
* Never implement directly on `main` unless explicitly instructed.
* Keep each phase/workstream isolated to its own branch where practical.

### 17.2 Mandatory Checkpoint Commits

The agent MUST commit after every meaningful implementation checkpoint.

A checkpoint is reached when one coherent unit of work is complete and verified. Examples:

* project/scaffolding setup completed
* database schema/models for one entity group completed
* migration created and successfully applied
* one API resource CRUD completed and tested
* authentication/RBAC slice completed and verified
* one solver constraint H-code implemented + its tests pass
* one conflict-checker constraint implemented + its tests pass
* one frontend feature/screen completed and verified
* one API ↔ frontend integration completed
* one bug fixed with a regression test
* one phase milestone or independently testable vertical slice completed
* documentation/configuration updated as part of a completed decision

**Do NOT wait until an entire phase is complete before committing.**

Conversely, do NOT create meaningless commits for every tiny edit such as changing one variable, renaming a local variable, or making intermediate edits that are not independently useful.

### 17.3 Required Commit Loop

After completing each checkpoint, follow this exact sequence:

1. Inspect the working tree with `git status`.
2. Inspect the changes with `git diff`.
3. Run the tests/checks relevant to the checkpoint.
4. Fix any failures before committing.
5. Review the final diff again.
6. Create a focused commit containing only the completed checkpoint.
7. Verify the commit succeeded with `git status` and `git log -1`.
8. Continue to the next checkpoint.

The agent MUST NOT continue accumulating unrelated completed work after reaching a commit-worthy checkpoint.

### 17.4 Commit Size

Prefer small, cohesive commits over large milestone dumps.

A commit should answer:

> "What single piece of functionality, infrastructure, correctness, or documentation became complete in this commit?"

Avoid commits such as:

* `implement phase 1`
* `lots of backend work`
* `final changes`
* `updates`
* `misc fixes`

when they contain multiple unrelated pieces of work.

If multiple files are required to complete one coherent feature, they SHOULD be committed together. File count alone is not a reason to split a commit.

### 17.5 Commit Message Format

Use conventional, descriptive commit messages:

`<type>(<scope>): <short description>`

Allowed types:

* `feat` — new functionality
* `fix` — bug fix
* `test` — tests without production behavior changes
* `refactor` — behavior-preserving restructuring
* `perf` — performance improvement
* `docs` — documentation
* `chore` — tooling/configuration/dependency work
* `ci` — CI/CD changes

Examples:

* `feat(api): add tenant CRUD endpoints`
* `feat(solver): implement H1 faculty collision constraint`
* `test(solver): add H1 satisfaction and infeasibility cases`
* `feat(auth): add tenant-scoped RBAC dependency`
* `fix(db): preserve tenant context during transaction refresh`
* `feat(web): add timetable generation review grid`

For solver constraints, include the H-code whenever applicable.

### 17.6 Test-to-Commit Rule

A checkpoint that has a defined automated test MUST NOT be committed as complete while that test is failing.

For example:

> Implement H1 → add H1 tests → run tests → all H1 tests pass → commit.

Do not implement H1–H9 and then make one large commit after all constraints are finished. Prefer one or a small number of commits corresponding to independently completed constraints or coherent solver slices.

### 17.7 Bug-Fix Rule

Every non-trivial bug fix SHOULD include a regression test when practical.

Preferred workflow:

`reproduce → add regression test → fix → verify → commit`

Example:

`fix(rules): reject unsupported rule types`

with a corresponding test proving that an unsupported rule type cannot be persisted.

### 17.8 Checkpoint Recovery

Commits should leave the repository in a recoverable state.

A future agent should be able to:

* inspect the commit history,
* understand what has already been completed,
* run the relevant tests,
* continue from the latest successful checkpoint,
* and revert a problematic checkpoint without losing unrelated work.

Do not leave large amounts of completed-but-uncommitted work in the working tree.

### 17.9 Push / GitHub Synchronization

When GitHub MCP or equivalent Git tooling is available:

* Push completed checkpoint commits to the active remote branch periodically.
* At minimum, push after a significant vertical slice and before moving into a risky or substantially different implementation area.
* Before opening/updating a PR, ensure the branch is clean and all intended checkpoint commits are present on the remote.
* Do not force-push or rewrite shared history unless explicitly instructed.

If the environment does not permit pushing, still create the local checkpoint commits.

### 17.10 Phase Completion

A phase is not complete merely because its implementation exists.

Before declaring a phase complete:

1. Run the phase's Definition-of-Done tests from §14.
2. Inspect `git status` and confirm there is no unintended uncommitted work.
3. Review the phase's commit history.
4. Ensure each major checkpoint is represented by a focused commit.
5. Push the branch when GitHub access is available.
6. Only then prepare/update the PR.

A PR touching the solver includes the relevant `solver/tests/constraints/` results in the description and identifies the affected H-codes.

A PR touching `constraint_rule` or the rule parser confirms invariants #5/#6/#8 were not violated.

Don't merge a phase's branch until its §14 Definition-of-Done tests are green.

### 17.11 Commit Before Context Switching

Before switching from one major workstream to another, the agent SHOULD commit the completed work.

For example:

`database schema → commit → API implementation → commit → solver constraint → commit → frontend integration → commit`

Do not leave completed backend, solver, and frontend work mixed together in one uncommitted working tree unless they are genuinely one atomic feature.

### 17.12 Documentation Synchronization

When an implementation decision resolves an item listed under §19, update this `AGENTS.md` in the same checkpoint or immediately adjacent documentation commit.

The commit should clearly identify the decision, for example:

`docs(infra): lock LLM provider decision`

### 17.13 Git Safety Rules

* Never commit `.env`, API keys, credentials, tokens, private keys, or other secrets.
* Respect `.gitignore`.
* Never use `git reset --hard`, `git clean -fd`, force-push, or history-rewriting commands to discard work unless explicitly instructed.
* Before destructive Git operations, stop and ask the developer.
* Do not amend an existing commit unless explicitly instructed or unless the commit has not been shared and the correction is clearly part of the same immediate checkpoint.
* Prefer adding a corrective commit over rewriting history.

---
## 18. MCP Servers — when to use each

These are available for this build; use them the way a developer would
reach for the right tool, not by default on everything.

| Server | Use it for | Notes |
|---|---|---|
| **GitHub MCP** | Repo/PR/CI operations — opening the phase branches from §17, creating PRs, checking CI status before merge | Connect via remote `serverUrl` or a local Docker container |
| **Google Data Cloud MCP** (Cloud SQL / AlloyDB for Postgres) | Direct schema administration and SQL generation against a managed Postgres instance | Only if **Option A** in §5 is chosen |
| **Firebase MCP** | Building and running a deployment plan for the React frontend | A live alternative to Vercel for `apps/web`; only if **Option A** in §5 is chosen |
| **Supabase MCP** | Directly connectable Postgres + RLS + Auth administration | Only if **Option B** in §5 is chosen — don't wire this alongside Google Data Cloud MCP, they're alternative paths, not complementary |
| **Playwright MCP** | Automated verification of the drag-drop editor (§21.3) and the rule-builder confirm card (§21.2) as they're built | Also the natural fit for the §22.3 usability walkthrough once Phase 5's review screen exists |

**Rule of thumb:** GitHub MCP and Playwright MCP are useful throughout the
whole build. The database/hosting MCPs (Google Data Cloud vs Supabase) are
mutually exclusive — resolve §5 first, then only connect the one that
matches.

---

## 19. What's Genuinely Open (spec §31) — decide freely, just document it

Not gaps in the spec, ordinary engineering judgment calls:

- Exact LLM provider/model for rule parsing — any provider supporting
  constrained/structured JSON output satisfies the pipeline.
- Default numeric weights for soft constraints S1–S9 — tenants can retune
  later; pick a reasonable starting default.
- Tie-break rule for ranking eligible substitutes (FR-10.2) beyond
  "eligible, free, not overloaded" — e.g. least-loaded-first vs
  most-recently-taught-this-cohort-first. Either is valid; document
  whichever is chosen in code.
- Exact visual spacing/styling of the §21 screens — those are structural
  wireframes, not pixel-level design.
- Frontend component/icon library choices beyond React + Tailwind.

---

## 20. Quick Reference — Resolved Items (spec §24)

If a question about the following ever seems open again while coding, it
isn't — check spec §24 for the resolution before re-litigating:

- Review-before-publish: **mandatory for every tenant**, no exceptions.
- NL rule builder: **in v1**, not roadmap.
- Tenant isolation: **both** row-level (default) and schema-per-tenant
  (explicit upgrade path) are in scope.
- Multi-period courses: supported, **opt-in per course** via `block_size`.
- Rooms/labs: **confirmed hard-constrained** resources.
- Elective/exam modules: **explicitly toggleable per tenant**.
- Cross-tenant faculty identity: **supported** at the auth layer, isolated
  at the data layer.
