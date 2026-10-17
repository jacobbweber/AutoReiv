---
id: CARD-687
title: "Agora skill folder loader for colocated tools and references"
type: feature
status: Done
priority: P1
milestone: M26
needs_decision: none
proof:
  journeys: [card-687-agora-skill-folder-loader]
  checks:
    - tests/unit/architecture/test_card687_agora_skill_folders.py
    - tests/integration/test_card687_agora_capabilities_contract.py
branch: feat/card-687-agora-skill-folder-loader
log: {minutes: 18, qa_runs: 2, findings: 2}
created: 2026-10-15
completed: 2026-10-15
---

# CARD-687 Agora skill folder loader for colocated tools and references

## Intent
Jacob wants to eliminate the heavy hands-on tax of maintaining separate `SKILL.md` tool lists, `tool.json` metadata files, and multi-studio wiring by adopting the Agora skill folder layout (`ADR-0065`). In this first slice of M26, any skill folder (`platform/skills/<id>/` or `<data>/skills/<id>/`) becomes a self-contained capability package that can hold `SKILL.md`, on-demand `references/*.md` docs, and executable `tools/*.py` callables with schemas inferred directly from Python type hints and docstrings.

## Goal
- A skill folder under `platform/skills/<id>/` or `<data>/skills/<id>/` can contain `tools/<tool_name>.py` (defining `def run(...)`) and `references/<topic>.md` alongside `SKILL.md`, with zero `tool.json` required.
- AutoReiv discovers colocated `tools/*.py` via AST inspection (never importing untrusted code at scan time), infers description + JSON Schema `parameters` from `def run(...)` docstrings and type annotations, runs `ToolCheckService` static/access analysis, and mounts enabled tools into `ScopedToolRegistry` and `ContentStore.skill_tools`.
- Calling `skill_view(skill_id)` returns the `SKILL.md` runbook plus the index of colocated `references/` and `tools/`, and calling `skill_view(skill_id, reference="<topic>.md")` loads that reference file on demand.
- `GET /api/capabilities/tree` returns the structured Agora directory tree for every skill (`SKILL.md`, `references/`, `tools/` with inferred schemas, access warnings, and enable/approval state), and `POST /api/capabilities/skills/{skill_id}/tools/{tool_name}/toggle` enables or disables a colocated tool.

## Change
```text
skills/<skill-id>/
├── SKILL.md                  # Entry point & overview
├── references/               # Progressive disclosure reference docs (*.md)
│   └── <topic>.md
└── tools/                    # Colocated Python tools (*.py)
    └── <tool_name>.py        # `def run(arg: str = "default") -> dict:`
```
- **New `src/application/skills/agora_loader.py`**:
  - AST-parses `skills/<id>/tools/*.py` (`extract_agora_tool_spec`): validates `def run(...)`, extracts module/`run` docstring as `description`, converts parameter type annotations (`str`, `int`, `float`, `bool`, `list`, `dict`, `Optional[...]`) and defaults into JSON Schema `parameters`, reads optional `RISK` constant, and computes `code_sha256` + `ToolCheckService.detect_access(code)`.
  - Lists `skills/<id>/references/*.md` (`list_skill_references`, `read_skill_file`) with path-traversal jailing.
  - Builds the full Agora tree model for a skill folder (merging shipped `platform/skills/<id>/` and user `<data>/skills/<id>/`, where user files win and `.tool_approvals.json` tracks approved SHA-256 hashes for user-authored `tools/*.py`; shipped `platform/skills/<id>/tools/*.py` are trusted by default unless disabled).
- **Update `src/infrastructure/content/store.py`**:
  - `ContentStore.skill_tools(skill_ids)` includes both frontmatter `tools:` and enabled colocated `tools/*.py` from the skill folder so `resolve_allowed_tools(agent)` (`src/application/agent_skills/allowed_tools.py`) stays the single permission decider (`ADR-0061`).
- **Update `src/application/skills/user_catalog.py`**:
  - `skill_view(skill_id, reference=None)` lists colocated `references` (`["topic.md", ...]`) and colocated `tools` when `reference` is omitted, and returns the markdown content of `references/<reference>` when `reference` is passed.
- **Update `src/infrastructure/agents/registry.py`**:
  - Mounts enabled colocated skill tools at bootstrap (`mount_all_enabled_skill_tools`), executing them via `SandboxedSubprocessWorker` (`_run_sandboxed`).
- **Update `src/web/routers/capabilities.py`**:
  - `GET /api/capabilities/tree`: returns the Agora folder tree across all skills (`SKILL.md`, `references/`, `tools/`).
  - `GET /api/capabilities/skills/{skill_id}/file?path=...`: reads `SKILL.md`, `references/<name>.md`, or `tools/<name>.py`.
  - `POST /api/capabilities/skills/{skill_id}/tools/{tool_name}/toggle`: enables (approving current SHA-256 and mounting) or disables (unmounting) a colocated tool.

## What dies
Nothing in Slice 1 (existing `<data>/tools/` and studios stay working until Slice 4 retires `skill_studio.js` and `tools_studio.js`).

## Proof
- Journey `card-687-agora-skill-folder-loader`:
  1. Seed a skill folder with `SKILL.md`, `references/guide.md`, and `tools/calc_checksum.py` (typed `def run(text: str, modulo: int = 65535) -> dict`, no `tool.json`).
  2. Query `GET /api/capabilities/tree` and `GET /api/capabilities/skills/agora-checksum/file` and assert the skill's Agora tree lists `SKILL.md`, `references/guide.md`, and `tools/calc_checksum.py` with the inferred JSON schema (`text: string, required`).
  3. Enable `calc_checksum` via the toggle endpoint, tick `agora-checksum` on Architect in Agent Studio, and verify `calc_checksum` is granted in `allowed_tools` on both desktop and phone viewports.
  4. Untick `agora-checksum`, disable `calc_checksum`, and clean up the seeded skill folder.
- Checks:
  - `tests/unit/architecture/test_card687_agora_skill_folders.py` (`pytest.mark.guard` for `ADR-0065`).
  - `tests/integration/test_card687_agora_capabilities_contract.py` (operator contract: real FastAPI + temp data dir, verifies AST schema inference, reference reading, SHA-256 approval gating, sandboxed execution, and negative assertion that unapproved user tool code cannot execute).

## Plan and decisions
- **Decision D1 (Architecture — `ADR-0065`, Approved)**: Colocate `tools/<name>.py` (inferring JSON Schema from `def run(...)` type annotations + docstring via AST) and `references/<topic>.md` directly inside `skills/<id>/`, exposed via `GET /api/capabilities/tree` and `skill_view(..., reference=...)`.

## Findings
- **Fixed in-area (`scripts/smoke_server.py`)**: `resolve_paths()` passed `local_appdata=env.get("LOCALAPPDATA")` to `DataDirResolver` without passing `home=fake_home`, causing `resolver.platform_default()` on Linux (`POSIX`) to return `Path.home() / ".autoreiv"` and trip the live-data guard during `live_qa.py`. Fixed by passing `home=fake_home` when `LOCALAPPDATA` is set in `env`.
- **Fixed in-area (checkout boundary)**: Deleted an untracked `wiki/` directory left in the checkout root from an earlier session so `git status` stays clean per `.agents/rules/boundaries.md`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-687-agora-skill-folder-loader` | desktop | PASS | 3/3 steps passed; Agora tree, AST schema, reference read, and tool toggle verified |
| `card-687-agora-skill-folder-loader` | phone | PASS | 3/3 steps passed; Agora tree, AST schema, reference read, and tool toggle verified |

Screenshots:
- `/tmp/autoreiv-qa/card-687/card-687-agora-skill-folder-loader-desktop-01-seed-an-agora-skill-folder-on-disk-and-verify-ap.png`
- `/tmp/autoreiv-qa/card-687/card-687-agora-skill-folder-loader-desktop-02-enable-colocated-tool-via-toggle-api-and-verify-.png`
- `/tmp/autoreiv-qa/card-687/card-687-agora-skill-folder-loader-phone-02-enable-colocated-tool-via-toggle-api-and-verify-.png`

## Release note
Added Agora skill folder loader (`skills/<id>/tools/*.py` with AST schema inference, `skills/<id>/references/*.md` on-demand reading, and `/api/capabilities/tree`) per ADR-0065.
