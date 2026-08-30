# [CARD-108] Okta skill pack template (scaffold only)

> **Status**: Ready
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/agent-builder-hitl/`
> **Labels**: `type:feature`, `area:skills`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
First homelab template: an Okta admin skill pack the user can open in Skills Studio. Playbook `SKILL.md` plus declared tools as JSON stubs. No live Okta API. No credentials.

## 2. What to Build
- Repo seed copied if-missing to `$DATA_DIR/skills/okta-admin/SKILL.md`. Do not overwrite user edits.
- agentskills.io frontmatter `name` + `description`. SOP body for homelab Okta admin (find user, reset/unlock, assign app, MFA check).
- JSON tool stubs with `name` + `parameters` (at least list users, reset/unlock, assign app). CARD-104 playbook handler: not executable Python, no HTTP to Okta.
- Visible in Skills Studio pack list and pack pane (tools + markdown).

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-BUILD-015]`: Copy-if-missing seeds `$DATA_DIR/skills/okta-admin/SKILL.md`. Dest exists => leave it. Skills Studio can open name, description, playbook, and tools.
- [ ] `[REQ-BUILD-016]`: Declared tools are JSON stubs. No Okta API, no Okta credentials, no Okta env keys.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Scaffold only. Depends on CARD-102 data dir + CARD-105 Skills Studio. No live Okta. No SkillOpt. No ACE. No LangGraph.
- Spec: `docs/specs/agent-builder-hitl/`.