---
id: CARD-689
title: "Inline Agora skill folder authoring and risk-tiered tool auto-enable"
type: feature
status: Done
priority: P1
milestone: M26
needs_decision: none
proof:
  journeys: [card-689-inline-agora-skill-folder-authoring-and]
  checks:
    - tests/unit/architecture/test_card689_agora_self_build_and_auto_enable.py
    - tests/integration/test_card689_agora_self_build_contract.py
branch: feat/card-689-agora-self-build-and-auto-enable
log: {minutes: 18, qa_runs: 1, findings: 0}
created: 2026-10-15
completed: 2026-10-15
---

# CARD-689 Inline Agora skill folder authoring and risk-tiered tool auto-enable

## Intent
Jacob wants agents (and operators) to author or update Agora skill folders (`skills/<id>/SKILL.md`, `references/<name>.md`, `tools/<name>.py`) inline without multi-hop studio forms or manual enable clicks for safe helpers. When a colocated tool `tools/<name>.py` is saved, `ToolCheckService` verifies it in the sandbox: pure `read_only` tools with zero outside access (`network`, `files`, `programs`, `hidden_imports`) auto-enable and mount immediately so the agent can call them in the same session, while tools with outside access or write/network/destructive risk are saved disabled for Jacob to review and enable.

## Goal
1. `save_skill_file(store, skill_id, rel_path, content, ...)` in `src/application/skills/agora_authoring.py` writes `SKILL.md`, `references/<name>.md`, or `tools/<name>.py` into `<data>/skills/<skill_id>/` (never touching `platform/skills/`).
2. Saving `tools/<name>.py` runs `ToolCheckService.check_native` against the AST-inferred parameters and risk level:
   - Broken code (`not check.ok`: syntax error, missing `def run`, path traversal, import error, or failed sample call) is refused and nothing is written to disk.
   - Pure `read_only` code (`check.status == "passed"`, `check.access == []`, `risk == "read_only"`) is written to `<data>/skills/<skill_id>/tools/<name>.py`, auto-approved in `.tool_approvals.json` (`enabled: True`, `approval: "enabled"`, `auto_enabled: True`), mounted onto `ScopedToolRegistry`, and activated for the current session.
   - Code with outside access (`network`, `files`, `programs`, `hidden_imports`) or non-`read_only` risk (`write`, `network`, `destructive`) is written to `<data>/skills/<skill_id>/tools/<name>.py` in disabled state (`enabled: False`, `approval: "disabled"`, `auto_enabled: False`), unmounted if previously mounted, and returns `access_warning(check.access)` so Jacob reviews it before enabling.
3. Both the HTTP endpoint `PUT /api/capabilities/skills/{skill_id}/file` and the agent tool `write_skill_file` (in `capability-authoring`) call `save_skill_file` as the single code path.

## Change
- `src/application/skills/agora_authoring.py`:
  - Implement `save_skill_file(store, skill_id, rel_path, content, *, checker=None, tool_registry=None, sample_arguments=None)`.
- `src/web/routers/capabilities.py`:
  - Add `PUT /api/capabilities/skills/{skill_id}/file` (request body `{path, content, sample_arguments?}`) calling `save_skill_file`.
- `src/application/skills/agent_builder_tools.py`, `src/application/skills/manifest.py`, `src/application/agent_skills/schema.py`, `src/application/kernel/tool_access.py`, `platform/skills/capability-authoring/SKILL.md`:
  - Register `write_skill_file` on `AgentBuilderTools` and include it in `capability-authoring` (`WRITE_TOOLS` in `tool_access.py`).
- `src/application/skills/session_skills.py`:
  - Include `write_skill_file` in `session_activated_skills_from_history`.
- `docs/adr/0065-agora-skill-folders-and-unified-capabilities.md`:
  - Link `CARD-689` and its guard test.

## What dies
nothing

## Proof
- Journey `card-689-inline-agora-skill-folder-authoring-and`:
  1. Verifies via `PUT /api/capabilities/skills/agora-self-built/file` that saving a pure `read_only` tool (`tools/calc_compound.py`) runs `ToolCheckService`, passes the sample call, auto-enables (`auto_enabled: true`, `approval: "enabled"`), and mounts the tool immediately without a manual toggle click.
  2. Verifies via `PUT /api/capabilities/skills/agora-self-built/file` that saving an outside-access tool (`tools/fetch_remote.py` importing `urllib.request`) is flagged (`access: ["network"]`, `status: "not_run_review"`), saved disabled (`auto_enabled: false`, `approval: "disabled"`), and not mounted until explicitly enabled.
  3. In Chat with `AutoReiv` (`skills: ["*"]`), asks `AutoReiv` to open `capability-authoring` with `skill_view`, use `write_skill_file` to create `skills/agora-temp-converter/tools/celsius_to_kelvin.py` (`def run(celsius: int = 25) -> dict`), and then immediately call `celsius_to_kelvin(celsius=100)` in the same turn (`373`).
- Checks:
  - `tests/unit/architecture/test_card689_agora_self_build_and_auto_enable.py` (`pytest.mark.guard`)
  - `tests/integration/test_card689_agora_self_build_contract.py`

## Plan and decisions
- Approved by Jacob under `ADR-0065` Slice 3 (`Option 1`, `Option A`, `build`).

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-689-inline-agora-skill-folder-authoring-and` | desktop | PASS | Pure `read_only` tool `calc_compound` auto-enabled; network tool `fetch_remote` saved disabled; `AutoReiv` self-built and executed tools in one turn: `skill_view -> write_skill_file -> celsius_to_kelvin` (`373 K`) |
| `card-689-inline-agora-skill-folder-authoring-and` | phone | PASS | Pure `read_only` tool `calc_compound` auto-enabled; network tool `fetch_remote` saved disabled; `AutoReiv` self-built and executed tools in one turn: `skill_view -> write_skill_file -> celsius_to_kelvin` (`373 K`) |

Screenshots:
- `/tmp/autoreiv-qa/card-689/card-689-inline-agora-skill-folder-authoring-and-desktop-02-enable-auto-discover-all-skills-on-autoreiv-in-a.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-689\card-689-inline-agora-skill-folder-authoring-and-desktop-02-enable-auto-discover-all-skills-on-autoreiv-in-a.png`)
- `/tmp/autoreiv-qa/card-689/card-689-inline-agora-skill-folder-authoring-and-desktop-03-in-chat-autoreiv-builds-celsius-to-kelvin-via-wr.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-689\card-689-inline-agora-skill-folder-authoring-and-desktop-03-in-chat-autoreiv-builds-celsius-to-kelvin-via-wr.png`)
- `/tmp/autoreiv-qa/card-689/card-689-inline-agora-skill-folder-authoring-and-phone-03-in-chat-autoreiv-builds-celsius-to-kelvin-via-wr.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-689\card-689-inline-agora-skill-folder-authoring-and-phone-03-in-chat-autoreiv-builds-celsius-to-kelvin-via-wr.png`)

## Release note
Agents and operators can now write `SKILL.md`, `references/*.md`, and `tools/*.py` directly into Agora skill folders via `write_skill_file` and `PUT /api/capabilities/skills/{skill_id}/file`, with `ToolCheckService` auto-enabling pure `read_only` tools while holding outside-access tools for review (CARD-689, ADR-0065).
