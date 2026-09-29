/**
 * CARD-573 follow-up: Agent Studio must not overwrite an edit made while the agent was still loading.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { createForgeLoadGuard, setForgeFormBusy } from '../../../src/web/static/modules/studios/forge.js';

const ROOT = path.resolve(__dirname, '../../..');
const forge = fs.readFileSync(path.join(ROOT, 'src/web/static/modules/studios/forge.js'), 'utf-8');

describe('CARD-573 Agent Studio load timing', () => {
  it('a newer render makes an older one stale', () => {
    const g = createForgeLoadGuard();
    const first = g.beginRender();
    expect(first()).toBe(true);
    const second = g.beginRender();
    expect(first()).toBe(false);
    expect(second()).toBe(true);
  });

  it('a background load knows the user picked an agent after it started', () => {
    const g = createForgeLoadGuard();
    const mark = g.pickMark();
    expect(g.pickedSince(mark)).toBe(false);
    g.userPicked();
    expect(g.pickedSince(mark)).toBe(true);
    expect(g.pickedSince(g.pickMark())).toBe(false);
  });

  it('busy makes the editable sections inert, and clears it after', () => {
    const attrs = [new Map(), new Map()];
    const els = attrs.map((m) => ({ setAttribute: (k, v) => m.set(k, v), removeAttribute: (k) => m.delete(k) }));
    const doc = { querySelectorAll: (sel) => (sel === 'details.forge-section' ? els : []) };
    setForgeFormBusy(true, doc);
    expect(attrs.every((m) => m.has('inert') && m.get('aria-busy') === 'true')).toBe(true);
    setForgeFormBusy(false, doc);
    expect(attrs.every((m) => m.size === 0)).toBe(true);
    expect(() => setForgeFormBusy(true, null)).not.toThrow();
  });

  it('forge.js wires it: stale renders stop after awaits, a late load keeps the picked form, Save waits while busy', () => {
    expect(forge).toMatch(/await loadTones\(agent\.tone \|\| 'default'\);\s*if \(!isCurrent\(\)\) return;/);
    expect(forge).toMatch(/if \(!isCurrent\(\)\) return;\s*currentAgentMcpServers = mcpServers;/);
    expect(forge).toMatch(/loadGuard\.pickedSince\(pickMark\)/);
    expect(forge).toMatch(/loadGuard\.userPicked\(\)/);
    expect(forge).toMatch(/if \(forgeBusy\) \{ showToast/);
  });
});
