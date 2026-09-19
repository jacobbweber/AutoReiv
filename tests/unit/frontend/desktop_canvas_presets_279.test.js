import { describe, it, expect, beforeEach } from 'vitest';
import {
  computeTwoColumnsRects,
  computeThreeColumnsRects,
  computeLeftStackedRightFullRects,
  computeLeftFullRightStackedRects,
  loadDesktopPrefs,
  saveDesktopPrefs,
  scrubSessionsFromDesktopPrefs,
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

describe('CARD-279: Canvas Layout Presets & Sticky Saved Layouts', () => {
  const vp = { width: 1400, height: 900, dockH: 72 };

  beforeEach(() => {
    installMemoryLocalStorage();
    localStorage.removeItem(PREFS_KEY);
  });

  describe('3-Window Layout: Left Stacked, Right Full (Jacob Cockpit Scheme)', () => {
    it('computes 3 non-overlapping rects with two left-stacked windows and one full-height right window', () => {
      const rects = computeLeftStackedRightFullRects(vp);
      expect(rects).toHaveLength(3);

      const [w0, w1, w2] = rects;

      // Window 0: Top-left
      expect(w0.x).toBe(8);
      expect(w0.y).toBe(8);
      expect(w0.w).toBeGreaterThanOrEqual(320);

      // Window 1: Bottom-left
      expect(w1.x).toBe(8);
      expect(w1.y).toBeGreaterThan(w0.y + w0.h);
      expect(w1.w).toBe(w0.w);

      // Left column vertical fit: w0.h + w1.h + gap should approximate available height
      const availableH = vp.height - vp.dockH - 16;
      expect(w0.h + w1.h + 8).toBeCloseTo(availableH, -1);

      // Window 2: Right full-height
      expect(w2.x).toBeGreaterThan(w0.x + w0.w);
      expect(w2.y).toBe(8);
      expect(w2.h).toBeCloseTo(availableH, -1);
      expect(w2.x + w2.w).toBeLessThanOrEqual(vp.width);
    });

    it('enforces MIN_W and MIN_H boundaries on smaller viewports', () => {
      const smallVp = { width: 780, height: 600, dockH: 72 };
      const rects = computeLeftStackedRightFullRects(smallVp);
      expect(rects).toHaveLength(3);
      rects.forEach((r) => {
        expect(r.w).toBeGreaterThanOrEqual(320);
        expect(r.h).toBeGreaterThanOrEqual(240);
      });
    });
  });

  describe('3-Window Layout: Left Full, Right Stacked', () => {
    it('computes 3 non-overlapping rects with one full-height left window and two right-stacked windows', () => {
      const rects = computeLeftFullRightStackedRects(vp);
      expect(rects).toHaveLength(3);

      const [w0, w1, w2] = rects;

      // Window 0: Left full-height
      expect(w0.x).toBe(8);
      expect(w0.y).toBe(8);
      const availableH = vp.height - vp.dockH - 16;
      expect(w0.h).toBeCloseTo(availableH, -1);

      // Window 1: Top-right
      expect(w1.x).toBeGreaterThan(w0.x + w0.w);
      expect(w1.y).toBe(8);

      // Window 2: Bottom-right
      expect(w2.x).toBe(w1.x);
      expect(w2.y).toBeGreaterThan(w1.y + w1.h);
      expect(w1.h + w2.h + 8).toBeCloseTo(availableH, -1);
    });
  });

  describe('Column Layout Presets', () => {
    it('computes 2 equal-width side-by-side columns spanning full height', () => {
      const rects = computeTwoColumnsRects(vp);
      expect(rects).toHaveLength(2);
      expect(rects[0].x).toBe(8);
      expect(rects[1].x).toBeGreaterThan(rects[0].x + rects[0].w);
      expect(rects[0].w).toBe(rects[1].w);
      expect(rects[0].h).toBe(rects[1].h);
      expect(rects[1].x + rects[1].w).toBeLessThanOrEqual(vp.width);
    });

    it('computes 3 equal-width columns side-by-side', () => {
      const rects = computeThreeColumnsRects(vp);
      expect(rects).toHaveLength(3);
      expect(rects[0].x).toBe(8);
      expect(rects[1].x).toBeGreaterThan(rects[0].x + rects[0].w);
      expect(rects[2].x).toBeGreaterThan(rects[1].x + rects[1].w);
      expect(rects[0].w).toBe(rects[1].w);
      expect(rects[1].w).toBe(rects[2].w);
      expect(rects[2].x + rects[2].w).toBeLessThanOrEqual(vp.width);
    });
  });

  describe('Desktop Preferences & Saved Layouts Persistence', () => {
    it('defaults to autoRestore true, empty openWindows, and empty savedPresets', () => {
      const prefs = loadDesktopPrefs();
      expect(prefs.autoRestore).toBe(true);
      expect(prefs.openWindows).toEqual([]);
      expect(prefs.savedPresets).toEqual([]);
      expect(prefs.windows).toEqual({});
    });

    it('persists and recalls saved custom layout presets cleanly', () => {
      const initial = loadDesktopPrefs();
      initial.savedPresets = [
        {
          id: 'preset-1',
          name: 'Cockpit (Chat + Agents + Wiki)',
          createdAt: 1789859549000,
          windows: [
            { tab: 'chat', rect: { x: 8, y: 8, w: 600, h: 380 }, maximized: false },
            { tab: 'agents', rect: { x: 8, y: 396, w: 600, h: 380 }, maximized: false },
            { tab: 'wiki', rect: { x: 616, y: 8, w: 600, h: 768 }, maximized: false },
          ],
        },
      ];
      initial.openWindows = ['chat', 'agents', 'wiki'];
      initial.autoRestore = true;

      saveDesktopPrefs(initial);

      const reloaded = loadDesktopPrefs();
      expect(reloaded.autoRestore).toBe(true);
      expect(reloaded.openWindows).toEqual(['chat', 'agents', 'wiki']);
      expect(reloaded.savedPresets).toHaveLength(1);
      expect(reloaded.savedPresets[0].name).toBe('Cockpit (Chat + Agents + Wiki)');
      expect(reloaded.savedPresets[0].windows).toHaveLength(3);
      expect(reloaded.savedPresets[0].windows[0].tab).toBe('chat');
    });

    it('scrubs sessions drawer from saved presets and open windows', () => {
      const dirty = {
        windows: {
          chat: { x: 8, y: 8, w: 500, h: 500 },
          sessions: { x: 8, y: 8, w: 500, h: 500 },
        },
        openWindows: ['chat', 'sessions'],
        savedPresets: [
          {
            id: 'p1',
            name: 'Test',
            windows: [
              { tab: 'chat', rect: { x: 8, y: 8, w: 500, h: 500 } },
              { tab: 'sessions', rect: { x: 8, y: 8, w: 500, h: 500 } },
            ],
          },
        ],
      };

      const scrubbed = scrubSessionsFromDesktopPrefs(dirty);
      expect(scrubbed.windows.sessions).toBeUndefined();
      expect(scrubbed.openWindows).toEqual(['chat']);
      expect(scrubbed.savedPresets[0].windows).toEqual([{ tab: 'chat', rect: { x: 8, y: 8, w: 500, h: 500 } }]);
    });
  });
});
