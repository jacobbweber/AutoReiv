/**
 * CARD-430: Agent Studio Assigned Skills is one list.
 * REQ-430-001..005
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { assignedSkillListHtml, skillHomeLabel } from '../../../src/web/static/modules/studios/forge/runbook.js';
import { toggleSkillInAllowlist } from '../../../src/web/static/modules/studios/forge/skill_pills.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio one skill list [CARD-430]', () => {
  const html = read('src/web/templates/index.html');
  const runbook = read('src/web/static/modules/studios/forge/runbook.js');
  const toolsJs = read('src/web/static/modules/studios/forge/tools.js');

  it('lists platform, operator, and pack skills in one list with a home label [REQ-430-001]', () => {
    const list = assignedSkillListHtml({
      platformSkills: [{ id: 'wiki', name: 'Wiki', description: 'Vault' }],
      operatorSkills: [{ id: 'dock-notes', name: 'Dock Notes', description: 'Store' }],
      ownSkillRows: [{ id: 'sdlc-engineering', name: 'SDLC', description: 'Pack runbook' }],
      archivedSkills: [{ id: 'old-skill', name: 'Old', description: 'Retired' }],
    });

    expect(skillHomeLabel('platform')).toBe('Platform');
    expect(skillHomeLabel('operator')).toBe('Operator');
    expect(skillHomeLabel('agent')).toBe('Agent');
    expect(list).toContain('data-testid="forge-skill-home-label">Platform');
    expect(list).toContain('data-testid="forge-skill-home-label">Operator');
    expect(list).toContain('data-testid="forge-skill-home-label">Agent');
    expect(list).toContain('data-home="platform"');
    expect(list).toContain('data-home="operator"');
    expect(list).toContain('data-home="agent"');
    expect(list).toContain('data-testid="forge-skill-pill"');
    expect(list).toContain('Open in Skill Studio');
    expect(list.indexOf('data-home="platform"')).toBeLessThan(list.indexOf('data-home="operator"'));
    expect(list.indexOf('data-home="operator"')).toBeLessThan(list.indexOf('data-home="agent"'));
    expect(list.indexOf('data-skill-id="old-skill"')).toBeGreaterThan(list.indexOf('data-home="agent"'));
    expect(list).toContain('data-testid="forge-skill-archived"');
    expect(list).toContain('>Archived<');
    expect(list).not.toContain('<h4');
    expect(list.match(/data-testid="forge-assigned-skills"/g)).toBeNull();

    expect(html).toContain('id="forgeSkillsGrid"');
    expect(html).toContain('data-testid="forge-assigned-skills"');
    expect(html.match(/id="forgeSkillsGrid"/g)).toHaveLength(1);
    expect(runbook).toContain('renderAssignedSkills');
    expect(runbook).toContain('assignedSkillListHtml');
  });

  it('keeps the allowlist toggle on data-home and does not open an editor [REQ-430-002]', () => {
    const list = assignedSkillListHtml({
      operatorSkills: [{ id: 'dock-notes', name: 'Dock Notes' }],
    });
    expect(list).toContain('data-home="operator"');
    expect(list).toContain('role="switch"');
    const turnedOn = toggleSkillInAllowlist(['wiki'], 'dock-notes');
    expect(turnedOn.allowed_skill).toEqual(['wiki', 'dock-notes']);
    expect(turnedOn.opensEditor).toBe(false);
    expect(runbook).toContain('applySkillPillToggle');
    expect(runbook).toContain("skillRowHtml(skill, 'operator', false)");
  });

  it('does not copy skill files between homes [REQ-430-003]', () => {
    expect(runbook).not.toContain('copytree');
    expect(runbook).not.toContain('writeFile');
    expect(runbook).not.toContain('/api/skills/user-skills');
    const list = assignedSkillListHtml({
      ownSkillRows: [{ id: 'sdlc-engineering', name: 'SDLC' }],
    });
    expect(list).toContain('data-home="agent"');
    expect(list).not.toContain('$DATA_DIR');
  });

  it('keeps the six baseline chips and the Direct caption [REQ-430-004, CARD-578]', () => {
    expect(html).toContain('id="forgeBaselineGrid"');
    expect(html).toContain('Direct mounts none');
    for (const name of [
      'ask_clarification',
      'get_session_info',
      'recall_agent_memory',
      'memorize_fact',
    ]) {
      expect(toolsJs).toContain(name);
    }
    expect(toolsJs).not.toContain('activate_skill');
    expect(html).toContain('id="forgeMcpServersCard"');
    expect(html).toContain('id="forgeCredentialGrantsCard"');
  });

  it('omits a per-home empty box when that home has no skills [REQ-430-005]', () => {
    const operatorOnly = assignedSkillListHtml({
      operatorSkills: [{ id: 'dock-notes', name: 'Dock Notes' }],
    });
    expect(operatorOnly).toContain('data-home="operator"');
    expect(operatorOnly).not.toContain('data-home="platform"');
    expect(operatorOnly).not.toContain('data-home="agent"');
    expect(operatorOnly).not.toContain('No platform runbooks');
    expect(operatorOnly).not.toContain('No operator skills');
    expect(operatorOnly).not.toContain('No pack-owned skills');
    expect(operatorOnly).not.toContain('forge-skills-empty');

    const empty = assignedSkillListHtml({});
    expect(empty).toContain('data-testid="forge-skills-empty"');
    expect(empty).not.toContain('<h4');
    expect(empty).not.toContain('Platform Skills & Tools');
    expect(empty).not.toContain('Operator skills');
    expect(empty).not.toContain('Custom Agent Pack');

    expect(html).not.toContain('id="forgePlatformBox"');
    expect(html).not.toContain('id="forgeOperatorBox"');
    expect(html).not.toContain('id="forgeSkillBox"');
    expect(html).not.toContain('id="forgeSkillBoxTitle"');
    expect(html).not.toContain('id="forgeOperatorSkillsGrid"');
    expect(html).not.toContain('id="forgeRunbooksGrid"');
    expect(html).not.toContain('Platform Skills & Tools');
    expect(html).not.toContain('Custom Agent Pack Skills & Tools');
    expect(html).not.toContain('Toggle a platform skill');
    expect(html).not.toContain('Dedicated runbooks owned by this agent pack');
    expect(runbook).not.toContain('renderPlatformSkills');
    expect(runbook).not.toContain('renderOperatorSkills');
    expect(runbook).not.toContain('renderOwnSkills');
    expect(runbook).not.toContain('No pack-owned skills yet.');
  });
});
