# TeleMed Deployment

Scope reality check: BRD sections 5 and 8 make this an assessed prototype run locally with `npm start` and **no Docker**. Section 1 (dev) is therefore the only environment that is implemented and graded. Sections 2-6 are a concrete, minimal design for staging/prod so the system can be promoted later; nothing here is required for the rubric and none of it adds runtime dependencies. Anything marked (proposed) is unbuilt.

## 1. Environments

| | dev (implemented) | staging (proposed) | prod (proposed) |
|---|---|---|---|
| Host | developer laptop | 1 small VM | 1 VM (same shape, larger disk) |
| Process | `npm start`: uvicorn :8000 (reload) + vite :5173 | systemd `telemed-api` (uvicorn, 1 worker) behind Caddy | same |
| DB | `backend/telemed.db` (SQLite, WAL) | `/var/lib/telemed/telemed.db` on a persistent volume | same + nightly offsite backup |
| Frontend | vite dev server, proxies `/api` and `/health` | `vite build` output served by Caddy | same |
| TLS | none | Caddy automatic HTTPS | same |
| Data | `scripts/seed.py` synthetic (`@example.test`) | seed allowed (synthetic only) | no seed; first admin created by one-off command |
| `PROVIDER_TIMEZONE` | default `UTC` (e2e fixes `Asia/Kolkata`) | provider zone | provider zone |
| Config source | `.env` copied from `.env.example` by `init.sh` | env file `/etc/telemed/telemed.env` (0600) | secrets manager injected at start |

Bootstrap (dev): `bash init.sh` = `uv sync`, `npm ci`, copy `.env.example`, `alembic upgrade head`, `npm start`, poll `:8000/health` and `:5173`. `/deploy` runs this.

## 2. Configuration and secrets

Settings (all in `.env.example`, validated at startup; unknown `PROVIDER_TIMEZONE` aborts with an error naming it):

| Variable | Default | Secret | Purpose |
|---|---|---|---|
| `DATABASE_PATH` | `./telemed.db` | no | SQLite file |
| `BUSY_TIMEOUT_MS` | `10000` (min 5000) | no | lock wait |
| `JWT_SECRET` | none (no fixed default; unset in `APP_ENV=dev` generates a random per-process secret, unset or the old published dev value is refused when `APP_ENV != dev`) | **yes** | HS256 key, >= 32 bytes |
| `JWT_LIFETIME_MINUTES` | `30` | no | access token lifetime |
| `PROVIDER_TIMEZONE` | `UTC` | no | template wall-clock zone, queue day |
| `SLOT_WINDOW_DAYS` | `14` | no | booking window |
| `CHANGE_WINDOW_MINUTES` | `60` | no | cancel/reschedule cutoff |
| `VIDEO_BASE_URL` | `https://video.example.test/visit` | no | stub join URL base |
| `APP_ENV` | `dev` | no | `dev`/`staging`/`prod` |
| `LOG_LEVEL` | `INFO` | no | log verbosity |
| `VITE_API_PROXY_TARGET` (frontend, dev only) | `http://localhost:8000` | no | Vite proxy |

Secrets handling: only `JWT_SECRET` (and, if added later, initial admin password) is secret. Never committed (`.gitignore` has `.env`); CI uses repository secrets; prod reads from the platform secret store into the environment of the systemd unit (`LoadCredential=` or env file 0600 owned by the service user). Rotating `JWT_SECRET` invalidates all sessions, which is acceptable (30-minute tokens, no refresh). The initial admin is created by a one-off `python backend/scripts/create_admin.py` that prompts for the password (no secret on the command line). Logs never contain secrets or PHI.

## 3. CI/CD (proposed; GitHub Actions)

`.github/workflows/ci.yml` (on every PR and push to `main`), jobs in parallel then gate:
1. backend: `uv sync --frozen`, `uv run ruff check .`, `uv run mypy --strict src/`, `uv run lint-imports`, `uv run pytest --cov` (fail under 80 overall, 95 domain), `python scripts/check_traceability.py`, migration-lock test.
2. frontend: `npm ci`, `npm run lint`, `npm run typecheck`, `npm test`.
3. e2e (needs 1 and 2): start stack with fixed clock/timezone and a seeded temp DB, `npx playwright test` (desktop + mobile projects, screenshot baselines).
4. security: `pip-audit`, `npm audit --omit=dev` (warn on moderate, fail on high), secret scan.

`.github/workflows/deploy.yml`:
- push to `main` and CI green -> auto-deploy to **staging**.
- tag `vX.Y.Z` -> manual approval -> **prod**.
- Artifact: a tarball `telemed-<sha>.tar.gz` containing the backend wheel (built with `uv build`), `alembic/`, and `frontend/dist`. Deploy steps on the host (via SSH or SSM): (1) snapshot DB (`sqlite3 db ".backup ..."`), (2) unpack to `/opt/telemed/releases/<sha>`, (3) `alembic upgrade head` using the new release, (4) repoint symlink `/opt/telemed/current`, (5) `systemctl restart telemed-api`, (6) poll `/health` (must return 200 within 1 s of listening; up to 30 s total wait), (7) smoke test: login as seeded/synthetic user in staging, one search call. Any failing step triggers rollback (section 5).

## 4. Infrastructure as code (proposed)
- `infra/terraform/`: one VM, one data volume (snapshots enabled), firewall (80/443 only), DNS record. Single `staging` and `prod` workspaces with different sizes; state in a remote backend.
- Slot generation has **no scheduled job**: no systemd timer, cron entry or CI schedule calls `generate_slots`. It runs only at doctor onboarding, in the seed script and at application startup (per the BRD), so a restart or a deploy tops the 14-day window up.
- `infra/systemd/telemed-api.service`: `ExecStart=uvicorn telemed.api.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1`, `Restart=on-failure`, `User=telemed`, hardening (`NoNewPrivileges`, `ProtectSystem=strict`, `ReadWritePaths=/var/lib/telemed`), `EnvironmentFile=/etc/telemed/telemed.env`.
- `infra/caddy/Caddyfile`: TLS, `root /opt/telemed/current/frontend/dist` with SPA fallback to `index.html`, `reverse_proxy /api/* /health 127.0.0.1:8000`, rate limit at proxy per the production recommendation in `api-contracts.md` 0.5 (10 login attempts/min/IP, 120 req/min/user), security headers.
- No Docker/Kubernetes: SQLite single-writer model does not benefit from horizontal scaling; scaling path would be PostgreSQL (BRD option B) and is out of scope.

## 5. Rollback and recovery
- Migrations are append-only and forward-only (NFR-05); we do not write downgrade scripts. Schema changes follow expand/contract: a release only adds nullable columns/new tables/indexes; destructive cleanup ships in a later release once no running code needs the old shape. Consequence: the previous release's code runs correctly against the new schema, so **code rollback = repoint `current` symlink to the previous release and restart**, with no DB change.
- If data was damaged (bad migration, bug): stop service, restore the pre-deploy snapshot taken in step 3.1 (`cp` of the `.backup` file, never of a live WAL pair), restart the previous release. Data written after the snapshot is lost; acceptable at prototype scale, and the append-only event log makes reconciliation possible.
- Backups (proposed): pre-deploy snapshot + nightly `sqlite3 .backup` to offsite storage, 14-day retention; restore drill each release in staging.
- Health gating: failed health/smoke check auto-rolls back; deploy job keeps the last 3 releases on disk.
- Slot catch-up on startup means a restart after downtime self-heals the 14-day window (startup is the only periodic-style trigger; there is deliberately no timer).

## 6. Operational notes
- One writer process; do not run two instances on the same DB file over a network filesystem. Keep `--workers 1` unless load testing proves otherwise (D13 in `system-design.md`).
- `/health` is public and unauthenticated by contract; it must not expose version or DB details.
- Logs go to stdout as JSON (journald in prod). Correlation id = `X-Request-ID`; search by it. Alert on 5xx rate, 503 count (lock timeouts) and health failures.
- Synthetic data only: the app contains no real PHI; staging must never be loaded with real patient data.
