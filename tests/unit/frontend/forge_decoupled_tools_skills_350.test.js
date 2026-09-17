/**
 * CARD-350: Agent Forge: Decouple Tools and Skills UI & Scoping
 * Verifies that tools ("hands") and skills ("brain") are independent peer sections:
 * - Allowed Skills ("Brain") on top (Platform Skills and Custom Pack Skills)
 * - Allowed Tools ("Hands") below with locked platform primitives chips, search bar, and flat tool cards
 * - Skill-to-tool helper affordance (.forge-skill-recommend-tools-btn)
 * - Save logic does not discard checked tools when a skill is unticked
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('CARD-350: Agent Forge Decoupled Tools and Skills', () => {
  it('index.html renders two distinct stacked sections for Allowed Skills and Allowed Tools', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="forgeSkillsSection"');
    expect(html).toContain('Allowed Skills (Runbooks)');
    expect(html).toContain('id="forgeToolsSection"');
    expect(html).toContain('Allowed Tools (Callables)');

    const skillsSectionAt = html.indexOf('id="forgeSkillsSection"');
    const toolsSectionAt = html.indexOf('id="forgeToolsSection"');
    expect(skillsSectionAt).toBeGreaterThan(-1);
    expect(toolsSectionAt).toBeGreaterThan(skillsSectionAt);
  });

  it('index.html contains locked OS Baseline chips and domain tools search bar', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="forgeBaselineBox"');
    expect(html).toContain('id="forgeBaselineGrid"');
    expect(html).toContain('id="forgeToolSearchInput"');
    expect(html).toContain('id="forgeToolsGrid"');
    expect(html).toContain('id="selectAllToolsBtn"');
    expect(html).toContain('id="clearAllToolsBtn"');
  });

  it('forge.js removes nested tool accordions and adds skill-to-tool recommend buttons', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('forge-skill-row');
    expect(forgeJs).toContain('forge-skill-recommend-tools-btn');
    expect(forgeJs).toContain('selectRecommendedToolsForSkill');
    expect(forgeJs).not.toContain('forge-skill-expand');
    expect(forgeJs).not.toContain('forge-skill-tools hidden');
  });

  it('forge.js renders locked platform primitives and flat domain tools in peer grid', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('renderBaselineTools');
    expect(forgeJs).toContain('renderAllowedTools');
    expect(forgeJs).toContain('applyToolChecks');
    expect(forgeJs).toContain('activate_skill');
    expect(forgeJs).toContain('ask_clarification');
    expect(forgeJs).toContain('handoff_to_agent');
    expect(forgeJs).toContain('get_session_info');
    expect(forgeJs).toContain('forge-tool-card');
  });

  it('forge.js save handler does not couple checked tools to ticked skills', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    // Ensure the legacy coupling line is completely absent
    expect(forgeJs).not.toContain('!tickedSkills.has(skillId)');
    expect(forgeJs).not.toContain('cb.dataset.skillId');
  });
});
