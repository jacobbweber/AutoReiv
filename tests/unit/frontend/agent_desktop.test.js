import { describe, it, expect } from 'vitest';
import {
  DOCK_LAUNCHERS,
  cascadeOffset,
  clampWindowRect,
  collectAgentsFromDom,
} from '../../../src/web/static/modules/ui/agent-desktop.js';

describe('Agent Desktop helpers [radical demo 04]', () => {
  it('exposes dock launchers for required studios (not a sidebar list)', () => {
    const tabs = DOCK_LAUNCHERS.map((d) => d.tab);
    expect(tabs).toEqual(
      expect.arrayContaining([
        'chat',
        'wiki',
        'projects',
        'agents',
        'factory',
        'routines',
        'observability',
        'settings',
        'prompts',
        'sessions',
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

  it('collectAgentsFromDom reads state agents without inventing metrics', () => {
    expect(collectAgentsFromDom({ agents: [{ id: 'coder', name: 'Coder' }] })).toEqual([
      { id: 'coder', name: 'Coder' },
    ]);
    expect(collectAgentsFromDom({})).toEqual([]);
  });
});
