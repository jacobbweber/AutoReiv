---
id: CARD-733
title: "Remember approved cli_exec commands for the active project"
type: feature
status: Ready
priority: P2
milestone: M32
needs_decision: "How should AutoReiv remember approved cli_exec commands? Option 1 (Recommended): Per-project exact command allowlist via an 'Approve & remember for project' button on cli_exec approval cards, with a revoke list in Projects Studio. Option 2: Per-project command prefix allowlist (e.g. 'pytest', 'npm test'). Option 3: Session-only memory (remember for the current chat session only, cleared on new chat)."
proof:
  journeys: [card-733-remember-approved-cli-exec]
  checks: [tests/integration/test_project_approved_commands.py]
branch: feat/card-733-remember-approved-cli-exec
log: {minutes: 0, qa_runs: 0, findings: 0}
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
- `src/web/routers/projects.py`, `src/web/templates/partials/wiki_projects.html`, `src/web/static/modules/studios/projects.js`: show remembered commands for the active project with a remove button.

## What dies
nothing

## Proof
- Journey `card-733-remember-approved-cli-exec`:
  1. Select a project and ask AutoReiv to run a safe `cli_exec` command; click `Approve & remember for project`.
  2. Ask AutoReiv to run the same `cli_exec` command again; verify it runs with zero approval prompt.
  3. Revoke the remembered command in Projects Studio and verify the next run asks for approval again.
- Checks: operator contract `tests/integration/test_project_approved_commands.py` (including negative assertions that a different command still asks, a dangerous command is still blocked, and another project does not inherit the approval).

## Plan and decisions
- **Decision needed (`needs_decision`)**:
  1. **(Recommended) Per-project exact command allowlist + Projects Studio revoke list**: Adds an `Approve & remember for project` button on `cli_exec` approval cards that stores the exact normalized command string per project slug in durable settings, plus a revoke list in Projects Studio. Safe against broad prefix abuse (`python -c ...`, `npm exec ...`).
  2. **Per-project command prefix allowlist**: Stores the binary/prefix (e.g. `pytest`, `npm test`) per project so flag variations don't re-prompt, at the cost of broader shell surface.
  3. **Session-only command memory**: Remembers the approved command only for the open chat session (`session_id`), with no Projects Studio UI changes.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Added: `cli_exec` approval cards can now remember an approved command for the active project so repeat test and build runs do not prompt every time (CARD-733).
