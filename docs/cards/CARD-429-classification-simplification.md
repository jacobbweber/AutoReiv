---
id: CARD-429
title: "Classification simplification for agents, skills, tools, and packs"
status: Ready
created: 2026-09-23
adr: docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md
labels:
  - type:planning
  - type:cleanup
  - area:agents
  - area:skills
  - area:tools
  - area:packs
---

# [CARD-429] Classification simplification for agents, skills, tools, and packs

> **Status**: Ready (planning only — **no product code** until Jacob says **build**)
> **Created**: 2026-09-23
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md), [ADR-0057](../adr/0057-three-studios-and-developer-mediated-authoring.md)
> **Audit**: read-only pass on `qa`. This card records the simplification epic. It does not implement it.

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Pick an option below or tighten the first slice — **still no product code** |
| **`build`** | Implement **only the first slice** on `feat/card-429-*` from `qa` |
| **`merge to qa`** | After In Review + a live look at Agent Studio, Skill Studio, and Tools Studio |

Do not treat this Ready card as approval to merge skill folders, delete `agent-builder`, or change seed overwrite rules.

---

## Options (pick before build)

| Option | What it does | Recommendation |
|--------|----------------|----------------|
| **A. Labels only** | Rename what Jacob sees. Leave folders, SQLite, and boot rules alone. | Safe, but the three skill boxes stay. |
| **B. First slice (recommended)** | Drop the non-functional skill tier control, make tool catalog labels match the four names Tools Studio already shows, and make the “always on” tool chips match the real required list. Do not move files. | **Build this.** |
| **C. Merge skill homes on disk** | One folder for every runbook. | Later. [CARD-203](./CARD-203-pure-platform-skill-isolation-and-pack-boundary-guardrails.md) and ADR-0056 depend on the split. |

---

## 1. Why / Intent (Beat 1)

Jacob wants fewer names for the same thing. Today Agent Studio shows three skill boxes (Platform Skills, Operator skills, Custom Agent Pack). Skill Studio has an Advanced tier of `platform` / `pack` / `user` that the screen itself says does not change which agent may run the skill. Tools Studio shows four origins, while the factory catalog API still invents `Platform:`, `Dynamic:`, and `Built-in Primitives` for tools that are all the same kind of shipped callable.

The useful differences are: which agent is on, which skills are ticked, where the runbook file lives, and whether a tool is shipped with AutoReiv, written as a native custom tool, loaded from an old pack Python file, or attached from an MCP server.

---

## 2. What AutoReiv does now (Beat 2)

- **Agents.** Live packs are `autoreiv`, `direct`, `developer`, and `tutor` (`platform-packs/` copied into `$DATA_DIR/packs/<id>/` when missing). `AgentOrigin` still has legacy values `platform` and `custom`, but `/api/agents` only returns `system` (hidden `agent-builder`) or `pack` (everyone else). Agent Studio badges say `System Baseline` or `Agent Pack`. `platform-packs/README.md` still describes the old three-pack set that includes `assistant`.
- **Skills.** Three homes: hardcoded platform skill ids in `src/application/agent_packs/schema.py` (`PLATFORM_SKILL_TOOLS`), operator files under `$DATA_DIR/skills/` that are not bundled seeds, and runbooks under `packs/<id>/skills/`. Turning a skill on is the same pill in all three boxes. Frontmatter `tier` is stored on `skill_binding_meta` and does not enter `resolve_scoped_tools`.
- **Tools.** Turn-time allowlist is `resolve_scoped_tools` plus `ScopedToolRegistry.get_tools_for_agent`. Required tools with no `SKILL.md` are the `platform_base` list in `schema.py` (`activate_skill`, `ask_clarification`, `handoff_to_agent`, `lookup_agents`, `get_session_info`, `recall_agent_memory`, `memorize_fact`). Agent Studio’s OS BASELINE chips show only the first five and say they apply to every agent. `direct` gets no tools. Tools Studio labels are Platform, Native custom, Legacy pack tool, and MCP.
- **agent-builder.** A Python builtin in `src/domain/agents/profiles.py`, not a folder under `platform-packs/`. Hidden from Chat. Still the target of paused routines `skill-eval-sleep` and `skill-curator`. Operator-facing authoring goes to the `developer` pack (`src/application/skills/developer_authoring.py`).

---

## 3. What will change (Beat 3) — first slice only

When Jacob says **build**, change labels and the one dead control. Do not move runbooks or change boot.

1. Skill Studio: remove the Advanced tier dropdown (`factorySkillTierSelect` in `src/web/templates/index.html`) from the operator form. Keep writing `tier: pack` on save so existing rows still round-trip. Do not read `tier` to decide who may run a skill.
2. Tools catalog: `GET` factory capabilities (`src/web/routers/agent_training_factory.py` `get_factory_capabilities`) shall label shipped callables as `Platform`, matching `catalog_origin_label` in `src/application/tools/native_packaging.py`. Stop emitting operator-facing `Dynamic:` and `Built-in Primitives` groups.
3. Agent Studio baseline chips (`src/web/static/modules/studios/forge/tools.js` and the caption in `src/web/templates/index.html`): list the same seven names as `REQUIRED_PLATFORM_TOOLS`, and say Direct has none.
4. Replace the stale sentences in `platform-packs/README.md` so the seeded ids match `DEFAULT_SEEDED_PACK_IDS`.

Out of this slice: merging the three Agent Studio skill boxes, deleting `agent-builder`, and any folder move. Those stay written here so a later card can take them.

---

## 4. What dies today (Beat 4)

- The operator-facing Advanced tier control (`platform` / `pack` / `user`).
- Operator-facing catalog group names `Dynamic:` and `Built-in Primitives` for shipped tools.
- The OS BASELINE caption that says the locked tools apply to every agent.
- The `platform-packs/README.md` claim that the always-installed packs are `assistant`, `autoreiv`, and `developer`.

Not in this slice (do not delete yet): `SkillTier` enum, `user_modified`, legacy pack loader, `agent-builder` profile, `$DATA_DIR/skills/` vs `packs/<id>/skills/`.

---

## 5. Acceptance criteria (EARS)

- **[REQ-429-001]** THE SYSTEM SHALL NOT show a skill tier control that chooses `platform`, `pack`, or `user` on the Skill Studio form.
- **[REQ-429-002]** WHEN Skill Studio saves a runbook THE SYSTEM SHALL still persist a tier value of `pack` so existing `skill_binding_meta` rows keep a value, AND SHALL NOT use that value to allow or deny a skill on an agent.
- **[REQ-429-003]** WHEN Tools Studio lists a shipped callable that is not native custom, not a legacy pack module, and not MCP, THE SYSTEM SHALL label it `Platform`.
- **[REQ-429-004]** THE SYSTEM SHALL show the seven required tool names from `REQUIRED_PLATFORM_TOOLS` as always-on chips, AND SHALL state that Direct mounts no tools.
- **[REQ-429-005]** WHEN AutoReiv boots THE SYSTEM SHALL still copy a missing platform pack from `platform-packs/` into `$DATA_DIR/packs/<id>/` and SHALL NOT overwrite a pack marked `user_modified`.
- **[REQ-429-006]** THE SYSTEM SHALL NOT delete the `agent-builder` profile, SHALL NOT merge `$DATA_DIR/skills/` into pack skill folders, and SHALL NOT stop loading `packs/<id>/tools/*.py` as legacy pack tools.

---

## 6. Human verification runbook

1. Open Agent Studio on AutoReiv. The always-on chips include `recall_agent_memory` and `memorize_fact`. The caption does not say every agent, including Direct.
2. Open Agent Studio on Direct. Chat still has no tools for Direct (unchanged).
3. Open Skill Studio. There is no Advanced tier dropdown. Saving a runbook still works.
4. Open Tools Studio. Shipped tools say Platform. A native custom tool still says Native custom. An MCP server still says MCP. A `packs/<id>/tools/*.py` module still says Legacy pack tool.
5. Restart serve. A platform pack you edited (prompt change) is still your text.

---

## 7. Out of scope

- Deleting or replacing `agent-builder` (paused routines and `propose_skill` / `commit_skill_pack` still name it).
- Collapsing `$DATA_DIR/skills/`, bundled seeds, and `packs/<id>/skills/` into one tree.
- Changing ADR-0056 `user_modified` / seed-hash rules, except the negative test that they still hold.
- MCP hosting UI (stays in Settings).
- Renaming the product word Platform. `platform-packs/README.md` already says the name is Platform, not Global. “Use Global Default” on the model picker means the Settings model, not an agent class.
