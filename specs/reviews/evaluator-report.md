# Evaluator Report - Group C (E1-S4, F017-F021, plus C-UR-1), mode local

Verdict: PASS (all checks). Evidence: live server on 127.0.0.1:8000 per start_command, raw sqlite3 edits, forged PyJWT tokens, pytest, live start-refusal runs.

- Architecture: the 3 required files exist. Content rules verified: get_current_user re-reads the user via AuthService each request and returns 401 for any bad token (generic body); require_roles gives 403; access.py holds ownership; /api/auth/me exists in auth.py; deps.py has no sqlite or repository imports. The old dev secret appears only as _REFUSED_JWT_SECRET (denylist) in settings.py. It is absent from .env.example, where JWT_SECRET= is blank. jwt_secret has no fixed default, and the dev fallback uses secrets.token_urlsafe(48).
- C-API-1a/1b/1c/1d: PASS live. Missing header, 'Bearer garbage', 'Bearer a.b.c', 'Basic xxx', empty bearer (via curl), expired, wrong-secret and alg=none all return 401 UNAUTHENTICATED with an identical generic body. Valid token returns 200 with the User shape and no password fields.
- C-API-1e (19 passed), 2a (2), 3a (4), 3b (5), 4c (3), 5a (5), C-API-6 (68 passed incl. group B regression): PASS.
- C-API-2b: PASS live. A forged ADMIN-claim token returns role PATIENT. After UPDATE role='DOCTOR' the same token returns DOCTOR.
- C-API-4a/4b: PASS live. active=0 gives 401, active=1 gives 200 with the same token.
- C-API-5b: PASS live. The admin row was inserted via sqlite3, login returned 200, and /me returned role ADMIN.
- C-API-3c: N/A. Only /health, /api/auth/register, /login and /me exist as real routes (routers: auth, system), so there is no role-restricted real route. Covered by C-API-3a/3b pytest.
- C-UR-1-a: PASS (10 selected; the whole test_settings.py has 15 passed).
- C-UR-1-b: PASS live. APP_ENV=prod and staging with no JWT_SECRET exit 1 with "JWT_SECRET is required unless APP_ENV=dev". The old dev value under prod exits 1 and the output does not contain the value. A short secret under dev exits 1. In dev with no secret, two processes started and a token minted by process 1 returned 401 on process 2.
- Notes (non-blocking): users column is `active` (not is_active) and has no full_name column. full_name in /me is null for the admin and DOCTOR rows, which have no profile. The API-05 shape expects a string, and this affects only users without a patient profile. The startup refusal surfaces as a raw pydantic traceback, which is clear and names JWT_SECRET. C-UR-1 has no features.json entry (feature null), so features.json was not modified.
- Cleanup: servers stopped (ports 8000/8021/8022 closed), backend/eval-c.db, eval-c2.db and eval-c-server.log deleted.
