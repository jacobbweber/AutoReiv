# [CARD-125] Revisit Wiki schema, tools, and operating manual

> **Status**: Ready
> **Created**: 2026-08-31
> **Spec Reference**: CARD-022; CARD-025; CARD-117; CARD-121
> **Labels**: `type:docs`, `type:feat`, `later`

---

## 1. Why / Intent
Wiki exists today as a pile of tools (`wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_overview`, `wiki_graph`, and related). It is not a designed Platform skill yet.

**Walked (2026-08-31 Jacob t198u):** Create a Platform skill `wiki` (a `SKILL.md` he can fill) on the Studio/platform-packs card. **This card** is the later revisit: Wiki's schema, tools, and operating manual. Emphasis: **correct deterministic YAML front matter** and **extensive metadata**.

This is a **backlog** card. Do not implement until Jacob says build. Do not fold it into the Agent Studio / Platform packs squeeze-in. Do not name inspiration products.

---

## 2. What to Build (when picked up)
- Revisit the Wiki note schema: required YAML front matter that is deterministic (same note, same fields, stable key order / types), plus extensive metadata (what the note is, when, who, links, status — lock the field list with Jacob before code).
- Revisit the Wiki tools so they read/write that schema instead of loose markdown.
- Revisit the Wiki operating manual (the `wiki` SKILL.md body). The skill file may already exist as a stub from the Platform-skill squeeze-in; this card fills and aligns it.
- Do not invent a second wiki. Do not move Wiki off Platform into a user pack.

---

## 3. Acceptance Criteria
- [ ] Front matter schema locked with Jacob (deterministic YAML, metadata field list).
- [ ] Tools create/read/update/list/search notes against that schema.
- [ ] `wiki` SKILL.md is the operating manual for that schema.
- [ ] Status In Review after code. Not Done until live test. Local commit only. No push.

---

## 4. Constraints
- Pickup later. Not the current Studio / Platform packs card. Not CARD-116 memory.
- Skill = one `SKILL.md` runbook. Tools stay atomic callables.
- Work on `qa`. Do not push unless Jacob asks.

---

## 5. Pickup
After Platform `wiki` skill stub exists. Say **build** / **continue**.
