/**
 * Tool escalation: the remedy for "this needs a new or changed tool" [CARD-520 REQ-520-001/004/006].
 * The pre-rename name is no longer read (CARD-574).
 */

export const TOOL_ESCALATION = 'tool_escalation';

export function isToolEscalationRemedy(kind) {
  return kind === TOOL_ESCALATION;
}

/** Escalation object from a distill result or stored proposal. */
export function readToolEscalation(obj) {
  if (!obj || typeof obj !== 'object') return {};
  const esc = obj[TOOL_ESCALATION];
  return esc && typeof esc === 'object' ? esc : {};
}

/** Escalation object from a rendered Teach proposal card (data-tool-escalation). */
export function escalationFromCard(card) {
  if (!card || typeof card.getAttribute !== 'function') return {};
  const raw = card.getAttribute('data-tool-escalation') || '{}';
  try {
    const esc = JSON.parse(raw);
    return esc && typeof esc === 'object' ? esc : {};
  } catch {
    return {};
  }
}
