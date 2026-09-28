---
id: CARD-541
title: "Drop platform pack.json allowed_tool_names / pack_tool_names; no fixed domain text in packs"
status: Done
completed: 2026-09-28
created: 2026-09-26
branch: fix/card-541-drop-pack-tool-lists
proof:
  checks:
    - tests/unit/agent_packs/test_card541_no_pack_tool_lists.py
log:
  - 2026-09-28 remainder done on fix/card-541-drop-pack-tool-lists; set In Review
  - 2026-09-28 fixed oc_s6 test isolation under xdist (AUTOREIV_DB_PATH leak)
related:
  - CARD-539
labels:
  - type:chore
  - area:agents
  - P3
needs_decision: none
milestone: M25
---

# [CARD-541] Drop platform pack.json allowed_tool_names / pack_tool_names

> **Status**: Done (Developer pack done in CARD-562; the rest on fix/card-541-drop-pack-tool-lists, 2026-09-28).
> **Related**: CARD-539 (ADR-0061)
> **Labels**: `type:chore`, `area:agents`, `P3`

## Why

After CARD-539 an agent's tools come only from `resolve_allowed_tools` (REQUIRED_PLATFORM_TOOLS + tools of ticked skills). Platform `pack.json` files still carry `allowed_tool_names` / `pack_tool_names`, kept as read-only compat; they grant nothing and can drift from the real set.

## Change

Also replace the Tutor pack's fixed "Focus strictly on ..." domain sentence with a pointer to the generated domain line (D5; CARD-539 did this for AutoReiv only). Remove the fields from the shipped platform packs and from the pack schema/export (import still tolerates and ignores them); update the pack linter.

## Done when

Shipped packs have no tool lists; import of an old pack with tool lists ignores them with a note; the per-agent agreement test still passes.

## Results (partial)
CARD-562 (merged to qa 2026-09-28) removed `pack_tool_names` from the Developer pack; the Tutor fixed-domain sentence was already replaced in CARD-537. Remaining: the autoreiv, direct and tutor packs plus the pack schema/export/linter (about 170 references in 61 files); tracked in docs/findings.md (2026-09-28).

## Results (remainder, 2026-09-28)
- Packs: `pack_tool_names` removed from platform-packs/autoreiv, tutor and direct (autoreiv -38 lines, tutor -20, direct -1). No shipped pack has a flat tool list now.
- Schema: `AgentPackManifest` has no `pack_tool_names` field. A legacy `pack_tool_names` / `allowed_tool_names` key is dropped on load and kept only as `ignored_tool_lists`. `pack_tool_names` is now a read-only union of the pack's skill tools.
- Export writes no flat list; with no stored skill map the profile's tools go on the primary skill. scaffold_pack binds a flat spec list to the primary skill.
- Import: an old pack with a flat list imports, the list is ignored, and a note goes to the log and `last_import_notes` ("Ignored pack_tool_names in X/pack.json: tools come from the pack's skills (CARD-541).").
- Seed/promotion: new `seed_pack_tools()` (union of skill tools) is used for promotion. Refreshing the live AppData pack.json drops a stale flat list.
- Linter: no pack linter reads these fields (skills/linter.py doesn't), so the guard test `test_card541_no_pack_tool_lists.py` does the linter job (4 tests: shipped packs, manifest never dumps the lists, seed tools come from skills, live refresh drops a stale list).
- Agreement: resolved tools per agent are unchanged. The live check before/after the serve restart gave developer 26, direct 1, tutor 33, architect 20, autoreiv 43, all identical.
- Tests updated: agent_pack schema/import-export, card332, card438/439/441, oc_s2 (export has no flat list).

## Findings
- Deliberately left, since it is bigger than this card: the runtime `AgentProfile.allowed_tool_names` / `pack_tool_names`, the DB columns, the Agent Studio API/PUT fields, the settings customization fields, capability_migration (it uses old allowed_tool_names to propose skill ticks), the frontend platform_defaults.js labels and the e2e PUT bodies. Removing those is a DB/API migration; logged in docs/findings.md.
- The live AppData `packs/direct/pack.json` still has `"pack_tool_names": []`, because its seed hash already matched and no refresh ran. It is harmless: empty, and import ignores it.
- Fixed (was failing on qa too): `test_oc_s6_local_gate_and_docker_hard_fail` failed under `-n auto` and when run alone. Cause: the first `import src.web.app` runs a module-level create_app() that persists a local wiki_path into the DB named by AUTOREIV_DB_PATH; the test's docker phase moved AUTOREIV_DATA_DIR but left AUTOREIV_DB_PATH on that DB, so the resolver peeked the local wiki and create_app did not hard-fail. Serially an earlier test did the import first, which hid it. Fix: the docker phase now points AUTOREIV_DB_PATH at its own DB (test isolation only, no product change).

## Test steps (Jacob)
1. Open Agent Studio for AutoReiv and Tutor: the skills and tools show as before.
2. Export AutoReiv (Agent Studio export / `/api/agents/autoreiv/pack.zip`): pack.json has skills with tools and no `pack_tool_names`.
3. Import an old pack zip whose pack.json has `pack_tool_names`: the import works, and the server log shows the "Ignored pack_tool_names ..." note.
