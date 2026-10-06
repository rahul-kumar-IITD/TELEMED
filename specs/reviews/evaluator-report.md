# Evaluator Report - Sprint Group G (lean, local mode)

Stories: E3-S3, E4-S2, E5-S2, E6-S1. Features F060-F064, F083-F088, F099-F103, F121-F123.
Design checks skipped (lean mode).

## Overall verdict: PASS

All architecture, API and Playwright checks passed. No structured failure file was written because there were no failures.

Setup: backend on :8000 with a fresh eval-g.db, Vite on :5173, admin inserted via sqlite3 with an argon2 hash, doctors docA..docE, patients p1..p3. Cancel-window cases were arranged by updating slots.start_time. Servers were killed and eval-g*.db / eval-g*.log artifacts were deleted afterwards.

## Architecture checks: PASS
- All 18 files_must_exist files are present.
- Cancel route guarded by require_roles(PATIENT, DOCTOR). The admin 403 and non-owner 404 were confirmed live.
- CancellationService takes an injected Clock. There is no SQL in the routers (grep for select/execute/text found nothing).
- The auth dependency rejects inactive users (docstring says "401 for ... inactive user"; a live check showed the old token returning 401).
- Frontend grep found no parseFloat, toFixed, alert( or console.log. Slot times use Intl.DateTimeFormat with timeZoneName "short".
- routes.tsx maps /doctors and /doctors/:doctor_id to the new pages. The /book/:slot_id route was added. The 409 path refetches slots and shows an inline message.
- seed_service checks email existence before creating users. Slots come from DoctorService.onboard (the slot generator).
- pytest: test_cancel.py, test_seed.py and test_admin_users.py gave 29 passed. This includes the refund spy and the exact 60:00 boundary tests.

## API checks
| ID | Result | Evidence |
|---|---|---|
| G-API-0 | PASS | health 200, admin login, 5 doctors onboarded (201), 3 patients registered, bookings 201 |
| G-API-1 | PASS | start = now + 60:30 (30s slack). 200 CANCELLED, slot AVAILABLE, events [BOOKED/PATIENT, CANCELLED/PATIENT] with no duplicate CANCELLED. A re-cancel returned 409 INVALID_APPOINTMENT_STATE. Refund count == 1 and the exact boundary are covered by the pytest spy tests, which passed. |
| G-API-2 | PASS | now + 59m gives 409 CHANGE_WINDOW_CLOSED. Appointment BOOKED, slot BOOKED, still 1 event. |
| G-API-14 | PASS | past start gives 409 CHANGE_WINDOW_CLOSED. Status unchanged, no new event. |
| G-API-3 | PASS | other patient gets 404 NOT_FOUND. Appointment BOOKED, 1 event. |
| G-API-4 | PASS | doctor A at +10m gives 200 CANCELLED, slot BLOCKED, events [BOOKED/PATIENT, CANCELLED/DOCTOR]. Doctor B 404, admin 403. |
| G-API-5 | PASS | CHECKED_IN, IN_PROGRESS, COMPLETED, CANCELLED, NO_SHOW each gave 409 INVALID_APPOINTMENT_STATE as patient and as doctor. Event counts unchanged. |
| G-API-6 | PASS | no token 401. Unknown id 404 as patient and as doctor. |
| G-API-7 | PASS | items carry user_id, role, active, and total is an int. ?role=DOCTOR returned only the 5 doctors. ?role=BAD 422. Patient token 403. Deactivated users stay listed with active=false. |
| G-API-8 | PASS with caveat | deactivate gives 200 active=false. Login 401. Old token on /api/auth/me 401. BOOKED appointment rows remain (3). Caveat: no doctor check-in endpoint exists in the app, so the "doctor A can still check-in -> 200" sub-step could not be run. Only row survival was verified. |
| G-API-9 | PASS | BOOKED, CHECKED_IN and IN_PROGRESS doctors each gave 409 ACTIVE_APPOINTMENTS_EXIST and docA stayed active=1. The terminal-only doctor gave 200 and was absent from GET /api/doctors. |
| G-API-10 | PASS | self-deactivate gives 409 CANNOT_DEACTIVATE_SELF. sqlite shows active=1. |
| G-API-11 | PASS | reactivate gives 200 active=true. P1 login 200. The doctor reappears in GET /api/doctors. Unknown id 404. |
| G-API-12 | PASS | 200 PatientProfile with version_number 2. Version rows went 1 to 2, earlier row unchanged, changed_by_user_id = admin. Non-patient id 404, patient token 403, age=-5 422. |
| G-API-13 | PASS | Run 1 exit 0: 1 admin, 3 doctors with 3 distinct specialties, 5 patients, 252 slots. Run 2 exit 0, "0 users, 0 slots created", counts identical. All emails @example.test (0 violations). Slots span 2026-10-06 09:00 to 2026-10-19 11:30, within 14 days of today (2026-10-06). Admin password hash verifies against the seed password. test_seed.py passed. A live login against a server on the seed DB was not run. |

## Playwright checks (Chromium, tz Asia/Kolkata)
| ID | Result | Evidence |
|---|---|---|
| G-PW-1280 | PASS | F099: filters and sort present, fee "500.00" on cards. Specialty filter narrows to docF, language filter to docG, sort by fee and by name reorder correctly, date range operable, nonsense filter shows the empty state. F100: 14 day groups, times such as "14:30 GMT+5:30". F101: summary and confirmation show doctor, local time and fee "300.00". F102: after another patient booked the slot via API, Confirm gave the inline "no longer available" message and the slot was gone. F103: no horizontal overflow on search, detail, confirm or confirmation. No page errors or dialogs. |
| G-PW-375 | PASS | Same flow passes at 375px. scrollWidth <= clientWidth on all pages. Zero visible interactive controls below 44x44 on search, detail, pre-confirm and confirmation. No page errors or dialogs. |

Notes:
- My first F101 assertion expected the literal "IST". Chromium's Intl short name for Asia/Kolkata is "GMT+5:30", so my assertion failed in the script. The UI output is correct (local time with a zone abbreviation) and I counted F101 as PASS. This was an evaluator-side expectation error, not an app defect.
- A first API run crashed in my own script because I used a deactivated patient's token to list slots. I reset the DB and reran cleanly. All results above are from the clean run.
- Screenshots are in the session scratchpad: g-search/detail/confirm-{1280,375}.png.
