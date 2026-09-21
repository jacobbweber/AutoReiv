/**
 * CARD-389: Uniform Skill-First Architecture and Agent Forge Realignment
 * Verifies that naked tools are excised from Agent Forge and capabilities are configured strictly via skills:
 * - Assigned Skills on top with declared tools rendered as chips
 * - Raw Allowed Tools section (#forgeToolsSection) is completely excised
 * - Zero naked tool checkboxes
 * - Save handler derives allowed tools from checked skills + storage
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('CARD-389: Agent Forge Uniform Skill-First Architecture', () => {
  it('index.html renders Assigned Skills section and completely excises raw forgeToolsSection', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="forgeSkillsSection"');
    expect(html).toContain('Assigned Skills');
    expect(html).not.toContain('id="forgeToolsSection"');
    expect(html).not.toContain('Allowed Tools (Callables)');
  });

  it('index.html contains locked OS Baseline chips and no raw domain tool grids or search bars', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="forgeBaselineBox"');
    expect(html).toContain('id="forgeBaselineGrid"');
    expect(html).not.toContain('id="forgeToolSearchInput"');
    expect(html).not.toContain('id="forgeToolsGrid"');
    expect(html).not.toContain('id="selectAllToolsBtn"');
    expect(html).not.toContain('id="clearAllToolsBtn"');
  });

  it('forge.js renders skill rows with declared tool chips and excises naked tool buttons', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('forge-skill-row');
    expect(forgeJs).toContain('declared tool');
    expect(forgeJs).not.toContain('forge-skill-recommend-tools-btn');
    expect(forgeJs).not.toContain('selectRecommendedToolsForSkill');
    expect(forgeJs).not.toContain('forge-tool-checkbox');
  });

  it('forge.js renders locked platform primitives and excises renderAllowedTools', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('renderBaselineTools');
    expect(forgeJs).not.toContain('renderAllowedTools');
    expect(forgeJs).not.toContain('applyToolChecks');
    expect(forgeJs).toContain('activate_skill');
    expect(forgeJs).toContain('ask_clarification');
    expect(forgeJs).toContain('handoff_to_agent');
    expect(forgeJs).toContain('lookup_agents');
    expect(forgeJs).toContain('get_session_info');
  });

  it('forge.js save handler derives tools strictly from checked skills', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('derivedTools');
    expect(forgeJs).toContain('sqlite-storage');
  });
});
