---
id: CARD-701
title: "Live ApprovalMode in Settings UI with read_only and state_change tool effect tiers"
type: feature
status: In Review
priority: P2
milestone: M30
needs_decision: none
proof:
  journeys: [card-701-live-approval-mode-and-effect-tiers]
  checks: [tests/unit/architecture/test_card701_live_approval_mode.py]
branch: feat/card-701-live-approval-mode-and-effect-tiers
log: {minutes: 25, qa_runs: 2, findings: 0}
created: 2026-10-17
---

# CARD-701 Live ApprovalMode in Settings UI with read_only and state_change tool effect tiers

## Intent
Adapted from `Crucible` (`ADR-0015` §4.6, `docs/architecture-comparison-crucible-agent-os.md` §5 & §7.1): `CARD-691` added `AUTOREIV_APPROVAL_MODE` (`strict` vs `hands_off`) via environment variable. Operators should be able to switch `ApprovalMode` (`strict` / `balanced` / `hands_off`) live in Settings Studio without restarting the server, where `balanced` auto-mounts smoke-verified `read_only` tools and skills while gating `state_change` and `destructive` capabilities.

## Goal
Persist `approval_mode` (`strict`, `balanced`, `hands_off`) in live runtime settings (`DB > env > default`), surface it in Settings Studio, and enforce `read_only` vs `state_change`/`destructive` tool effect gating across tool authoring and execution.

## Change
- Added `src/application/safety/approval_mode.py` resolving `approval_mode` (`"strict" | "balanced" | "hands_off"`, plus `"autonomous"` alias) with precedence `DB setting > AUTOREIV_APPROVAL_MODE env > default ("balanced")`, plus `classify_tool_effect` (`"read_only" | "state_change" | "destructive"`) and `should_auto_enable_tool`.
- Wired `save_skill_file` in `src/application/skills/agora_authoring.py`, `PUT /api/capabilities/skills/{id}/file` in `src/web/routers/capabilities.py`, `write_skill_file` in `src/application/skills/agent_builder_tools.py`, and `ToolPolicyGate.apply_to_tool_result` in `src/application/safety/tool_policy_gate.py` to enforce the live `ApprovalMode` and tool effect tiers without restarting the server.
- Exposed `GET /api/settings/approval-mode`, `PUT /api/settings/approval-mode`, and `approval_mode` on `GET /api/settings` and `POST /api/settings/matrix`, splitting `src/web/routers/settings_data_backup.py` out of `src/web/routers/settings.py` to keep `settings.py` under 800 lines.
- Added the live Tool Approval Mode card (`#settingsApprovalModeCard`, `#approvalModeSelect`, `#approvalModeSaveBtn`, `#approvalModeStatus`) in Settings Studio (`src/web/templates/index.html` and `src/web/static/modules/studios/settings_approval_mode.js`).

## What dies
- Env-only approval mode lookup (`_is_auto_enable_read_only_mode`) in `src/application/skills/agora_authoring.py` that required a server restart to switch between `strict` and `hands_off`.

## Proof
- Journey `card-701-live-approval-mode-and-effect-tiers`:
  1. Switch Approval Mode in Settings Studio across `strict`, `balanced`, and `hands_off`, verify `read_only`, `state_change`, and `destructive` tool authoring follows the 3x3 autonomy matrix immediately without server restart on desktop and phone.
- Checks:
  - `tests/unit/architecture/test_card701_live_approval_mode.py`

## Plan and decisions
- Approved by Jacob under `CARD-698` Option 2 (2026-10-17).

## Findings
- None.

## Results
| Journey / Check | Viewport | Result | Notes |
|---|---|---|---|
| `preflight.py --fast --base qa` | — | PASS (18 s) | ruff PASS, eslint PASS, pytest guard 240 passed, changed tests 4 passed, mapped tests 331 passed, vitest 1121 passed |
| `card-701-live-approval-mode-and-effect-tiers` | desktop (1280×800) | PASS | `strict`, `balanced`, and `hands_off` switched live via `#approvalModeSelect` + `#approvalModeSaveBtn`; `read_only`, `state_change`, and `destructive` tool authoring verified |
| `card-701-live-approval-mode-and-effect-tiers` | phone (390×844) | PASS | Mobile Settings Studio Approval Mode card verified with 0px horizontal overflow |

Screenshots:
- `/tmp/autoreiv-qa/card-701/card-701-live-approval-mode-and-effect-tiers-desktop-01-open-settings-studio-and-verify-tool-approval-mo.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-701\card-701-live-approval-mode-and-effect-tiers-desktop-01-open-settings-studio-and-verify-tool-approval-mo.png`)
- `/tmp/autoreiv-qa/card-701/card-701-live-approval-mode-and-effect-tiers-desktop-04-switch-to-hands-off-mode-in-settings-ui-and-veri.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-701\card-701-live-approval-mode-and-effect-tiers-desktop-04-switch-to-hands-off-mode-in-settings-ui-and-veri.png`)
- `/tmp/autoreiv-qa/card-701/card-701-live-approval-mode-and-effect-tiers-phone-04-switch-to-hands-off-mode-in-settings-ui-and-veri.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-701\card-701-live-approval-mode-and-effect-tiers-phone-04-switch-to-hands-off-mode-in-settings-ui-and-veri.png`)

## Release note
- Added live `ApprovalMode` (`strict` / `balanced` / `hands_off`) selector in Settings Studio with `read_only`, `state_change`, and `destructive` tool effect gating [CARD-701].

