import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import { loadPageHtml } from './template_helper.js';
import { buildChatStreamPayload } from '../../../src/web/static/modules/studios/chat/stream.js';
import * as toggles from '../../../src/web/static/modules/studios/chat/runtime_toggles.js';

/**
 * CARD-470 - Chat Auto-run toggle inverted since the CARD-397 split.
 * Unchecked must mean approval_mode "ask" (fail safe); the choice is remembered once
 * (after a one-time reset of any saved 'run'), and the chips follow the toggles.
 */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

class FakeClassList {
  constructor(initial = []) { this.set = new Set(initial); }
  add(...c) { c.forEach((x) => this.set.add(x)); }
  remove(...c) { c.forEach((x) => this.set.delete(x)); }
  contains(c) { return this.set.has(c); }
  toggle(c, force) {
    const on = force === undefined ? !this.set.has(c) : !!force;
    if (on) this.set.add(c); else this.set.delete(c);
    return on;
  }
}

class FakeToggle {
  constructor(checked = false) { this.checked = checked; this.listeners = {}; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  set(checked) {
    this.checked = checked;
    (this.listeners.change || []).forEach((fn) => fn({ type: 'change', target: this }));
  }
}

const badge = () => ({ classList: new FakeClassList(['hidden']) });

function memoryStore(initial = {}) {
  const data = { ...initial };
  return {
    data,
    reader: (k, fb = null) => (k in data ? data[k] : fb),
    writer: (k, v) => { data[k] = v; },
  };
}

function setup(initial = {}) {
  const store = memoryStore(initial);
  const els = {
    approvalToggle: new FakeToggle(false),
    verifyToggle: new FakeToggle(false),
    approvalBadge: badge(),
    verifyBadge: badge(),
  };
  const state = { approvalAutoRun: false, verifyEnabled: false };
  toggles.setupRuntimeModeToggles(state, { ...els, reader: store.reader, writer: store.writer });
  return { store, state, ...els };
}

describe('CARD-470 payload mapping [REQ-470-001/002]', () => {
  it('Auto-run off sends ask; on sends run', () => {
    expect(buildChatStreamPayload({ approvalAutoRun: false }).approval_mode).toBe('ask');
    expect(buildChatStreamPayload({ approvalAutoRun: true }).approval_mode).toBe('run');
  });
});

describe('CARD-470 setupRuntimeModeToggles', () => {
  it('fresh install: toggle off, state ask, chip hidden [REQ-470-003]', () => {
    const t = setup();
    expect(t.approvalToggle.checked).toBe(false);
    expect(t.state.approvalAutoRun).toBe(false);
    expect(t.approvalBadge.classList.contains('hidden')).toBe(true);
  });

  it('one-time reset: a saved run (pre-fix) loads as ask and is rewritten [REQ-470-007]', () => {
    const t = setup({ [toggles.APPROVAL_AUTORUN_STORAGE_KEY]: 'run' });
    expect(t.approvalToggle.checked).toBe(false);
    expect(t.state.approvalAutoRun).toBe(false);
    expect(t.store.data[toggles.APPROVAL_AUTORUN_STORAGE_KEY]).toBe('ask');
    expect(t.store.data[toggles.APPROVAL_RESET_MARKER_KEY]).toBeTruthy();
  });

  it('after the reset has run once, a saved run is restored [REQ-470-004/007]', () => {
    const t = setup({
      [toggles.APPROVAL_AUTORUN_STORAGE_KEY]: 'run',
      [toggles.APPROVAL_RESET_MARKER_KEY]: '1',
    });
    expect(t.approvalToggle.checked).toBe(true);
    expect(t.state.approvalAutoRun).toBe(true);
    expect(t.approvalBadge.classList.contains('hidden')).toBe(false);
  });

  it('change saves the choice, updates state and the chip [REQ-470-004/005/006]', () => {
    const t = setup();
    t.approvalToggle.set(true);
    expect(t.state.approvalAutoRun).toBe(true);
    expect(t.store.data[toggles.APPROVAL_AUTORUN_STORAGE_KEY]).toBe('run');
    expect(t.approvalBadge.classList.contains('hidden')).toBe(false);
    t.approvalToggle.set(false);
    expect(t.state.approvalAutoRun).toBe(false);
    expect(t.store.data[toggles.APPROVAL_AUTORUN_STORAGE_KEY]).toBe('ask');
    expect(t.approvalBadge.classList.contains('hidden')).toBe(true);
  });

  it('a later load keeps the operator choice (reset does not repeat) [REQ-470-007]', () => {
    const first = setup();
    first.approvalToggle.set(true);
    const store = memoryStore(first.store.data);
    const state = { approvalAutoRun: false, verifyEnabled: false };
    const approvalToggle = new FakeToggle(false);
    toggles.setupRuntimeModeToggles(state, { approvalToggle, reader: store.reader, writer: store.writer });
    expect(approvalToggle.checked).toBe(true);
    expect(state.approvalAutoRun).toBe(true);
  });

  it('Self-Verify toggle drives state.verifyEnabled and its chip [REQ-470-005/006]', () => {
    const t = setup();
    expect(t.verifyBadge.classList.contains('hidden')).toBe(true);
    t.verifyToggle.set(true);
    expect(t.state.verifyEnabled).toBe(true);
    expect(t.verifyBadge.classList.contains('hidden')).toBe(false);
    t.verifyToggle.set(false);
    expect(t.state.verifyEnabled).toBe(false);
    expect(t.verifyBadge.classList.contains('hidden')).toBe(true);
  });

  it('storage failures fail safe to ask', () => {
    const state = { approvalAutoRun: true };
    const approvalToggle = new FakeToggle(true);
    const boom = () => { throw new Error('denied'); };
    toggles.setupRuntimeModeToggles(state, { approvalToggle, reader: boom, writer: boom });
    expect(approvalToggle.checked).toBe(false);
    expect(state.approvalAutoRun).toBe(false);
  });
});

describe('CARD-470 source and template contracts', () => {
  const chatSrc = read('src/web/static/modules/studios/chat.js');

  it('never derives approval_mode from a negated .checked [REQ-470-008]', () => {
    const files = [chatSrc, read('src/web/static/modules/studios/chat/stream.js'), read('src/web/static/modules/studios/education.js')];
    for (const src of files) expect(src).not.toMatch(/(?<!!)!\s*approvalToggle\??\.checked/);
    expect(chatSrc).toMatch(/approvalAutoRun:\s*!!approvalToggle\?\.checked/);
  });

  it('chat.js wires the toggles through the helper and stays within its cap', () => {
    expect(chatSrc).toMatch(/setupRuntimeModeToggles\(state,/);
    expect(chatSrc.split('\n').length).toBeLessThanOrEqual(1045);
  });

  it('Auto-run tooltip and chip say what it really does [REQ-470-009, D3]', () => {
    const html = loadPageHtml();
    expect(html).toContain('title="Off: AutoReiv asks before write, shell and code tools. On: they run without asking. Blocked tools stay blocked."');
    const chip = html.match(/<span id="approvalBadge"[^>]*>([\s\S]*?)<\/span>/);
    expect(chip).not.toBeNull();
    expect(chip[0]).toMatch(/amber/);
    expect(chip[1].trim()).toBe('Auto-run ON');
    expect(html).not.toContain('Allow safe tools to run without asking');
  });
});
