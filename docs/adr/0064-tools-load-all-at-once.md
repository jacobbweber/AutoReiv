# [ADR-0064] Tools Load All at Once

> **Status**: Accepted  
> **Date**: 2026-09-29  
> **Deciders**: Jacob Weber (Product Owner), coding assistant  
> **Related Cards**: [CARD-578](../../.agents/cards/CARD-578-tools-load-all-at-once.md) (implementation), CARD-562, CARD-566, CARD-577, CARD-539, CARD-454, CARD-362  
> **Supersedes**: [ADR-0054](./0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md) Rule of 7 per-turn tool clamp (`MAX_ACTIVE_TOOLS_PER_TURN`, 8 then 15) and demand-paged tool mounting  
> **Amends**: [ADR-0061](./0061-capability-scoping-skills-only-permission-one-enforcement-point.md) rule 4 (selection: there is none left inside the allowed set); [ADR-0052](./0052-skill-and-tool-scoping-and-specialist-dispatch.md) section 3 Layer 1 (intent matching) and Layer 2 (`activate_skill`) are removed

---

## 1. Context

Each model call got at most 15 tools, chosen by pins (10 project and card tools since CARD-562/566), baseline
coordination tools, keyword/intent matching and BM25-style ranking. Developer is allowed 26 tools, so a plain turn
never saw `skill_view` although its skill index tells it to open runbooks with that tool, and a coding turn dropped
`activate_skill`, `skill_view` and `ask_clarification` (probe 2026-09-29, CARD-577). `activate_skill` only reordered tools
inside the cap. A tool left off the list still ran if the model named it, because execution checked the broader
allowed set, and a bare name such as `lookup` could run `mcp_srv_lookup` through a suffix match. The cap was a judgment
number, not a measured limit (ADR-0054 amendment, CARD-562). Jacob decided on 2026-09-29: keep it simple, send every
tool the agent is allowed.

## 2. Decision

1. **All at once.** Every model call sends every tool from the agent's ticked skills plus the base tools, exactly the set
   `resolve_allowed_tools` returns (ADR-0061). No cap, no pins, no ranking, no keyword or intent matching.
   `MAX_ACTIVE_TOOLS_PER_TURN`, the pin sets, `_match_intent_skills`, `ticked_skills_for_domains` and `tool_ranker.py`
   are deleted.
2. **Only policy narrows**, and only where the gate enforces the same rule: the Direct agent gets none; a Formulate
   (planning) phase does not get work tools (CARD-554); a job phase locked to matched capabilities gets those plus the
   required platform tools; education priming phases drop the forbidden wiki tools. A normal chat turn has none of these.
3. **`activate_skill` is removed.** It has no job once nothing is paged. Base tools are `ask_clarification`,
   `handoff_to_agent`, `lookup_agents`, `get_session_info`, `recall_agent_memory`, `memorize_fact` (Architect is still
   withheld `handoff_to_agent` / `lookup_agents`, CARD-563). `skill_view` and `list_user_skills` are sent whenever the
   agent has at least one ticked skill, so the skill index always works.
4. **Only a sent tool runs.** The kernel gate refuses a tool call whose name was not in the tools sent on that call
   (`tool_not_offered`) before policy or approval, and the registry checks the same set. Platform-side runs that are not
   a model call (an approved HITL resume, reflexion verifiers) check only the allowed set.
5. **Exact names only.** The bare-name suffix match to `mcp_*` tools is removed from execution. Wildcard skill bindings
   such as `mcp_files_*` still grant the tools they name.
6. The per-skill authoring cap (linter CAP-001, 15 tools) stays as a guideline for small skills; it is no longer tied to
   a runtime number. The architectural tool-bloat detector is advisory at 50 tools.

## 3. Consequences

- The model always sees the tools its runbooks name; no turn loses `skill_view` or a project tool to ranking.
- Every call carries the full schema set. Measured on 2026-09-29 (CARD-578 live test, qwen3.8): Developer 25 tools =
  2,778 schema tokens (prompt 3.75K), AutoReiv 38 = 5,169 (prompt 6.5K), Tutor 32 = 4,878, Architect 19 = 2,163,
  Toolsmith 13 = 1,999, Direct 0. Before, the 15-tool cap sent about 1.7K schema tokens. On the local models this raises
  prefill time; the lever is ticking fewer skills, not a cap.
- An agent with many ticked skills (Tutor 32, AutoReiv 38) pays for all of them on "hi". Revisit with measurements if
  tool choice or latency degrades; a future change would narrow by skill, never by keyword.
- Guard test `tests/unit/kernel/test_card578_tools_all_at_once.py` fails if the cap, ranking or `activate_skill` return, if
  any allowed tool is not sent, or if an unsent tool or a bare `mcp_*` suffix name runs.
