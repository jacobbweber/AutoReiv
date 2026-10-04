/**
 * CARD-522: "Open in Skill Studio" from a capability gap prefills a new skill,
 * and a gap whose tool does not exist yet is steered to Ask Developer.
 */

import { describe, it, expect, vi } from 'vitest';
import {
  buildGapSkillDraft,
  catalogToolNames,
  formHasDraft,
  gapMissingToolNote,
  gapToolIsMissing,
  titleCaseCapability,
} from '../../../src/web/static/modules/studios/skill_studio/gap_prefill.js';
import { SKILL_DESCRIPTION_LIMIT } from '../../../src/web/static/modules/studios/skill_studio/workshop_meta.js';
import { planSkillStudioDeepLink } from '../../../src/web/static/modules/studios/skill_studio.js';
import { capabilityGapRowHtml, openGapInSkillStudio } from '../../../src/web/static/modules/studios/forge/tools.js';

const GAP = {
  id: 'gap_c5d4dcc6af35',
  agent_id: 'autoreiv',
  turn_text: 'Look up TC49 inventory counts',
  identified_capability: 'inventory_lookup',
  suggested_tool_name: 'get_tc49_inventory',
};
const CATALOG = [{ name: 'core', tools: [{ name: 'get_session_info' }, { name: 'read_document_file' }] }];

describe('gap prefill draft [CARD-522]', () => {
  it('fills name, slug, description, intent and a starter runbook from the gap', () => {
    const draft = buildGapSkillDraft(GAP, { toolNames: catalogToolNames(CATALOG), agentId: 'autoreiv' });
    expect(draft.name).toBe('Inventory Lookup');
    expect(draft.skillId).toBe('inventory_lookup');
    expect(draft.description).toBe('Inventory Lookup. Use when the user asks for something like: "Look up TC49 inventory counts"');
    expect(draft.intent).toContain('From a capability gap on autoreiv (gap_c5d4dcc6af35).');
    expect(draft.intent).toContain('The user asked: "Look up TC49 inventory counts"');
    expect(draft.markdown).toContain('# Inventory Lookup');
    expect(draft.markdown).toContain('## Steps');
    expect(draft.markdown).toContain('Look up TC49 inventory counts');
    expect(draft.gapId).toBe('gap_c5d4dcc6af35');
  });

  it('a missing suggested tool ticks nothing and is named in the note and runbook', () => {
    const names = catalogToolNames(CATALOG);
    expect(gapToolIsMissing(GAP, names)).toBe(true);
    const draft = buildGapSkillDraft(GAP, { toolNames: names });
    expect(draft.tools).toEqual([]);
    expect(draft.missingTool).toBe('get_tc49_inventory');
    expect(draft.markdown).toContain('does not exist yet (`get_tc49_inventory`)');
    expect(gapMissingToolNote('get_tc49_inventory')).toBe(
      'This gap needs a tool that does not exist yet (get_tc49_inventory). A skill can only use existing tools: Ask Developer to build it first.',
    );
  });

  it('a suggested tool that exists is ticked', () => {
    const gap = { ...GAP, suggested_tool_name: 'get_session_info' };
    const draft = buildGapSkillDraft(gap, { toolNames: catalogToolNames(CATALOG) });
    expect(draft.tools).toEqual(['get_session_info']);
    expect(draft.missingTool).toBe('');
    expect(gapToolIsMissing(gap, catalogToolNames(CATALOG))).toBe(false);
  });

  it('keeps the description near the soft limit and title-cases without losing capitals', () => {
    const long = buildGapSkillDraft({ ...GAP, turn_text: 'word '.repeat(120) });
    expect(long.description.length).toBeLessThanOrEqual(SKILL_DESCRIPTION_LIMIT);
    expect(titleCaseCapability('TC49 stock-level check')).toBe('TC49 Stock Level Check');
    expect(buildGapSkillDraft({ turn_text: 'Book a meeting room' }).name).toBe('Book a meeting room');
    expect(buildGapSkillDraft({}).name).toBe('New Skill');
  });

  it('never reuses an existing skill id (Save would overwrite it)', () => {
    const draft = buildGapSkillDraft(GAP, { takenIds: new Set(['inventory_lookup', 'inventory_lookup_2']) });
    expect(draft.name).toBe('Inventory Lookup 3');
    expect(draft.skillId).toBe('inventory_lookup_3');
    expect(draft.takenSkillId).toBe('inventory_lookup');
    expect(draft.markdown).toContain('# Inventory Lookup 3');
    expect(buildGapSkillDraft(GAP).takenSkillId).toBe('');
  });

  it('a form with any text counts as a draft not to clobber', () => {
    expect(formHasDraft({ name: '', description: ' ', intent: '', markdown: '' })).toBe(false);
    expect(formHasDraft({ name: 'My edit' })).toBe(true);
    expect(formHasDraft({ markdown: '# Body' })).toBe(true);
  });
});

describe('gap payload reaches Skill Studio [CARD-522]', () => {
  it('Open in Skill Studio passes the gap', () => {
    const openSkillStudio = vi.fn();
    expect(openGapInSkillStudio('autoreiv', { openSkillStudio }, GAP)).toBe(true);
    expect(openSkillStudio).toHaveBeenCalledWith('autoreiv', null, { gap: GAP });
  });

  it('the deep link carries the gap for a new skill only', () => {
    expect(planSkillStudioDeepLink({ agentId: 'autoreiv', gap: GAP }).gap).toBe(GAP);
    expect(planSkillStudioDeepLink({ agentId: 'autoreiv', skillId: 'wiki-knowledge', gap: GAP }).gap).toBeNull();
    expect(planSkillStudioDeepLink({ agentId: 'autoreiv' }).gap).toBeNull();
  });

  it('a missing-tool gap row makes Ask Developer the first, primary button', () => {
    const steered = capabilityGapRowHtml(GAP, { toolMissing: true });
    expect(steered.indexOf('btn-gap-ask-developer')).toBeLessThan(steered.indexOf('btn-gap-open-skill-studio'));
    expect(steered).toContain('data-primary="true"');
    expect(steered).toContain('(not built yet)');
    const plain = capabilityGapRowHtml(GAP);
    expect(plain.indexOf('btn-gap-open-skill-studio')).toBeLessThan(plain.indexOf('btn-gap-ask-developer'));
    expect(plain).toContain('data-primary="false"');
    expect(plain).not.toContain('(not built yet)');
  });
});
