# Evaluator re-run: Groups J (E5-S3, E5-S4, E6-S2) and K (E6-S3)

Source and features files were not edited. Playwright started the backend and frontend itself (webServer).

## Gate results (all executed fresh)
- backend `pytest --cov`: 442 passed, 1 skipped (test_request_id.py:39, "client cannot encode this header", not an architecture or traceability test). Coverage 100%, fail_under 80 met.
- backend `ruff check .`: pass. `mypy --strict src/`: Success, 68 files. `lint-imports`: 3 kept, 0 broken (layers, API, Repository must not import Service).
- `scripts/check_traceability.py`: AC-01..10 and NFR-01..08 each have 1 or more tests, exit 0.
  - Scratch copy with NFR-03 tags renamed: "MISSING tagged tests for: NFR-03".
  - Scratch repository module importing a service module: lint-imports reports the broken Repository -> Service contract.
- frontend `npm test`: 12 files, 88 tests passed. `npm run lint` and `npm run typecheck`: clean.
- `.github/workflows/ci.yml` runs pytest --cov, lint-imports, mypy --strict, ruff and the traceability script. pyproject has fail_under 80 and domain_fail_under 95.
- `npx playwright test` (no --update-snapshots), run twice on a fresh DB each time: 13 passed both times (desktop 8, mobile 5). Working tree stayed clean (no snapshot rewrites). 17 baseline PNGs are tracked in git. No test.skip/fixme/only in e2e. Config has desktop 1280 and mobile 375 projects, timezoneId Asia/Kolkata, and a fixed clock fixture. Config specs assert both.

## Not executed
- The bespoke J-PW-S3-1280, J-PW-S4-1280 and J-PW-S4-375 scripts (sqlite-arranged status/window states, route interception, 375px overflow) were NOT run as separate scripts.
- Their behaviours are covered only by vitest (change-window, appointment-card, allowed-actions) and the e2e specs.
- The J-API 409 and window-edge regressions (J-API-1..6, 12, 13) were not re-run by hand. The backend suite passes.
- K mutation spot check and the modified-baseline check were not run.

## Per-feature verdicts
Verdict is on evidence from the runs above. Features whose bespoke Playwright step was not run are marked PASS (partial).

| ID | Verdict | Evidence |
|---|---|---|
| F104 status text and Join visit rule | PASS (partial) | appointment-card unit tests, e2e patient flow showing BOOKED/CANCELLED |
| F105 60-minute window disable | PASS (partial) | change-window unit tests |
| F106 cancel and 409 | PASS (partial) | e2e cancel to CANCELLED, both viewports; booking-409 unit test |
| F107 reschedule | PASS | e2e reschedule, desktop and mobile |
| F108 read-only notes | PASS | e2e "read consultation notes", both viewports |
| F109 profile edit | PASS (partial) | no e2e profile test; typecheck/lint/unit only. Not independently exercised in a browser |
| F110 queue and timezone label | PASS (partial) | e2e doctor queue; route-intercept timezone change not run |
| F111 allowed_actions buttons | PASS | allowed-actions unit tests, e2e doctor flow, NO_SHOW disabled before start |
| F112 status change and 409 refetch | PASS (partial) | e2e Check in/Start/Complete real backend; 409 interception not run |
| F113 slot block/unblock | PASS (partial) | e2e "slot calendar lists open and blocked slots"; block/unblock click not confirmed |
| F114 notes form only on COMPLETED | PASS | e2e doctor flow adds a note after COMPLETED |
| F115 no horizontal overflow at 1280/375 | NOT VERIFIED | scrollWidth check not run; only patient screens ran at 375 in e2e |
| F124 coverage gates | PASS | cov 100%, fail_under 80, domain threshold 95 configured |
| F125 traceability script | PASS | exit 0, negative check names the missing ID |
| F126 import-linter / layers | PASS | 3 contracts kept, negative scratch check broke |
| F127 mypy strict and ruff | PASS | both clean |
| F128 Playwright config (projects, tz, clock) | PASS | config.spec x2 projects, --list |
| F129 patient e2e | PASS | desktop and mobile, 3 tests each |
| F130 doctor e2e | PASS | 2 desktop tests |
| F131 admin e2e | PASS | onboard, deactivate, reactivate |
| F132 vitest behaviours and baselines | PASS (partial) | 88 unit tests; 2 stable e2e runs with 17 tracked baselines; modified-baseline check not run |
| F136 full suite and CI | PASS | pytest green, ci.yml has all gates |

## Key finding: two features.json files
- `C:\Users\Lenovo\OneDrive\Desktop\telemed\Telemed\features.json` (repo root) has F104 and F128 and F136 as passes:true (last_evaluated set).
- `...\Telemed\specs\features.json` has F104..F115, F124..F132 and F136 as passes:false with null failure_reason. This is the stale copy. The earlier flips went to the root file.
- Which file is canonical needs a decision. CLAUDE.md names root `features.json`. Either sync the specs copy or remove the duplicate.
