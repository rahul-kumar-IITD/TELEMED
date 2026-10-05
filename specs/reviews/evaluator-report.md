# Evaluator Report - Group B (E1-S3, E2-S1, E3-S1), mode local

Verdict: PASS (all checks). Evidence: live server on 127.0.0.1:8000, raw sqlite3 inspection, pytest.

- Architecture: all 8 files exist; all 5 content rules satisfied.
- B-API-1..7d, 2b, 6a/6b/6c: PASS (live HTTP + sqlite3).
- B-API-8 (45 passed), 10-14, 15-19, 17b: PASS (pytest).
- Notes: contract says users.is_active, actual column is users.active (used that). Patient FK is patient_profile_versions.patient_id and version_number. No doctors seeded in live DB so the live slot duplicate query returned 0 rows (vacuous); duplicate coverage comes from pytest. api/deps.py binds stubs through container (container.py), providers overridable.
- Cleanup: server stopped, eval-b.db and eval-b-server.log deleted.
