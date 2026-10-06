# Evaluator Report - Group E (E2-S3, E2-S4; F038-F048)

Verdict: PASS (all architecture checks and all 23 api_checks passed; no failures; no eval-failures JSON written)

Contract: sprint-contracts/group-E.json (final, unmodified). Mode: local. Backend started per start_command (DATABASE_PATH=./eval-e.db, JWT_SECRET 40 bytes, PROVIDER_TIMEZONE=UTC, APP_ENV=dev; alembic upgrade head, uvicorn --factory on 127.0.0.1:8000). Health returned 200 on the first attempt. Admin inserted via sqlite3 with an argon2 hash from telemed.service.security. Doctors A (Carl Cardio, Cardiology, [hi,en], 500.00), B (Abe Derm, Dermatology, [en], 750.00), C (Zed Cardio, Cardiology, [hi], 300.00) onboarded through POST /api/admin/doctors (201, slots_created > 0, 14 days of slots); patient P registered via the API. BOOKED/past/far/BLOCKED states arranged via sqlite3. 92 individual assertions executed (script in the scratchpad), 0 failed. Server stopped, backend/eval-e.db and eval-e-server.log deleted, port 8000 confirmed closed.

## Architecture checks: PASS
- All 6 files_must_exist present (routers/doctors.py, schemas/slots.py, schemas/doctors.py, doctor_service.py, slots_repo.py, doctors_repo.py).
- Block/unblock: slots_repo.transition is a single conditional UPDATE (slot_id AND doctor_id AND status = expected), rowcount checked. The service does not read-then-write; it reads after the UPDATE only to classify a no-op (absent or foreign slot is 404, wrong state is 409 INVALID_SLOT_STATE).
- /api/doctors/me/* guarded by require_roles(Role.DOCTOR); the literal /me routes are registered before /{doctor_id} in routers/doctors.py.
- GET /me/slots uses aliases from/to with AwareDatetime, defaults from=now and to=from+14d, and a service-level check (to>=from, range<=31d) that returns 422.
- Filter and sort logic lives in doctors_repo.search_active: lower() specialty, json_each language, EXISTS over AVAILABLE slots, sort earliest_slot (nulls last), fee (fee_minor) or name, ties by lower(name) then doctor_id. sort is the DoctorSort enum (422 when invalid). The router does no filtering or sorting.
- Fee serialised through format_fee (str, quantize 0.01); the summary query filters User.active == 1 and role DOCTOR.
- open_slots query: status = AVAILABLE AND start_time > now AND start_time < now + 14d, ordered by start_time.
- All /api/doctors routes depend on get_current_user (401).

## API checks
- E-API-0 PASS: health 200; onboard A, B, C 201 with slots_created > 0; all logins and the patient registration succeeded.
- E-API-1a PASS: 200, non-empty, fields typed correctly, all doctor_id == A, ascending, total == len(items).
- E-API-1b PASS: BLOCKED and BOOKED slots appear with their real status; a narrow window returns only the slot inside it; the default range matches the DB count for now..+14d; to<from 422 VALIDATION_ERROR; 32 days 422; exactly 31 days 200.
- E-API-2a PASS: 200 with slot_id, doctor_id, status BLOCKED and times; sqlite and listing confirm BLOCKED.
- E-API-2b PASS: second block 409 INVALID_SLOT_STATE with a message; row unchanged.
- E-API-3 PASS: block on a BOOKED slot gives 409 INVALID_SLOT_STATE; slot, appointment row (byte-identical) and appointment_events count unchanged.
- E-API-4a PASS: unblock 200 AVAILABLE, confirmed in sqlite. E-API-4b PASS: unblock on AVAILABLE and on BOOKED each 409 INVALID_SLOT_STATE, rows unchanged.
- E-API-5a PASS: doctor A block and unblock on B's slot 404 (code and message strings present), B's slot still AVAILABLE; slot 999999 404 on both.
- E-API-5b PASS: patient and admin get 403 on block, unblock and GET /me/slots; no token gives 401 on block and unblock; slot unchanged.
- E-API-5c PASS: A block and unblock on B's BOOKED slot and on B's BLOCKED slot all 404, not 409; B's slots and appointment unchanged.
- E-API-6a PASS: Cardiology gives {A, C} only, total == len, case-insensitive, unknown specialty gives {"items":[],"total":0}.
- E-API-6b PASS: language=hi gives {A, C}, HI gives the same, en gives {A, B}, specialty=Cardiology&language=en gives {A}.
- E-API-7a PASS: all of A's slots on day D blocked or booked, so the range D 00:00Z..23:59Z returns B and not A; a wider range containing open days returns A.
- E-API-7b PASS: available_to < available_from gives 422 VALIDATION_ERROR; naive datetimes give 422 VALIDATION_ERROR.
- E-API-8 PASS: sort=fee gives C(300.00), A(500.00), B(750.00); sort=name gives B(Abe), A(Carl), C(Zed); default and sort=earliest_slot are nondecreasing with nulls last; sort=bogus 422.
- E-API-9a PASS: fee is a JSON string matching ^\d+\.\d{2}$; earliest_slot equals the sqlite MIN(start_time) of AVAILABLE slots in (now, now+14d) for every doctor; items expose exactly the six DoctorSummary fields.
- E-API-9b PASS: no admin deactivate route is mounted (404 on POST and PUT), so I used the sqlite fallback (UPDATE users SET active=0 on C). C is absent from the unfiltered, specialty, language and sort listings. GET /api/doctors/{C}/slots 404, GET /api/doctors/{C} 404, GET /api/doctors/{A} 200.
- E-API-9c PASS: total == len; A and B specialty, languages and fee match the onboarding values.
- E-API-10a PASS: with A's AVAILABLE (now+2h), BOOKED, BLOCKED, past (-1h) and +15d slots arranged, only the AVAILABLE future one is returned; the other four are absent by slot_id; every item AVAILABLE, ascending, within the window, total == len; the list equals the sqlite query result.
- E-API-10b PASS: doctor id 999999 gives 404; a patient's user id gives 404.
- E-API-10c PASS: doctor and admin tokens get 200 on /api/doctors and /api/doctors/{A}/slots.
- E-API-11a PASS: no token and a garbage token on /api/doctors give 401.
- E-API-11b PASS: no token and a garbage token give 401 on /api/doctors/{A}/slots, /api/doctors/{A} and /api/doctors/me/slots; the patient token on /me/slots gives 403 (route ordering correct).

## Notes
- No application code modified. features.json not modified by this run (the caller did not ask for it).
- Observation, not a failure: the deactivate route is not mounted, which the contract allows (sqlite fallback).
