import { describe, it, expect, beforeEach } from 'vitest';
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
  loadDesktopPrefs,
  saveDesktopPrefs,
  GRID_SIZE,
  PREFS_KEY,
} from '../../../src/web/static/modules/ui/agent-desktop.js';

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
        'chat', 'wiki', 'projects', 'agents', 'factory', 'routines',
        'observability', 'settings', 'prompts', 'education', 'sessions',
      ]),
    );
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
    const clamped = clampWindowRect(
      { x: -40, y: -20, w: 5000, h: 4000 },
      { width: 1200, height: 800, dockH: 72 },
    );
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
