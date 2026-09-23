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
    expect(html).not.toContain('id="forgePackBox"');
    expect(html).not.toContain('id="forgeFleetBox"');
    expect(html).not.toContain('Also ticked');
  });

  it('forge.js removes "Also ticked" and renders one skill list [CARD-430]', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/runbook.js');
    expect(forgeJs).toContain('renderNestedHomes');
    expect(forgeJs).toContain('renderAssignedSkills');
    expect(forgeJs).not.toContain('renderPlatformSkills');
    expect(forgeJs).not.toContain('renderPackSkills');
    expect(forgeJs).not.toContain('renderFleetSkills');
    expect(forgeJs).not.toContain('packOwnedIds');
    expect(forgeJs).not.toContain('Also ticked');
    expect(forgeJs).not.toContain('ungrouped_pack_tools');
  });

  it('renders required platform tools with REQUIRED badge and disabled input [CARD-330]', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/runbook.js');
    expect(forgeJs).toContain('required_platform');
    expect(forgeJs).toContain('REQUIRED');
    expect(forgeJs).toContain('INCLUDES REQUIRED TOOLS');
  });

  it('index.html contains AutoReiv OS Baseline section [CARD-330]', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="forgeBaselineBox"');
    expect(html).toContain('id="forgeBaselineGrid"');
    expect(html).toContain('AutoReiv OS Baseline');
  });

  it('renders AutoReiv OS Baseline tools with uncheckable references [CARD-330]', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/tools.js');
    expect(forgeJs).toContain('renderBaselineTools');
    expect(forgeJs).toContain('baselineToolCardHtml');
    expect(forgeJs).toContain('OS BASELINE');
  });

  it('shows seven required tools and says Direct mounts none [CARD-429]', () => {
    const html = read('src/web/templates/index.html');
    const toolsJs = read('src/web/static/modules/studios/forge/tools.js');
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
    expect(html).toContain('Direct mounts none');
    expect(html).not.toContain('enforced for every agent');
    expect(toolsJs).not.toContain('for all agents');
  });
});

