# [CARD-115] Remove Forge 12-tool allowlist warning

> **Status**: In Review
> **Created**: 2026-08-30
> **Spec Reference**: `docs/specs/forge-allowlist-warning/` (CARD-078 reversed; no new 3-file spec)
> **Labels**: `type:fix`, `area:web`

---

## 1. Why / Intent
Jacob now understands agents/skills/tools. The CARD-078 caution banner that fires when an agent has 12+ tools is in the way. Delete the UI warning. Do not add a hard cap.

---

## 2. What to Build
- Remove `FORGE_ALLOWLIST_WARN_AT` and `#forgeAllowlistWarning` from `forge.js`, `forge_allowlist.js`, `index.html`, and tests that assert the warning.
- Do not change actual tool mounting.
- Do not add a new cap.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Agent Studio (Forge) does not show a 12-tool allowlist warning banner.
- [x] `FORGE_ALLOWLIST_WARN_AT`, `#forgeAllowlistWarning`, and `#forgeAllowlistWarningText` are gone.
- [x] `forge_allowlist.js` warning helper is removed.
- [x] Save and tool mounting are unchanged. No hard cap.
- [x] Tests that expected the warning now expect it gone.
- [x] CHANGELOG Unreleased updated.
- [x] Automated tests green via vitest on touched JS tests.

---

## 4. Constraints & Honor Flags
- Work on `qa`. Do not push. Do not clone.
- Delete the UI warning only. Do not add a hard cap. Do not change actual tool mounting.
- Skill-proposal `ALLOWLIST_WARN_AT` (HITL sprawl note) is out of scope unless it only referenced the deleted Forge constant.
