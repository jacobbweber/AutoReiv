/**
 * CARD-127: Platform skills and Agent Pack Studio layout.
 * Top-down hierarchy: Platform Skills & Tools, then Agent Pack Skills & Tools. Zero "Also ticked" stray tools.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio Platform and Pack hierarchy [CARD-127]', () => {
  it('index.html has one Assigned Skills list and no fleet box [CARD-430]', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="forgeSkillsGrid"');
    expect(html).toContain('data-testid="forge-assigned-skills"');
    expect(html).not.toContain('id="forgePlatformBox"');
    expect(html).not.toContain('id="forgeSkillBox"');
    expect(html).not.toContain('id="forgeFleetBox"');
    expect(html).not.toContain('Also ticked');
  });

  it('forge.js removes "Also ticked" and renders one skill list [CARD-430]', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/runbook.js');
    expect(forgeJs).toContain('renderNestedHomes');
    expect(forgeJs).toContain('renderAssignedSkills');
    expect(forgeJs).not.toContain('renderPlatformSkills');
    expect(forgeJs).not.toContain('renderOwnSkills');
    expect(forgeJs).not.toContain('renderFleetSkills');
    expect(forgeJs).not.toContain('ownedSkillIds');
    expect(forgeJs).not.toContain('Also ticked');
    expect(forgeJs).not.toContain('ungrouped_skill_tool_list');
  });

  it('skill rows no longer show REQUIRED tool badges [CARD-330, CARD-656]', () => {
    const runbookJs = read('src/web/static/modules/studios/forge/runbook.js');
    expect(runbookJs).not.toContain('INCLUDES REQUIRED TOOLS');
    expect(runbookJs).not.toContain('declared tool');
  });

  it('index.html contains AutoReiv OS Baseline section [CARD-330]', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="forgeBaselineBox"');
    expect(html).toContain('id="forgeBaselineGrid"');
    expect(html).toContain('Always-on baseline');
  });

  it('renders AutoReiv OS Baseline tools with uncheckable references [CARD-330]', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/tools.js');
    expect(forgeJs).toContain('renderBaselineTools');
    expect(forgeJs).toContain('baselineSummaryHtml'); // CARD-656: one quiet line, not chips
  });

  it('shows six required tools and says Direct mounts none [CARD-429, CARD-578]', () => {
    const html = read('src/web/templates/index.html');
    const toolsJs = read('src/web/static/modules/studios/forge/tools.js');
    for (const name of [
      'ask_clarification',
      'get_session_info',
      'recall_agent_memory',
      'memorize_fact',
    ]) {
      expect(toolsJs).toContain(name);
    }
    expect(toolsJs).not.toContain('activate_skill');
    expect(toolsJs).toContain('Always on'); // CARD-656 replaces the chip caption
    expect(html).not.toContain('enforced for every agent');
    expect(toolsJs).not.toContain('for all agents');
  });
});

