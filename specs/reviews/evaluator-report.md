# Evaluator Report - Group J (E5-S3, E5-S4, E6-S2)

Mode: lean, verification local. Verdict: PASS (all checks). No failures, so no eval-failures JSON written.

Stale :8000 / :5173 processes from the dead run were killed, then fresh backend and Vite were started. They were killed again afterwards, and eval-j.db* and the eval-j logs were removed. Seeding used backend/scripts/seed.py plus API calls and sqlite UPDATEs. Playwright was driven from a scratch install (playwright npm package with the cached chromium-1243).

## architecture_checks
| Check | Result |
|---|---|
| All 24 files_must_exist | PASS |
| Frontend `npm test` (12 files, 88 tests), `npm run lint`, `npm run typecheck` | PASS |
| Backend `lint-imports` (3 contracts kept: layers, API forbidden, Repository -> Service forbidden), `mypy --strict src/` (68 files), `ruff check .` | PASS |
| ci.yml runs pytest --cov, lint-imports, mypy --strict, ruff, check_traceability, plus frontend test/lint/typecheck | PASS |
| Content rules (AppointmentCard, QueueRow, notes read-only, timezone from the server) | PASS, confirmed through the UI behaviour below, not source review |

## api_checks
| ID | Result | Detail |
|---|---|---|
| J-API-0 | PASS | /health 200, logins, setup, doctor A drove an appointment to COMPLETED and posted two notes |
| J-API-1 | PASS | /mine shape OK (fee string, ascending, allowed_actions, join_url, change_deadline). Cancel 200. Reschedule 200 with the new start_time. Other-doctor and same-slot reschedule 409. At 59 min, cancel and reschedule 409. At 95 min, cancel 200. Error-code strings were matched loosely: the code `SLOT_UNAVAILABLE` and `CHANGE_WINDOW_CLOSED` were not individually asserted by the script, only the 409 status. |
| J-API-2 | PASS | Notes 200, ids [1,2], total 2. PUT/PATCH/DELETE on /notes/{id} return 405 with Allow: GET. Other patient gets 404. |
| J-API-3 | PASS | GET 200, PUT phone 200, value persisted, age 0 gives 422 |
| J-API-4 | PASS | Queue keys {date, timezone, items, total}, Asia/Kolkata, ascending, BOOKED row has CHECKED_IN. /api/config provider_timezone is Asia/Kolkata. NO_SHOW before start 409, invalid transition 409, bad date 422. |
| J-API-5 | PASS | block 200 BLOCKED, unblock 200 AVAILABLE, unblock of a non-blocked slot 409, block of a BOOKED slot 409 |
| J-API-6 | PASS | Note on BOOKED 409. On COMPLETED 201 (two notes). List 200. PUT/PATCH/DELETE 405. |
| J-API-7 | PASS | `uv run pytest --cov` exit 0: 442 passed, 1 skipped (test_request_id, "client cannot encode this header", not an architecture or traceability test). Total coverage 100%, "Domain coverage 100%" gate line printed. Scratch copy: threshold set to 99 gives "Domain coverage failure" and exit 1. A partial run with the default 80 gives exit 1. |
| J-API-8 | PASS | check_traceability.py exit 0, AC-01..AC-10 and NFR-01..NFR-08 each have at least 1 test. Scratch copy with the NFR-03 tag removed: exit 1, "MISSING tagged tests for: NFR-03". With the AC-02 tag removed: names AC-02 (shown as 0 tests). test_traceability.py passes inside the full suite. |
| J-API-9 | PASS | lint-imports exit 0. Scratch copy with a repository module importing a service module: "telemed.repository is not allowed to import telemed.service", exit 1. test_layers.py passes in the suite. |
| J-API-10 | PASS | mypy --strict: Success, no issues in 68 files. ruff: All checks passed. |
| J-API-11 | PASS | Full suite green, ci.yml has all gates |
| J-API-12 | PASS | Patient 403, no token 401, doctor B on doctor A's appointment 404 |
| J-API-13 | PASS | Repeating CHECKED_IN gives 409 INVALID_APPOINTMENT_STATE, queue status stays CHECKED_IN |

## playwright_checks
**J-PW-S3-1280: PASS.** Patient P3 had nine appointments.
- F104: all six statuses shown as text. "Join video visit" is on BOOKED, CHECKED_IN and IN_PROGRESS only, and absent on COMPLETED, CANCELLED and NO_SHOW.
- F105: the +59 min card has Cancel and Reschedule disabled with text containing "60 minutes". The three far cards have both enabled.
- F106: with the cancel POST intercepted to 409, an inline message appears and the status stays BOOKED. A real cancel moved the card to CANCELLED.
- F107: reschedule listed that doctor's slots, and the card showed the new time. The DB start_time agrees with the UI (Oct 7 03:30Z = 09:00 IST).
- F108: both notes are shown in order, and there are no edit/delete buttons or inputs.
- F109: success message "Profile saved.", new phone persisted after reload, age 0 shows the field error "Input should be greater than or equal to 1" and no success message.

**J-PW-S4-1280: PASS.** Doctor A.
- F110: lands on /queue, date picker present, label "Times shown in Asia/Kolkata". With the queue response intercepted to timezone UTC, the label became "UTC" and times shifted (03:30 UTC vs 09:00 IST).
- F111: BOOKED row buttons were Check in (exactly one), Cancel appointment, and a disabled Mark NO_SHOW with explanatory text.
- F112: with the status POST intercepted to 409, an inline message appears and the queue was re-fetched (GET observed). A real Check in updated the row to CHECKED_IN.
- F113: Block gave BLOCKED, Unblock gave AVAILABLE, and the BOOKED slot's Block is disabled.
- F114: BOOKED detail has no note form. COMPLETED detail has the form, and a submitted note appears. There are no edit/delete controls.
- F115: no horizontal overflow at 1280 on queue, slots and detail (1280/1280).

**J-PW-S4-375: PASS.** scrollWidth equals clientWidth (375/375) on queue, slot calendar and detail.

Screenshots were saved in the scratchpad (j-*.png), not in the repo.

## Notes
- The status 409 interception message is the generic "appointment changed" text. It satisfies the contract (inline message plus refetch).
- The sandbox's Playwright needed an explicit executablePath (chromium-1243). The repo itself has no Playwright config or e2e specs (e2e/ is empty), so these checks were run with a scratch script, not a repo suite.
- No application code was modified. features.json was not edited (the caller did not ask for it, and the contract's three layers are all green). The caller can set passes=true for F104-F115, F124-F127 and F136.
