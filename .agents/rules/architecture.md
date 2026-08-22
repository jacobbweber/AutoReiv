# Rule: Unified Code Architecture & Documentation Standards

You must balance tactical simplicity with structural scalability by enforcing **Strategic (SOLID)**, **Tactical (Global)**, and **Living Architectural Documentation** standards.

---

## 1. Living Architecture & C4 Modeling Invariants

You are responsible for maintaining text-first, machine-readable architectural models using Mermaid:
1. **System-Level Context & Containers (`docs/architecture/`)**:
   - When bootstrapping an application or adding new external systems / deployable containers (APIs, databases, frontends, workers), update or create high-level Mermaid C4 diagrams in `docs/architecture/`.
2. **Feature-Level Components & Sequence Flows (`docs/specs/<feature>/design.md`)**:
   - Every feature spec must document its internal component topology (Ports & Adapters) and request/response sequence diagrams using Mermaid syntax.
3. **Architectural Decision Records (`docs/adr/`)**:
   - Whenever introducing a major framework, database, structural protocol, or significant trade-off, record the rationale by running `python .agents/skills/adr-manager/scripts/new_adr.py "<Title>"`.

---

## 2. Strategic Architecture (SOLID Boundaries)
Use these rules to design how modules, classes, and components interact:

* **Decouple via Abstraction (DIP / OCP)**:
  - High-level application logic must never depend directly on low-level infrastructure (e.g., specific databases, third-party API clients, or OS-specific shells).
  - Depend on abstract interfaces / ports so providers can be added, mocked, or swapped without altering core runtime loops.
* **Enforce Single Boundaries (SRP / ISP)**:
  - Isolate tasks. A module should handle data fetching, data parsing, OR data storage—never all three.
  - Keep interfaces lean so consumers aren't forced to implement unused methods.
* **Preserve Behavior (LSP)**:
  - All subclasses or interface implementations must be fully interchangeable with their parent definitions without changing runtime exception or type expectations.

---

## 3. Tactical Execution (DRY / KISS / YAGNI)
Use these rules when writing individual functions, loops, and logic blocks:

* **KISS over Cleverness**:
  - Prioritize explicit, readable code over hyper-dense, complex optimizations, obscure language idioms, or heavily nested ternary operators.
  - If a junior developer cannot read and understand the intent immediately, rewrite it.
* **YAGNI Constraint**:
  - Write code exclusively for the current instruction or explicit requirement.
  - Do not build speculative placeholder structures, hypothetical extension points, or unused configuration properties.
* **Pragmatic DRY (The Rule of Three)**:
  - Do not copy-paste code blocks blindly.
  - However, do not introduce complex abstractions for only two instances of similarity. Duplicate safely twice; extract an abstraction or helper only on the third distinct occurrence.
