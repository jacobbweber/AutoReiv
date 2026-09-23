---
id: CARD-429
title: "Classification simplification for agents, skills, tools, and packs"
status: In Review
created: 2026-09-23
adr: docs/adr/0058-retire-agent-builder-into-developer.md
labels:
  - type:cleanup
  - area:agents
  - area:skills
  - area:tools
  - area:packs
---

# [CARD-429] Classification simplification for agents, skills, tools, and packs

> **Status**: In Review
> **Created**: 2026-09-23
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md), [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md), [ADR-0058](../adr/0058-retire-agent-builder-into-developer.md)
> **Operator contract**: `tests/integration/operator_contracts/test_oc429_retire_agent_builder.py`

Jacob locked Part B: retire `agent-builder` by moving still-useful capabilities onto the `developer` pack, then drop `agent-builder`. Say **merge to qa** after a live look. Do not merge from this card alone.

---

## 1. Why / Intent (Beat 1)

Jacob wants fewer names for the same thing, and one authoring agent. Skill Studio’s Advanced tier did not change who may run a skill. The tool catalog invented `Dynamic:` and `Built-in Primitives` for shipped callables that Tools Studio already calls Platform. Agent Studio’s always-on chips omitted two required tools and said they apply to every agent, including Direct. The hidden `agent-builder` builtin was still a live agent even though Chat and Factory hid it and Developer already authors packs.

---

## 2. What AutoReiv does now (Beat 2)

- **Agents.** Live packs are `autoreiv`, `direct`, `developer`, and `tutor`. `agent-builder` is not registered. `GET /api/agents/agent-builder` is 404. Creating that id is rejected.
- **Skills.** Three homes stay: platform skill ids, `$DATA_DIR/skills/`, and `packs/<id>/skills/`. Skill Studio has no tier dropdown. Save writes `tier: pack`. Tier is not an allow/deny check.
- **Tools.** Shipped callables are one Platform group (`catalog_origin_label`). Native custom, legacy pack modules, and MCP stay their own labels. Always-on chips are the seven `REQUIRED_PLATFORM_TOOLS`. Direct mounts none.
- **Developer.** Allowlist includes `capability-authoring`, `proposals`, and `build-agent-pack`: `propose_skill`, `propose_tool`, `commit_skill_pack`, `list_available_skills_and_tools`, `scaffold_agent_pack`, plus export/import. `save_agent_specification` stays registered and is not allowlisted. A `user_modified` developer gets the new skill ids from the additive grant. The prompt is not rewritten.
- **Routines.** `skill-eval-sleep` and `skill-curator` target `developer` and stay paused.
- **Old rows.** Boot deletes a leftover `custom_agents` row and `agent_overrides` row for `agent-builder`, and moves routines that still name it to `developer`. Historical sessions and jobs stay.

---

## 3. What will change (Beat 3)

Part A (labels / dead control) and Part B (retire agent-builder onto developer) are both in this slice.

1. Remove `factorySkillTierSelect`. Keep writing `tier: pack`.
2. `get_factory_capabilities` labels shipped callables `Platform`.
3. Baseline chips list all seven required tools. Caption says Direct mounts none.
4. `platform-packs/README.md` lists the four seeded ids.
5. Developer pack gains the builder HITL and scaffold tools and a `capability-authoring` runbook.
6. Remove the builtin profile, the plan-engine agent-builder branch, and boot recreation of that agent.

---

## 4. What dies today (Beat 4)

- The Skill Studio Advanced tier dropdown (`platform` / `pack` / `user`).
- Operator-facing catalog groups `Dynamic:` and `Built-in Primitives`.
- The OS BASELINE caption that said the locked tools apply to every agent.
- The README claim that the always-installed packs are `assistant`, `autoreiv`, and `developer`.
- The live `agent-builder` profile (`AGENT_BUILDER_PROFILE`, `BUILTIN_PROFILES` entry, registry registration).
- The plan-engine agent-builder-only planner prompt and research fallback.
- `agent_id="agent-builder"` on `skill-eval-sleep` and `skill-curator`.
- The tool-group id `agent-builder` (renamed `capability-authoring`; `save_agent_specification` is not in that group).

Kept: `SkillTier` enum, `user_modified` / seed-hash rules, legacy `packs/<id>/tools/*.py` loading, `$DATA_DIR/skills/` separate from pack skill folders, MCP hosting in Settings, Agent Studio’s three skill boxes, Python implementations of the HITL tools (still registered). `save_agent_specification` stays in the process registry and off the developer allowlist.

---

## 5. Acceptance criteria (EARS)

- **[REQ-429-001]** THE SYSTEM SHALL NOT show a skill tier control that chooses `platform`, `pack`, or `user` on the Skill Studio form.
- **[REQ-429-002]** WHEN Skill Studio saves a runbook THE SYSTEM SHALL still persist a tier value of `pack`, AND SHALL NOT use that value to allow or deny a skill on an agent.
- **[REQ-429-003]** WHEN Tools Studio lists a shipped callable that is not native custom, not a legacy pack module, and not MCP, THE SYSTEM SHALL label it `Platform` AND SHALL NOT group it as `Dynamic:` or `Built-in Primitives`.
- **[REQ-429-004]** THE SYSTEM SHALL show the seven required tool names from `REQUIRED_PLATFORM_TOOLS` as always-on chips, AND SHALL state that Direct mounts no tools.
- **[REQ-429-005]** WHEN AutoReiv boots THE SYSTEM SHALL still copy a missing platform pack from `platform-packs/` into `$DATA_DIR/packs/<id>/` and SHALL NOT overwrite a pack marked `user_modified`.
- **[REQ-429-006]** THE SYSTEM SHALL NOT merge `$DATA_DIR/skills/` into pack skill folders, and SHALL NOT stop loading `packs/<id>/tools/*.py` as legacy pack tools.
- **[REQ-429-007]** THE SYSTEM SHALL NOT register `agent-builder` as a live agent. `get_agent("agent-builder")` is None. Boot SHALL NOT recreate it from a leftover SQLite profile row.
- **[REQ-429-008]** WHEN the operator chats with Developer about proposing or committing a skill, or scaffolding an agent pack, THE SYSTEM SHALL expose the applicable builder tools (`propose_skill`, `propose_tool`, `commit_skill_pack`, `list_available_skills_and_tools`, `scaffold_agent_pack`) on that agent AND SHALL NOT allowlist `save_agent_specification`.
- **[REQ-429-009]** THE SYSTEM SHALL set `skill-eval-sleep` and `skill-curator` to `agent_id="developer"` AND SHALL leave both paused by default.
- **[REQ-429-010]** WHEN the developer profile is `user_modified` THE SYSTEM SHALL append the capability-authoring grant onto the allowlist AND SHALL NOT rewrite that developer’s prompt.

---

## 6. Human verification runbook

1. Open Agent Studio on AutoReiv. The always-on chips include `recall_agent_memory` and `memorize_fact` (seven chips). The caption says Direct mounts none. It does not say every agent.
2. Open Agent Studio on Direct. Chat still has no tools for Direct.
3. Open Skill Studio. There is no Advanced tier dropdown. Saving a runbook still works and the file’s tier is `pack`.
4. Open Tools Studio. Shipped tools say Platform. There is no Dynamic or Built-in Primitives group. A native custom tool still says Native custom. An MCP server still says MCP. A `packs/<id>/tools/*.py` module still says Legacy pack tool.
5. Open Chat. The agent list has AutoReiv, Direct, Developer, and Tutor. There is no Agent Builder.
6. Start a Developer chat and ask it to propose a skill (name `propose_skill` or “propose a skill”). The turn can call `propose_skill`. Ask it to scaffold an agent pack. It can call `scaffold_agent_pack`. It cannot call `save_agent_specification`.
7. Open Routines. `skill-eval-sleep` and `skill-curator` show Developer and stay off until you enable them.
8. Restart serve. A platform pack you edited (prompt change) is still your text. Agent Builder does not come back.

---

## 7. Out of scope

- Collapsing `$DATA_DIR/skills/`, bundled seeds, and `packs/<id>/skills/` into one tree. **Blocked.** [CARD-203](./CARD-203-pure-platform-skill-isolation-and-pack-boundary-guardrails.md) and [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md) keep those homes separate. No successor card.
- Changing ADR-0056 `user_modified` / seed-hash rules, except the additive grant already used for developer skills. A later prompt sentence is [CARD-433](./CARD-433-user-modified-developer-prompt-authoring-sentence.md), append-only.
- MCP hosting UI (stays in Settings).
- Collapsing Agent Studio’s three skill boxes. Successor: [CARD-430](./CARD-430-agent-studio-one-skill-list.md).
- Rewriting historical session rows that still say `agent-builder`. Successor: [CARD-432](./CARD-432-scrub-historical-agent-builder-rows.md).
- Removing the `save_agent_specification` Python handler. Successor: [CARD-431](./CARD-431-unregister-save-agent-specification.md).

---

## 8. SQLite choice

Leftover `custom_agents` and `agent_overrides` rows for `agent-builder` are deleted on boot (`retire_agent_builder_rows`). Routines that still name that id move to `developer`. Sessions and jobs are not rewritten. A row inserted after boot is ignored by `get_agent` and removed on the next purge.

---

## 9. Successors (Ready, not this slice)

| Card | What it is |
| --- | --- |
| [CARD-430](./CARD-430-agent-studio-one-skill-list.md) | In Review. One Agent Studio skill list. Disk homes stay. |
| [CARD-431](./CARD-431-unregister-save-agent-specification.md) | Optional. Unregister `save_agent_specification` if nothing still calls it. |
| [CARD-432](./CARD-432-scrub-historical-agent-builder-rows.md) | Optional. Point old session and job rows at `developer`. |
| [CARD-433](./CARD-433-user-modified-developer-prompt-authoring-sentence.md) | Optional. Append one authoring sentence onto a `user_modified` developer prompt. |

Merging `$DATA_DIR/skills/` with `packs/<id>/skills/` is not a successor. It stays blocked by CARD-203 and ADR-0056.
