# Repository Structure & Boundary Steering

> **Purpose**: Documents the structural topology, directory responsibilities, and layer boundaries for this repository.

---

## 1. Directory Layout

```text
├── .agents/                      # Antigravity agent configuration, constitution & rules
│   ├── rules/                   # Always-on rules: boundaries, code-quality, testing, definition-of-done (+ frontend)
│   └── skills/                  # Procedural runbooks & deterministic helper scripts
│       ├── adr-manager/         # Scaffold numbered ADRs
│       ├── boundary-audit/      # Working-tree hygiene & path resolver scanner
│       ├── card/                # Card loop, bug/feature templates, new_card.py, list_card_status.py
│       ├── lifecycle-audit/     # State persistence & reboot survival verification
│       ├── live-qa/             # Live journeys against the real model (scripts/live_qa.py)
│       ├── merge-to-qa/         # Merge a reviewed card to qa
│       ├── preflight/           # preflight.py --fast/--full/--nightly (+ honesty smoke script)
│       ├── serve-hygiene/       # Serve restart & port hygiene runbook
│       ├── single-lever-audit/  # Architectural anti-duplication check
│       └── ui-review/           # UI screenshot review
├── .github/                     # GitHub templates and labels
│   └── ISSUE_TEMPLATE/          # Work card, bug, and epic issue templates
├── docs/                        # SDLC and Architectural Knowledge Base
│   ├── adr/                     # Architecture Decision Records (ADR-0001 through ADR-0037)
│   ├── cards/                   # Active work cards (CARD-xxx)
│   └── archive_artifacts/       # Historical 3-file specs & legacy rtm.json
├── src/                         # Production application source code
│   ├── domain/                  # Pure business entities and domain logic (zero external dependencies)
│   ├── application/             # Use cases, orchestrators, ports/interfaces (native custom tools: application/tools/native_packaging.py)
│   ├── infrastructure/          # Adapters, databases, external API clients (legacy in-process pack tools: infrastructure/agents/legacy_pack_tools.py)
│   ├── cli/                     # Command-line entry points
│   └── web/                     # FastAPI backend application & static assets
│       ├── app.py               # Unified FastAPI server & REST routes
│       └── static/              # Native ES Module frontend
│           ├── app.js           # Subsystem orchestrator & entry point
│           └── modules/         # Modular studios, state store, services, and utils
│               ├── dom.js       # Defensive DOM helpers ($, $query, $on)
│               ├── state/       # Reactive state store (store.js)
│               ├── services/    # HTTP API client wrappers (api.js)
│               ├── studios/     # Modular UI studios (chat, routines, observability, forge, settings, skill studio, tools studio intent + catalog, wiki)
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
