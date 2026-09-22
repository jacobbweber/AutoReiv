/**
 * CARD-411 REQ-411-003: Forge is not a skill write path. Factory owns structured editing.
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
  const factory = read('src/web/static/modules/studios/factory.js')
    + read('src/web/static/modules/studios/factory/workshop_meta.js')
    + read('src/web/static/modules/studios/factory/skill_scope.js');

  it('Forge inspector is read-only and opens Skill Studio', () => {
    expect(html).toContain('id="studioRunbookOpenFactoryBtn"');
    expect(html).toContain('Open in Skill Studio');
    expect(html).not.toContain('Open in Factory Workshop');
    expect(html).toContain('id="studioRunbookTier"');
    expect(html).toContain('id="studioRunbookSafety"');
    expect(html).toContain('id="studioRunbookTools"');
    expect(html).toContain('readonly');
    expect(html).not.toContain('id="studioRunbookSaveBtn"');
    expect(html).not.toContain('id="studioRunbookArchiveBtn"');
    expect(html).not.toContain('id="studioRunbookDeleteBtn"');
    expect(html).not.toContain('id="studioNewRunbookBtn"');
    expect(runbook).toContain('studioRunbookOpenFactoryBtn');
    expect(runbook).toContain('openSkillStudio');
    expect(runbook).not.toContain('openFactoryWorkshop');
    expect(runbook).not.toContain("method: 'PUT'");
    expect(runbook).not.toContain("'/archive'");
    expect(runbook).not.toContain('/unarchive');
    expect(runbook).not.toContain('studioRunbookSaveBtn');
  });

  it('Factory workshop edits tier, safety, and required tools', () => {
    expect(html).toContain('id="factorySkillTierSelect"');
    expect(html).toContain('id="factorySkillSafetyHitl"');
    expect(html).toContain('id="factoryRequiredToolsChips"');
    expect(html).toContain('id="factoryExistingSkillSelect"');
    expect(html).toContain('data-testid="factory-skill-tier-advanced"');
    expect(factory).toContain('requires_tools');
    expect(factory).toContain('applyWorkshopMetadata');
    expect(factory).toContain('/api/agent_training_factory/skills/');
    expect(factory).toContain('syncFrontmatter');
  });
});
