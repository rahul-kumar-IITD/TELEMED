# telemed

TeleMed — a telemedicine appointment booking platform (BC-AINE-010, Healthcare / Digital Health). Roles: PATIENT (profile, doctor search, 14-day slots, book / cancel / reschedule, read notes), DOCTOR (slot calendar, daily queue, appointment state machine, append-only consultation notes), ADMIN (onboard doctors, manage users). Atomic booking (SlotUnavailableException), InvalidAppointmentStateException on bad transitions, fixed-point decimal fees, append-only events/notes/profile changes, no PHI in logs, structured JSON logs with correlation IDs. Video, payments, e-prescription and notifications are stubbed. Synthetic data only.

## Quick Reference

**Backend:** `cd backend && uv run pytest -x -q` | `uv run ruff check --fix .` | `uv run mypy --strict src/` | `uv run lint-imports`
**Frontend:** `cd frontend && npm test` | `npm run lint` | `npm run typecheck`
**E2E:** `npx playwright test`
**Full stack:** `npm start` (backend :8000 + frontend :5173, no Docker; see init.sh)
**Database:** SQLite file, WAL mode, busy_timeout set. Migrations via Alembic.

## Architecture

Strict layered architecture: Types → Config → Repository → Service → API → UI.
One-way dependencies only (enforced by import-linter). See `.claude/architecture.md` for full rules.

## Where to Find Things

| What | Where |
|------|-------|
| Architecture rules | `.claude/architecture.md` |
| Quality principles | `.claude/skills/code-gen/SKILL.md` |
| Testing patterns | `.claude/skills/testing/SKILL.md` |
| Evaluation rubric | `.claude/skills/evaluation/SKILL.md` |
| Sprint contract format | `.claude/skills/evaluation/references/contract-schema.json` |
| Playwright patterns | `.claude/skills/evaluation/references/playwright-patterns.md` |
| Human control knobs | `.claude/program.md` |
| Session recovery | `claude-progress.txt` |
| Feature tracking | `features.json` |
| Learned rules | `.claude/state/learned-rules.md` |

## Pipeline Commands

| Command | Purpose |
|---------|---------|
| `/brd` | Socratic interview → BRD |
| `/spec` | BRD → stories + features.json |
| `/design` | Architecture + schemas + mockups |
| `/build` | Full 8-phase pipeline |
| `/auto` | Autonomous ratcheting loop |
| `/implement` | Code gen with agent teams |
| `/evaluate` | Run app, verify contract |
| `/review` | Evaluator + security review |
| `/test` | Test plan + Playwright E2E |
| `/deploy` | Local dev bootstrap (`npm start`) + init.sh |

## Code Style

- TDD mandatory: test first, then implement
- 100% meaningful coverage target, 80% floor
- Functions < 50 lines, files < 300 lines
- Static typing everywhere (mypy strict, zero `any`)
- Never log PHI; use fixed-point Decimal for money
- See `.claude/skills/code-gen/SKILL.md` for full rules

## Git

Branch: `<type>/<description>` (e.g., `feat/user-auth`)
Commits: conventional format (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`)
