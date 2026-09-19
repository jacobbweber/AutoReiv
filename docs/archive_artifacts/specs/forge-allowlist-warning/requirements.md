# Requirements

> **CARD-115 (2026-08-30):** The CARD-078 Forge 12-tool allowlist warning is **removed**. Intent is delete the UI warning, not add a hard cap. `FORGE_ALLOWLIST_WARN_AT` and `#forgeAllowlistWarning` are gone. Tool mounting is unchanged.

- REQ-FORGE-007: **Superseded by CARD-115.** Agent Studio does not show a 12-tool allowlist warning. Checking 12 or more tools does not display `#forgeAllowlistWarning`.
- REQ-FORGE-008: **Superseded by CARD-115.** There is no live warning to update. Save is not blocked. There is no hard cap on `allowed_tool_names`.
