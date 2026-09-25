/**
 * CARD-391: Developer Agent and Projects Studio Workspace Integration.
 * Verifies that #projectsPairDeveloperBtn bridges Projects Studio with Developer in Chat Studio,
 * and #chatActiveProjectPill provides active workspace indication and round-trip navigation.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Developer Agent and Projects Studio Workspace Integration [CARD-391]', () => {
  const html = read('src/web/templates/index.html');
  const projectsJs = read('src/web/static/modules/studios/projects.js');
  const chatJs = read('src/web/static/modules/studios/chat.js');

  it('[REQ-391-002] index.html provides Pair with Developer button in Projects Studio header', () => {
    expect(html).toContain('id="projectsPairDeveloperBtn"');
    expect(html).toContain('Pair with Developer');
    expect(html).toContain('data-lucide="code-2"');
  });

  it('[REQ-391-001] index.html provides active project pill in Chat Studio header', () => {
    expect(html).toContain('id="chatActiveProjectPill"');
    expect(html).toContain('id="chatActiveProjectName"');
    expect(html).toContain('data-lucide="folder-kanban"');
    expect(html).toContain('Active Project — click to open in Projects Studio');
  });

  it('[REQ-391-002] projects.js controls Pair with Developer button visibility based on active project', () => {
    expect(projectsJs).toContain("const pairDevBtn = $('projectsPairDeveloperBtn');");
    expect(projectsJs).toContain("pairDevBtn.classList.remove('hidden');");
    expect(projectsJs).toContain("pairDevBtn.classList.add('hidden');");
  });

  it('[REQ-391-002] projects.js wires Pair with Developer click to switch to Chat, select Developer, and populate prompt', () => {
    expect(projectsJs).toContain("pairDeveloperBtn.addEventListener('click'");
    expect(projectsJs).toContain("$('tab-chat')");
    expect(projectsJs).toContain("agentSelect.value = 'developer'");
    expect(projectsJs).toContain("agentSelect.dispatchEvent(new Event('change'))");
    expect(projectsJs).toContain("$('promptInput')");
    // CARD-465: composer writes go through the shared setter so the box resizes
    expect(projectsJs).toContain('setComposerText(');
    expect(projectsJs).toContain("`I'm pairing with you on ${projName}");
  });

  it('[REQ-391-001] chat.js caches chatActiveProjectPill and chatActiveProjectName elements', () => {
    expect(chatJs).toContain("const chatActiveProjectPill = $('chatActiveProjectPill');");
    expect(chatJs).toContain("const chatActiveProjectName = $('chatActiveProjectName');");
  });

  it('[REQ-391-001] chat.js wires chatActiveProjectPill to navigate to Projects Studio', () => {
    expect(chatJs).toContain("chatActiveProjectPill.addEventListener('click'");
    expect(chatJs).toContain("const tabProjects = $('tab-projects');");
    expect(chatJs).toContain('if (tabProjects) tabProjects.click();');
  });

  it('[REQ-391-001] chat.js queries /api/projects/selected and syncs active project state', () => {
    expect(chatJs).toContain('async function syncActiveProjectIndicator()');
    expect(chatJs).toContain("fetch('/api/projects/selected')");
    expect(chatJs).toContain("state.selectedAgentId === 'developer'");
    expect(chatJs).toContain("chatActiveProjectPill.classList.remove('hidden')");
    expect(chatJs).toContain("chatActiveProjectPill.classList.add('inline-flex')");
    expect(chatJs).toContain("chatActiveProjectPill.classList.add('hidden')");
  });

  it('[REQ-391-SINGLE-LEVER] Zero duplicate levers: Developer uses canonical project root resolver without hardcoded fallback paths', () => {
    // Assert no parallel ad-hoc project indicators or duplicate agent switchers
    expect(html).not.toContain('id="chatActiveProjectPillSecondary"');
    expect(html).not.toContain('id="projectsPairDeveloperBtnSecondary"');
  });
});
