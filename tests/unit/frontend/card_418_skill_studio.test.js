/**
 * CARD-418: Skill Studio dock open and Forge deep-link hydrate.
 * REQ-418-001..004
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { DOCK_LAUNCHERS, VIEW_BY_TAB } from '../../../src/web/static/modules/ui/agent-desktop.js';
import { openWindow } from '../../../src/web/static/modules/ui/agent_desktop/window.js';
import {
  CAPABILITIES_STUDIO_LABEL,
  CAPABILITIES_STUDIO_TAB,
  planCapabilitiesStudioDeepLink,
} from '../../../src/web/static/modules/studios/capabilities_studio.js';
import { applyLoadedSkillView } from '../../../src/web/static/modules/studios/skill_studio/workshop_meta.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Capabilities Studio dock and skill deep link [CARD-418, CARD-742]', () => {
  const html = read('src/web/templates/index.html');
  const capView = html.slice(html.indexOf('id="view-capabilities"'));

  it('dock open presents Capabilities Studio and retires view-skill-studio [REQ-418-001, CARD-692, CARD-742]', () => {
    const capLauncher = DOCK_LAUNCHERS.find((d) => d.tab === 'capabilities');
    expect(capLauncher).toBeTruthy();
    expect(capLauncher.id).toBe('dock-capabilities');
    expect(DOCK_LAUNCHERS.find((d) => d.tab === 'skill-studio')).toBeUndefined();
    expect(CAPABILITIES_STUDIO_LABEL).toBe('Capabilities');
    expect(VIEW_BY_TAB[CAPABILITIES_STUDIO_TAB]).toBe('view-capabilities');
    expect(VIEW_BY_TAB['skill-studio']).toBeUndefined();
    expect(html).not.toContain('id="view-skill-studio"');

    const switched = [];
    const created = [];
    const win = openWindow('capabilities', {}, {
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

    expect(created).toEqual(['Capabilities']);
    expect(switched).toEqual(['capabilities']);
    expect(win.tab).toBe('capabilities');
    expect(switched).not.toContain('factory');

    expect(capView).toContain('id="capabilitiesTreeList"');
    expect(capView).toContain('id="capabilitiesNewSkillBtn"');
    expect(capView).toContain('id="capabilitiesSaveFileBtn"');
    expect(capView).not.toContain('id="factoryAgentPromptInput"');
    expect(capView).not.toContain('id="factoryIntakeAgentCard"');
  });

  it('Forge open hydrates a catalog skill in Capabilities Studio [REQ-418-002]', () => {
    const plan = planCapabilitiesStudioDeepLink({ agentId: 'autoreiv', skillId: 'wiki-knowledge' });
    expect(plan.tab).toBe('capabilities');
    expect(plan.label).toBe('Capabilities');
    expect(plan.skillId).toBe('wiki-knowledge');
    expect(plan.agentId).toBe('autoreiv');
    expect(plan.filePath).toBe('SKILL.md');

    const view = applyLoadedSkillView({
      skill_id: 'wiki-knowledge',
      name: 'Wiki Knowledge',
      description: 'Read and file wiki notes',
      tier: 'platform',
      safety: { read_only: true, requires_hitl: false, untrusted_input_allowed: false },
      tools: ['wiki_note_read'],
      markdown_content: '---\nname: Wiki Knowledge\n---\n# Wiki\n',
    }, 'wiki-knowledge');

    expect(view.notFound).toBe(false);
    expect(view.ok).toBe(true);
    expect(view.name).toBe('Wiki Knowledge');
    expect(view.skillId).toBe('wiki-knowledge');
    expect(view.description).toBe('Read and file wiki notes');
    expect(view.tools).toEqual(['wiki_note_read']);
    expect(view.markdown).toContain('# Wiki');
    expect(view.detail).not.toMatch(/not found/i);

    const missing = applyLoadedSkillView({ detail: "Skill 'ghost' not found" }, 'ghost');
    expect(missing.notFound).toBe(true);
    expect(missing.ok).toBe(false);
  });

  it('Factory and Skill Studio are not second skill write surfaces and Forge does not save [REQ-418-003, REQ-418-004]', () => {
    expect(html).not.toContain('id="view-factory"');
    expect(html).not.toContain('id="view-skill-studio"');
    expect(html).not.toContain('id="factoryIntakeAgentCard"');

    const runbook = read('src/web/static/modules/studios/forge/runbook.js');
    const capStudio = read('src/web/static/modules/studios/capabilities_studio.js');
    expect(runbook).toContain('Manage skills'); // CARD-656: header link, not per row
    expect(html).not.toContain('id="studioRunbookEditor"');
    expect(html).not.toContain('Open in Factory Workshop');
    expect(html).not.toContain('Author skill in Factory');
    expect(runbook).not.toContain("method: 'PUT'");
    expect(runbook).not.toContain('studioRunbookSaveBtn');
    expect(capStudio).toContain('api.capabilities.saveFile');
    expect(fs.existsSync(path.join(repoRoot, 'src/web/static/modules/studios/factory.js'))).toBe(false);
    expect(fs.existsSync(path.join(repoRoot, 'src/web/static/modules/studios/skill_studio.js'))).toBe(false);
  });
});
