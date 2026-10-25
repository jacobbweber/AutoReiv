/**
 * CARD-391 / CARD-740: Projects Studio and Chat Studio Active Project Single Lever.
 * Verifies that #projectsPairDeveloperBtn is retired and Set Active + #chatActiveProjectPill
 * provides active workspace indication and round-trip navigation.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Projects Studio and Chat Active Project Single Lever [CARD-391, CARD-740]', () => {
  const html = read('src/web/templates/index.html');
  const wikiProjectsHtml = read('src/web/templates/partials/wiki_projects.html');
  const projectsJs = read('src/web/static/modules/studios/projects.js');
  const chatJs = read('src/web/static/modules/studios/chat.js');

  it('[CARD-740] Projects Studio header retires redundant Pair with Developer button', () => {
    expect(html).not.toContain('id="projectsPairDeveloperBtn"');
    expect(html).not.toContain('Pair with Developer');
    expect(wikiProjectsHtml).not.toContain('id="projectsPairDeveloperBtn"');
    expect(wikiProjectsHtml).not.toContain('Pair with Developer');
    expect(wikiProjectsHtml).toContain('id="projectsActiveName"');
    expect(wikiProjectsHtml).toContain('id="projectsActiveBadge"');
  });

  it('[REQ-391-001] index.html provides active project pill in Chat Studio header', () => {
    expect(html).toContain('id="chatActiveProjectPill"');
    expect(html).toContain('id="chatActiveProjectName"');
    expect(html).toContain('data-lucide="folder-kanban"');
    expect(html).toContain('Active Project — click to open in Projects Studio');
  });

  it('[CARD-740] projects.js updates active project badge without Pair with Developer button or composer prefill', () => {
    expect(projectsJs).toContain("const activeName = $('projectsActiveName');");
    expect(projectsJs).toContain("const activeBadge = $('projectsActiveBadge');");
    expect(projectsJs).not.toContain('projectsPairDeveloperBtn');
    expect(projectsJs).not.toContain('pairDevBtn');
    expect(projectsJs).not.toContain('pairDeveloperBtn');
    expect(projectsJs).not.toContain("I'm pairing with you on");
    expect(projectsJs).not.toContain('setComposerText');
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
    expect(chatJs).toContain("state.selectedAgentId === 'autoreiv'");
    expect(chatJs).toContain("chatActiveProjectPill.classList.remove('hidden')");
    expect(chatJs).toContain("chatActiveProjectPill.classList.add('inline-flex')");
    expect(chatJs).toContain("chatActiveProjectPill.classList.add('hidden')");
  });

  it('[REQ-391-SINGLE-LEVER] Zero duplicate levers: Set Active + chatActiveProjectPill is the single project binding path', () => {
    const appJs = read('src/web/static/app.js');
    expect(html).not.toContain('id="chatActiveProjectPillSecondary"');
    expect(html).not.toContain('id="projectsPairDeveloperBtn"');
    expect(html).not.toContain('id="projectsPairDeveloperBtnSecondary"');
    expect(appJs).toContain('chatCtrl.syncActiveProjectIndicator()');
  });
});

