/**
 * CARD-496: Retire the Agent Training Factory UI (ADR-0060).
 * No Factory window, Lab Monitor, training popup or "Agent Training Optimization" panel.
 * Gaps open Skill Studio or a Developer chat. Skill Studio keeps its backend calls and factory* ids.
 */

import { describe, it, expect, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');
const STATIC = 'src/web/static';
const read = (rel) => fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
const exists = (rel) => fs.existsSync(path.join(repoRoot, rel));

function walkJs(dir) {
  const out = [];
  for (const entry of fs.readdirSync(path.join(repoRoot, dir), { withFileTypes: true })) {
    const rel = `${dir}/${entry.name}`;
    if (entry.isDirectory()) out.push(...walkJs(rel));
    else if (entry.name.endsWith('.js')) out.push(rel);
  }
  return out;
}
const stripComments = (src) => src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '').replace(/<!--[\s\S]*?-->/g, '');

const indexHtml = read('src/web/templates/index.html');
const staticJs = walkJs(STATIC);

describe('REQ-496-001/002: the Factory UI is gone', () => {
  it('index.html has none of the retired ids', () => {
    for (const id of ['tab-factory', 'view-factory', 'labMonitorDrawer', 'trainAgentHandshakeModal', 'trainAgentToggle', 'trainAgentBadge', 'forgeScaffoldQueueCard', 'forgeScaffoldOpenFactoryBtn', 'factoryAgentSelect']) {
      expect(indexHtml, id).not.toContain(`id="${id}"`);
    }
  });

  it('no visible UI text says Training Factory, Factory Studio or Lab Training Monitor', () => {
    const phrases = /Training Factory|Factory Studio|Lab Training Monitor/;
    expect(stripComments(indexHtml)).not.toMatch(phrases);
    for (const rel of staticJs) {
      expect(stripComments(read(rel)), rel).not.toMatch(phrases);
    }
  });

  it('retired modules are deleted and Skill Studio helpers moved out of studios/factory/', () => {
    for (const rel of ['modules/studios/factory.js', 'modules/studios/factory', 'modules/studios/forge/lab_monitor.js', 'modules/studios/chat/train_modal.js', 'modules/studios/chat/training.js']) {
      expect(exists(`${STATIC}/${rel}`), rel).toBe(false);
    }
    expect(exists(`${STATIC}/modules/studios/skill_studio/workshop_meta.js`)).toBe(true);
    expect(exists(`${STATIC}/modules/studios/skill_studio/skill_scope.js`)).toBe(true);
  });
});

describe('No factory tab anywhere in the shell', () => {
  it('dock, view map and presets have no factory entry', async () => {
    const desktop = await import('../../../src/web/static/modules/ui/agent-desktop.js');
    expect(desktop.DOCK_LAUNCHERS.map((d) => d.tab)).not.toContain('factory');
    expect(desktop.DOCK_LAUNCHERS.map((d) => d.id)).not.toContain('dock-factory');
    expect(Object.keys(desktop.VIEW_BY_TAB)).not.toContain('factory');
    expect(read(`${STATIC}/modules/ui/agent_desktop/presets.js`)).not.toMatch(/'factory'/);
    expect(read(`${STATIC}/modules/ui/agent_desktop/window.js`)).not.toMatch(/tab === 'factory'/);
  });

  it('app.js registers no Factory studio or openers; the event bus has no FACTORY_OPEN', async () => {
    const app = read(`${STATIC}/app.js`);
    for (const s of ['initFactoryStudio', 'factoryCtrl', 'openFactoryStudio', 'getFactoryCtrl', "'factory'"]) {
      expect(app, s).not.toContain(s);
    }
    const { EVENTS } = await import('../../../src/web/static/modules/events/event-bus.js');
    expect(Object.keys(EVENTS)).not.toContain('FACTORY_OPEN');
    for (const rel of staticJs) {
      expect(read(rel), rel).not.toMatch(/openFactoryStudio|openLabMonitorDrawer/);
    }
  });
});

describe('REQ-496-003/004: capability gaps open Skill Studio or a Developer chat', () => {
  const gap = { id: 'g1', identified_capability: 'inventory_lookup', suggested_tool_name: 'get_tc49_inventory', turn_text: 'Look up TC49 inventory counts' };

  it('a gap row shows Open in Skill Studio, Ask Developer and Dismiss', async () => {
    const { capabilityGapRowHtml } = await import('../../../src/web/static/modules/studios/forge/tools.js');
    const html = capabilityGapRowHtml(gap);
    expect(html).toContain('btn-gap-open-skill-studio');
    expect(html).toContain('Open in Skill Studio');
    expect(html).toContain('btn-gap-ask-developer');
    expect(html).toContain('Ask Developer');
    expect(html).toContain('btn-dismiss-gap');
    expect(html).not.toMatch(/Factory|btn-open-factory-gap/);
  });

  it('Open in Skill Studio opens Skill Studio for the gap agent', async () => {
    const { openGapInSkillStudio } = await import('../../../src/web/static/modules/studios/forge/tools.js');
    const openSkillStudio = vi.fn();
    expect(openGapInSkillStudio('autoreiv', { openSkillStudio })).toBe(true);
    expect(openSkillStudio).toHaveBeenCalledWith('autoreiv');
  });

  it('Ask Developer drafts the gap as a create-tool request', async () => {
    const { buildGapDeveloperDraft } = await import('../../../src/web/static/modules/studios/forge/tools.js');
    const draft = buildGapDeveloperDraft(gap, 'autoreiv');
    expect(draft.intent).toBe('create');
    expect(draft.tool_name).toBe('get_tc49_inventory');
    expect(draft.behavior).toContain('Look up TC49 inventory counts');
    expect(draft.behavior).toContain('autoreiv');
  });

  it('Ask Developer posts to the Tools Studio talk route and opens the Developer chat', async () => {
    const { askDeveloperAboutGap, buildGapDeveloperDraft } = await import('../../../src/web/static/modules/studios/forge/tools.js');
    const draft = buildGapDeveloperDraft(gap, 'autoreiv');
    const fetchFn = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ session_id: 'dev1', agent_id: 'developer', prompt: `Create ${draft.tool_name}: ${draft.behavior}`, opened_job: false }) }));
    const openDeveloperSession = vi.fn(async () => {});
    const callbacks = { switchTab: vi.fn(), getChatCtrl: () => ({ openDeveloperSession }), openToolsStudio: vi.fn() };
    const ok = await askDeveloperAboutGap(gap, 'autoreiv', { fetchFn, callbacks, toastFn: vi.fn() });
    expect(ok).toBe(true);
    expect(fetchFn.mock.calls[0][0]).toBe('/api/tools_studio/authoring/talk');
    const body = JSON.parse(fetchFn.mock.calls[0][1].body);
    expect(body.intent).toBe('create');
    expect(body.draft.tool_name).toBe('get_tc49_inventory');
    expect(callbacks.switchTab).toHaveBeenCalledWith('chat');
    expect(openDeveloperSession).toHaveBeenCalledWith('dev1', expect.stringContaining('get_tc49_inventory'));
    expect(callbacks.openToolsStudio).not.toHaveBeenCalled();
  });

  it('when the talk route fails, Ask Developer toasts and opens Tools Studio for that agent', async () => {
    const { askDeveloperAboutGap } = await import('../../../src/web/static/modules/studios/forge/tools.js');
    const fetchFn = vi.fn(async () => ({ ok: false, status: 500, json: async () => ({ detail: 'boom' }) }));
    const toastFn = vi.fn();
    const callbacks = { switchTab: vi.fn(), getChatCtrl: () => null, openToolsStudio: vi.fn() };
    const ok = await askDeveloperAboutGap(gap, 'autoreiv', { fetchFn, callbacks, toastFn });
    expect(ok).toBe(false);
    expect(toastFn).toHaveBeenCalledWith(expect.stringContaining('Opening Tools Studio'), 'error');
    expect(callbacks.openToolsStudio).toHaveBeenCalledWith('autoreiv');
  });

  it('the backlog is labelled Capability gaps (ids unchanged)', () => {
    expect(indexHtml).toContain('id="agentTrainingBacklogCard"');
    expect(indexHtml).toContain('Capability gaps');
    expect(indexHtml).not.toContain('Needs Training Backlog');
  });
});

describe('REQ-496-005: the "agent created" chat card', () => {
  it('shows Open in Skill Studio and Open in Agent Studio, and no Factory button', async () => {
    const { renderAgentHandoffCardHtml } = await import('../../../src/web/static/modules/studios/chat/stream.js');
    const html = renderAgentHandoffCardHtml({ agentId: 'kube', agentName: 'Kube SRE' });
    expect(html).toContain('data-action="open-skill-studio"');
    expect(html).toContain('Open in Skill Studio');
    expect(html).toContain('Open in Agent Studio');
    expect(html).not.toMatch(/launch-factory|Factory/);
  });

  it('chat delegation routes Open in Skill Studio and drops the Factory, Lab and promotion handlers', () => {
    const render = read(`${STATIC}/modules/studios/chat/render.js`);
    expect(render).toContain('[data-action="open-skill-studio"]');
    expect(render).toMatch(/openSkillStudio\(agentId/);
    for (const s of ['launch-factory', 'open-lab-drawer-btn', 'approve-factory-btn', 'reject-factory-btn', 'factory-promotion-card', '/api/agent_training_factory/jobs']) {
      expect(render, s).not.toContain(s);
    }
  });
});

describe('REQ-496-006: Quick Scaffold stays in Agent Studio', () => {
  it('scaffold.js has no Factory jump and no Optimization panel code', () => {
    const scaffold = read(`${STATIC}/modules/studios/forge/scaffold.js`);
    for (const s of ['openFactoryStudio', 'openFactoryStudioForAgent', 'forgeScaffoldOpenFactoryBtn', 'forgeScaffoldQueueBody', '/api/capabilities/scaffold']) {
      expect(scaffold, s).not.toContain(s);
    }
  });
});

describe('REQ-496-007: saved desktop layouts drop the Factory window', () => {
  it('prefs scrub removes factory from open windows, geometry and presets', async () => {
    const { scrubSessionsFromDesktopPrefs } = await import('../../../src/web/static/modules/ui/agent_desktop/prefs.js');
    const clean = scrubSessionsFromDesktopPrefs({
      windows: { chat: { x: 0, y: 0, w: 400, h: 300 }, factory: { x: 10, y: 10, w: 500, h: 400 } },
      openWindows: ['chat', 'factory'],
      savedPresets: [{ name: 'Mine', windows: [{ tab: 'chat' }, { tab: 'factory' }] }],
    });
    expect(clean.openWindows).toEqual(['chat']);
    expect(Object.keys(clean.windows)).toEqual(['chat']);
    expect(clean.savedPresets[0].windows.map((w) => w.tab)).toEqual(['chat']);
  });
});

describe('REQ-496-008: the app calls no Factory job or scaffold-queue route', () => {
  it('no frontend file references /api/agent_training_factory/jobs or /api/capabilities/scaffold', () => {
    for (const rel of staticJs) {
      const src = read(rel);
      expect(src, rel).not.toContain('/api/agent_training_factory/jobs');
      expect(src, rel).not.toContain('/api/capabilities/scaffold');
    }
  });
});

describe('D7, D8, D10 and leftovers', () => {
  it('the agent picker has no factory key and clears the stale stored value', async () => {
    const picker = await import('../../../src/web/static/modules/studios/agent_picker.js');
    expect(Object.keys(picker.PICKER_KEYS)).not.toContain('factory');
    const store = new Map([['autoreiv_factory_selected_agent_id', '__new__'], ['autoreiv_forge_selected_agent_id', 'autoreiv']]);
    picker.clearRetiredPickerKeys({ removeItem: (k) => store.delete(k) });
    expect(store.has('autoreiv_factory_selected_agent_id')).toBe(false);
    expect(store.get('autoreiv_forge_selected_agent_id')).toBe('autoreiv');
  });

  it('chat.js drops the auto-train and dead handoff branches and the training popup wiring', () => {
    const chat = read(`${STATIC}/modules/studios/chat.js`);
    for (const s of ['auto_train_progress', "eventType === 'handoff'", 'setupTrainModal', 'trainAgentTargetSelect', 'populateTrainAgentTargetOptions', './chat/training.js', './chat/train_modal.js']) {
      expect(chat, s).not.toContain(s);
    }
  });

  it('Agent Studio Save no longer sends auto-training fields', () => {
    const forge = read(`${STATIC}/modules/studios/forge.js`);
    expect(forge).not.toContain('allow_autonomous_training');
    expect(forge).not.toContain('max_training_retries');
    expect(forge).not.toMatch(/lab_monitor/);
  });

  it('the Teach button class is btn-escalate-developer; the data attribute stays until CARD-497', () => {
    const render = read(`${STATIC}/modules/studios/chat/render.js`);
    const teach = read(`${STATIC}/modules/studios/chat/teach_modal.js`);
    expect(render).toContain('btn-escalate-developer');
    expect(render).not.toContain('btn-escalate-factory');
    expect(teach).toContain(".btn-escalate-developer'");
    expect(render).toContain('data-factory-escalation');
  });
});

describe('REQ-496-009/010: Skill Studio keeps working on the existing backend', () => {
  it('Skill Studio imports the moved helpers and still calls the Factory-prefixed routes', () => {
    const skill = read(`${STATIC}/modules/studios/skill_studio.js`);
    expect(skill).toContain("from './skill_studio/workshop_meta.js'");
    expect(skill).toContain("from './skill_studio/skill_scope.js'");
    expect(skill).toContain('/api/agent_training_factory/scaffold/save');
    expect(skill).toContain('/api/agent_training_factory/capabilities');
    expect(skill).not.toContain('getFactoryCtrl');
    expect(read(`${STATIC}/modules/studios/tools_studio_catalog.js`)).toContain('/api/agent_training_factory/capabilities');
  });

  it('Skill Studio keeps its factory* ids (ADR-0060 D5)', () => {
    const start = indexHtml.indexOf('id="view-skill-studio"');
    expect(start).toBeGreaterThan(0);
    const skillView = indexHtml.slice(start, start + 60000);
    for (const id of ['factorySkillIdInput', 'factorySaveSkillBtn', 'factoryCapabilitiesContainer']) {
      expect(skillView, id).toContain(`id="${id}"`);
    }
  });
});
