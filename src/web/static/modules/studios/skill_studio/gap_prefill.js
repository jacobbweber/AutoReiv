/**
 * CARD-522: a new-skill draft built from a capability gap, for Skill Studio's "Open in Skill Studio".
 * Pure: no DOM. Skill Studio applies it to a new skill only, and asks before replacing a draft.
 */

import { toSnakeCase } from '../../utils/slug.js';
import { SKILL_DESCRIPTION_LIMIT, cleanDescription } from './workshop_meta.js';

/** The gap's capability label (identified_capability, else missing_capability). */
export function gapCapabilityLabel(gap = {}) {
  return String((gap && (gap.identified_capability || gap.missing_capability)) || '').trim();
}

/** "inventory_lookup" -> "Inventory Lookup"; keeps capitals already there ("TC49 lookup" -> "TC49 Lookup"). */
export function titleCaseCapability(text) {
  return String(text || '')
    .replace(/[_-]+/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/** Tool names in a /api/tools_studio/capabilities namespaces list. */
export function catalogToolNames(namespaces) {
  const names = new Set();
  (Array.isArray(namespaces) ? namespaces : []).forEach((ns) => {
    ((ns && ns.tools) || []).forEach((tool) => {
      if (tool && tool.name) names.add(String(tool.name));
    });
  });
  return names;
}

/** True when the gap names a tool that is not in the catalog (it has to be built first). */
export function gapToolIsMissing(gap = {}, toolNames = new Set()) {
  const tool = String((gap && gap.suggested_tool_name) || '').trim();
  return Boolean(tool) && !toolNames.has(tool);
}

/** The note Skill Studio shows for a gap whose tool does not exist yet. */
export function gapMissingToolNote(toolName) {
  return `This gap needs a tool that does not exist yet (${toolName}). A skill can only use existing tools: Ask Developer to build it first.`;
}

function clip(text, limit) {
  const s = String(text || '');
  return s.length > limit ? `${s.slice(0, Math.max(0, limit - 3)).trimEnd()}...` : s;
}

/**
 * @param {object} gap  a capability gap row (id, turn_text, identified_capability, suggested_tool_name, context_summary)
 * @param {{ toolNames?: Set<string>, agentId?: string, takenIds?: Set<string> }} [opts]
 *   takenIds: skill ids that already exist; Save would overwrite one, so the draft picks "<name> 2" instead.
 * @returns {{ gapId: string, name: string, skillId: string, takenSkillId: string, description: string, intent: string, markdown: string, tools: string[], missingTool: string }}
 */
export function buildGapSkillDraft(gap = {}, { toolNames = new Set(), agentId = '', takenIds = new Set() } = {}) {
  const g = gap && typeof gap === 'object' ? gap : {};
  const asked = cleanDescription(g.turn_text || g.user_prompt || '');
  const context = String(g.context_summary || g.assistant_response || '').trim();
  const label = gapCapabilityLabel(g);
  const baseName = titleCaseCapability(label) || clip(asked, 60) || 'New Skill';
  let name = baseName;
  let skillId = toSnakeCase(name);
  for (let n = 2; takenIds.has(skillId) && n < 100; n += 1) {
    name = `${baseName} ${n}`;
    skillId = toSnakeCase(name);
  }
  const takenSkillId = name === baseName ? '' : toSnakeCase(baseName);
  const suggested = String(g.suggested_tool_name || '').trim();
  const missingTool = gapToolIsMissing(g, toolNames) ? suggested : '';
  const tools = suggested && !missingTool ? [suggested] : [];

  const lead = `${name}. Use when the user asks for something like: `;
  const description = asked
    ? `${lead}"${clip(asked, Math.max(20, SKILL_DESCRIPTION_LIMIT - lead.length - 2))}"`
    : `${name}.`;

  const owner = String(agentId || g.agent_id || '').trim();
  const intentLines = [
    `From a capability gap${owner ? ` on ${owner}` : ''}${g.id ? ` (${g.id})` : ''}.`,
    asked ? `The user asked: "${asked}"` : '',
    context ? `Context: ${context}` : '',
    missingTool ? `Needs a tool that does not exist yet: ${missingTool}.` : '',
  ].filter(Boolean);

  const toolStep = missingTool
    ? `2. This needs a tool that does not exist yet (\`${missingTool}\`). Ask Developer to build it, then add it to this skill's tools.`
    : (tools.length
      ? `2. Use \`${tools[0]}\` to get the answer.`
      : '2. Use the selected tools to get the answer.');
  const markdown = [
    `# ${name}`,
    '',
    '## When to use',
    asked ? `Use when the user asks for something like: "${asked}".` : `Use for ${name.toLowerCase()} requests.`,
    '',
    '## Steps',
    '1. Confirm what the user needs and anything missing from the request.',
    toolStep,
    '3. Answer with the result and say where it came from.',
    '',
  ].join('\n');

  return {
    gapId: String(g.id || ''),
    name,
    skillId,
    takenSkillId,
    description,
    intent: intentLines.join('\n'),
    markdown,
    tools,
    missingTool,
  };
}

/** True when the workshop already holds something an operator may not want to lose. */
export function formHasDraft(fields = {}) {
  return ['name', 'description', 'intent', 'markdown'].some((key) => String((fields && fields[key]) || '').trim());
}
