/**
 * Forge tool-allowlist warning threshold [REQ-FORGE-007].
 * One band: warn when the checked tool count is at or above this value.
 */
export const FORGE_ALLOWLIST_WARN_AT = 12;

export function allowlistWarningVisible(count, threshold = FORGE_ALLOWLIST_WARN_AT) {
  return Number(count) >= threshold;
}

export function formatAllowlistWarning(count, threshold = FORGE_ALLOWLIST_WARN_AT) {
  return `${count} tools selected. Local models get unreliable past about ${threshold}. Split this into a specialist.`;
}
