/**
 * CARD-411 REQ-411-003: Forge is not a skill write path. Skill Studio owns structured editing (Factory retired, CARD-496).
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Forge vs Factory skill lever [CARD-411]', () => {
  const html = read('src/web/templates/index.html');
  const runbook = read('src/web/static/modules/studios/forge/runbook.js');
  const factory = read('src/web/static/modules/studios/skill_studio.js')
    + read('src/web/static/modules/studios/skill_studio/workshop_meta.js')
    + read('src/web/static/modules/studios/skill_studio/skill_scope.js');

  it('Agent Studio does not inspect runbooks inline and opens Skill Studio [CARD-419]', () => {
    expect(html).not.toContain('id="studioRunbookEditor"');
    expect(html).not.toContain('id="studioRunbookOpenFactoryBtn"');
    expect(html).toContain('Author skill in Skill Studio');
    expect(runbook).toContain('Open in Skill Studio');
    expect(html).not.toContain('Open in Factory Workshop');
    expect(html).not.toContain('id="studioRunbookSaveBtn"');
    expect(html).not.toContain('id="studioRunbookArchiveBtn"');
    expect(html).not.toContain('id="studioRunbookDeleteBtn"');
    expect(html).not.toContain('id="studioNewRunbookBtn"');
    expect(runbook).not.toContain('studio-runbook-open-btn');
    expect(runbook).not.toContain('studioRunbookOpenFactoryBtn');
    expect(runbook).toContain('openSkillStudio');
    expect(runbook).not.toContain('openFactoryWorkshop');
    expect(runbook).not.toContain("method: 'PUT'");
    expect(runbook).not.toContain("'/archive'");
    expect(runbook).not.toContain('/unarchive');
    expect(runbook).not.toContain('studioRunbookSaveBtn');
  });

  it('Factory workshop edits safety and required tools and writes tier pack [CARD-429]', () => {
    expect(html).not.toContain('id="factorySkillTierSelect"');
    expect(html).not.toContain('data-testid="factory-skill-tier-advanced"');
    expect(html).toContain('id="factorySkillSafetyHitl"');
    expect(html).toContain('id="factoryRequiredToolsChips"');
    expect(html).toContain('id="factoryExistingSkillSelect"');
    expect(factory).toContain('requires_tools');
    expect(factory).toContain('applyWorkshopMetadata');
    expect(factory).toContain('/api/agent_training_factory/skills/');
    expect(factory).toContain('syncFrontmatter');
    expect(factory).toContain("tier: 'pack'");
  });

  it('save writes tier pack and ignores a leftover tier select [CARD-429]', async () => {
    const { createSkillWorkshop } = await import(
      '../../../src/web/static/modules/studios/skill_studio/workshop_meta.js'
    );
    const workshop = createSkillWorkshop({
      showToast: () => {},
      getCapabilities: () => [],
      getSelectedTools: () => new Set(['wiki_note_read']),
      setSelectedTools: () => {},
      setIdentityLocked: () => {},
      renderCapabilities: () => {},
      updateSelectedToolBadge: () => {},
      elements: () => ({
        factorySkillNameInput: { value: 'Backup' },
        factorySkillTriggerInput: { value: 'Backup a host' },
        factorySkillTierSelect: { value: 'platform' },
        factorySkillSafetyReadOnly: { checked: false },
        factorySkillSafetyHitl: { checked: true },
        factorySkillSafetyUntrusted: { checked: false },
      }),
    });
    const fields = workshop.workshopFields();
    expect(fields.tier).toBe('pack');
    expect(fields.tier).not.toBe('platform');
    expect(fields.requires_tools).toEqual(['wiki_note_read']);
  });
});
