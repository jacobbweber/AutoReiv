# Design

UI only. Save still posts `allowed_tool_names` no matter how large the list is.

## Action to route to function

1. Tool checkbox change or pack-master change -> count `.forge-tool-checkbox:checked` -> `updateAllowlistWarning` in `forge.js` -> show or hide `#forgeAllowlistWarning`.
2. Select All / Clear All -> same count -> same banner.
3. Agent loaded into the form (`renderAgentToForge`) or New Agent reset -> same count -> same banner.

Threshold is `FORGE_ALLOWLIST_WARN_AT = 12` in `forge_allowlist.js`. Visible when `allowlistWarningVisible(count)` is true (`count >= 12`). One warning, not two tiers. Skills packs are ignored; only `.forge-tool-checkbox` / `allowed_tool_names` count.

Copy: `{count} tools selected. Local models get unreliable past about 12. Split this into a specialist.`

Amber styling matches Chat HITL (`bg-amber-950/40 border-amber-500/30 text-amber-200`). Not a modal. No Chat warning. No Settings field.
