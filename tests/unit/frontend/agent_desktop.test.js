import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  DOCK_LAUNCHERS,
  cascadeOffset,
  clampWindowRect,
  collectAgentsFromDom,
  snapToGrid,
  snapRectToGrid,
  computeTileRects,
  computeCascadeRects,
  computeSnapHalf,
  computeMaximizeRect,
  computeMobileLayout,
  computeTwoColumnsRects,
  computeThreeColumnsRects,
  computeLeftStackedRightFullRects,
  computeLeftFullRightStackedRects,
  loadDesktopPrefs,
  saveDesktopPrefs,
  GRID_SIZE,
  PREFS_KEY,
} from '../../../src/web/static/modules/ui/agent-desktop.js';
import { renderDock } from '../../../src/web/static/modules/ui/agent_desktop/dock.js';
import { openWindow } from '../../../src/web/static/modules/ui/agent_desktop/window.js';
import { hydrateRestoredStudioPicker } from '../../../src/web/static/modules/ui/agent_desktop/agent_hydration.js';
import { bindStudioAgentPickers, PICKER_KEYS } from '../../../src/web/static/modules/studios/agent_picker.js';
import { EVENTS, eventBus } from '../../../src/web/static/modules/events/event-bus.js';
import { publishAgentsLoaded, state } from '../../../src/web/static/modules/state/store.js';

function installMemoryLocalStorage() {
  const store = new Map();
  globalThis.localStorage = {
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    setItem(key, value) {
      store.set(String(key), String(value));
    },
    removeItem(key) {
      store.delete(key);
    },
    clear() {
      store.clear();
    },
  };
}

describe('Agent Desktop helpers [radical demo 04]', () => {
  beforeEach(() => {
    installMemoryLocalStorage();
    localStorage.removeItem(PREFS_KEY);
  });

  it('exposes dock launchers for required studios (not a sidebar list)', () => {
    const tabs = DOCK_LAUNCHERS.map((d) => d.tab);
    expect(tabs).toEqual(
      expect.arrayContaining([
        'chat',
        'wiki',
        'projects',
        'agents',
        'skill-studio',
        'routines',
        'observability',
        'settings',
        'prompts',
        'education',
      ])
    );
    expect(tabs).not.toContain('factory'); // CARD-496: Factory retired (ADR-0060)
    expect(DOCK_LAUNCHERS.every((d) => d.icon && d.label && d.id)).toBe(true);
  });

  it('cascades window offsets deterministically', () => {
    const a = cascadeOffset(0);
    const b = cascadeOffset(1);
    expect(a.x).toBeLessThan(b.x);
    expect(a.y).toBeLessThan(b.y);
    expect(cascadeOffset(8).x).toBe(cascadeOffset(0).x);
  });

  it('clamps window rects inside the viewport above the dock', () => {
    const clamped = clampWindowRect({ x: -40, y: -20, w: 5000, h: 4000 }, { width: 1200, height: 800, dockH: 72 });
    expect(clamped.x).toBe(0);
    expect(clamped.y).toBe(0);
    expect(clamped.w).toBeLessThanOrEqual(1200 - 16);
    expect(clamped.h).toBeLessThanOrEqual(800 - 72 - 16);
    expect(clamped.w).toBeGreaterThanOrEqual(320);
    expect(clamped.h).toBeGreaterThanOrEqual(240);
  });

  it('snaps values and rects to the desktop grid (Alt disables)', () => {
    expect(GRID_SIZE).toBe(16);
    expect(snapToGrid(17)).toBe(16);
    expect(snapToGrid(32)).toBe(32);
    expect(snapToGrid(17, GRID_SIZE, true)).toBe(17);
    const snapped = snapRectToGrid({ x: 10, y: 18, w: 333, h: 250 });
    expect(snapped.x % GRID_SIZE).toBe(0);
    expect(snapped.y % GRID_SIZE).toBe(0);
    expect(snapped.w % GRID_SIZE).toBe(0);
  });

  it('computes tile / cascade / snap-half / maximize layouts', () => {
    const vp = { width: 1200, height: 800, dockH: 72 };
    const tiles = computeTileRects(4, vp);
    expect(tiles).toHaveLength(4);
    expect(tiles[0].x).toBeGreaterThanOrEqual(0);
    expect(tiles[3].x + tiles[3].w).toBeLessThanOrEqual(vp.width);
    const cascade = computeCascadeRects(3, vp, { w: 640, h: 480 });
    expect(cascade).toHaveLength(3);
    expect(cascade[1].x).toBeGreaterThan(cascade[0].x);
    const left = computeSnapHalf('left', vp);
    const right = computeSnapHalf('right', vp);
    expect(left.x).toBeLessThan(right.x);
    expect(left.w + right.w).toBeLessThanOrEqual(vp.width);
    const max = computeMaximizeRect(vp);
    expect(max.w).toBeGreaterThan(1000);
    expect(max.h).toBeGreaterThan(600);

    const twoCols = computeTwoColumnsRects(vp);
    expect(twoCols).toHaveLength(2);
    expect(twoCols[0].w).toBe(twoCols[1].w);

    const threeCols = computeThreeColumnsRects(vp);
    expect(threeCols).toHaveLength(3);

    const stackedRight = computeLeftStackedRightFullRects(vp);
    expect(stackedRight).toHaveLength(3);
    expect(stackedRight[0].h + stackedRight[1].h).toBeLessThanOrEqual(vp.height - vp.dockH);

    const fullLeft = computeLeftFullRightStackedRects(vp);
    expect(fullLeft).toHaveLength(3);
    expect(fullLeft[1].h + fullLeft[2].h).toBeLessThanOrEqual(vp.height - vp.dockH);
  });

  it('computes mobile full maximize above the dock for any open count (no 50/50 stack)', () => {
    const vp = { width: 390, height: 844, dockH: 64 };
    const one = computeMobileLayout(1, 0, vp);
    expect(one.mode).toBe('full');
    expect(one.h).toBe(vp.height - vp.dockH);
    const two0 = computeMobileLayout(2, 0, vp);
    const two1 = computeMobileLayout(2, 1, vp);
    expect(two0.mode).toBe('full');
    expect(two1.mode).toBe('full');
    expect(two0.h).toBe(vp.height - vp.dockH);
    expect(two1.h).toBe(vp.height - vp.dockH);
    expect(two0.y).toBe(0);
    expect(two1.y).toBe(0);
  });

  it('persists desktop prefs in localStorage schema v1', () => {
    saveDesktopPrefs({
      windows: { chat: { x: 48, y: 36, w: 720, h: 560, maximized: false } },
      gridOverlay: true,
    });
    const loaded = loadDesktopPrefs();
    expect(loaded.gridOverlay).toBe(true);
    expect(loaded.windows.chat.w).toBe(720);
    expect(PREFS_KEY).toContain('agentDesktop');
  });

  it('collectAgentsFromDom reads state agents without inventing metrics', () => {
    expect(collectAgentsFromDom({ agents: [{ id: 'coder', name: 'Coder' }] })).toEqual([
      { id: 'coder', name: 'Coder' },
    ]);
    expect(collectAgentsFromDom({})).toEqual([]);
  });
});

describe('CARD-410 restored window agent binding', () => {
  const agents = [
    { id: 'developer', name: 'Developer', show_in_chat: true },
    { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
  ];
  let prevDocument;
  let prevAgents;
  let prevSelected;
  let forgeSelect;

  beforeEach(() => {
    installMemoryLocalStorage();
    prevDocument = globalThis.document;
    prevAgents = state.agents;
    prevSelected = state.selectedAgentId;
    state.agents = [];
    state.selectedAgentId = 'autoreiv';
    eventBus.clear(EVENTS.AGENTS_LOADED);
    localStorage.setItem(PICKER_KEYS.agents, 'autoreiv');
    localStorage.setItem(PICKER_KEYS.chat, 'autoreiv');
    forgeSelect = {
      id: 'forgeAgentSelect',
      dataset: {},
      options: [],
      _value: '',
      appendChild(opt) {
        this.options.push(opt);
      },
      addEventListener() {},
      get value() {
        return this._value;
      },
      set value(v) {
        this._value = v == null ? '' : String(v);
      },
    };
    let html = '';
    Object.defineProperty(forgeSelect, 'innerHTML', {
      configurable: true,
      get() {
        return html;
      },
      set(v) {
        html = String(v);
        forgeSelect.options.length = 0;
      },
    });
    const agentSelect = {
      id: 'agentSelect',
      dataset: {},
      options: [],
      _value: '',
      appendChild(opt) {
        this.options.push(opt);
      },
      addEventListener() {},
      get value() {
        return this._value;
      },
      set value(v) {
        this._value = v == null ? '' : String(v);
      },
    };
    let agentHtml = '';
    Object.defineProperty(agentSelect, 'innerHTML', {
      configurable: true,
      get() {
        return agentHtml;
      },
      set(v) {
        agentHtml = String(v);
        agentSelect.options.length = 0;
      },
    });
    globalThis.document = {
      getElementById(id) {
        if (id === 'forgeAgentSelect') return forgeSelect;
        if (id === 'agentSelect') return agentSelect;
        return null;
      },
      createElement() {
        return { value: '', textContent: '' };
      },
    };
  });

  afterEach(() => {
    eventBus.clear(EVENTS.AGENTS_LOADED);
    state.agents = prevAgents;
    state.selectedAgentId = prevSelected;
    globalThis.document = prevDocument;
  });

  function restoredWindowCtx(hydrateStudioAgentPickerFn) {
    return {
      windows: new Map([
        ['agents', { minimized: false, maximized: false, rect: { x: 0, y: 0, w: 800, h: 600 }, el: { classList: { remove() {} }, setAttribute() {} } }],
      ]),
      launcherForTabFn: () => ({ tab: 'agents', label: 'Agents', defaultSize: { w: 820, h: 580 } }),
      createWindowShellFn: () => {
        throw new Error('restored window must be reused');
      },
      focusWindowFn() {},
      applyRectFn() {},
      applyMobileLayoutFn() {},
      updateDockActiveFn() {},
      root: { classList: { add() {} } },
      viewportSizeFn: () => ({ width: 1200, height: 800, dockH: 72 }),
      switchTabFn() {},
      scheduleSyncHostedViewsFn() {},
      schedulePersistFn() {},
      isMobileFn: () => false,
      hydrateStudioAgentPickerFn,
    };
  }

  it('restored window callback fills the agent picker when the roster arrives [REQ-410-001, REQ-410-002]', () => {
    const boundTabs = [];
    const win = openWindow('agents', {}, restoredWindowCtx((tab) => {
      boundTabs.push(tab);
      hydrateRestoredStudioPicker(tab, {
        state,
        eventBus,
        eventName: EVENTS.AGENTS_LOADED,
        bind: (_tab, roster) => bindStudioAgentPickers(roster, { state }),
      });
    }));

    expect(win).toBeTruthy();
    expect(boundTabs).toEqual(['agents']);
    expect(forgeSelect.options.map((opt) => opt.value)).toEqual([]);

    publishAgentsLoaded(agents);

    expect(forgeSelect.options.map((opt) => opt.value)).toEqual(['autoreiv', 'developer']);
    expect(forgeSelect.value).toBe('autoreiv');
    expect(forgeSelect.options.map((opt) => opt.value)).not.toContain('assistant');
  });

  it('dock launch hydrates the studio agent picker [REQ-410-003]', () => {
    const hydrated = [];
    const opened = [];
    const btn = {
      getAttribute(name) {
        if (name === 'data-dock-tab') return 'agents';
        return 'dock-agents';
      },
      addEventListener(type, fn) {
        if (type === 'click') btn.onClick = fn;
      },
    };
    const dockApps = {
      innerHTML: '',
      querySelectorAll() {
        return [btn];
      },
    };
    renderDock({
      dockApps,
      windows: new Map(),
      root: { getAttribute() { return ''; } },
      openWindow: (tab) => opened.push(tab),
      minimizeWindow() {},
      toast() {},
      dockLaunchers: [{ id: 'dock-agents', tab: 'agents', label: 'Agents', icon: 'users' }],
      hydrateStudioAgentPicker: (tab) => hydrated.push(tab),
    });
    btn.onClick();
    expect(opened).toEqual(['agents']);
    expect(hydrated).toEqual(['agents']);
  });
});
