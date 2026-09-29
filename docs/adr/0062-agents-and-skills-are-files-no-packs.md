# [ADR-0062] Agents and Skills Are Files; No Packs

> **Status**: Accepted  
> **Date**: 2026-09-28  
> **Deciders**: Jacob Weber (Product Owner), coding assistant  
> **Related Cards**: [CARD-570](../cards/CARD-570-agents-skills-from-platform.md) (implementation), CARD-568, CARD-569  
> **Supersedes**: the pack parts of [ADR-0048](./0048-autonomous-agent-pack-factory-and-capability-loop.md), [ADR-0056](./0056-durable-runtime-registry-hybrid-c-plus.md) (SQLite skill bindings, platform pack promotion) and [ADR-0058](./0058-retire-agent-builder-into-developer.md) (pack install / seeding)  
> **Amends**: [ADR-0061](./0061-capability-scoping-skills-only-permission-one-enforcement-point.md) (the skill-to-tool source is the SKILL.md `tools:` list)

---

## 1. Context

Agents and skills lived in three places at once: `platform-packs/<id>/pack.json` (seed), a copy promoted into data `packs/`, and DB rows (`agent_overrides`, `custom_agents`, `skill_tool_bindings`) plus `platform_*` settings keys. A reconciler, seeding, keep-customizations, per-agent content backups and a platform-defaults badge existed only to keep these copies in step. Edits were lost or duplicated, and "what does this agent have" needed four readers.

## 2. Decision

1. **Shipped content is read in place** from the repo: `platform/agents/<id>.md` (frontmatter `name, description, tone, purpose, avatar, show_in_chat, skills`; the body is the system prompt) and `platform/skills/<id>/SKILL.md` (frontmatter includes `tools:`). Nothing is copied at startup.
2. **User copies win by id.** Saving in a Studio writes the whole file to data `agents/<id>.md` or `skills/<id>/SKILL.md`. No field merging. A copy of a shipped item stores `based_on: <shipped hash>`; when the shipped hash differs the Studio shows "The shipped version changed since you edited this." **Use shipped version** deletes the copy.
3. **Deleting a shipped item hides it** (`agents/.hidden.json`, `skills/.hidden.json`, survives restart; Unhide reverses it). Deleting a user-created item removes its file. A hidden skill grants nothing.
4. **Shipped ids are reserved**: a new custom agent or skill cannot take a shipped id (HTTP 409).
5. **`tools:` lists are validated at boot**: an unknown tool id is a warning (`/api/health` `skill_tool_warnings`, Agent Studio status line) and grants nothing. A test fails if a shipped skill names an unknown tool.
6. **Per-agent model/provider** stay in one settings key (`agent_model_settings`), not in the agent file; Use shipped version keeps them.
7. **The DB holds chats and settings only.** `agent_overrides`, `custom_agents`, `skill_tool_bindings` and the `platform_*` keys are gone. Agent data lives in `agents/<id>/storage.db` and `agents/<id>/memory.db`.
8. `resolve_allowed_tools` stays the single permission decider (ADR-0061); it reads the winning SKILL.md `tools:` list through `ContentStore.skill_tools`.

## 3. Rules

- **No old-format readers before 1.0.** A format change ships with a data wipe or relies on Use shipped version; the code never reads the previous layout.
- **A skill is a job that groups several tools, not one skill per tool.** Short instructions are fine for obvious tools. The skill's tools list shapes what the model sees; the permission check and the tools themselves are the safety.

## 4. Consequences

- One loader (`src/infrastructure/content/store.py`) and one registry path; about 10 modules and their tests were deleted.
- Upgrading from a pack-era data dir needs the one-time wipe (CARD-570 Data wipe); model/provider settings are re-entered or restored.
- Open follow-ups: runtime-built tools in data `tools/` with an approved-code hash and Jacob-only enable; Skill Studio edits that add tools becoming proposals; renaming the `user-packs` routes and `list_user_skill_packs`.
