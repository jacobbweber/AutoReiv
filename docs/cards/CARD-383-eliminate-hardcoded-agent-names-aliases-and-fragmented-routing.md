---
id: CARD-383
title: "Eliminate Hardcoded Agent Names, Aliases and Fragmented Routing"
status: In Review
created: 2026-09-20
adr: none
labels:
  - type:refactor
  - domain:agents
  - domain:kernel
  - frontend
  - clean-up
---

# [CARD-383] Eliminate Hardcoded Agent Names, Aliases and Fragmented Routing

> **Status**: In Review  
> **Created**: 2026-09-20  
> **Labels**: `type:refactor`, `domain:agents`, `domain:kernel`, `frontend`, `clean-up`  
> **Branch**: `feat/card-383-eliminate-hardcoded-agent-names` off `qa`  
> **Reply to build**: **merge to qa**  

---

## 1. The Four Beats

### Beat 1: What Jacob Means
Eliminate hardcoded agent names, scattered alias tables, and string-matching blocklists across both frontend and backend. Agent resolution and visibility must be driven by canonical schema attributes (`show_in_chat`, `origin`, and canonical ID mappings) rather than ad-hoc string comparisons checking for obsolete or retired agents (`coding`, `review`, `conductor`, `hyperv`, `assistant`, `wiki`, `system-agent`, `tutor`).

### Beat 2: What AutoReiv Does Now
1. In `src/web/static/modules/studios/chat.js` (and `stream.js`), agent visibility is filtered using a 7-string hardcoded comparison:
   `if (agent.id === 'agent-builder' || agent.id === 'coding' || agent.id === 'review' || agent.id === 'conductor' || agent.id === 'hyperv' || agent.id === 'assistant' || agent.id === 'wiki') return false;`
   This leaks obsolete names and ignores the schema's `show_in_chat` property.
2. In `src/application/orchestration/job_phase_orchestrator.py`, multiple routing branches hardcode checks against legacy strings:
   `if default_agent_id in ("assistant", "wiki", "developer", "coding"): return "autoreiv"` and `if "tutor" in s: return "tutor"`.
3. In `src/web/routers/education.py`, 50 router request models declare `agent_id: str = "tutor"`, even though `tutor` is a legacy alias requiring fallback mapping.
4. In `src/application/orchestration/handoff_engine.py` and `src/application/kernel/supervisor_orchestrator.py`, local `alias_map` dictionaries duplicate the canonical `LEGACY_AGENT_ALIASES` that already lives in `src/domain/agents/profiles.py`.
5. In `src/web/static/modules/studios/routines.js` (line 536), routine agent creation falls back to `'system-agent'`, an obsolete agent ID.

### Beat 3: What Will Change
1. **Schema-Driven Chat Visibility**: Replace the hardcoded agent ID blocklist in `chat.js` and `stream.js` with schema properties:
   `agent.show_in_chat !== false && agent.origin !== 'system' && agent.id !== 'agent-builder'`.
2. **Canonical Single-Source Alias Resolution**:
   - Make `canonical_agent_id()` in `src/domain/agents/profiles.py` the single canonical resolver across the entire application.
   - Update `src/application/orchestration/handoff_engine.py` and `src/application/kernel/supervisor_orchestrator.py` to import and call `canonical_agent_id()` instead of maintaining duplicate `alias_map` dictionaries.
   - Update `src/application/orchestration/job_phase_orchestrator.py` to use `canonical_agent_id()` and remove hardcoded checks for `"assistant"`, `"wiki"`, `"developer"`, `"coding"`.
3. **Education Router Defaults**: Update all request models in `src/web/routers/education.py` to default `agent_id: str = "autoreiv"` (the canonical platform agent providing the `socratic-tutoring` skill).
4. **Routines Studio Fallback**: In `src/web/static/modules/studios/routines.js`, update fallback from `'system-agent'` to `(routineAgentSelect?.value || '').trim() || 'autoreiv'`.
5. **Canonical Platform Constant**: Define `DEFAULT_PLATFORM_AGENT_ID = "autoreiv"` in `src/domain/agents/profiles.py` and use it wherever the platform's default primary agent is needed.

### Beat 4: What Dies Today (The Prune List)
1. The 7-agent hardcoded string blocklist in `src/web/static/modules/studios/chat.js` line 62.
2. The duplicate `alias_map` dictionary in `src/application/orchestration/handoff_engine.py` lines 202-213.
3. The duplicate `alias_map` dictionary in `src/application/kernel/supervisor_orchestrator.py` lines 54-65.
4. Legacy routing checks `("assistant", "wiki", "developer", "coding")` and `("tutor")` in `src/application/orchestration/job_phase_orchestrator.py`.
5. The dead `'system-agent'` fallback string in `src/web/static/modules/studios/routines.js` line 536.
6. The obsolete default `agent_id: str = "tutor"` across 50 endpoints in `src/web/routers/education.py`.

---

## 2. Acceptance Criteria (EARS)

- [x] **[REQ-383-001] (Schema-Driven Chat Visibility)**: THE FRONTEND SHALL filter visible agents in Chat using `agent.show_in_chat !== false && agent.origin !== 'system'` without hardcoding obsolete agent IDs (`coding`, `review`, `conductor`, `hyperv`, `assistant`, `wiki`).
- [x] **[REQ-383-002] (Single Source of Agent Aliases)**: THE BACKEND SHALL use `canonical_agent_id()` as the single source of truth for resolving agent IDs, eliminating duplicate alias dictionaries in `handoff_engine.py` and `supervisor_orchestrator.py`.
- [x] **[REQ-383-003] (Orchestrator Clean Routing)**: THE SYSTEM SHALL route job phases using canonical agent IDs, removing obsolete branch checks for `"developer"`, `"coding"`, `"wiki"`, and `"tutor"`.
- [x] **[REQ-383-004] (Education Router Alignment)**: In `src/web/routers/education.py`, THE SYSTEM SHALL default `agent_id` to `"autoreiv"` rather than legacy `"tutor"`.
- [x] **[REQ-383-005] (Routines Fallback Clean-Up)**: In `src/web/static/modules/studios/routines.js`, THE SYSTEM SHALL eliminate the `'system-agent'` fallback.
- [x] **[REQ-383-006] (Negative Assertion & Regression Prevention)**: Automated tests SHALL verify that `handoff_engine.py`, `supervisor_orchestrator.py`, and `job_phase_orchestrator.py` correctly resolve legacy aliases via `canonical_agent_id()` without local duplicate maps.
- [x] **[REQ-383-007] (Zero Test Regressions)**: All existing 593 vitest tests and 1,777 pytest tests SHALL pass.

---

## 3. Constraints & Verification Plan

- Isolated feature branch: `feat/card-383-eliminate-hardcoded-agent-names` cut from `qa`.
- Subtractive engineering: prune duplicate maps and obsolete string literals.
- Pass `npm run preflight` before In Review.
