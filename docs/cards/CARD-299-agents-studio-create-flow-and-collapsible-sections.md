# [CARD-299] Agents Studio create flow and collapsible sections

> **Status**: In Review  
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
- [x] Quick Scaffold toolbar button removed; New Agent remains
- [x] Collapsible Identity / Agent Preferences / Overrides / Capabilities
- [x] Platform Skills & Tools + Custom Agent Pack Skills & Tools headers
- [x] Vitest `agents_studio_create_collapse_299.test.js` green

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.

## Design lock (UI/UX — marathon)
- Ditch Quick Scaffold.
- Collapsible: Agent Preferences / Overrides / Capabilities / Identity — keep all levers.
- Headers: **Platform Skills & Tools** + **Custom Agent Pack Skills & Tools**.
