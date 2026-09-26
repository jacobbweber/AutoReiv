/**
 * Tool escalation: the remedy for "this needs a new or changed tool" [CARD-520 REQ-520-001/004/006].
 * Readers accept the pre-rename name for one release (removed by CARD-498).
 */

export const TOOL_ESCALATION = 'tool_escalation';
export const LEGACY_TOOL_ESCALATION = 'factory_escalation';
const LEGACY_ATTR = 'data-factory-escalation';

export function isToolEscalationRemedy(kind) {
  return kind === TOOL_ESCALATION || kind === LEGACY_TOOL_ESCALATION;
}

/** Escalation object from a distill result or stored proposal (new key first). */
export function readToolEscalation(obj) {
  if (!obj || typeof obj !== 'object') return {};
  const esc = obj[TOOL_ESCALATION] || obj[LEGACY_TOOL_ESCALATION];
  return esc && typeof esc === 'object' ? esc : {};
}

/** Escalation object from a rendered Teach proposal card (data-tool-escalation, old attribute as fallback). */
export function escalationFromCard(card) {
  if (!card || typeof card.getAttribute !== 'function') return {};
  const raw = card.getAttribute('data-tool-escalation') || card.getAttribute(LEGACY_ATTR) || '{}';
  try {
    const esc = JSON.parse(raw);
    return esc && typeof esc === 'object' ? esc : {};
  } catch {
    return {};
  }
}
