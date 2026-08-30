# Design

> **CARD-115:** UI warning removed. Save still posts `allowed_tool_names` no matter how large the list is. No hard cap. Tool mounting unchanged.

The CARD-078 banner (`#forgeAllowlistWarning`), threshold constant (`FORGE_ALLOWLIST_WARN_AT = 12`), and `src/web/static/modules/utils/forge_allowlist.js` helper are deleted. Checkbox / Select All / Clear All still toggle `.forge-tool-checkbox` only.

HITL skill-proposal sprawl copy (`ALLOWLIST_WARN_AT` in `skill_proposals.py`) is a separate CARD-106/107 note and is not a Forge UI banner.
