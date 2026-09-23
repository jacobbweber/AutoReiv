/**
 * CARD-390 put ADR-0054 lint chrome on the Agent Studio runbook inspector.
 * CARD-419 removed that inspector. Agent Studio no longer validates a runbook inline.
 * Skill Studio remains the skill view and edit surface.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio no longer hosts the inline runbook linter [CARD-419]', () => {
  const html = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/runbook.js');

  it('index.html has no Agent Studio runbook validate chrome', () => {
    expect(html).not.toContain('id="studioRunbookEditor"');
    expect(html).not.toContain('id="studioRunbookValidateBtn"');
    expect(html).not.toContain('id="studioRunbookLintStatus"');
    expect(html).not.toContain('id="studioRunbookCharCount"');
  });

  it('forge does not lint or scaffold a runbook body', () => {
    expect(forgeJs).not.toContain('CANONICAL_RUNBOOK_TEMPLATE');
    expect(forgeJs).not.toContain('updateRunbookCharCount');
    expect(forgeJs).not.toContain('renderRunbookLintReport');
    expect(forgeJs).not.toContain('validateActiveRunbook');
    expect(forgeJs).not.toContain("fetch('/api/skills/lint'");
    expect(forgeJs).not.toContain("method: 'PUT'");
    expect(forgeJs).toContain('Open in Skill Studio');
  });

  it('[REQ-390-SINGLE-LEVER] Standalone Skills Studio (#view-skills) remains retired', () => {
    expect(html).not.toContain('id="tab-skills"');
    expect(html).not.toContain('id="view-skills"');
    expect(forgeJs).not.toContain('initSkillsStudio');
  });
});