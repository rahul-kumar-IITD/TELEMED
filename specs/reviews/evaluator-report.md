# Evaluator Report - Group F (E3-S2, F054-F059)

Verdict: PASS (local mode, live backend on :8000, throwaway eval-f.db; server killed, db and log deleted)

## Architecture checks: PASS
- All 6 required files exist.
- slots_repo.claim: single conditional UPDATE (status AVAILABLE, now < start_time < now+14d, doctor active subquery), rowcount == 1.
- BookingService.book: claim, appointment insert and BOOKED event insert in one UnitOfWork.transaction (BEGIN IMMEDIATE, rollback on exception). Charge after commit.
- Rowcount 0 gives SlotUnavailableException (409) or NotFound (404); busy_timeout is applied by pragmas.
- Router guarded by require_roles(PATIENT); payment from get_payment_service in deps; fee via format_fee; no SQL in the router.

## API checks
| Check | Result | Evidence |
|---|---|---|
| F-API-0 | PASS | health 200, doctors A (500.00) and B (300.00) onboarded with 644 slots each, 21 patients registered |
| F-API-1a | PASS | 201 with all required fields, fee "500.00", join_url set |
| F-API-1b | PASS | slot BOOKED, 1 appointment, 1 BOOKED event, slot gone from listing |
| F-API-1c | PASS | 409 SLOT_UNAVAILABLE, counts unchanged |
| F-API-1d | PASS | 404 NOT_FOUND |
| F-API-1e | PASS | 422 VALIDATION_ERROR with field slot_id (missing and "abc") |
| F-API-2 | PASS | 20 threads released by a barrier, twice: each burst gave 1x201, 19x409 SLOT_UNAVAILABLE, 0 5xx; 1 appointment, 1 event, slot BOOKED |
| F-API-3a | PASS | 409, counts unchanged |
| F-API-3b | PASS | blocked slot 409, still BLOCKED |
| F-API-3c | PASS | past slot 409, still AVAILABLE |
| F-API-3d | PASS | now+15d 409, still AVAILABLE; now+13d23h gives 201 |
| F-API-4 | PASS | deactivated doctor B slot 409, still AVAILABLE, no appointment |
| F-API-5a | PASS | doctor 403, admin 403 |
| F-API-5b | PASS | no token 401, garbage token 401 |
| F-API-5c | PASS | doctor with bad slot or invalid body 403; no token 401 |
| F-API-6a | PASS | fee is the string "500.00", equals profile fee, fee_minor 50000 stored |
| F-API-6b | PASS | pytest test_payment_charged_once_on_success_and_never_on_conflict passed: 1 charge on success, still 1 after conflict, calls == [] on failed bookings |

Notes: slot timestamps set via sqlite3 use the format "%Y-%m-%d %H:%M:%S.%f" (UtcDateTime). A first run hit a 500 because of a malformed admin seed row I inserted in the wrong format. That was an evaluator setup error, not an app defect. The database was reset and the run repeated cleanly.

No failures, so no eval-failures-NNN.json written. Application code was not modified.
