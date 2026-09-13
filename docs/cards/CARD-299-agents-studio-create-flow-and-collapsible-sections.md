# [CARD-299] Agents Studio create flow and collapsible sections

> **Status**: Ready  
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-13
> **Spec Reference**: scratch/jacobs-walk-braindump.txt
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
One reliable New Agent path (ditch Quick Scaffold); landing condensed into labeled collapsible sections without losing controls.

---

## 2. What to Build
Remove or hide Quick Scaffold; group preferences/overrides/capabilities/identity drawers; Custom Agent Pack Skills and Tools label; keep Platform Skills and Tools header.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Requirement 1: ...
- [ ] Requirement 2: ...
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.

## Design lock (UI/UX — marathon)
- Ditch Quick Scaffold.
- Collapsible: Agent Preferences / Overrides / Capabilities / Identity — keep all levers.
- Headers: **Platform Skills & Tools** + **Custom Agent Pack Skills & Tools**.
