import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import { loadPageHtml } from './template_helper.js';
import {
  AUTORUN_CHAT_CHOICES_KEY,
  APPROVAL_AUTORUN_STORAGE_KEY,
  applySessionAutoRun,
  setupRuntimeModeToggles,
} from '../../../src/web/static/modules/studios/chat/runtime_toggles.js';

/** CARD-573: an agent's Always auto-run starts the Chat Auto-run box checked per chat; unticking sticks for that chat. */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

class FakeEl {
  constructor() {
    this.checked = false;
    this.cls = new Set(['hidden']);
    this.classList = { toggle: (c, on) => (on ? this.cls.add(c) : this.cls.delete(c)), contains: (c) => this.cls.has(c) };
    this.handlers = {};
  }
  addEventListener(t, fn) { this.handlers[t] = fn; }
  tick(v) { this.checked = v; this.handlers.change?.({ target: this }); }
}

function memStorage(initial = {}) {
  const data = { 'autoreiv_approval_autorun_reset_470': '1', ...initial };
  return { data, reader: (k, d) => (k in data ? data[k] : d), writer: (k, v) => { data[k] = v; } };
}

describe('CARD-573 Always auto-run', () => {
  const trusted = { id: 'tutor', always_auto_run: true };
  const plain = { id: 'autoreiv', always_auto_run: false };

  it('chat with a trusted agent starts checked; untick sticks for that chat only; other agents keep CARD-470', () => {
    const mem = memStorage();
    const state = {};
    const approvalToggle = new FakeEl();
    const approvalBadge = new FakeEl();
    setupRuntimeModeToggles(state, { approvalToggle, approvalBadge, reader: mem.reader, writer: mem.writer });
    expect(approvalToggle.checked).toBe(false);

    state.activeSessionId = 's1';
    expect(applySessionAutoRun(state, { approvalToggle, approvalBadge, agent: trusted, sessionId: 's1', reader: mem.reader })).toBe(true);
    expect(approvalToggle.checked).toBe(true);
    expect(approvalBadge.classList.contains('hidden')).toBe(false);

    approvalToggle.tick(false); // Jacob unticks in chat s1
    expect(JSON.parse(mem.data[AUTORUN_CHAT_CHOICES_KEY]).s1).toBe('ask');
    expect(mem.data[APPROVAL_AUTORUN_STORAGE_KEY]).toBeUndefined(); // the global CARD-470 choice is untouched

    state.activeSessionId = 's2';
    expect(applySessionAutoRun(state, { approvalToggle, approvalBadge, agent: trusted, sessionId: 's2', reader: mem.reader })).toBe(true);
    state.activeSessionId = 's1';
    expect(applySessionAutoRun(state, { approvalToggle, approvalBadge, agent: trusted, sessionId: 's1', reader: mem.reader })).toBe(false);

    state.activeSessionId = 's3';
    expect(applySessionAutoRun(state, { approvalToggle, approvalBadge, agent: plain, sessionId: 's3', reader: mem.reader })).toBe(false);
    approvalToggle.tick(true); // plain agent: remembered globally as before
    expect(mem.data[APPROVAL_AUTORUN_STORAGE_KEY]).toBe('run');
  });

  it('Agent Studio has the checkbox and saves it; chat applies it on session select; routines pre-check new ones', () => {
    const html = loadPageHtml();
    const prefs = html.indexOf('data-section="preferences"');
    const box = html.indexOf('id="forgeAlwaysAutoRunInput"');
    expect(box).toBeGreaterThan(prefs);
    expect(box).toBeLessThan(html.indexOf('data-section="overrides"'));
    const forge = read('src/web/static/modules/studios/forge.js');
    expect(forge).toContain('always_auto_run: Boolean(forgeAlwaysAutoRunInput && forgeAlwaysAutoRunInput.checked)');
    expect(forge).toContain('forgeAlwaysAutoRunInput.checked = agent.always_auto_run === true');
    const sessionSelect = read('src/web/static/modules/studios/chat/session_select.js');
    expect(sessionSelect).toMatch(/if \(!sessionId\) return;\s*applySessionAutoRun\(state\);/);
    const routines = read('src/web/static/modules/studios/routines.js');
    expect(routines).toContain('routineApprovalRunInput.checked = agentAlwaysAutoRun(');
    expect(routines).toContain("routineApprovalRunInput.checked = routine.approval_mode === 'run'");
  });
});
