---
id: CARD-388
title: "Restore Developer and Tutor as Unified Agent Packs"
status: In Review
created: 2026-09-20
adr: 0054
labels:
  - type:feature
  - domain:agents
  - domain:chat
  - area:packs
---

# [CARD-388] Restore Developer and Tutor as Unified Agent Packs

> **Status**: In Review  
> **Created**: 2026-09-20  
> **ADR Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)  
> **Labels**: `type:feature`, `domain:agents`, `domain:chat`, `area:packs`  

---

## 1. Why / Intent (Beat 1)

In our architectural realignment, we resolved that while conversational roundtables are an anti-pattern, **specialized agent packs** with distinct security scopes, dedicated models, and separate working memories are essential:
1. **Developer**: Paired software engineer with high-capacity coding model routing, SDLC runbooks (`sdlc-engineering`), and project workspace tools.
2. **Tutor**: Socratic learning partner with pedagogical guidance, adaptive depth, and educational mastery ledger access (`socratic-tutoring`).

Furthermore, we are eliminating the artificial "Platform Pack vs. Custom Pack" hierarchy. **Everything is simply an Agent Pack.** The repository directory `platform-packs/` is strictly **Factory Seeds** that populate `$DATA_DIR/packs/` on first startup. Operators maintain full sovereignty over their agents (including editing display names, modifying skills, or deleting packs).

In Chat Studio, operators can select between seeded or custom agents using human-friendly display names (`agent.name`) while the runtime deterministically routes by immutable slug (`agent.id`).

---

## 2. What AutoReiv Does Now (Beat 2)

1. `platform-packs/` only contains `autoreiv` and `direct`. `developer` and `tutor` packs are missing from factory seeds.
2. In `src/application/agent_packs/schema.py` and `src/infrastructure/skills/platform_packs.py`:
   - `PLATFORM_PACK_IDS` is restricted to `("autoreiv", "direct")`.
   - `RETIRED_PLATFORM_PACK_IDS` includes `developer` and `tutor`, causing any on-disk packs for them to be cleaned up or deleted.
   - `LEGACY_AGENT_ALIASES` redirects `developer` and `tutor` to `autoreiv`.
3. In `src/web/templates/index.html` (lines 1543–1552), Chat Studio's header `#chatEngineSelector` is locked to a binary two-button toggle (`#engineBtnCore` / `#engineBtnDirect`).
4. Operators cannot select Developer or Tutor to run dedicated engineering or tutoring sessions.

---

## 3. What Will Change (Beat 3)

1. **Restore Factory Seed Packs**:
   - Re-seed `platform-packs/developer/pack.json` with:
     - Display name: `"Developer"`, slug: `"developer"`
     - Purpose: `"code"`, system prompt for full-lifecycle engineering
     - Assigned skill: `"sdlc-engineering"` (which declares git and project tools; zero naked tools)
   - Re-seed `platform-packs/tutor/pack.json` with:
     - Display name: `"Tutor"`, slug: `"tutor"`
     - Purpose: `"reasoning"`, system prompt for Socratic tutoring
     - Assigned skill: `"socratic-tutoring"` (which declares wiki and mastery ledger tools; zero naked tools)
2. **Unified Agent Pack Seeding & Un-retire**:
   - In `schema.py` and `platform_packs.py`:
     - Update factory seeds to include `developer` and `tutor`.
     - Remove `developer` and `tutor` from `RETIRED_PLATFORM_PACK_IDS` and `LEGACY_AGENT_ALIASES`.
     - Ensure startup seeder copies missing default packs into `$DATA_DIR/packs/` without overwriting user customizations if already present.
3. **Chat Studio Agent Selector**:
   - Update Chat Studio header `#chatEngineSelector` to display agent pills for available agents:
     - **AutoReiv** (General orchestrator & sysadmin)
     - **Developer** (SDLC, coding & project engineering)
     - **Tutor** (Socratic learning & mastery ledger)
     - **Direct** (Raw zero-overhead LLM stream)
   - Use `agent.name` for the visible label and `agent.id` for the value.
   - Switching agents dynamically switches session context, model indicator, and active history thread.
4. **Demand-Paged Capability Scoping**:
   - Restored agents load only Platform Required primitives + their active skill runbooks, maintaining KV-cache pre-fill efficiency (<2,000 tokens).

---

## 4. What Dies Today (The Prune List - Beat 4)

- Delete `developer` and `tutor` entries from `RETIRED_PLATFORM_PACK_IDS`.
- Delete `developer` and `tutor` redirect entries from `LEGACY_AGENT_ALIASES`.
- Prune `(Platform)` and `(Custom)` tags from `formatAgentSelectOption` across all Studio dropdowns.
- Prune `Platform Agent Pack` vs `Custom Agent` distinction in Agent Studio badges (unify to `Agent Pack`).
- Prune origin-based automatic pack purging in `DeclarativePackReconciler` (only explicitly retired packs are purged).
- Prune the binary 2-button lock in Chat Studio header (`#engineBtnCore` / `#engineBtnDirect` exclusivity).
- Retire hardcoded assumptions that only `autoreiv` and `direct` can appear in Chat.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-388-001] (Ubiquitous)**: THE SYSTEM SHALL seed `developer` and `tutor` from factory seeds (`platform-packs/`) into `$DATA_DIR/packs/` on startup if missing.
- **[REQ-388-002] (Ubiquitous)**: THE API SHALL return `developer` and `tutor` in `GET /api/agents` with `show_in_chat: true`.
- **[REQ-388-003] (Event-Driven)**: WHEN an operator opens Chat Studio, THE SYSTEM SHALL display selectable agent pills for all chat-visible agents using their display names (`agent.name`).
- **[REQ-388-004] (Event-Driven)**: WHEN an operator selects `Developer` or `Tutor`, THE SYSTEM SHALL execute the turn with that agent's distinct system prompt, model preferences, and scoped skill capabilities.
- **[REQ-388-005] (State-Driven)**: WHILE switching between agents in Chat Studio, THE SYSTEM SHALL preserve and display independent conversation session threads keyed by `agent.id`.
- **[REQ-388-006] (Negative Assertion)**: Automated tests shall explicitly assert that `developer` and `tutor` requests are NOT redirected or aliased to `autoreiv`, and are NOT deleted by retired pack cleanup routines.
- **[REQ-388-007] (Ubiquitous)**: THE SYSTEM SHALL drop the primitive distinction between "Platform" and "Custom" agents across domain models, UI, API, and database, normalizing all agent packs to `AgentOrigin.PACK = "pack"`, displaying clean agent names without tags, automatically healing legacy `purpose: "code"`, and restricting delete protection strictly to core orchestration identities (`autoreiv` and `agent-builder`).

---

## 6. Constraints & Verification Plan

- Feature branch: `feat/CARD-388-restore-developer-and-tutor-agents` cut from `qa`.
- Live user data packs stay in `%LOCALAPPDATA%\AutoReiv\packs\`, never in git checkout.
- Automated tests:
  - `pytest tests/unit/agent_packs/` (seeding, pack schema, alias elimination).
  - `npm run test:frontend` (Vitest for Chat Studio agent selector and stream handling).
- Linting: `ruff check .` and `npm run lint:frontend` with 0 errors.
- Preflight: `python .agents/skills/sdd-workflow/scripts/preflight.py`.
