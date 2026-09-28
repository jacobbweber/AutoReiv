---
name: adr-manager
description: >-
  Manages Architecture Decision Records (ADRs). Use when proposing, creating, or updating structural, technology, or pattern decisions in docs/adr/.
---

# Architecture Decision Record (ADR) Manager

Follow this runbook to maintain an accurate history of architectural decisions with zero token overhead.

---

## 1. When to Create an ADR

Create an ADR only for a decision that constrains code, whenever it:

- Selects or replaces a primary framework, library, database, or infrastructure component.
- Establishes a system-wide boundary, protocol, or design pattern (e.g. Event-Driven vs. REST).
- Deprecates a major subsystem or architectural pattern.

---

## 2. Deterministic ADR Scaffolding

Run the automated ADR generator to determine the next sequential number and instantiate the template:

```bash
python .agents/skills/adr-manager/scripts/new_adr.py "<Short Title of Decision>"
```

_Example_: `python .agents/skills/adr-manager/scripts/new_adr.py "One decider for allowed tools"`

---

## 3. Fill Decision Context & Record

1. Open the newly generated ADR file (e.g. `docs/adr/0062-<slug>.md`).
2. Fill out:
   - **Context & Problem Statement**: What technical or business forces prompted this decision?
   - **Considered Options**: At least 2-3 viable alternatives with pros/cons.
   - **Decision Outcome**: Selected option, rationale, and positive/negative trade-offs.
3. If superseding an older ADR, update the status of the older ADR to `Superseded by ADR-XXXX`.
4. Every ADR that constrains code names its guard test (a `pytest.mark.guard` test that fails if the decision is broken).
5. Reference the new ADR in active work cards (`.agents/cards/CARD-xxx.md`) and update `steering/tech.md` or `steering/structure.md` if structural boundaries shifted.
