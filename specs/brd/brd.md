# TeleMed - Business Requirements Document

Status: DRAFT, awaiting human approval. Project: BC-AINE-010 (Healthcare / Digital Health). Date: 2026-10-05.

## 1. Executive Summary
TeleMed is a telemedicine appointment booking platform for a single telehealth provider. Patients self-serve: find a doctor, see real open slots, and book, reschedule or cancel. Doctors work a daily queue, drive an enforced appointment lifecycle, and append consultation notes. Admins onboard doctors and manage users. It is an assessed capstone prototype graded by an automated rubric against the repo, not a live clinical product. Data is synthetic only. Video, payments, e-prescription and notifications are stubbed.

## 2. Problem Statement
- Main pain: patients cannot easily find a suitable doctor (specialty, language, availability), cannot see real open slots, and cannot book, reschedule or cancel without phone-tag.
- Second pain: no clear per-doctor daily queue, no enforced appointment lifecycle (no-shows unrecorded), no append-only record of consultation notes.
- Context: one organisation owns the platform; admin-onboarded doctors. Not a provider network, marketplace or reference platform.
- Cost of not solving (ASSUMPTION, the brief does not describe the current process): booking runs through phone, WhatsApp or front desk, causing double-bookings, no visible availability, unrecorded missed appointments, disputed cancellations/refunds, and notes kept outside any controlled append-only record.

## 3. Target Users
| Role | Profile | Device |
|------|---------|--------|
| Patient | Non-technical, occasional, few taps | Mobile-first, 375px |
| Doctor | Moderately technical, fast status changes and note capture between visits | Desktop, 1280px |
| Admin | Moderately technical, onboarding and user management | Desktop, 1280px |

## 4. Success Metrics
a. Median search-to-confirmed-booking under 2 minutes.
b. Zero double-bookings: 20 concurrent requests for one slot yield exactly 1 booking (201) and 19 SlotUnavailableException (409) (NFR-08).
c. No-show rate tracked; NO_SHOW is a lifecycle state and every transition is an append-only event (AC-08, NFR-02).
d. At least 90% of bookings complete without admin help.
e. Coverage >= 80% overall, >= 95% on the domain layer.
f. Each of the 10 acceptance criteria has at least one test tagged with its AC-NN ID.
g. /health returns 200 within 1s of successful startup (NFR-07).

## 5. Scope
In scope: patient self-registration (AC-01), profile management (patient and admin), doctor search, 14-day slots, book, cancel (AC-06), reschedule (AC-07), doctor slot calendar with block/unblock, daily queue, lifecycle state machine (AC-08), append-only consultation notes, admin doctor onboarding (AC-10) with availability template, admin user list/deactivate/reactivate, role separation (NFR-04).

Out of scope: real video (stubbed join link), real payments and refunds, e-prescription, real notifications, multi-provider, insurance, recurring appointments, ratings, chat, file uploads, password-reset email, HIPAA workflows, refresh tokens, rate limiting, doctor self-signup, admin cancel-on-behalf.

## 6. MVP Definition
The MVP is the full in-scope list above, including reschedule, admin user management, role separation and the concurrency guarantee, because the brief lists them. All 10 ACs are covered.

Key rules:
- Patient registration always creates PATIENT; role is never accepted from the body. Duplicate email: 409. Password 8-128 chars.
- Doctors/admins are never self-registered.
- Slots are generated from the admin-set availability template (no hand-created slots, no publish step). Slot length default 30 min, constant per doctor.
- Doctor search: filter by specialty, language, availability range (available_from, available_to); sort by earliest slot, fee, or name; fee visible before booking. Deactivated doctors hidden.
- Consultation notes: free text, max 5000 chars, multiple per appointment, never editable/deletable. Only the appointment's doctor may add, only after COMPLETED. Readable only by that patient, that doctor and an admin.
- Fees: integer minor units in DB, Decimal in domain, converted only at the repository boundary, API string like "500.00". No floats (NFR-01).
- Stubs (video, payments/refund, e-prescription, notifications) sit behind interfaces. They do not write to the appointment event log; each emits one structured JSON log line with identifiers only. Tests use spies (e.g. refund stub called exactly once on cancellation).

## 7. Alternatives Considered
- A (CHOSEN): layered modular monolith on SQLite (WAL, busy_timeout), DB-enforced atomicity via a single conditional UPDATE inside one transaction. Every transition and reschedule appends an immutable event row in the same transaction (required by NFR-02). Rationale: simplest, matches the scaffold, zero infrastructure, fast startup, easy to verify.
- B (rejected): same monolith on PostgreSQL with row locks. Rejected: needs Docker/Postgres, conflicts with local `npm start`, adds startup friction and risks the 1s health target. Better suited to real production.
- C (rejected): full event sourcing. Rejected: over-engineered, needs projections/read models for queue and search, risks schedule and coverage targets. Instead, state lives on the appointment row with an append-only event log beside it.

## 8. Technical Architecture
- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, uv, ruff, mypy --strict, pytest (pytest-bdd, pytest-cov), import-linter.
- Frontend: React 18, Vite, Tailwind, react-router, TypeScript, vitest; E2E Playwright.
- Ports: backend :8000, frontend :5173. `npm start` runs both. No Docker.
- Layers (one-way imports, enforced): Types, Config, Repository, Service, API, UI.
- Auth: short-lived JWT, argon2 hashing, no refresh tokens, no password reset. Role and ownership checks server-side on every route (NFR-04). Role is loaded from the DB user per request (token claim never trusted alone). Deactivated users rejected at login and on every token use. Admins can access everything. UI route guards are convenience only.
- Status codes: 401 bad/missing token; 403 wrong role for route; 404 right role asking for another user's object; login failure = one generic message with 401; 422 only for malformed input (naive datetime, bad fee, bad template); 409 for any valid request refused by state or business rule; 503 generic body on SQLite lock timeout.
- Concurrency: busy_timeout long enough that 20 concurrent bookings give one 201 and nineteen 409, never 503. No idempotency key; the loser gets 409.
- Time: stored in UTC; API rejects naive datetimes (422). PROVIDER_TIMEZONE setting (default UTC) governs template wall-clock times and the "day" of the queue; expansion is zone-aware.
- Slot generation: idempotent; runs at onboarding, in the seed script, and on app startup. Creates a slot only if now < start < now + 14 days. Past slots never listed or bookable; no cleanup job.
- Observability: structured JSON logs; correlation_id from validated incoming X-Request-ID or generated, echoed in the response header. Identifiers only (user_id, appointment_id); never note content, medical history, names or contact details (NFR-03).
- Performance: only two requirements: NFR-07 (/health within 1s) and NFR-08 (20 concurrent -> 1 booking). No latency target.

## 9. Data Model Overview
- User (role, active status); PatientProfile (identity) + patient_profile_versions (insert-only; current = latest); DoctorProfile (specialty, languages, fee); AvailabilityTemplate (weekday, start, end, slot length); Slot (AVAILABLE | BOOKED | BLOCKED, UTC); Appointment; AppointmentEvent (append-only, records actor role, old/new slot for reschedule); ConsultationNote (append-only).
- patient_profile_versions, appointment_events, consultation_notes are protected by SQLite triggers rejecting UPDATE and DELETE.
- Slot transitions (single conditional UPDATEs): book AVAILABLE->BOOKED; block AVAILABLE->BLOCKED (never over a booked slot); unblock BLOCKED->AVAILABLE. A doctor may only block/unblock their own slots.

Appointment state machine (each transition inserts exactly one event):
BOOKED -> CHECKED_IN | CANCELLED | NO_SHOW; CHECKED_IN -> IN_PROGRESS | NO_SHOW; IN_PROGRESS -> COMPLETED. COMPLETED, CANCELLED, NO_SHOW are terminal. CHECKED_IN cannot go to CANCELLED. NO_SHOW only after start time has passed, else InvalidAppointmentStateException (409).

## 10. External Integrations
None real. Video (stub join link), payments/refunds, e-prescription and notifications are stubbed behind interfaces; see Section 6 for stub behaviour.

## 11. Edge Cases & Constraints
- Patient cancel (AC-06): allowed when (start - now) >= 60 min (exactly 60:00 allowed; 59:59 or after start refused with 409). Slot returns to AVAILABLE, refund stub called once, one event appended.
- Doctor cancel: BOOKED->CANCELLED, no 60-min window, slot set to BLOCKED, refund stub once, actor role recorded. COMPLETED/NO_SHOW slots stay BOOKED as history.
- Reschedule (AC-07): atomic (claim target + release old in one transaction), same appointment_id, appends RESCHEDULED event (old and new slot), 60-min rule applies, BOOKED only, same doctor only. 409 with nothing changed if target is unavailable, blocked, started, outside the 14-day window, the same slot, or another doctor's.
- Deactivation: deactivating a doctor with any non-terminal appointment (BOOKED, CHECKED_IN, IN_PROGRESS) -> 409. Deactivated doctors hidden from search; their slots cannot be booked even by slot ID. Deactivated patient cannot log in; existing appointments remain but cannot be extended; doctor can still process them. Admin cannot deactivate own account. Reactivation allowed.
- Likely failure modes (first 6 months): template misconfiguration (end not after start, slot length not positive or not dividing the window -> 422 at onboarding); stale slots after long downtime (startup generation catches up); SQLite lock contention.
- Compliance bar limited to the brief: append-only appointment events, notes and profile changes; no health information in logs; strict role separation (a patient can never read another patient's data). Synthetic data only. Real HIPAA workflows out of scope.

## 12. UI Context
- Design source: HTML mockups in `specs/design/mockups/` (one self-contained file per E5 story, generated by /design with the ui-designer) are the visual contract: calm clinical look, teal or blue, high contrast. React pages are ported from them. No external design tool (Stitch) is used.
- Screens: Public: register, login. Patient: doctor search (filters and sort), doctor detail with 14-day slot picker, booking confirmation, My appointments (cancel/reschedule), consultation notes view, profile edit. Doctor: daily queue (status actions), slot calendar (block/unblock), appointment detail with append-only notes. Admin: onboard doctor (with availability template), user list with deactivate/reactivate and Edit profile for patients (AC-01).
- Lifecycle in UI: each appointment API response includes a list of allowed next actions; the queue shows only those buttons (frontend does not duplicate the state machine). Mark NO_SHOW disabled until start time passes. On My appointments, cancel and reschedule are DISABLED with an explanation inside the last 60 minutes. Disabled is a hint only; server is authoritative and the UI still handles 409.
- States: every screen has loading, empty and error states. 409 -> inline message + refresh slot list; 503 -> generic "try again"; 401 -> clear session and redirect to login; unknown or other users' objects -> not-found page.
- Viewports: exactly 375px and 1280px, no 768px tier, no horizontal scroll at 375px. Patient screens 375-first; doctor/admin 1280-first; every screen works at both.
- Time display: patient screens show browser-local zone with abbreviation (e.g. "10:30 IST"); doctor/admin show provider timezone with its label. The queue endpoint takes a date interpreted in the provider zone.
- Session/routing: role-specific home (patient: doctor search; doctor: daily queue; admin: user list and onboarding); redirect to login when unauthenticated; "not allowed" page for wrong role; access token in sessionStorage (never localStorage); expired token -> login.
- Accessibility: build target (not a graded gate), aim WCAG 2.1 AA: keyboard nav, visible focus, labelled controls, 4.5:1 contrast, status by text as well as color, 44px tap targets, ARIA live regions for errors. No separate accessibility test suite.
- Video join link (PROPOSED BY ASSISTANT, PENDING USER APPROVAL; the user said "if required" and gave no detail): the video stub returns a placeholder join URL (no real video). The UI shows a "Join video visit" link/button on appointment cards and detail, for the patient and the doctor only, while the appointment is BOOKED, CHECKED_IN or IN_PROGRESS; hidden for terminal states. The stub emits one JSON log line with identifiers only (appointment_id, event type) and writes nothing to the appointment event log. Tests verify it with a spy.
- Frontend testing (PROPOSED BY ASSISTANT, PENDING USER APPROVAL; builds on the user-stated desktop/mobile Playwright projects with screenshot baselines, fixed timezone and fixed clock):
  - vitest + @testing-library/react for components and hooks: cancel/reschedule disabled with explanation inside 60 min, queue buttons driven by the allowed-actions list, 409 inline message + slot refresh, 401 redirect, not-found page, sessionStorage token.
  - Playwright E2E, desktop (1280) and mobile (375) projects, fixed timezone and clock, screenshot baselines, covering: patient booking flow (search -> slot -> book -> My appointments -> cancel/reschedule); doctor daily queue (status actions, NO_SHOW disabled before start, append note after COMPLETED); admin doctor onboarding and user deactivate/reactivate.
  - Each AC has at least one test tagged with its AC-NN ID.

## 13. Open Questions
1. Fee and refund amount rules (only fixed-point fees and "refund stub called once on cancellation" are specified).
2. Fee currency.
3. API versioning prefix (/api/v1) and error body format (e.g. RFC 7807).
4. Seed-data size.
5. How seed data is marked as synthetic.
6. Approve the assistant-proposed defaults for the video join link UI and the frontend testing plan (Section 12), which the user requested "if required" without further detail.
7. Dimension 2 was accepted as drafted but not explicitly confirmed as a summary; treated as accepted.

## Appendix A. Source Acceptance Criteria and NFRs (Business Case BC-AINE-010, Section 5)

Provided verbatim by the user. Each AC must have at least one test referencing its AC-NN identifier.

### A.1 Functional Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-01 | Patient can register with profile (name, age, gender, contact details); profile is editable by the patient and admin only |
| AC-02 | Patient can search the doctor catalog by specialty, language, and availability; results are filterable and sortable |
| AC-03 | Patient can view available slots for a selected doctor for the next 14 days |
| AC-04 | Patient can book an available slot; appointment enters BOOKED state with a unique appointment_id |
| AC-05 | Slot conflict prevention: an already-booked slot cannot be booked again; system raises SlotUnavailableException |
| AC-06 | Patient can cancel an appointment up to 1 hour before start time; cancellation triggers refund stub |
| AC-07 | Patient can reschedule an appointment to another available slot of the same doctor; reschedule audited |
| AC-08 | Appointment lifecycle BOOKED -> CHECKED_IN -> IN_PROGRESS -> COMPLETED / NO_SHOW / CANCELLED is enforced; invalid transitions raise InvalidAppointmentStateException |
| AC-09 | Doctor can add consultation notes to an appointment after marking it COMPLETED; notes are append-only and visible to the patient |
| AC-10 | Admin can onboard a new doctor with specialty, languages, consultation fee, and slot availability template |

### A.2 Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | Consultation fees are computed in fixed-point (BigDecimal / decimal), never floating-point |
| NFR-02 | Appointment state transitions, consultation notes, and patient profile changes are append-only |
| NFR-03 | Patient health information (medical history, consultation notes) is never written to logs in plaintext |
| NFR-04 | Authentication boundary at controller layer; patient / doctor / admin roles are separated; a patient cannot access another patient's data |
| NFR-05 | Database migrations are append-only |
| NFR-06 | Structured JSON logs with request correlation IDs |
| NFR-07 | Health endpoint returns 200 within 1 second of a successful startup |
| NFR-08 | Architecture rules enforced as tests: slot booking is atomic (no double-booking under concurrent requests); consultation notes once added cannot be edited |

### A.3 Story coverage

| Criterion | Stories |
|---|---|
| AC-01 | E1-S3, E1-S5, E4-S2, E5-S3, E5-S5 |
| AC-02 | E2-S4, E5-S2, E6-S3 |
| AC-03 | E2-S1, E2-S3, E2-S4, E5-S2 |
| AC-04 | E3-S2, E4-S3, E5-S2, E6-S3 |
| AC-05 | E3-S2 |
| AC-06 | E3-S1, E3-S3, E5-S3, E6-S3 |
| AC-07 | E3-S4, E5-S3, E6-S3 |
| AC-08 | E3-S5, E5-S4, E6-S3 |
| AC-09 | E4-S1, E4-S3, E5-S3, E5-S4, E6-S3 |
| AC-10 | E2-S2, E5-S5, E6-S3 |
| NFR-01 | E1-S1, E2-S2 |
| NFR-02 | E1-S1, E1-S5, E3-S4, E3-S5, E4-S1 |
| NFR-03 | E1-S2, E1-S5, E4-S1 |
| NFR-04 | E1-S4, E4-S2, E5-S1 |
| NFR-05 | E1-S1 |
| NFR-06 | E1-S2 |
| NFR-07 | E1-S2 |
| NFR-08 | E3-S2, E4-S1 |

E6-S2 enforces tagged-test traceability for every AC and NFR.
