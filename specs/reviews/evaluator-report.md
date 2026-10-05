# Evaluator Report - Sprint Group A (E1-S1, E1-S2) - lean mode

Overall verdict: PASS (all checks pass; no failures, so no eval-failures-001.json written)

Server: uvicorn started locally on 127.0.0.1:8000, health-checked, stopped afterwards (port verified closed).

| Check | Verdict | Evidence |
|---|---|---|
| A-API-1 | PASS | GET /health 200, body {"status":"ok"}, ~0.2s |
| A-API-1b | PASS | "Uvicorn running" logged 18:30:21.81, first 200 served 18:30:22.20 (<1s). Poll granularity 1s, so measured via server log timestamps |
| A-API-2 | PASS | UUID echoed |
| A-API-2b | PASS | abc.DEF_123-x echoed |
| A-API-3 | PASS | invalid value replaced with fresh UUID |
| A-API-3b | PASS | 65-char value replaced with UUID |
| A-API-4 | PASS | generated UUID when header absent |
| A-API-5 | PASS | 404 has X-Request-ID |
| A-API-5b | PASS | 405 has X-Request-ID |
| A-API-5c | PASS | every stdout line parsed as JSON; correlation_id=log-check-1 present; no email/name/note text in log |
| A-API-6 | PASS | 21 passed, 1 skipped (test_request_id.py:39 "client cannot encode this header", non-ASCII header case; minor, not in contract) |
| A-API-7 | PASS | 4 passed |
| A-API-8 | PASS | 5 passed |
| A-API-9a | PASS | 3 passed |
| A-API-9b | PASS | 9 passed |
| A-API-9c | PASS | 2 passed |
| A-API-9d | PASS | 9 passed |
| A-API-9e | PASS | 10 passed |
| A-API-10 | PASS | alembic upgrade head on fresh DB rc=0; all 9 required tables present |
| A-API-10b | PASS | raw sqlite3: 6/6 UPDATE/DELETE rejected ("... is append-only"), rows unchanged |
| A-API-11 | PASS | PROVIDER_TIMEZONE=Not/AZone: exit 1, error names PROVIDER_TIMEZONE (raw pydantic traceback, but meets contract) |

Architecture checks:
- files_must_exist: all 12 files present. PASS
- Content rule E1-S1 AC3 (no float in money paths): grep for `float` in types/money.py, repository/mappers.py, repository/models.py found nothing. PASS
- Content rule E1-S1 AC6: sha256 of 0001_initial_schema.py matches versions.lock.json. PASS

Notes: no application code modified. Playwright/design skipped (lean mode).
