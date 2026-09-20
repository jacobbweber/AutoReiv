---
id: CARD-388
title: "Restore Developer and Tutor as First-Class Platform Agents"
status: Ready
created: 2026-09-20
adr: 0054
labels:
  - type:feature
  - domain:agents
  - domain:chat
  - area:packs
---

# [CARD-388] Restore Developer and Tutor as First-Class Platform Agents

> **Status**: Ready  
> **Created**: 2026-09-20  
> **ADR Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)  
> **Labels**: `type:feature`, `domain:agents`, `domain:chat`, `area:packs`  

---

## 1. Why / Intent (Beat 1)

In our architectural realignment discussions (archived in `D:\Projects\research\autoreiv-architecture-realignment-conways-law-and-autonomic-os.md`), we resolved that while multi-agent chat roundtables are an anti-pattern, **specialized platform agents** representing distinct security scopes, dedicated models, and separate working memories are essential.

Specifically:
1. **Developer Agent**: Dedicated to software engineering, SDLC workflows, project workspace inspection, git operations, testing, and paired coding with its own model routing (e.g. high-capacity coding models).
2. **Tutor Agent**: Dedicated to education, Socratic dialogue, adaptive depth, and the learning ledger (mastery model, quiz/retrieval) without polluting general sysadmin or engineering logs.

In CARD-366, these agents were temporarily collapsed into skills under `autoreiv` (`sdlc-engineering`, `socratic-tutoring`), and Chat Studio was locked to a binary `[Core | Direct]` engine selector (CARD-361). Jacob wants Developer and Tutor brought back as first-class, selectable platform agents with their own identities, prompts, default model routing, and persistent session histories.

---

## 2. What AutoReiv Does Now (Beat 2)

1. `platform-packs/` only contains `autoreiv` and `direct`. `platform-packs/developer` and `platform-packs/tutor` were deleted.
2. In `src/application/agent_packs/schema.py` and `src/infrastructure/skills/platform_packs.py`:
   - `PLATFORM_PACK_IDS` is restricted to `("autoreiv", "direct")`.
   - `RETIRED_PLATFORM_PACK_IDS` includes `developer` and `tutor`, actively deleting or retiring them if encountered.
   - `LEGACY_AGENT_ALIASES` maps `developer` and `tutor` to `autoreiv`.
3. In `src/web/templates/index.html` (lines 1543–1552), Chat Studio header `#chatEngineSelector` only offers two buttons: `#engineBtnCore` (`data-engine="autoreiv"`) and `#engineBtnDirect` (`data-engine="direct"`).
4. An operator cannot select Developer or Tutor to start dedicated paired coding or tutoring sessions.

---

## 3. What Will Change (Beat 3)

1. **Platform Pack Seed Templates**:
   - Restore `platform-packs/developer/pack.json` with dedicated SDLC system prompt, skills (`sdlc-engineering`), engineering tools, and purpose `code`.
   - Restore `platform-packs/tutor/pack.json` with dedicated pedagogical Socratic prompt, skills (`socratic-tutoring`), learning ledger tools, and purpose `reasoning`.
2. **Platform Schema & Lifecycle**:
   - In `src/application/agent_packs/schema.py` and `src/infrastructure/skills/platform_packs.py`:
     - Update `PLATFORM_PACK_IDS` to `("autoreiv", "developer", "tutor", "direct")`.
     - Remove `developer` and `tutor` from `RETIRED_PLATFORM_PACK_IDS` and `LEGACY_AGENT_ALIASES`.
     - Ensure pack seeder cleanly installs/upgrades both packs in `$DATA_DIR/packs/`.
3. **Chat Studio Front Door Selection**:
   - Update Chat Studio header `#chatEngineSelector` (or agent pill selector) to present the primary platform agents:
     - **AutoReiv** (General orchestrator & sysadmin)
     - **Developer** (SDLC, coding & project engineering)
     - **Tutor** (Socratic learning & mastery ledger)
     - **Direct** (Raw zero-overhead LLM stream)
   - Selecting an agent updates the active session scope, model indicator, and loads the conversation history specific to that agent.
4. **Demand-Paged Capability Scoping**:
   - Developer and Tutor dynamically demand-page their assigned skills and tools on turn execution, keeping active KV context lean (<2,000 tokens).

---

## 4. What Dies Today (The Prune List - Beat 4)

- Retire `developer` and `tutor` entries from `RETIRED_PLATFORM_PACK_IDS`.
- Delete `developer` and `tutor` redirects from `LEGACY_AGENT_ALIASES`.
- Prune the hardcoded binary 2-button restriction (`Core` vs `Direct` only) in Chat Studio's engine bar.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-388-001] (Ubiquitous)**: THE SYSTEM SHALL maintain `developer` and `tutor` as active built-in platform packs in `PLATFORM_PACK_IDS` seeded into `$DATA_DIR/packs/` on application startup.
- **[REQ-388-002] (Ubiquitous)**: THE API SHALL return `developer` and `tutor` in `GET /api/agents` with `is_platform_pack: true` and `show_in_chat: true`.
- **[REQ-388-003] (Event-Driven)**: WHEN an operator clicks the agent selector in Chat Studio, THE SYSTEM SHALL display `AutoReiv`, `Developer`, `Tutor`, and `Direct` as selectable options.
- **[REQ-388-004] (Event-Driven)**: WHEN an operator selects `Developer` or `Tutor` and sends a message, THE SYSTEM SHALL execute the turn with that agent's distinct system prompt, model preferences, and scoped capabilities.
- **[REQ-388-005] (State-Driven)**: WHILE switching between agents in Chat Studio, THE SYSTEM SHALL preserve and display independent conversation session threads for each agent.
- **[REQ-388-006] (Negative Assertion)**: Automated tests shall explicitly assert that `developer` and `tutor` are NOT cleaned up by `RETIRED_PLATFORM_PACK_IDS` and that their requests are NOT aliased or redirected to `autoreiv`.

---

## 6. Constraints & Verification Plan

- Feature branch: `feat/CARD-388-restore-developer-and-tutor-agents` cut from `qa`.
- Live user data packs stay in `%LOCALAPPDATA%\AutoReiv\packs\`, never in git checkout.
- Automated tests:
  - `pytest tests/unit/agent_packs/` (platform packs schema, lifecycle seeding, alias checks).
  - `npm run test:frontend` (Vitest for Chat Studio agent selector and stream handling).
- Linting: `ruff check .` and `npm run lint:frontend` with 0 errors.
- Preflight: `python .agents/skills/sdd-workflow/scripts/preflight.py`.
