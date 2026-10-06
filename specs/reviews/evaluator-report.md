# Evaluator Report - Group I (E4-S1 notes, E4-S3 my appointments)

Verdict: PASS (local mode, backend :8000, live app plus pytest)

Layers: API (live) PASS, pytest 26 passed with 0 skipped, architecture PASS. Playwright and design: none in contract.

| Check | Result | Evidence |
|---|---|---|
| I-API-0 | PASS | /health 200; admin login; 2 doctors onboarded; P1-P3 registered; bookings |
| I-API-1 | PASS | Real flow BOOKED -> CHECKED_IN -> IN_PROGRESS -> COMPLETED; 2 notes 201 with larger note_id; list ascending, total 2; 2 DB rows |
| I-API-2 | PASS | 409 INVALID_APPOINTMENT_STATE for 5 non-COMPLETED statuses; patient 403 on those; on COMPLETED other doctor 404, patient 403, admin 403, no token 401; nonexistent 404; no rows added |
| I-API-3 | PASS | 5000 ASCII and 5000 Unicode chars round-trip; 5001, empty, whitespace, missing, int, null, list all 422 VALIDATION_ERROR; only accepted notes stored |
| I-API-4 | PASS | PUT/PATCH/DELETE 405 METHOD_NOT_ALLOWED with Allow containing GET; raw sqlite UPDATE/DELETE fail with "append-only"; row unchanged |
| I-API-5 | PASS | Owner patient, doctor A, admin 200 for list and single; P2 and doctor B 404; nonexistent appt 404; other appt's note_id 404; no token 401; no notes gives 200 [] total 0 |
| I-API-6 | PASS | note_added log lines carry appointment_id and user_id; unique PHIMARKER (201 and 422 cases) absent from server log (0 matches); test_note_post_logs_ids_never_text exists and passes |
| I-API-7 | PASS | /mine 200 (not shadowed); only caller's items; ascending start_time; total == len; fee string "500.00"; doctor name; allowed_actions list; ?status=CANCELLED filter; bogus status 422; empty patient gives [] and 0; doctor 403, admin 403, none 401 |
| I-API-8 | PASS | P1 200, P2 404, doctor A 200, doctor B 404, admin 200 with [] and null join_url, nonexistent 404, no token 401 |
| I-API-9 | PASS | +90m: [CANCEL, RESCHEDULE], change_deadline = start - 60m (GET and mine); +30m: []; CANCELLED: none. Exact boundary: test_sixty_minute_boundary_with_injected_clock passes |
| I-API-10 | PASS | join_url non-empty and contains id for BOOKED/CHECKED_IN/IN_PROGRESS (P1, doctor, mine); null for COMPLETED/CANCELLED/NO_SHOW; admin always null; booking response has join_url |
| I-API-11 / 12 | PASS | pytest test_notes.py + test_notes_immutable.py + test_my_appointments.py: 26 passed, none skipped |
| Architecture | PASS | All 7 files exist; notes router included in app; POST uses require_roles(DOCTOR); ensure_can_read used; notes_repo has insert/list_for_appointment/get only; lint-imports 2 kept 0 broken; mypy --strict clean; ruff clean; all files < 300 lines |

Caveats:
- NO_SHOW and CANCELLED were reached via the real API (slot moved to started via sqlite) rather than raw status updates; equivalent states.
- Content rules for logging and the injected-clock created_at were verified behaviourally and by passing tests, not by reading code.
- Frontend is out of scope for this group.
- Setup note: sqlite timestamps must use the format "YYYY-MM-DD HH:MM:SS.ffffff"; the ISO "T" form made login return 500. This is a test-setup note, not a defect.
- Server stopped; eval-i.db and eval-i-server.log removed. No application code modified.
