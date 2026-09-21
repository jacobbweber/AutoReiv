/**
 * CARD-403: Agent Desktop Window Manager Monolith Decomposition Contract Test.
 * Asserts file size caps (<800 lines for submodules, <1000 lines for orchestrator)
 * and verifies complete backward compatibility of exported APIs and layout calculators.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-403: Agent Desktop Window Manager Monolith Decomposition and Submodule Hygiene', () => {
  const repoRoot = path.resolve(__dirname, '../../..');
  const desktopJsPath = path.join(repoRoot, 'src/web/static/modules/ui/agent-desktop.js');
  const desktopDir = path.join(repoRoot, 'src/web/static/modules/ui/agent_desktop');

  it('orchestrator agent-desktop.js is strictly under 1,000 lines', () => {
    const content = fs.readFileSync(desktopJsPath, 'utf-8');
    const lines = content.split('\n').length;
    expect(lines).toBeLessThan(1000);
    // Sanity check: must be substantial enough to be the real orchestrator
    expect(lines).toBeGreaterThan(250);
  });

  it('all submodules under agent_desktop/ are strictly under 800 lines', () => {
    const files = fs.readdirSync(desktopDir).filter((f) => f.endsWith('.js'));
    expect(files.length).toBeGreaterThanOrEqual(6);

    const oversized = [];
    files.forEach((file) => {
      const filePath = path.join(desktopDir, file);
      const lines = fs.readFileSync(filePath, 'utf-8').split('\n').length;
      if (lines >= 800) {
        oversized.push({ file, lines });
      }
    });

    expect(oversized).toEqual([]);
  });

  it('re-exports required backward-compatible APIs and symbols', async () => {
    const desktopModule = await import('../../../src/web/static/modules/ui/agent-desktop.js');

    // Controller entry point
    expect(typeof desktopModule.initAgentDesktop).toBe('function');

    // Dock constants
    expect(Array.isArray(desktopModule.DOCK_LAUNCHERS)).toBe(true);
    expect(desktopModule.DOCK_LAUNCHERS.length).toBeGreaterThan(5);

    // Z-stack & grid constants
    expect(desktopModule.GRID_SIZE).toBe(16);
    expect(desktopModule.DESKTOP_DOCK_Z).toBe(10000);
    expect(desktopModule.DESKTOP_MODAL_Z).toBe(11000);
    expect(desktopModule.DESKTOP_WINDOW_Z_CAP).toBe(9000);
    expect(typeof desktopModule.nextDesktopStackZ).toBe('function');

    // Preferences & persistence
    expect(desktopModule.PREFS_KEY).toBe('autoreiv.agentDesktop.v1');
    expect(typeof desktopModule.scrubSessionsFromDesktopPrefs).toBe('function');
    expect(typeof desktopModule.collectAgentsFromDom).toBe('function');
    expect(typeof desktopModule.loadDesktopPrefs).toBe('function');
    expect(typeof desktopModule.saveDesktopPrefs).toBe('function');

    // Layout calculators & geometry
    expect(typeof desktopModule.cascadeOffset).toBe('function');
    expect(typeof desktopModule.snapToGrid).toBe('function');
    expect(typeof desktopModule.snapRectToGrid).toBe('function');
    expect(typeof desktopModule.clampWindowRect).toBe('function');
    expect(typeof desktopModule.computeTileRects).toBe('function');
    expect(typeof desktopModule.computeCascadeRects).toBe('function');
    expect(typeof desktopModule.computeSnapHalf).toBe('function');
    expect(typeof desktopModule.computeTwoColumnsRects).toBe('function');
    expect(typeof desktopModule.computeThreeColumnsRects).toBe('function');
    expect(typeof desktopModule.computeLeftStackedRightFullRects).toBe('function');
    expect(typeof desktopModule.computeLeftFullRightStackedRects).toBe('function');
    expect(typeof desktopModule.computeMaximizeRect).toBe('function');
    expect(typeof desktopModule.computeMobileLayout).toBe('function');
  });

  it('preserves layout calculations and snap behavior', async () => {
    const {
      snapToGrid,
      snapRectToGrid,
      clampWindowRect,
      computeTwoColumnsRects,
      computeThreeColumnsRects,
      computeLeftStackedRightFullRects,
    } = await import('../../../src/web/static/modules/ui/agent-desktop.js');

    expect(snapToGrid(17)).toBe(16);
    expect(snapToGrid(25)).toBe(32);
    expect(snapToGrid(25, 16, true)).toBe(25);

    const snapped = snapRectToGrid({ x: 15, y: 31, w: 300, h: 200 });
    expect(snapped.x).toBe(16);
    expect(snapped.y).toBe(32);
    expect(snapped.w).toBeGreaterThanOrEqual(320);
    expect(snapped.h).toBeGreaterThanOrEqual(240);

    const vp = { width: 1280, height: 800, dockH: 72 };
    const clamped = clampWindowRect({ x: -50, y: -20, w: 500, h: 400 }, vp);
    expect(clamped.x).toBeGreaterThanOrEqual(0);
    expect(clamped.y).toBeGreaterThanOrEqual(0);

    const twoCols = computeTwoColumnsRects(vp);
    expect(twoCols.length).toBe(2);

    const threeCols = computeThreeColumnsRects(vp);
    expect(threeCols.length).toBe(3);

    const leftStacked = computeLeftStackedRightFullRects(vp);
    expect(leftStacked.length).toBe(3);
  });
});
