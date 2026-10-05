# TeleMed Folder Structure

Follows `.claude/skills/architecture` (Types -> Config -> Repository -> Service -> API -> UI). Two adaptations, both forced by the toolchain:
- Backend code lives in a named package `telemed` under `backend/src/` (`src/types` would shadow the stdlib `types` module). Layers are its sub-packages, so import-linter targets `telemed.types`, `telemed.config`, ...
- The frontend gets an extra `api/` folder (typed HTTP client) between `config/` and `hooks/`; the UI layer depends on API types, as the skill states. Playwright lives at the repo root (`e2e/`, run by `npx playwright test` per CLAUDE.md), not under `frontend/tests/e2e`.

```
telemed/                              repo root
  package.json                        root scripts: `npm start` (concurrently backend :8000 + frontend :5173), `npm run e2e`
  playwright.config.ts                desktop 1280 + mobile 375 projects, fixed timezone and clock
  init.sh                             dev bootstrap (exists)
  .env.example                        every env var documented (backend + frontend)
  .github/workflows/                  CI pipeline (see deployment.md)
    ci.yml                            lint, typecheck, layers, tests+coverage, traceability, e2e
    deploy.yml                        staging/prod release
  .claude/                            harness config, skills, hooks (exists)
  specs/                              BRD, stories, design docs, mockups (exists)
    design/mockups/                   HTML mockups, one per E5 story: the visual contract for the React pages (BRD sec.12)
  sprint-contracts/                   per-sprint evaluation contracts (exists)
  e2e/                                Playwright specs + screenshot baselines
    patient.spec.ts                   search -> book -> my appointments -> cancel/reschedule
    doctor.spec.ts                    queue, NO_SHOW gating, notes
    admin.spec.ts                     onboarding, deactivate/reactivate
    fixtures/                         fixed clock, seeded-DB reset, login helpers
    __screenshots__/                  committed baselines per viewport
  infra/                              deployment IaC (staging/prod); see deployment.md
    terraform/                        single VM + volume + DNS (optional, not needed for dev)
    systemd/telemed-api.service       process unit (single host)
    caddy/Caddyfile                   TLS + static frontend + /api reverse proxy
  scripts/
    check_traceability.py             every AC-01..10 / NFR-01..08 has a tagged test (E6-S2)
    migrations_manifest.py            regenerates/validates revision hashes (NFR-05)

  backend/
    pyproject.toml                    uv project, ruff, mypy --strict, pytest, coverage, import-linter contracts
    alembic.ini                       Alembic config (script_location = alembic)
    alembic/
      env.py                          binds Alembic to telemed.repository metadata
      versions/                       append-only migration revisions (never edited once committed)
      versions.lock.json              sha256 of every committed revision, checked by a test
    scripts/
      seed.py                         thin CLI wrapper over service.seed_service (E6-S1)
      create_admin.py                 one-off first-admin creation for staging/prod (proposed, deploy-time)
    src/telemed/
      __init__.py
      types/                          LAYER 1: pure types, no imports from other layers
        enums.py                      Role, SlotStatus, AppointmentStatus, EventType, AllowedAction
        ids.py                        NewType ids (UserId, SlotId, AppointmentId, NoteId, ...)
        errors.py                     domain exceptions (SlotUnavailableException, InvalidAppointmentStateException, ...) with stable codes
        money.py                      Decimal <-> minor-unit helpers and fee parsing (pure)
        state_machine.py              appointment transition table (data only)
        domain.py                     frozen dataclasses: User, Slot, Appointment, AppointmentEvent, Note, ...
      config/                         LAYER 2: environment and process-wide setup
        settings.py                   pydantic-settings Settings (validates PROVIDER_TIMEZONE etc.)
        logging.py                    JSON formatter, correlation-id contextvar, PHI-safe filter
        clock.py                      Clock protocol + system clock (injectable "now")
      repository/                     LAYER 3: persistence only, no business rules
        database.py                   engine, pragmas (WAL, busy_timeout), BEGIN IMMEDIATE session helpers
        types.py                      UtcDateTime TypeDecorator
        models.py                     SQLAlchemy 2 models + CHECK constraints (split into models/ if > 300 lines)
        mappers.py                    row <-> domain, minor units <-> Decimal (the only conversion point)
        triggers.py                   append-only trigger DDL (reused by migrations and tests)
        users_repo.py                 users queries
        profiles_repo.py              patient_profiles + versions
        doctors_repo.py               doctor_profiles, templates, search query
        slots_repo.py                 slot queries and conditional-UPDATE transitions
        appointments_repo.py          appointments, queue query, active-count check
        events_repo.py                append-only event inserts and reads
        notes_repo.py                 append-only note inserts and reads
      service/                        LAYER 4: business logic and orchestration
        unit_of_work.py               transaction boundary exposed upward (API never imports repository)
        bootstrap.py                  composition root: builds Settings, Clock, logging setup and service wiring for the API layer (API imports no Config/Repository)
        security.py                   argon2 hash/verify, JWT encode/decode
        access.py                     role/ownership policy (401/403/404 rules)
        auth_service.py               register, login, current-user resolution
        profile_service.py            versioned profile get/update (patient and admin)
        slot_generator.py             zone-aware idempotent expansion of templates
        doctor_service.py             onboarding, search, doctor slot calendar, block/unblock
        booking_service.py            atomic book + charge stub
        cancellation_service.py       patient/doctor cancel, 60-min rule, refund stub
        reschedule_service.py         atomic reschedule
        lifecycle_service.py          state-machine transitions, NO_SHOW rule, queue
        allowed_actions.py            computes allowed_actions and change_deadline per role and clock
        notes_service.py              append/list notes
        user_admin_service.py         list/deactivate/reactivate, admin profile edit
        seed_service.py               idempotent synthetic seed
        integrations/
          interfaces.py               VideoService, PaymentService, PrescriptionService, NotificationService protocols
          stubs.py                    default stubs (one identifier-only log line per call)
      api/                            LAYER 5: HTTP only, no business rules; imports ONLY service and types (never repository or config)
        app.py                        create_app(), lifespan (migrations check, startup slot generation), router registration order
        deps.py                       auth dependencies (get_current_user, require_roles), DI wiring of services and stubs
        middleware.py                 X-Request-ID / correlation id, access log
        errors.py                     exception -> {code,message,errors} mapping (409/422/503/500)
        schemas/                      Pydantic request/response models (common, auth, profile, doctors, slots, appointments, notes, admin)
        routers/
          system.py                   /health, /api/config
          auth.py                     register, login, me
          patients.py                 profile endpoints
          doctors.py                  search, detail, slots, /me/slots, block/unblock, /me/queue (literal /me routes first)
          admin.py                    onboarding, users, patient profile edit
          appointments.py             book, mine, detail, cancel, reschedule, status
          notes.py                    notes create/list/get + 405 handlers
    tests/
      unit/                           pure logic: money, state machine, allowed_actions, slot generator, security
      integration/                    API + real SQLite tmp file per test: auth, booking, lifecycle, notes, admin
      concurrency/                    20-way booking race, reschedule race, 503-never assertion
      architecture/                   append-only triggers, migration lock, import-linter run, PHI-in-logs scan
      conftest.py                     tmp DB, frozen clock fixture, stub spies, ac(...) marker registration
      factories.py                    synthetic data builders (all emails @example.test)

  frontend/
    package.json                      React 18, Vite, Tailwind, react-router, vitest
    vite.config.ts                    dev proxy /api and /health -> :8000
    tailwind.config.ts, tsconfig.json, eslint config
    index.html
    src/
      types/                          LAYER 1: TS types mirroring api-contracts (snake_case fields kept as-is)
      config/                         env, constants (14-day window, 60-min rule labels), route paths
      api/                            typed fetch client, error normaliser, 401/503 handling, one module per resource
      hooks/                          data hooks (useAuth, useDoctors, useSlots, useAppointments, useQueue, ...)
      components/                     reusable primitives: Button, FormField, StatusBadge, AriaLiveRegion, LoadingState, EmptyState, ErrorState
      app/
        routes.tsx                    route table and role guards
        layouts/                      PatientLayout (375-first), StaffLayout (1280-first)
        pages/
          auth/                       LoginPage, RegisterPage
          patient/                    DoctorSearchPage, DoctorDetailPage, BookingConfirmationPage, MyAppointmentsPage, NotesPage, ProfilePage
          doctor/                     QueuePage, SlotCalendarPage, AppointmentDetailPage
          admin/                      OnboardDoctorPage, UserListPage, EditPatientProfileDialog
          system/                     NotAllowedPage, NotFoundPage
        main.tsx                      entry
    tests/
      unit/                           vitest + Testing Library: 60-min disabled state, allowed-actions buttons, 409, 401 redirect, not-found, sessionStorage token
```

## Layer rules enforced mechanically
- `backend/pyproject.toml` declares import-linter `layers` contract: `telemed.api` > `telemed.service` > `telemed.repository` > `telemed.config` > `telemed.types`. Additional `forbidden` contract: `telemed.api` must not import `telemed.repository` or `telemed.config` (stricter project rule, also stated in `.claude/architecture.md`: **API imports only Service and Types**; a plain `layers` contract would still allow API -> Repository, hence the explicit contract; `service/unit_of_work.py` is the transaction seam and `service/bootstrap.py` hands settings/clock/logging setup to the API layer).
- `check-architecture` hook (`.claude/hooks`) re-checks on save; E6-S2 AC3 verifies a Repository -> Service import fails.
- Files < 300 lines, functions < 50 lines (CLAUDE.md): the repository and service folders are split per aggregate for this reason.
- Frontend: `types` < `config` < `api` < `hooks` < `components` < `app`; ESLint `no-restricted-imports` blocks upward imports.
