# ADR-0058: Retire agent-builder into the developer pack

> **Date**: 2026-09-23  
> **Status**: Accepted  
> **Deciders**: Jacob Weber, coding assistant  
> **Related**: [ADR-0056](./0056-durable-runtime-registry-hybrid-c-plus.md), [ADR-0057](./0057-three-studios-and-developer-mediated-authoring.md), [CARD-429](../cards/CARD-429-classification-simplification.md)

---

## 1. Context & Problem Statement

`agent-builder` was a hidden Python builtin, not a folder under `platform-packs/`. Chat and Factory already hid it. Developer is the authoring face (`DEVELOPER_AGENT_ID`, ADR-0057). The builtin still owned HITL propose/commit tools, two paused routines, a plan-engine prompt branch, and deletion protection. Jacob locked the retirement: Developer holds scaffold, improve, and build for agents, skills, and tools, then `agent-builder` stops being a live agent.

---

## 2. Decision Drivers

* One authoring agent in Chat (Developer).
* Keep HITL propose/commit and `scaffold_agent_pack` callable.
* Do not merge `$DATA_DIR/skills/` with `packs/<id>/skills/`.
* Do not change `user_modified` / seed-hash overwrite rules.
* Boot must not recreate `agent-builder` from an old SQLite row.

---

## 3. Considered Options

* **Option 1**: Leave the hidden builtin and only fix labels.
* **Option 2**: Move the still-useful tools onto Developer, delete the builtin profile, purge leftover SQLite profile rows, retarget the two paused routines to `developer`.
* **Option 3**: Alias `agent-builder` to `developer` so old ids still resolve to a live agent.

---

## 4. Decision Outcome

Chosen option: **Option 2**.

Developer’s pack allowlist gains `capability-authoring`, `proposals`, and `build-agent-pack`, including `propose_skill`, `propose_tool`, `commit_skill_pack`, `list_available_skills_and_tools`, and `scaffold_agent_pack`. `save_agent_specification` stays registered for old callers and is **not** on the Developer allowlist. `scaffold_agent_pack` is the pack write. The runbook is `platform-packs/developer/skills/capability-authoring/SKILL.md`.

A `user_modified` developer receives those skill ids through the existing additive grant. The prompt is not rewritten.

`BUILTIN_PROFILES` is empty. `get_agent("agent-builder")` returns None. Boot deletes a leftover `custom_agents` row and its `agent_overrides` row. Routines that still name `agent-builder` move to `developer`. Historical sessions and job rows are left in place so old transcripts still open. The plan engine uses one planner prompt for every agent.

Python tool classes stay where they are and remain registered on the master tool registry.

### Positive Consequences

* Chat with Developer can propose and commit skills and scaffold agent packs.
* No second hidden agent in the roster or API.

### Negative Consequences / Trade-offs

* Old transcripts may still say `agent-builder`. They do not bring the agent back.
* A `user_modified` developer prompt is not updated. The skill file and allowlist grant carry the new tools.
* `save_agent_specification` remains in the process registry so a stray call does not crash, but Developer cannot invoke it.
