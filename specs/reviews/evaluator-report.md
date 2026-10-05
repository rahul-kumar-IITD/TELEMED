# Evaluator Report - Group D (E1-S5, E2-S2, E5-S1)

Verdict: PASS (all gating checks passed; no failures; no eval-failures JSON written)

Contract: sprint-contracts/group-D.json (final, unmodified). Mode: local. Servers started via root `npm start` with DATABASE_PATH=./eval-d.db (start-backend.mjs defaults JWT_SECRET/APP_ENV=dev/PROVIDER_TIMEZONE=UTC). Health on :8000 and :5173 (proxy) returned 200 on first attempt. Admin inserted via sqlite3 with argon2 hash from backend security module. Evaluation instant was 2026-10-05T23:06Z (Monday, UTC); the first slot window still yielded Mondays 10-12 and 10-19, 12 slots as expected.

## Architecture checks
- All 21 files_must_exist present. files_must_not_exist (routers/doctors.py, routers/appointments.py) absent.
- No UPDATE/DELETE on patient_profile_versions in backend/src; lint-imports: 2 contracts kept, 0 broken.
- Router order: /me/profile routes before /{patient_id}/profile; admin router guarded by require_roles(ADMIN) at router level.
- Only user_id/version_number logged in profile_service and doctor_service.
- localStorage appears only in a comment in api/session.ts; fetch( only in api/client.ts; no hard-coded backend URL in frontend/src (only the Vite proxy target in vite.config.ts).

## API checks
- D-API-0 PASS: :8000 and :5173 /api/config -> {UTC, 14, 60}; :5173/health ok.
- D-API-1a PASS; 1b PASS (no token/malformed, GET+PUT -> 401 UNAUTHENTICATED, no version rows added).
- D-API-2a PASS (version +1, earlier rows byte-identical incl. hex, carried forward, changed_by=p1). 2b PASS (both triggers abort with "patient_profile_versions is append-only", data unchanged).
- D-API-3 PASS. D-API-4a PASS (doctor+admin 403 on /me GET/PUT, invalid body still 403, counts unchanged). 4b PASS (404 bodies byte-identical for other patient, missing id, doctor id; own 200, doctor 403, admin 200).
- D-API-5a PASS (1 selected, passed). 5b PASS: profile_updated lines carry user_id; 0 occurrences of unique names, phones, "Orig Name", initial_password in server log.
- D-API-6a PASS (single-field updates, ages 1/130, all 16 invalid bodies -> 422 with errors[].field (empty body -> field "body"), no version rows, extra role ignored). 6b PASS (4 passed).
- D-API-6c N/A (optional): PUT /api/admin/patients/{id}/profile returns 404, not mounted; does not fail group D.
- D-API-7a PASS (201, doctor_id==user_id, DOCTOR/active/argon2, fee_minor 50000, 1 template, 12 AVAILABLE Monday slots, 6 per Monday 09:00-11:30, none past, no password fields). 7b PASS (500.50, 0.00, languages [en,hi], default full_name, two templates same weekday -> 16 slots).
- D-API-8a PASS (401/401/403/403, invalid body order preserved, counts unchanged). 9a PASS (all 7 cases, field paths correct, no rows, email reusable after). 10a PASS (5 fee cases, no echo). 11 PASS (409 for same, upper, mixed case, existing patient email; counts unchanged).
- D-API-12a PASS (login role DOCTOR, user_id==doctor_id; wrong password 401 INVALID_CREDENTIALS). 12b PASS. 12c PASS (1 passed). 13a PASS (1 passed). 13b PASS (235 passed, 1 skipped).

## Playwright checks (Chromium, 1280x800 and 375x812)
- D-PW-1 PASS (token only in sessionStorage key telemed.session; localStorage and cookies clean; survives reload; new context lands on /login).
- D-PW-2 PASS (/doctors, /queue, /admin/users, each renders shell). 3a PASS. 3b PASS (4 wrong-role cases show Not allowed, URL unchanged). 3c PASS (unknown route; mocked 404 on /api/doctors/999 -> not-found page).
- D-PW-4a PASS (mocked 401 clears session -> /login; login INVALID_CREDENTIALS stays on /login). 4b PASS (login 503 and protected 503 -> "try again", no technical detail, session kept).
- D-PW-5a PASS (inline email-field duplicate message for same and different-case email, stays /register). 5b PASS (wrong password, unknown email, deactivated user -> identical message). 5c PASS (no horizontal scroll at 375 and 1280 on /login and /register, initial and error states; submit visible and enabled; screenshots saved in the scratchpad evald folder).
- D-PW-6a PASS (login errors in role=alert/aria-live regions present in DOM beforehand; register 409 in #reg-email-error role=alert). 6b PASS (loading, empty, 500 and 503 error states visible via page.route on /api/doctors).
- D-PW-7 PASS: vitest 4 files / 31 tests passed; tsc --noEmit exit 0.

## Notes (non-failing)
- Browser console "Failed to load resource" entries (401/404/409/500/503) occurred only for intentionally mocked or expected non-2xx responses (and placeholder routes /api/doctors etc. not yet implemented); no uncaught page errors.
- Evaluator harness mistakes (admin timestamp format) were test setup, not application defects.
- Cleanup: servers stopped, backend/eval-d.db and eval-d-server.log removed. Untracked, git-ignored backend/dev.db-shm/-wal (created 04:34, before this run's server) left untouched.
