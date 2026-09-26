/**
 * CARD-418: Skill Studio dock open and Forge deep-link hydrate.
 * REQ-418-001..004
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { DOCK_LAUNCHERS, VIEW_BY_TAB } from '../../../src/web/static/modules/ui/agent-desktop.js';
import { openWindow } from '../../../src/web/static/modules/ui/agent_desktop/window.js';
import { planSkillStudioDeepLink, SKILL_STUDIO_LABEL, SKILL_STUDIO_TAB } from '../../../src/web/static/modules/studios/skill_studio.js';
import { applyLoadedSkillView } from '../../../src/web/static/modules/studios/skill_studio/workshop_meta.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

function sliceView(html, startId, endId) {
  const start = html.indexOf(`id="${startId}"`);
  const end = html.indexOf(`id="${endId}"`);
  expect(start).toBeGreaterThan(-1);
  expect(end).toBeGreaterThan(start);
  return html.slice(start, end);
}

describe('Skill Studio dock and deep link [CARD-418]', () => {
  const html = read('src/web/templates/index.html');
  const skillView = sliceView(html, 'view-skill-studio', 'artifactModal');

  it('dock open presents Skill Studio without the Factory agent brief [REQ-418-001]', () => {
    const launcher = DOCK_LAUNCHERS.find((d) => d.tab === SKILL_STUDIO_TAB);
    expect(launcher).toBeTruthy();
    expect(launcher.id).toBe('dock-skill-studio');
    expect(launcher.label).toBe(SKILL_STUDIO_LABEL);
    expect(launcher.label).toBe('Skill Studio');
    expect(VIEW_BY_TAB[SKILL_STUDIO_TAB]).toBe('view-skill-studio');

    const switched = [];
    const created = [];
    const win = openWindow(SKILL_STUDIO_TAB, {}, {
      windows: new Map(),
      launcherForTabFn: (tab) => DOCK_LAUNCHERS.find((d) => d.tab === tab) || null,
      createWindowShellFn: (item) => {
        created.push(item.label);
        return {
          tab: item.tab,
          label: item.label,
          minimized: false,
          maximized: false,
          rect: { x: 32, y: 32, w: 960, h: 680 },
          el: {
            classList: { add() {}, remove() {} },
            setAttribute() {},
          },
        };
      },
      focusWindowFn() {},
      applyRectFn() {},
      applyMobileLayoutFn() {},
      updateDockActiveFn() {},
      root: { classList: { add() {} } },
      viewportSizeFn: () => ({ width: 1280, height: 800, dockH: 72 }),
      switchTabFn: (tab) => switched.push(tab),
      scheduleSyncHostedViewsFn() {},
      schedulePersistFn() {},
      isMobileFn: () => false,
    });

    expect(created).toEqual(['Skill Studio']);
    expect(switched).toEqual(['skill-studio']);
    expect(win.tab).toBe('skill-studio');
    expect(switched).not.toContain('factory');

    expect(skillView).toContain('id="factoryExistingSkillSelect"');
    expect(skillView).toContain('id="factoryNewSkillFormBtn"');
    expect(skillView).toContain('id="factorySkillMarkdownEditor"');
    expect(skillView).toContain('id="factoryCapabilitiesContainer"');
    expect(skillView).toContain('id="factorySaveSkillBtn"');
    expect(skillView).not.toContain('data-testid="factory-skill-tier-advanced"');
    expect(skillView).not.toContain('id="factorySkillTierSelect"');
    expect(skillView).not.toContain('id="factoryAgentPromptInput"');
    expect(skillView).not.toContain('id="factoryIntakeAgentCard"');
  });

  it('Forge open hydrates a catalog skill in Skill Studio [REQ-418-002]', () => {
    const plan = planSkillStudioDeepLink({ agentId: 'autoreiv', skillId: 'wiki-knowledge' });
    expect(plan.tab).toBe('skill-studio');
    expect(plan.label).toBe('Skill Studio');
    expect(plan.skillId).toBe('wiki-knowledge');
    expect(plan.agentId).toBe('autoreiv');
    expect(plan.writeSurface).toBe('skill-studio');
    expect(plan.writeSurface).not.toBe('factory');

    const view = applyLoadedSkillView({
      skill_id: 'wiki-knowledge',
      name: 'Wiki Knowledge',
      description: 'Read and file wiki notes',
      tier: 'platform',
      safety: { read_only: true, requires_hitl: false, untrusted_input_allowed: false },
      requires_tools: ['wiki_note_read'],
      markdown_content: '---\nname: Wiki Knowledge\n---\n# Wiki\n',
    }, 'wiki-knowledge');

    expect(view.notFound).toBe(false);
    expect(view.ok).toBe(true);
    expect(view.name).toBe('Wiki Knowledge');
    expect(view.skillId).toBe('wiki-knowledge');
    expect(view.description).toBe('Read and file wiki notes');
    expect(view.requiresTools).toEqual(['wiki_note_read']);
    expect(view.markdown).toContain('# Wiki');
    expect(view.detail).not.toMatch(/not found/i);

    const missing = applyLoadedSkillView({ detail: "Skill 'ghost' not found" }, 'ghost');
    expect(missing.notFound).toBe(true);
    expect(missing.ok).toBe(false);
  });

  it('Factory is not a second skill write surface and Forge does not save [REQ-418-003, REQ-418-004]', () => {
    // CARD-496: the Factory view is gone; its editor ids now exist only once, inside Skill Studio.
    expect(html).not.toContain('id="view-factory"');
    expect(html).not.toContain('id="factoryIntakeAgentCard"');
    for (const id of ['factorySaveSkillBtn', 'factorySkillMarkdownEditor', 'factoryExistingSkillSelect', 'factoryCapabilitiesContainer']) {
      expect(html.split(`id="${id}"`).length - 1, id).toBe(1);
      expect(skillView, id).toContain(`id="${id}"`);
    }

    const runbook = read('src/web/static/modules/studios/forge/runbook.js');
    const skillStudio = read('src/web/static/modules/studios/skill_studio.js');
    expect(runbook).toContain('Open in Skill Studio');
    expect(html).not.toContain('id="studioRunbookEditor"');
    expect(html).not.toContain('Open in Factory Workshop');
    expect(html).not.toContain('Author skill in Factory');
    expect(runbook).not.toContain("method: 'PUT'");
    expect(runbook).not.toContain('studioRunbookSaveBtn');
    expect(skillStudio).toContain('/api/skill_studio/save');
    expect(skillStudio).toContain('requires_tools');
    // CARD-496: the Factory window is gone, so Skill Studio is the only caller of the save route.
    expect(fs.existsSync(path.join(repoRoot, 'src/web/static/modules/studios/factory.js'))).toBe(false);
  });
});
