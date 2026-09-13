# [CARD-089] Parse YAML Card Frontmatter

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/card-yaml-frontmatter/`
> **Labels**: `type:bug`, `area:sdlc`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Conductor cannot mark JARVIS-style YAML cards Ready. `parse_card_frontmatter` only reads AutoReiv `> **Key**: value` blockquotes, so `spec:` / `status:` YAML is ignored and Discuss -> Ready fails with "requires an existing spec path" even when `docs/specs/<slug>/` exists.

## 2. What to Build
- Parse YAML `---` KEY: VALUE `---` (no PyYAML) and merge with the blockquote parser. Blockquote wins on conflict; YAML fills missing keys.
- `spec_reference` aliases: Spec Reference, spec_reference, spec. `status` aliases: Status, status.
- YAML-origin cards keep YAML when `set_card_status` rewrites. AutoReiv cards stay blockquote.
- Do not convert Jacob's live CARD-001.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SDLC-070]`: YAML frontmatter parse without PyYAML. Dual format. Blockquote wins on conflict.
- [x] `[REQ-SDLC-071]`: spec_reference and status aliases are case-insensitive.
- [x] `[REQ-SDLC-072]`: YAML CARD-001-shaped Discuss -> Ready succeeds when the spec dir exists. Body preserved. Existing blockquote tests still pass.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- No PyYAML dependency.
- Do not delete Jacob's cards. Do not flip agentic-test CARD-001 to Ready.
- Do not clone. Do not push. Stay on `qa`.
