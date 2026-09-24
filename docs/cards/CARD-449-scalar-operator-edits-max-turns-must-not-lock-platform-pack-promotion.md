---
id: CARD-449
title: "Scalar operator edits (max_turns) must not lock platform pack promotion"
status: Ready
created: 2026-09-24
adr: ADR-0056
labels:
  - type:bug
  - area:packs
  - P1
parent: CARD-443
related:
  - CARD-445
---

# [CARD-449] Scalar operator edits (max_turns) must not lock platform pack promotion

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-443 live proof on Jarvis
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md)
> **Labels**: `type:bug`, `area:packs`, `P1`
> **Parent**: [CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine the scalar-vs-pack lock policy — still no product code |
| **`build`** | Implement finer-grained locks so max_turns/model edits do not block platform pack promotion |
| **`merge to qa`** | After proof that Tutor max_turns=100 survives while platform prompt/skills still promote |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Changing Tutor `max_turns` to 100 (CARD-445 intent) must not permanently block platform-pack → AppData / SQLite seed promotion.
2. CARD-443 correctly refused overwrite while `user_modified=true`, but that flag was set by a scalar Studio/API edit, not by intentional prompt/skill divergence.

### Beat 2: What AutoReiv does now

1. `PUT /api/agents/{id}` and settings paths call `mark_agent_user_modified(id, modified=True)` for any customization, including scalar `max_turns` / `model`.
2. CARD-443 promotion skips the entire pack when `user_modified` is set, including stock `system_prompt` and skill allowlist updates.
3. Live Tutor on Jarvis had `user_modified=1` with `max_turns=100` and a stale short SQLite prompt until `POST /api/agents/tutor/accept-platform-seed` cleared the lock.

### Beat 3: What will change

1. Distinguish **operator scalar locks** (max_turns, model, provider ticks) from **pack-content locks** (system_prompt, allowed_skill, skill bodies, tool allowlist divergence from seed).
2. Platform pack promotion must still preserve max_turns/model (CARD-443) while being allowed to update pack-owned fields when only scalars differ from seed.
3. Keep an explicit full lock when the operator truly diverged pack content (or document a separate `pack_locked` flag).

### Beat 4: What dies today

1. The need to manually clear `user_modified` after a harmless max_turns bump before platform Tutor skills/prompts can promote.

---

## 2. Acceptance criteria

- **[REQ-449-001]** WHEN only scalar operator fields (at least `max_turns` and `model`) differ from the platform seed, THE SYSTEM SHALL still promote pack-owned fields (`system_prompt` under shipped baseline, skills, pack tools) without requiring `accept-platform-seed`.
- **[REQ-449-002]** WHEN the operator has diverged pack content (prompt/skills/tools) from the last applied seed, THE SYSTEM SHALL continue to refuse overwrite and surface the CARD-443 skip + resolution path.
- **[REQ-449-003]** Tutor live proof: `max_turns=100` remains after a platform pack prompt/skill update without clearing a full user_modified lock by hand.

---

## 3. Reply phrases

- Refine: say **continue**.
- Implement: say **build**.
- After proof: say **merge to qa**.
