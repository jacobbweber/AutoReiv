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

/**
 * Title of a Teach proposal card [CARD-504]. A needs-tool answer has no skill name, so the card names the
 * missing tool ("Needs a tool: get_city_weather", or "Needs a new tool" without a name); skill cards keep
 * "Skill Proposal: <name>".
 */
export function proposalCardTitle(proposal, skillName) {
  if (proposal && proposal.needs_tool) {
    const tool = String(readToolEscalation(proposal).suggested_tool_name || '').trim();
    return tool ? `Needs a tool: ${tool}` : 'Needs a new tool';
  }
  return `Skill Proposal: ${skillName}`;
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
