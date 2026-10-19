---
id: CARD-725
title: "Unskip and Modernize 5 Legacy Capability-Authoring and MCP Lifecycle Tests"
type: bug
status: Ready
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-725-modernize-capability-authoring-contracts]
  checks:
    - tests/integration/mcp/test_mcp_dev_deploy_lifecycle.py
    - tests/integration/operator_contracts/test_oc428_list_user_skills_runbooks.py
    - tests/integration/operator_contracts/test_oc429_retire_agent_builder.py
    - tests/unit/orchestration/test_agent_builder_job_phase.py
    - tests/unit/orchestration/test_commit_skill.py
branch: feat/card-725-modernize-capability-authoring-contracts
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-18
---

# CARD-725 Unskip and Modernize 5 Legacy Capability-Authoring and MCP Lifecycle Tests

## Problem
Five tests in `tests/unit/orchestration/`, `tests/integration/mcp/`, and `tests/integration/operator_contracts/` have remained skipped with `@pytest.mark.skip(reason="Capability authoring / MCP building is on no agent (CARD-571 Toolsmith builds native tools only)")` since `CARD-571`:
1. `tests/integration/mcp/test_mcp_dev_deploy_lifecycle.py::test_mcp_dev_deploy_lifecycle_end_to_end`
2. `tests/integration/operator_contracts/test_oc428_list_user_skills_runbooks.py::test_oc428_list_user_skills_includes_allowlisted_pack_runbook_only`
3. `tests/integration/operator_contracts/test_oc429_retire_agent_builder.py::test_oc429_developer_owns_builder_tools_and_agent_builder_is_absent`
4. `tests/unit/orchestration/test_agent_builder_job_phase.py::test_developer_pack_holds_builder_tools`
5. `tests/unit/orchestration/test_commit_skill.py::test_coding_cannot_execute_propose_skill`

## Cause
When `CARD-571` temporarily removed skill/MCP authoring tools from `developer` and later M26–M28 (`ADR-0065`, `ADR-0066`) consolidated `Architect`, `Developer`, and `Toolsmith` into Agora skill folders (`capability-authoring`, `project-cards`, `software-development`) on `AutoReiv` (`autoreiv`) and M31 (`CARD-710`) retired `/api/tools_studio/capabilities`, these 5 tests were left with `@pytest.mark.skip` still referencing `developer`, `packs/developer/skills/`, and `/api/tools_studio/capabilities`.

## Change
- Remove `@pytest.mark.skip` from all 5 tests and update their assertions to test the live M28/M31 architecture:
  1. `test_mcp_dev_deploy_lifecycle.py`: verify `MCPEngineeringTools` (`scaffold_mcp_server`, `test_mcp_server`, `deploy_mcp_container`, `register_mcp_service`) registers the server, writes the `mcp-<server>` companion `SKILL.md` under `$DATA_DIR/skills/`, and attaches it to `autoreiv`.
  2. `test_oc428_list_user_skills_runbooks.py`: verify `render_skill_index` and `list_user_skills` list ticked platform and user Agora skills for `autoreiv` (name and description only, without body tokens or copying `platform/skills/` into `$DATA_DIR/skills/`) and omit unticked skills.
  3. `test_oc429_retire_agent_builder.py`: verify retired agents (`agent-builder`, `developer`, `toolsmith`, `architect`) are absent from `GET /api/agents` and rejected on `POST /api/agents`, `autoreiv` owns `capability-authoring` tools (`scaffold_skill`, `test_skill_tool`, `register_skill`, `audit_capabilities`), retired routines (`skill-eval-sleep`, `skill-curator`) are absent, and `GET /api/capabilities/tree` serves the unified Capabilities tree.
  4. `test_agent_builder_job_phase.py`: update `test_developer_pack_holds_builder_tools` to assert `autoreiv`'s `capability-authoring` tools via `resolve_allowed_tools`.
  5. `test_commit_skill.py`: update `test_coding_cannot_execute_propose_skill` so an unprivileged agent is denied `propose_skill` while `autoreiv` with `capability-authoring` has its authoring toolset.

## What dies
All 5 `@pytest.mark.skip(reason="Capability authoring / MCP building is on no agent...")` suppressions.

## Proof
- Journey `card-725-modernize-capability-authoring-contracts`: verifies `GET /api/agents` exposes only the 3-agent roster (`autoreiv`, `tutor`, `direct`), `autoreiv` has `capability-authoring` ticked in Agent Studio and Capabilities Studio (`/api/capabilities/tree`), and retired agent IDs are rejected.
- Checks:
  - `tests/integration/mcp/test_mcp_dev_deploy_lifecycle.py`
  - `tests/integration/operator_contracts/test_oc428_list_user_skills_runbooks.py`
  - `tests/integration/operator_contracts/test_oc429_retire_agent_builder.py`
  - `tests/unit/orchestration/test_agent_builder_job_phase.py`
  - `tests/unit/orchestration/test_commit_skill.py`

## Plan and decisions
- Preserve every negative boundary assertion (no `agent-builder`, no copying shipped `platform/skills/` into `$DATA_DIR/skills/`, no unauthorized tool execution) while updating the target agent from retired `developer` to `autoreiv`.

## Findings
- None yet.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `/tmp/autoreiv-qa/card-725/...`

## Release note
Unskipped and updated 5 capability-authoring and MCP lifecycle tests for the 3-agent Agora skill architecture.
