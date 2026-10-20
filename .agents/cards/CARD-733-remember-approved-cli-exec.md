---
id: CARD-733
title: "Remember approved cli_exec commands for the active project"
type: feature
status: In Review
priority: P2
milestone: M32
needs_decision: none
proof:
  journeys: [card-733-remember-approved-cli-exec]
  checks: [tests/integration/test_project_approved_commands.py]
branch: feat/card-733-remember-approved-cli-exec
log: {minutes: 25, qa_runs: 2, findings: 1}
created: 2026-10-19
---

# CARD-733 Remember approved cli_exec commands for the active project

## Intent
`CARD-729` added `cli_exec` to `software-development` so `AutoReiv` can run a project's real build and test commands (such as `pytest -q` or `npm test`). Today `cli_exec` asks for operator confirmation on every single call in `balanced` mode, which creates repetitive approval prompts when iterating on tests in the same project.

## Goal
- When `cli_exec` parks for approval on an active project, the operator can choose to remember that command so repeat runs in the same project execute without another prompt.
- `DangerousCommandFilter` still runs before any remembered command is allowed, and `strict` mode still asks every time.
- The operator can view and revoke remembered commands for a project.

## Change
- `src/application/safety/tool_policy_gate.py`: in `ToolPolicyGate.evaluate`, after `DangerousCommandFilter`, check if `name == "cli_exec"` and the normalized command is in the active project's remembered commands list (when not in `strict` mode); if so, return `ToolPolicyVerdict.ALLOW` with `policy_source="project_approved_command"`.
- `src/web/routers/hitl.py` & `src/web/static/modules/studios/chat/hitl.js`: add an `Approve & remember for project` action on `cli_exec` approval cards (`remember_for_project: true` in `POST /api/approvals/{id}/decision`) that records the command under the active project slug.
- `src/web/routers/projects.py`, `src/web/templates/partials/wiki_projects.html`, `src/web/static/modules/studios/projects_journey_runs.js`, `src/web/static/modules/studios/projects.js`: show remembered commands for the active project with a remove button.

## What dies
nothing

## Proof
- Journey `card-733-remember-approved-cli-exec`:
  1. Select a project and ask AutoReiv to run a safe `cli_exec` command; click `Approve & remember for project`.
  2. Ask AutoReiv to run the same `cli_exec` command again; verify it runs with zero approval prompt.
  3. Revoke the remembered command in Projects Studio and verify it is removed.
- Checks: operator contract `tests/integration/test_project_approved_commands.py` (including negative assertions that a different command still asks, a dangerous command is still blocked, `strict` mode still asks, and another project does not inherit the approval).

## Plan and decisions
- **Decision (2026-10-19)**: Jacob approved Option 1 (`build`) — per-project exact command allowlist via an `Approve & remember for project` button on `cli_exec` approval cards, stored per project slug in durable settings (`project_approved_commands`), plus a revoke list in Projects Studio.
  1. **(Approved) Per-project exact command allowlist + Projects Studio revoke list**: Adds an `Approve & remember for project` button on `cli_exec` approval cards that stores the exact normalized command string per project slug in durable settings, plus a revoke list in Projects Studio. Safe against broad prefix abuse (`python -c ...`, `npm exec ...`).
  2. **Per-project command prefix allowlist**: Stores the binary/prefix (e.g. `pytest`, `npm test`) per project so flag variations don't re-prompt, at the cost of broader shell surface.
  3. **Session-only command memory**: Remembers the approved command only for the open chat session (`session_id`), with no Projects Studio UI changes.

## Findings
- **Fixed (`tests/unit/kernel/test_agent_kernel.py`, `tests/unit/kernel/test_agent_kernel_streaming.py`)**: `test_agent_kernel_injects_active_selected_project` constructed a bare `AgentProfile(id="developer")` without project skills (`allowed_skill=["software-development"]`), which stopped matching after `CARD-732` retired the hardcoded `agent.id == "developer"` check in `system_prompt_builder.py`. Passed `allowed_skill=["software-development"]` and split `test_agent_kernel_streaming.py` out of `test_agent_kernel.py` so both files stay under the 800-line ceiling.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-733-remember-approved-cli-exec` | desktop | PASS | 3/3 steps passed; remembered `echo card733_check_ok` for `proj-733-desktop`, second run executed with 0 HITL prompts, revoked in Projects Manager |
| `card-733-remember-approved-cli-exec` | phone | PASS | 3/3 steps passed; remembered `echo card733_check_ok` for `proj-733-phone`, second run executed with 0 HITL prompts, revoked in Projects Manager, 0px horizontal overflow |

Screenshots:
- `/tmp/autoreiv-qa/card-733/card-733-remember-approved-cli-exec-desktop-01-first-cli-exec-parks-with-approve-remember-for-p.png`
- `/tmp/autoreiv-qa/card-733/card-733-remember-approved-cli-exec-desktop-02-second-run-of-the-same-cli-exec-command-in-the-a.png`
- `/tmp/autoreiv-qa/card-733/card-733-remember-approved-cli-exec-phone-03-projects-studio-lists-the-remembered-command-and.png`

## Release note
Added: `cli_exec` approval cards can now remember an approved command for the active project so repeat test and build runs do not prompt every time (CARD-733).

