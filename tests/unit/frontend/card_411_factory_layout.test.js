/**
 * CARD-411 UX: Factory column layout — assigned skills in col 1, picker in col 2.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Factory layout UX [CARD-411]', () => {
  const html = read('src/web/templates/index.html');
  const factoryJs = read('src/web/static/modules/studios/factory.js');
  const skillScope = read('src/web/static/modules/studios/factory/skill_scope.js');

  const agentCardStart = html.indexOf('id="factoryIntakeAgentCard"');
  const col2Start = html.indexOf('2. Skill Workshop');
  const col3Start = html.indexOf('3. Capabilities');
  const factoryEnd = html.indexOf('id="artifactModal"');
  const agentCard = html.slice(agentCardStart, col2Start);
  const col2 = html.slice(col2Start, col3Start);
  const col3 = html.slice(col3Start, factoryEnd > col3Start ? factoryEnd : col3Start + 8000);

  it('puts Assigned Skills under Role Persona in column 1', () => {
    expect(agentCard).toContain('id="factoryAgentPromptInput"');
    expect(agentCard).toContain('id="factoryCurrentSkillsList"');
    expect(agentCard).toContain('id="factoryAssignedSkillsCount"');
    expect(agentCard).toContain('data-testid="factory-assigned-skills"');
    expect(agentCard.indexOf('factoryAgentPromptInput')).toBeLessThan(
      agentCard.indexOf('factoryCurrentSkillsList'),
    );
    expect(col2).not.toContain('id="factoryCurrentSkillsList"');
    expect(col2).not.toContain('Assigned Skills (Active on Agent)');
  });

  it('column 2 is skill workshop with existing-skill picker and New Skill', () => {
    expect(col2).toContain('id="factoryExistingSkillSelect"');
    expect(col2).toContain('id="factoryExistingSkillFilter"');
    expect(col2).toContain('id="factoryNewSkillFormBtn"');
    expect(col2).toContain('data-testid="factory-existing-skill"');
    expect(col2).toContain('+ New Skill');
    expect(col2).toContain('id="factorySkillNameInput"');
    expect(col2).toContain('id="factorySkillMarkdownEditor"');
    expect(col2).toContain('id="factoryRequiredToolsChips"');
    expect(col2).toContain('id="factorySourceContextInput"');
    expect(col2.indexOf('factorySourceContextInput')).toBeLessThan(
      col2.indexOf('factorySkillMarkdownEditor'),
    );
  });

  it('column 3 stays tools and grounding only', () => {
    expect(col3).toContain('id="factoryCapabilitiesContainer"');
    expect(col3).not.toContain('id="factorySourceContextInput"');
    expect(col3).not.toContain('Assigned Skills');
    expect(col3).not.toContain('factoryExistingSkillSelect');
  });

  it('has no skill tier dropdown and documents safety flags [CARD-429]', () => {
    expect(html).not.toContain('data-testid="factory-skill-tier-advanced"');
    expect(html).not.toContain('Advanced: Tier (legacy taxonomy)');
    expect(html).not.toContain('id="factorySkillTierSelect"');
    expect(html).toContain('Pause for human approval before sensitive work.');
    expect(html).toContain('lint/contract flag, not a hard kernel lock');
    expect(html).toContain('Requires approval must also be on (linter enforces that).');
  });

  it('picker options come from skills the loader can open', async () => {
    const { indexListedSkills } = await import(
      '../../../src/web/static/modules/studios/factory/skill_scope.js'
    );
    const options = indexListedSkills(
      [
        { id: 'coordination', name: 'Agent Coordination', source: 'seed' },
        { id: 'wiki-knowledge', name: 'Wiki Knowledge', source: 'platform' },
      ],
      ['coordination', 'missing-skill'],
    );
    expect(options.map((row) => row.id)).toEqual(['coordination', 'wiki-knowledge']);
    expect(options[0].source).toBe('assigned');
    expect(options.some((row) => row.id === 'missing-skill')).toBe(false);
    const scope = read('src/web/static/modules/studios/factory/skill_scope.js');
    expect(scope).toContain('/api/agent_training_factory/skills');
  });

  it('assigned skills are display-only; picker loads the workshop', () => {
    expect(skillScope).toContain('Pinned to this agent');
    expect(skillScope).not.toContain('factory-skill-open-btn');
    expect(skillScope).toContain('onLoadSkill');
    const skillStudio = read('src/web/static/modules/studios/skill_studio.js');
    expect(skillStudio).toContain('createSkillScopeUI');
    expect(skillStudio).toContain('refreshEditableSkillOptions');
    expect(factoryJs).not.toContain('/api/agent_training_factory/scaffold/save');
  });
});

describe('mergeEditableSkillOptions [CARD-411]', () => {
  it('merges assigned, platform, pack, and user packs without duplicates', async () => {
    const { mergeEditableSkillOptions } = await import(
      '../../../src/web/static/modules/studios/factory/skill_scope.js'
    );
    const merged = mergeEditableSkillOptions({
      assignedIds: ['wiki-knowledge', 'custom-skill'],
      platformSkills: [{ id: 'wiki-knowledge', name: 'Wiki Knowledge' }],
      packOwnedIds: ['pack-skill'],
      userPacks: [{ id: 'custom-skill', name: 'Custom Skill' }, { id: 'user-only', name: 'User Only' }],
    });
    const ids = merged.map((o) => o.id);
    expect(ids).toEqual(['custom-skill', 'wiki-knowledge', 'pack-skill', 'user-only']);
    expect(merged.find((o) => o.id === 'wiki-knowledge').name).toBe('Wiki Knowledge');
    expect(merged.find((o) => o.id === 'wiki-knowledge').source).toBe('assigned');
    expect(merged.find((o) => o.id === 'user-only').source).toBe('user');
  });
});
