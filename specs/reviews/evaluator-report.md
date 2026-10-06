# Evaluator Report - Sprint Group H (lean, local mode)

Stories: E3-S4, E3-S5, E5-S5. Features F065-F076, F116-F120. Design checks: none (lean).

## Overall verdict: PASS

All architecture, pytest, API and Playwright checks passed. No eval-failures JSON was written because nothing failed. One minor non-AC observation is listed at the end.

Setup: backend on :8000 (fresh eval-h.db, PROVIDER_TIMEZONE=Asia/Kolkata), Vite on :5173. Admin was inserted with sqlite3 using an argon2 hash. Timestamps must use the DB format `YYYY-MM-DD HH:MM:SS.ffffff`. Doctors A and B were onboarded via the API, patients P1 and P2 were registered, and appointments were booked through the API. Time-dependent states were arranged with sqlite3 UPDATEs of slots.start_time and appointments.status. Servers were stopped and eval-h.db and the eval-h logs were deleted. Nothing is left in git status.

## Pytest-backed checks: PASS (120 passed, 0 skipped)
Command: `pytest test_reschedule.py test_lifecycle.py test_queue.py concurrency/test_reschedule_race.py unit/test_state_machine.py -v -rs`.
- test_sixty_minute_boundary has 3 parametrized cases (200 at exactly 60:00, 409 below). Not skipped, passing. (H-API-4 boundary)
- test_failure_after_claim_rolls_everything_back passes. test_ten_concurrent_reschedules_one_winner passes. (H-API-7)
- test_lifecycle.py, test_queue.py and the test_state_machine.py full matrix pass. (H-API-9, H-API-16)

## Architecture checks: PASS
- All 16 files_must_exist files are present.
- Routers contain no SQL (grep for select/execute/text found nothing).
- The reschedule route uses `require_roles(Role.PATIENT)`. The status route uses the doctor-only guard.
- `/me/queue` is registered before `/{doctor_id}` (line 59 against line 86). Live checks confirmed doctor-only access.
- The claim is a conditional UPDATE with a `rowcount == 1` check. RescheduleService takes an injected Clock.
- Transition logic lives in types/state_machine.py. A grep of routers and frontend found no CHECKED_IN transition logic.
- routes.tsx maps admin/users to UserListPage and admin/doctors/new to OnboardDoctorPage, both behind RequireRole(ADMIN).
- Frontend grep for parseFloat, toFixed, alert( and console.log found nothing.

## API checks (live): all PASS
| ID | Result | Evidence |
|---|---|---|
| H-API-0 | PASS | health 200. Admin login worked. Doctors A and B onboarded (201). P1 and P2 registered (201). Bookings 201. |
| H-API-1 | PASS | 200 with same appointment_id, slot_id == Y, status BOOKED. Slot Y BOOKED, slot X AVAILABLE. Exactly one appointment row for P1. GET shows the new slot. |
| H-API-2 | PASS | Exactly one new event, type RESCHEDULED, with old_slot_id=X and new_slot_id=Y. |
| H-API-3 | PASS | All six invalid targets (booked by P2, BLOCKED, started, +15d, current slot, doctor B's slot) gave 409 SLOT_UNAVAILABLE. Appointment, slots and event count were unchanged after each. Nonexistent id gave 404. Missing body and non-int body gave 422. |
| H-API-4 | PASS | +59m gave 409 CHANGE_WINDOW_CLOSED with nothing changed. +62m gave 200. The exact boundary is covered by pytest. |
| H-API-5 | PASS | CHECKED_IN, IN_PROGRESS, COMPLETED, CANCELLED and NO_SHOW each gave 409 INVALID_APPOINTMENT_STATE. No change to slots or events. |
| H-API-6 | PASS | No token 401, doctor 403, admin 403, other patient 404. Nothing changed. |
| H-API-7 | PASS | Via pytest (see above). |
| H-API-8 | PASS | BOOKED -> CHECKED_IN -> IN_PROGRESS -> COMPLETED each gave 200 with the new status. One event added per call, each with actor_role DOCTOR. |
| H-API-9 | PASS | 409 INVALID_APPOINTMENT_STATE with status and events unchanged for: BOOKED->IN_PROGRESS, BOOKED->COMPLETED, BOOKED->BOOKED, CHECKED_IN->CANCELLED, COMPLETED->IN_PROGRESS, COMPLETED->BOOKED, CANCELLED->CHECKED_IN, NO_SHOW->COMPLETED. Unknown status gave 422. The state-machine matrix test passes. |
| H-API-10 | PASS | Future NO_SHOW gave 409. After the start moved to the past, NO_SHOW from BOOKED gave 200 and from CHECKED_IN gave 200. The slot stayed BOOKED both times. |
| H-API-11 | PASS | With Asia/Kolkata, date=D returned only the 23:30 IST item plus the same-day CANCELLED item, ordered ascending, with total=2, timezone and date. date=D+1 returned only the 00:30 item. Doctor B's appointment was absent. Every item had allowed_actions, and CANCELLED items were included. Default date gave 200 with today in IST. A bad date gave 422, patient 403, admin 403, no token 401. Doctor B's queue held only its own item. |
| H-API-12 | PASS | Doctor BOOKED before start: CHECKED_IN and CANCEL, no NO_SHOW. After start: NO_SHOW appears. CHECKED_IN: IN_PROGRESS and NO_SHOW. IN_PROGRESS: COMPLETED. COMPLETED and NO_SHOW: []. Patient BOOKED: [CANCEL, RESCHEDULE]. Admin: []. |
| H-API-13 | PASS | Doctor B 404, patient 403, admin 403, no token 401. Status and events unchanged. |
| H-API-14 | PASS | Doctor CANCELLED on a BOOKED appointment gave 200. Slot BLOCKED. Exactly 2 events in total, the new one with actor_role DOCTOR. |
| H-API-15 | PASS | Reschedule after start gave 409 CHANGE_WINDOW_CLOSED with nothing changed. |
| H-API-16 | PASS | Via pytest (see above). |

## Playwright H-PW-1280 (1280x800): PASS
Reached onboarding through the in-app nav link (/admin/doctors/new) and the user list through the nav link (/admin/users). Screenshots h-onboard-1280.png, h-onboard-422-1280.png, h-users-1280.png and h-edit-profile-1280.png were produced in the scratchpad. They are not committed.
- F116 PASS. The form has specialty, languages, fee and a template-row editor. Two rows were added. After submit the success view showed name, email and specialty. The fee displayed "750.50" unchanged. GET /api/doctors listed the new doctor with Neurology and 750.50 (my first attempt in the script omitted the auth header, which was a script error and not an app failure; it was re-verified with a token).
- F117 PASS. Row 1 09:00-10:00 with 25 minutes showed the server message "slot length must divide the window" under row 1's slot-length field only. Email, specialty, languages, fee and all rows were preserved. End-before-start also showed a row-1 error.
- F118 PASS. The Doctor filter showed only DOCTOR rows and the Patient filter only PATIENT rows. The admin's own Deactivate was disabled. Deactivating p2 gave an INACTIVE status with a Reactivate button, and GET /api/admin/users agreed. Reactivating restored ACTIVE.
- F119 PASS. Deactivating doctor A (who has BOOKED appointments) showed the "active appointments" message inline. The row stayed ACTIVE with Deactivate, and the API agreed. No alert dialogs fired.
- F120 PASS. The form was prefilled. Age 0 showed a field error (#pf-age-error) with no success message. Saving valid values showed "Profile saved.". The backend profile became version 2 with the new values. GET /api/admin/users shows the new name. Reopening the dialog and reloading the page both show the new values.
- No horizontal overflow on onboarding or the user list at 1280px.

## Observations (non-blocking, not tied to an AC)
- After saving a patient profile, the open user list is not refetched. The row shows the old name until the page is reloaded or the filter changes. Data and the profile dialog are correct. E5-S5 AC5 requires only that the form saves and shows a success message, so this is recorded as a minor UX note. The contract step says "list/profile reflects the change", and the profile side is satisfied.
- Stub/mode limitation: none. The run used local mode with real endpoints.
