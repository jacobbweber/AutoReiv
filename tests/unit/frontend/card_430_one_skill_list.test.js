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
      packSkills: [{ id: 'sdlc-engineering', name: 'SDLC', description: 'Pack runbook' }],
      archivedSkills: [{ id: 'old-skill', name: 'Old', description: 'Retired' }],
    });

    expect(skillHomeLabel('platform')).toBe('Platform');
    expect(skillHomeLabel('operator')).toBe('Operator');
    expect(skillHomeLabel('pack')).toBe('Pack');
    expect(list).toContain('data-testid="forge-skill-home-label">Platform');
    expect(list).toContain('data-testid="forge-skill-home-label">Operator');
    expect(list).toContain('data-testid="forge-skill-home-label">Pack');
    expect(list).toContain('data-home="platform"');
    expect(list).toContain('data-home="operator"');
    expect(list).toContain('data-home="pack"');
    expect(list).toContain('data-testid="forge-skill-pill"');
    expect(list).toContain('Open in Skill Studio');
    expect(list.indexOf('data-home="platform"')).toBeLessThan(list.indexOf('data-home="operator"'));
    expect(list.indexOf('data-home="operator"')).toBeLessThan(list.indexOf('data-home="pack"'));
    expect(list.indexOf('data-skill-id="old-skill"')).toBeGreaterThan(list.indexOf('data-home="pack"'));
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
    expect(runbook).not.toContain('/api/skills/user-packs');
    const list = assignedSkillListHtml({
      packSkills: [{ id: 'sdlc-engineering', name: 'SDLC' }],
    });
    expect(list).toContain('data-home="pack"');
    expect(list).not.toContain('$DATA_DIR');
  });

  it('keeps the seven baseline chips and the Direct caption [REQ-430-004]', () => {
    expect(html).toContain('id="forgeBaselineGrid"');
    expect(html).toContain('Direct mounts none');
    for (const name of [
      'activate_skill',
      'ask_clarification',
      'handoff_to_agent',
      'lookup_agents',
      'get_session_info',
      'recall_agent_memory',
      'memorize_fact',
    ]) {
      expect(toolsJs).toContain(name);
    }
    expect(html).toContain('id="forgeMcpServersCard"');
    expect(html).toContain('id="forgeCredentialGrantsCard"');
  });

  it('omits a per-home empty box when that home has no skills [REQ-430-005]', () => {
    const operatorOnly = assignedSkillListHtml({
      operatorSkills: [{ id: 'dock-notes', name: 'Dock Notes' }],
    });
    expect(operatorOnly).toContain('data-home="operator"');
    expect(operatorOnly).not.toContain('data-home="platform"');
    expect(operatorOnly).not.toContain('data-home="pack"');
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
    expect(html).not.toContain('id="forgePackBox"');
    expect(html).not.toContain('id="forgePackBoxTitle"');
    expect(html).not.toContain('id="forgeOperatorSkillsGrid"');
    expect(html).not.toContain('id="forgeRunbooksGrid"');
    expect(html).not.toContain('Platform Skills & Tools');
    expect(html).not.toContain('Custom Agent Pack Skills & Tools');
    expect(html).not.toContain('Toggle a platform skill');
    expect(html).not.toContain('Dedicated runbooks owned by this agent pack');
    expect(runbook).not.toContain('renderPlatformSkills');
    expect(runbook).not.toContain('renderOperatorSkills');
    expect(runbook).not.toContain('renderPackSkills');
    expect(runbook).not.toContain('No pack-owned skills yet.');
  });
});
