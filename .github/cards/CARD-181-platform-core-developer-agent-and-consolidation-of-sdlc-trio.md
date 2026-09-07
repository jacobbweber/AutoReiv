# [CARD-181] Platform Core Developer Agent and Consolidation of SDLC Trio

> **Status**: Ready
> **Created**: 2026-09-07
> **Spec Reference**: CARD-124; CARD-174; CARD-179
> **Labels**: `type:feature`, `type:architecture`, `AutoReiv.Agents`, `AutoReiv.PlatformPacks`

---

## 1. Why / Intent

In CARD-124, AutoReiv established an SDLC specialist trio (`conductor`, `coding`, `review`) that used multi-agent handoffs to manage software development.

While well-intentioned, the multi-agent handoff relay introduces significant practical drawbacks:
1. **Context Starvation & Nuance Loss**: Passing work through serialized handoff packets loses the rich conversation history and specific nuances Jacob discusses.
2. **High Latency & Slowness**: Running three separate agent turns with queue handoffs takes 3x to 5x longer for routine development tasks.
3. **Redundancy with Reflexion**: With automated self-verification (`ReflexionLoopEngine` / CARD-179), a single agent can already write code, run automated tests, inspect error traces, and self-correct without needing an external "Reviewer" agent persona.
4. **Platform First-Class Need**: Development is a core function of AutoReiv. Out of the box, users should have immediate software engineering capabilities without needing to manually import external packs.

This card consolidates the SDLC capability into a single, unified **Platform Core Developer** agent that executes the full engineering lifecycle in a continuous context window using **Goal Mode + Reflexion**.

---

## 2. Three Beats: How It Works

### Beat 1: The Platform Developer Agent
1. **What you see**: A first-class built-in agent named **Developer** in Chat and Agent Studio with a `[Platform]` badge. It is immediately available upon launching AutoReiv.
2. **What AutoReiv does now**: Platform agents are strictly `assistant` and `autoreiv`. Development required manually importing three separate packs from `agent-packs/`.
3. **What will change**: `platform-packs/developer/` ships with the repository and is automatically seeded into `$DATA_DIR/packs/developer/` on startup.

### Beat 2: Single-Context SDLC via Goal Mode + Reflexion
1. **What you see**: You talk directly to **Developer** in Chat. For complex tasks, you toggle **Goal Mode** (which auto-enables Verify via CARD-179). Developer formulates the milestones (Spec $\rightarrow$ TDD Red-Green $\rightarrow$ Verification), edits the code, runs the test runner, self-corrects any failures, and presents the clean diff.
2. **What AutoReiv does now**: Work had to bounce from Conductor to Coding, then from Coding to Review, then back to Coding if tests failed.
3. **What will change**: A single engineer persona maintains complete memory and context across the entire turn.

### Beat 3: Retiring the Conductor / Coding / Review Trio
1. **What you see**: A clean, uncluttered Agent Studio and Chat picker. The legacy trio is retired and replaced by Developer.
2. **What AutoReiv does now**: Three separate pack folders exist in `agent-packs/`.
3. **What will change**: The trio is archived/deprecated, avoiding redundant personas and conflicting handoffs.

---

## 3. Technical Touchpoints

| Layer | Component | File Path |
| :--- | :--- | :--- |
| **Platform Seed** | Platform Pack Seed Registry | `src/infrastructure/skills/platform_packs.py` |
| **Pack Definition** | Shipped Developer Pack Manifest & Runbooks | `platform-packs/developer/pack.json`, `skills/` |
| **Profiles & Roster** | Builtin Roster & Studio Registration | `src/domain/agents/profiles.py` |

---

## 4. Acceptance Criteria (Definition of Done)

- [ ] [REQ-DEV-001] Author `platform-packs/developer` containing `pack.json`, SDLC skills (`SKILL.md` runbooks for planning, implementing, and verifying), and full developer tools (`read_project_file`, `write_project_file`, `execute_code`, git tools).
- [ ] [REQ-DEV-002] Add `"developer"` to `PLATFORM_PACK_IDS` in `src/infrastructure/skills/platform_packs.py` so it is automatically seeded on startup.
- [ ] [REQ-DEV-003] Update Agent Studio and Chat to display Developer with a `[Platform]` badge.
- [ ] [REQ-DEV-004] Archive or deprecate `conductor`, `coding`, and `review` from active catalog to prevent duplicate roles.
- [ ] [REQ-DEV-005] All automated unit and integration tests pass cleanly via `pytest`.
- [ ] [REQ-DEV-006] Zero lint errors via `ruff check .`.

---

## 5. Constraints & Working Agreement

- **Ready card only. Do not implement until Jacob explicitly says build.**
- Work strictly on local `qa` branch.
- No third-party product names in card or code.
