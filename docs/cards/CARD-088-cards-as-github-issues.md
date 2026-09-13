# [CARD-088] Cards As GitHub Issues

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/cards-as-github-issues/`
> **Labels**: `type:feature`, `area:sdlc`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Cards should become GitHub issues with status and type labels when `gh` is available. If `gh` is missing, say so clearly. Do not invent tokens or add GitHub MCP.

## 2. What to Build
- Tool `sync_card_issue` creates or updates an issue from a card.
- Labels: `status:discuss|ready|in-progress|in-review|returned|done` plus type labels from the card.
- Frontmatter `github_issue`.
- HITL on create/update.
- Dry-run/mock tests for the label map. Clear error when `gh` is missing.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SDLC-040]`: Status label map is complete.
- [x] `[REQ-SDLC-041]`: Type labels come from the card Labels line.
- [x] `[REQ-SDLC-042]`: Successful sync writes `github_issue`. Missing `gh` returns a clear error. No tokens invented.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Do not add GitHub MCP.
- Do not invent tokens.
- Do not add sync_card_issue to Conductor's locked 11-tool allowlist.
- Do not push. Stay on `qa`.
