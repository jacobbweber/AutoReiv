/**
 * CARD-115: Forge 12-tool allowlist warning is removed.
 * CARD-121: tools checklist is two groups (Pack-owned / Platform), not skill-pack RBAC.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Forge allowlist warning removed [CARD-115]', () => {
  it('does not keep FORGE_ALLOWLIST_WARN_AT or forge_allowlist.js', () => {
    const helperPath = path.join(repoRoot, 'src/web/static/modules/utils/forge_allowlist.js');
    expect(fs.existsSync(helperPath)).toBe(false);

    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).not.toContain('FORGE_ALLOWLIST_WARN_AT');
    expect(forgeJs).not.toContain('forge_allowlist');
    expect(forgeJs).not.toContain('updateAllowlistWarning');
    expect(forgeJs).not.toContain('allowlistWarningVisible');
    expect(forgeJs).not.toContain('formatAllowlistWarning');
  });

  it('does not render #forgeAllowlistWarning in Agent Studio', () => {
    const html = read('src/web/templates/index.html');
    expect(html).not.toContain('forgeAllowlistWarning');
    expect(html).not.toContain('forgeAllowlistWarningText');
  });
});

describe('Forge skill-first capability architecture [CARD-389 / CARD-350]', () => {
  it('configures capabilities via skills without raw tool checklists or master checkboxes', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/runbook.js');
    expect(forgeJs).toContain('renderNestedHomes');
    expect(forgeJs).toContain('forge-skill-row');
    expect(forgeJs).not.toContain('forge-skill-recommend-tools-btn');
    expect(forgeJs).not.toContain('renderAllowedTools');
    expect(forgeJs).toContain('renderAssignedSkills');
    expect(forgeJs).not.toContain('No pack-owned skills yet.');
    expect(forgeJs).toContain("'platform'");
    expect(forgeJs).toContain("'pack'");
    expect(forgeJs).not.toContain('forge-skill-expand');
    expect(forgeJs).not.toContain('forge-skill-tools hidden');
    expect(forgeJs).not.toContain('pack-master-checkbox');
    expect(forgeJs).not.toContain('data-pack=');
    expect(forgeJs).not.toContain('skill_packs');
    expect(forgeJs).not.toContain('RBAC');
    expect(forgeJs).not.toContain('Skill Capabilities');
    expect(forgeJs).not.toContain('Hermes');
  });

  it('Agent Studio renders Assigned Skills and OS Baseline, excising naked tool sections', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="forgeSkillsSection"');
    expect(html).toContain('id="forgeBaselineBox"');
    expect(html).toContain('id="forgeSkillsGrid"');
    expect(html).not.toContain('id="forgePlatformBox"');
    expect(html).not.toContain('id="forgePackBox"');
    expect(html).not.toContain('id="forgeToolsSection"');
    expect(html).not.toContain('Ticked schemas go to the model');
    expect(html).toContain('forgeSystemPrompt');
    expect(html).toContain('forgeStorageEnabled');
    const promptAt = html.indexOf('id="forgeSystemPrompt"');
    const skillsAt = html.indexOf('id="forgeSkillsSection"');
    expect(promptAt).toBeGreaterThan(-1);
    expect(skillsAt).toBeGreaterThan(promptAt);
    expect(html).not.toContain('RBAC');
    expect(html).not.toContain('rbac');
    expect(html).not.toContain('Skill Capabilities');
    expect(html).not.toContain('pack-master-checkbox');
    expect(html).not.toContain('Hermes');
  });

  it('CARD-117 skill ticks remain; inline runbook inspector does not [CARD-419]', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('forgeSkillsGrid');
    expect(html).not.toContain('studioRunbookBody');
    expect(html).not.toContain('id="studioRunbookEditor"');
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('forge-skill-pill');
    expect(forgeJs).not.toContain('forge-skill-checkbox');
    expect(forgeJs).toContain('allowed_skill');
    expect(forgeJs).not.toContain('loadAgentWorkflows');
    expect(forgeJs).not.toContain('studioWorkflowsList');
    expect(forgeJs).not.toContain('Workflow Studio');
  });
});


describe('CARD-118 one Agent Studio', () => {
  it('has no Skills Studio nav and no Forge place name', () => {
    const html = read('src/web/templates/index.html');
    expect(html).not.toContain('Skills Studio');
    expect(html).not.toContain('id="tab-skills"');
    expect(html).not.toContain('id="view-skills"');
    expect(html).not.toContain('Agent Forge');
    expect(html).not.toContain('Agent Forge Studio');
    expect(html).not.toContain('Workflow Studio');
    expect(html).toContain('Agent Studio');
    expect(html).not.toContain('studioRunbookBody');
    expect(html).not.toContain('studioRunbookOpenFactoryBtn');
    expect(html).toContain('Author skill in Skill Studio');
    expect(html).not.toContain('studioNewRunbookBtn');
    expect(html).not.toContain('studioRunbookArchiveBtn');
    expect(html).not.toContain('studioRunbookDeleteBtn');
    expect(html).not.toContain('studioWorkflowsList');
    expect(html).not.toContain('No workflows yet.');
    expect(html).not.toContain('Workflow Studio');
    expect(html).not.toContain('Hermes');
    expect(html).not.toContain('okta-admin');
  });

  it('app.js does not init Skills Studio or name Forge as a place', () => {
    const app = read('src/web/static/app.js');
    expect(app).not.toContain('initSkillsStudio');
    expect(app).not.toContain('Skills Studio');
    expect(app).not.toContain("'Agent Forge'");
    expect(app).toContain("'Agent Studio'");
    expect(app).not.toContain('Hermes');
  });

  it('Agent Studio opens Skill Studio instead of inspecting or saving a runbook [CARD-411, CARD-419]', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/runbook.js');
    expect(forgeJs).not.toContain('studio-runbook-open-btn');
    expect(forgeJs).not.toContain('/api/skills/user-packs');
    expect(forgeJs).not.toContain('studioRunbookOpenFactoryBtn');
    expect(forgeJs).toContain('Open in Skill Studio');
    expect(forgeJs).toContain('openSkillStudio');
    expect(forgeJs).not.toContain('studioRunbookSaveBtn');
    expect(forgeJs).not.toContain("method: 'PUT'");
    expect(forgeJs).not.toContain('Failed to load Agent Forge');
    expect(forgeJs).not.toContain('Agent Forge Studio');
    expect(forgeJs).not.toContain('Hermes');
    expect(forgeJs).toContain('assignedSkillListHtml');
    expect(forgeJs).not.toContain('No pack-owned skills yet.');
    expect(forgeJs).toContain('allowed_skill');
  });
});
