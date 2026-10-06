# Evaluator report: group K (E6-S3), local mode

Verdict: PASS (one caveat: baselines are present on disk but not yet git-tracked because nothing is committed; they are untracked, not ignored).

- K-UNIT-1: PASS. `npm test` 12 files / 88 tests green. Six named files 38/38. Behaviours: change-window (60 min text), allowed-actions, booking-409 (inline + refetch), guards (401 clears session -> /login; unknown route -> not-found), session (sessionStorage not localStorage). Mutation in scratch copy (sessionStorage->localStorage) made session.test fail.
- K-PW-CONFIG: PASS. `--list` shows 13 tests, desktop (1280) and mobile (375). timezoneId Asia/Kolkata in shared `use`, clock via fixtures/index.ts, config.spec.ts passes in both projects; no env-dependent settings.
- K-PW-PATIENT-1280/375, K-PW-DOCTOR-1280, K-PW-ADMIN-1280: PASS (all within full-suite runs; admin re-run alone also passed).
- K-PW-BASELINES: PASS with caveat. 17 win32 baselines (login, doctor-search, slot-picker, my-appointments, booking-confirmed, notes x desktop+mobile; queue, slot-calendar, appointment-notes, user-list, onboard-form desktop). Two consecutive `npx playwright test` runs (fresh servers, no --update-snapshots): 13 passed both. Tampering with a baseline made admin test fail (0.72 pixel ratio); restored (sha verified) and passes. `git ls-files e2e/__screenshots__` is empty because e2e/ is untracked (git check-ignore: not ignored); must be committed.
- Architecture: all files_must_exist present; no skip/fixme/only in e2e (grep); forbidOnly true; root package.json has @playwright/test devDependency and `e2e: npx playwright test`.
- No application code modified.
