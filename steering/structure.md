# Repository Structure & Boundary Steering

> **Purpose**: Documents the structural topology, directory responsibilities, and layer boundaries for this repository.

---

## 1. Directory Layout

```text
├── .agents/                      # Antigravity agent configuration & rules
│   ├── rules/                   # Modular operational rules
│   └── skills/                  # Procedural runbooks & deterministic helper scripts
│       ├── adr-manager/scripts/ # Helper script to scaffold numbered ADRs
│       ├── rtm-sync/scripts/    # Deterministic RTM & blast-radius validator
│       ├── sdd-workflow/scripts/# Helper script to scaffold 3-file EARS specs
│       └── tdd-cycle/           # TDD execution guide
├── .github/                     # GitHub workflows, issue/PR templates
├── docs/                        # SDLC and Architectural Knowledge Base
│   ├── architecture/            # C4 architecture models (Mermaid)
│   ├── adr/                     # Architecture Decision Records
│   ├── specs/                   # AWS Kiro-style 3-file feature specs
│   └── rtm.json                 # Machine-readable Traceability Matrix
├── src/                         # Production application source code
│   ├── domain/                  # Pure business entities and domain logic (zero external dependencies)
│   ├── application/             # Use cases, orchestrators, ports/interfaces
│   └── infrastructure/          # Adapters, databases, external API clients
├── tests/                       # Automated test suites
│   ├── unit/                    # Fast, isolated unit tests
│   └── integration/             # End-to-end and component integration tests
└── steering/                    # Persistent high-level context (AWS Kiro Model)
```

---

## 2. Layer Boundary Rules (Clean Architecture / DIP)

1. **Domain Layer (`src/domain/`)**:
   - Contains pure business models, value objects, and domain rules.
   - **Constraint**: Must NEVER import from `infrastructure/` or `application/`.
2. **Application Layer (`src/application/`)**:
   - Contains use cases, workflows, and abstract port interfaces.
   - **Constraint**: May import from `domain/`. Must NOT import directly from concrete infrastructure adapters.
3. **Infrastructure Layer (`src/infrastructure/`)**:
   - Contains database clients, REST controllers, external SDK wrappers, and filesystem adapters.
   - **Constraint**: Implements ports defined in `application/`.
