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

Developer’s pack allowlist gains `capability-authoring`, `proposals`, and `build-agent-pack`, including `propose_skill`, `propose_tool`, `commit_skill_pack`, `list_available_skills_and_tools`, and `scaffold_agent_pack`. CARD-429 left `save_agent_specification` registered and **not** on the Developer allowlist. CARD-431 later removed that registration (see follow-up below). `scaffold_agent_pack` is the pack write. The runbook is `platform-packs/developer/skills/capability-authoring/SKILL.md`.

A `user_modified` developer receives those skill ids through the existing additive grant. The prompt is not rewritten.

`BUILTIN_PROFILES` is empty. `get_agent("agent-builder")` returns None. Boot deletes a leftover `custom_agents` row and its `agent_overrides` row. Routines that still name `agent-builder` move to `developer`. Historical sessions and job rows are left in place so old transcripts still open. The plan engine uses one planner prompt for every agent.

Python tool classes stay where they are and remain registered on the master tool registry.

### Positive Consequences

* Chat with Developer can propose and commit skills and scaffold agent packs.
* No second hidden agent in the roster or API.

### Negative Consequences / Trade-offs

* Old transcripts may still say `agent-builder`. They do not bring the agent back.
* A `user_modified` developer prompt is not updated. The skill file and allowlist grant carry the new tools.
* CARD-429 left `save_agent_specification` in the process registry so a stray call would not crash, while Developer could not invoke it. CARD-431 removed that registration after no allowlist, job, routine, or in-checkout pending approval still named the tool.

### CARD-431 follow-up

`save_agent_specification` is not registered. It is not on the tool-policy `REQUIRE_CONFIRM` default or the HITL high-risk name list. The Python method is gone because nothing calls it. `scaffold_agent_pack` remains the pack write. `propose_skill`, `propose_tool`, and `propose_agent_specification` stay registered. `agent-builder` stays unregistered.

### CARD-432 follow-up

Boot rewrites `sessions.agent_id`, `messages.agent_id`, `jobs.agent_id`, and `phases.assigned_agent_id` from `agent-builder` to `developer`. Those rows are not deleted. Message content is not edited. A second boot leaves rows that already say `developer` alone. See [CARD-432](../cards/CARD-432-scrub-historical-agent-builder-rows.md).

### CARD-433 follow-up

A `user_modified` developer whose system prompt does not already mention `scaffold_agent_pack` receives one authoring paragraph on boot. The existing prompt text stays. The append is recorded in `platform_user_modified_prompt_appends`, so deleting that paragraph keeps it deleted. A developer that is not `user_modified` still takes the seed prompt. `save_agent_specification` stays off the allowlist. See [CARD-433](../cards/CARD-433-user-modified-developer-prompt-authoring-sentence.md).
