---
name: adr-manager
description: >-
  Manages Architecture Decision Records (ADRs). Use when proposing, creating, or updating structural, technology, or pattern decisions in docs/adr/.
---

# Architecture Decision Record (ADR) Manager

Follow this runbook to maintain an accurate history of architectural decisions with zero token overhead.

---

## 1. When to Create an ADR
Create an ADR whenever a decision:
- Selects or replaces a primary framework, library, database, or infrastructure component.
- Establishes a system-wide boundary, protocol, or design pattern (e.g. Event-Driven vs. REST).
- Deprecates a major subsystem or architectural pattern.

---

## 2. Deterministic ADR Scaffolding
Run the automated ADR generator to determine the next sequential number and instantiate the template:
```bash
python .agents/skills/adr-manager/scripts/new_adr.py "<Short Title of Decision>"
```
*Example*: `python .agents/skills/adr-manager/scripts/new_adr.py "Use Redis for Session Storage"`

---

## 3. Fill Decision Context & Record
1. Open the newly generated ADR file (e.g. `docs/adr/0002-use-redis-for-session-storage.md`).
2. Fill out:
   - **Context & Problem Statement**: What technical or business forces prompted this decision?
   - **Considered Options**: At least 2-3 viable alternatives with pros/cons.
   - **Decision Outcome**: Selected option, rationale, and positive/negative trade-offs.
3. If superseding an older ADR, update the status of the older ADR to `Superseded by ADR-XXXX`.
4. Link the new ADR in `docs/rtm.json` under relevant requirements.
