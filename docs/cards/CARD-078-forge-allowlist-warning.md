# [CARD-078] Forge Allowlist Warning

> **Status**: Done
> **Created**: 2026-08-28
> **Spec Reference**: `docs/specs/forge-allowlist-warning/`
> **Labels**: `type:feature`, `area:web`

---

## 1. Why / Intent
Specialist agents beat fat tool bags. Local models degrade when the Forge allowlist is huge.

## 2. What to Build
- Show one amber warning on Forge when the checked tool allowlist is 12 or more.
- Live update on checkbox change, Select All, Clear All, and when an agent is loaded.
- Do not block save. Do not warn on Chat. Do not add a Settings field.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-FORGE-007]`: Banner hidden when count < 12; visible when count >= 12. Copy includes the count.
- [x] `[REQ-FORGE-008]`: Warning updates live and does not block save. Tools only, not skill-pack count.
- [x] Automated tests green via vitest on touched JS tests.

## 4. Constraints & Honor Flags
- UI only. No backend gate, RBAC, or kernel change.
- One threshold (`FORGE_ALLOWLIST_WARN_AT = 12`). Not two tiers.
- Do not warn on Chat. Do not add a Settings field.
