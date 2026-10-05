# Architecture

## Layer Hierarchy

The project follows a strict layered architecture. Dependencies flow **downward only** — a layer may import from layers below it but never from layers above it.

```
┌─────────────┐
│     UI      │  ← Layer 6 (highest)
├─────────────┤
│     API     │  ← Layer 5
├─────────────┤
│   Service   │  ← Layer 4
├─────────────┤
│ Repository  │  ← Layer 3
├─────────────┤
│   Config    │  ← Layer 2
├─────────────┤
│    Types    │  ← Layer 1 (lowest)
└─────────────┘
```

### Layer Definitions

| Layer | Responsibility | May Import From |
|-------|---------------|-----------------|
| Types | Domain models, interfaces, enums, shared type definitions | (none) |
| Config | Environment variables, feature flags, constants, app configuration | Types |
| Repository | Data access, persistence, external data sources | Types, Config |
| Service | Business logic, domain rules, orchestration | Types, Config, Repository |
| API | Route handlers, request/response mapping, middleware, validation | Types, Service (**never Repository**; Config values reach it through Service-provided objects) |
| UI | Components, pages, client-side state, rendering | Types, Config, Service, API |

## One-Way Dependency Rule

**Never import from a higher layer.**

Violations:
- A `Service` importing from `API` — FORBIDDEN
- A `Repository` importing from `Service` — FORBIDDEN
- A `Config` importing from `Repository` — FORBIDDEN
- A `Types` importing from any other layer — FORBIDDEN

**Stricter rule for the API layer (project decision):** the API layer imports **only Service and Types**. It must never import Repository (or Config). Data access always goes through a Service function; the transaction boundary is exposed upward by the Service layer (e.g. `service/unit_of_work.py`). A router that needs a row calls a service, which calls the repository.
- An `API` importing from `Repository` — FORBIDDEN
- An `API` importing from `Config` — FORBIDDEN (settings, clock and logging setup are handed to it by the Service layer)

In Python projects this is enforced with an import-linter `forbidden` contract in addition to the `layers` contract (a plain `layers` contract would allow API -> Repository):
```ini
[importlinter:contract:api-no-repository]
name = API must not import Repository or Config
type = forbidden
source_modules = telemed.api
forbidden_modules = telemed.repository, telemed.config
```

The `check-architecture` hook enforces the one-way rule on every file save.

## Verification Commands

### Types layer
```bash
# No imports from Config, Repository, Service, API, or UI
grep -rn "from.*config\|from.*repository\|from.*service\|from.*api\|from.*ui" src/types/
```

### Config layer
```bash
# No imports from Repository, Service, API, or UI
grep -rn "from.*repository\|from.*service\|from.*api\|from.*ui" src/config/
```

### Repository layer
```bash
# No imports from Service, API, or UI
grep -rn "from.*service\|from.*api\|from.*ui" src/repository/
```

### Service layer
```bash
# No imports from API or UI
grep -rn "from.*api\|from.*ui" src/service/
```

### API layer
```bash
# No imports from UI, and (stricter project rule) none from Repository or Config
grep -rn "from.*ui\|from.*repository\|from.*config" src/api/
```

### Full architecture audit
```bash
# Run the architecture check hook directly
.claude/hooks/check-architecture.sh
```

## Cross-Cutting Concerns

The following concerns span all layers and are handled via shared utilities, not inline in each layer:

| Concern | Implementation |
|---------|---------------|
| **Logging** | Centralized logger (e.g., `src/lib/logger`) — all layers import from `lib`, not from each other |
| **Authentication** | Auth context passed via dependency injection or middleware; never hardcoded per-layer |
| **Telemetry** | Instrumentation via a shared `src/lib/telemetry` module with span/trace helpers |
| **Error Handling** | Typed error classes in `Types`; caught and mapped at `API` boundary; never swallowed silently |

## Customization

Layer names, paths, and verification commands can be overridden for non-standard stacks (e.g., monorepos, microservices, full-stack frameworks) via `project-manifest.json` in the project root.

Example override:
```json
{
  "layers": [
    { "name": "domain", "path": "src/domain", "rank": 1 },
    { "name": "application", "path": "src/application", "rank": 2 },
    { "name": "infrastructure", "path": "src/infrastructure", "rank": 3 },
    { "name": "presentation", "path": "src/presentation", "rank": 4 }
  ]
}
```

When `project-manifest.json` is present, the `check-architecture` hook reads layer definitions from it instead of using the defaults above.
