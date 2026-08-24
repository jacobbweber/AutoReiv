# Repository Structure & Boundary Steering

> **Purpose**: Documents the structural topology, directory responsibilities, and layer boundaries for this repository.

---

## 1. Directory Layout

```text
├── .agents/                      # Antigravity agent configuration, constitution & rules
│   ├── rules/                   # Modular operational rules (TDD, SDD, DoD, Git)
│   └── skills/                  # Procedural runbooks & deterministic helper scripts
│       ├── adr-manager/scripts/ # Helper script to scaffold numbered ADRs
│       ├── rtm-sync/scripts/    # Deterministic RTM validator & unified preflight runner
│       ├── sdd-workflow/scripts/# Helper script to scaffold 3-file EARS specs & cards
│       └── tdd-cycle/           # TDD execution guide
├── .github/                     # GitHub workflows, CI actions, cards, and templates
│   ├── cards/                   # Work cards (CARD-xxx)
│   └── workflows/ci.yml         # Automated 6-gate continuous integration pipeline
├── docs/                        # SDLC and Architectural Knowledge Base
│   ├── architecture/            # C4 architecture models (Mermaid)
│   ├── adr/                     # Architecture Decision Records (ADR-0001 through ADR-0037)
│   ├── specs/                   # AWS Kiro-style 3-file feature specs
│   └── rtm.json                 # Machine-readable Requirements Traceability Matrix
├── src/                         # Production application source code
│   ├── domain/                  # Pure business entities and domain logic (zero external dependencies)
│   ├── application/             # Use cases, orchestrators, ports/interfaces
│   ├── infrastructure/          # Adapters, databases, external API clients
│   ├── cli/                     # Command-line entry points
│   └── web/                     # FastAPI backend application & static assets
│       ├── app.py               # Unified FastAPI server & REST routes
│       └── static/              # Native ES Module frontend
│           ├── app.js           # Subsystem orchestrator & entry point
│           └── modules/         # Modular studios, state store, services, and utils
│               ├── dom.js       # Defensive DOM helpers ($, $query, $on)
│               ├── state/       # Reactive state store (store.js)
│               ├── services/    # HTTP API client wrappers (api.js)
│               ├── studios/     # 7 Modular UI studios (chat, routines, observability, forge, settings, docs, wiki)
│               └── utils/       # Pure functions (physics.js, formatters.js, debounce.js, storage.js)
├── tests/                       # Automated test suites
│   ├── unit/                    # Fast, isolated unit tests (Pytest + Vitest)
│   ├── integration/             # Hermetic FastAPI TestClient integration test suites
│   └── e2e/                     # Playwright multi-studio navigation smoke test suites
└── steering/                    # Persistent high-level context (AWS Kiro Model)
    ├── product.md               # Vision & 7-studio architecture definition
    ├── tech.md                  # Dual-runtime technology stack & CLI commands
    ├── structure.md             # Structural topology & clean architecture boundaries
    └── roadmap.md               # Macro milestone backlog and completion tracker
```

---

## 2. Layer Boundary Rules (Clean Architecture / DIP)

1. **Domain Layer (`src/domain/`)**:
   - Contains pure business models, value objects, and domain rules.
   - **Constraint**: Must NEVER import from `infrastructure/`, `application/`, or `web/`.
2. **Application Layer (`src/application/`)**:
   - Contains use cases, workflows, and abstract port interfaces.
   - **Constraint**: May import from `domain/`. Must NOT import directly from concrete infrastructure adapters.
3. **Infrastructure Layer (`src/infrastructure/`)**:
   - Contains database clients, REST controllers, external SDK wrappers, and filesystem adapters.
   - **Constraint**: Implements ports defined in `application/`.
4. **Web & Frontend Layer (`src/web/`)**:
   - Presentation layer hosting FastAPI routing and zero-build ES Module frontend components.
   - **Constraint**: UI studios must use defensive DOM helpers and delegate computational logic to pure utility modules.
