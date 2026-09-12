# [CARD-269] Foundation audit — Agent Instructions backfill (Assistant / System / Finance)

> **Status**: Done
> **Created**: 2026-09-12
> **Spec Reference**: Foundation audit after CARD-268. Architect feed: Assistant + System (AutoReiv-the-agent; rename later) + Finance adopt the “good agent” Instructions framework used for new agents. Live: open each agent → Instructions match template; Ask behaves under them. Evidence-only — no UI marathon, no rename product epic. Stack on `feat/foundation-honesty-resmoke-268` @ `ee93e1e`. Hold FF until Jacob merge phrase.
> **Labels**: `type:chore`, `P0`, `FoundationAudit`, `Agents`, `AntiTheatre`
> **Branch**: `feat/agent-instructions-backfill-269` (off 268 tip; push feat only)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. New agents get a solid “what makes a good agent” Instructions shape. **Old** Assistant, AutoReiv/System, and Finance never got that backfill — they feel thin / uneven.
2. Backfill those three to the same framework (role, mission, constraints, tools honesty, HITL, wiki/provenance). Rename AutoReiv→System is **later** (UI track); this card only upgrades Instructions content.
3. Live proof: open each agent in Forge/Chat → Instructions show the framework sections; a short Ask still runs under the new prompt (no blank / broken agent).
4. **Not this card**: Training Factory (270), ReAct audit (271), install (272), UI rename, Lumina.

### Beat 2: What AutoReiv Does Now
1. `AgentProfileGuardrail` only requires `system_prompt` length ≥ 10 — not the richer new-agent framework sections.
2. Platform packs `assistant` + `autoreiv` ship short legacy prompts; Finance is a custom/user agent (DB or pack) with thin or missing Instructions.
3. Forge create path can draft better prompts via builder tools; existing agents were not migrated.

### Beat 3: What Will Change
1. Codify the **good-agent Instructions template** (shared helper / constant) matching what new-agent create already aims for.
2. Backfill `system_prompt` (and Forge Instructions/runbook field if separate) for **assistant**, **autoreiv** (System-to-be), **finance**.
3. TDD: template sections present; agents load prompts containing them.
4. Live smoke: open each agent + one Ask each; artifact `notes/marathon-card269-live-smoke.json`.
5. CHANGELOG; push feat; hold FF until Jacob says merge.

---

## 2. Acceptance Criteria

- [x] **[REQ-FAUD-269-001]**: Shared good-agent Instructions template exists (deterministic sections).
- [x] **[REQ-FAUD-269-002]**: Assistant, AutoReiv/System, Finance `system_prompt` (or Instructions field) include those sections.
- [x] **[REQ-FAUD-269-003]**: Live: Forge/Chat shows updated Instructions for all three; short Ask succeeds under each (real job or turn — no invent).
- [x] **[REQ-FAUD-269-004]**: Tests + CHANGELOG; push feat only; hold FF until merge phrase. No qa/main.

## 3. Constraints

- Quality > speed. Do not rename agent id in this card.
- Prefer pack.json + registry seed path over one-off DB hacks when packs own the profile.
- Out of scope: 270–272, UI marathon, horizon D.

## 4. Modules Likely Touched

- `platform-packs/assistant/pack.json`, `platform-packs/autoreiv/pack.json`
- Finance pack or agent registry seed
- `src/domain/agents/` or `src/application/skills/agent_builder_tools.py` (template)
- `tests/unit/.../test_card269_*.py`
- `notes/scripts/agent_instructions_backfill_269.py`
- `CHANGELOG.md`

## 5. Design-room one-liner

Backfill Assistant / System / Finance to the good-agent Instructions framework — same bar as new agents, without the rename epic yet.

## 6. Build lock

CoS keep-rolling after 268: Builder may implement immediately on this Ready card.
