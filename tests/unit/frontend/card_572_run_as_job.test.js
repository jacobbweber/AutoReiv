import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import { loadPageHtml } from './template_helper.js';
import { buildChatStreamPayload } from '../../../src/web/static/modules/studios/chat/stream.js';
import { setupRunAsJobToggle, setRunAsJob, takeRunAsJob } from '../../../src/web/static/modules/studios/chat/runtime_toggles.js';

/** CARD-572: a chat message becomes a standing Job only when Jacob ticks Run as a job. */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

class FakeEl {
  constructor(hidden = true) {
    this.checked = false;
    this.cls = new Set(hidden ? ['hidden'] : []);
    this.classList = { toggle: (c, on) => (on ? this.cls.add(c) : this.cls.delete(c)), contains: (c) => this.cls.has(c) };
    this.handlers = {};
  }
  addEventListener(t, fn) { this.handlers[t] = fn; }
  tick(v) { this.checked = v; this.handlers.change?.({ target: this }); }
}

describe('CARD-572 Run as a job', () => {
  it('payload sends run_as_job only when asked, never on resume, and no goal_mode', () => {
    expect(buildChatStreamPayload({ agentId: 'a', sessionId: 's', content: 'First check X, then tell me' }).run_as_job).toBe(false);
    expect(buildChatStreamPayload({ agentId: 'a', sessionId: 's', content: 'x', runAsJob: true }).run_as_job).toBe(true);
    expect(buildChatStreamPayload({ agentId: 'a', sessionId: 's', resume: true, runAsJob: true }).run_as_job).toBe(false);
    expect('goal_mode' in buildChatStreamPayload({ agentId: 'a', sessionId: 's' })).toBe(false);
  });

  it('box starts off, shows the badge when ticked, and unticks after one send', () => {
    const state = {};
    const els = { runAsJobToggle: new FakeEl(false), runAsJobBadge: new FakeEl() };
    els.runAsJobToggle.checked = true; // a stale browser restore must not survive load
    setupRunAsJobToggle(state, els);
    expect(els.runAsJobToggle.checked).toBe(false);
    expect(state.runAsJob).toBe(false);
    els.runAsJobToggle.tick(true);
    expect(state.runAsJob).toBe(true);
    expect(els.runAsJobBadge.classList.contains('hidden')).toBe(false);
    expect(takeRunAsJob(state, els)).toBe(true);
    expect(els.runAsJobToggle.checked).toBe(false);
    expect(els.runAsJobBadge.classList.contains('hidden')).toBe(true);
    expect(takeRunAsJob(state, els)).toBe(false);
    setRunAsJob(state, true, els);
    expect(els.runAsJobToggle.checked).toBe(true);
  });

  it('composer has the box beside Auto-run, and the routine form has its own box', () => {
    const html = loadPageHtml();
    const autoRun = html.indexOf('id="approvalToggle"');
    const box = html.indexOf('id="runAsJobToggle"');
    expect(autoRun).toBeGreaterThan(0);
    expect(box).toBeGreaterThan(autoRun);
    expect(html.slice(autoRun, box)).not.toContain('Inspectors');
    expect(html).toContain('id="runAsJobBadge"');
    expect(html).toContain('id="routineRunAsJobInput"');
  });

  it('chat.js takes the box per send; routines.js saves run_as_job; Education asks explicitly', () => {
    const chat = read('src/web/static/modules/studios/chat.js');
    expect(chat).toContain('takeRunAsJob(state, runAsJobEls)');
    expect(chat).toContain('runAsJob,');
    const routines = read('src/web/static/modules/studios/routines.js');
    expect(routines).toContain('run_as_job,');
    expect(routines).toContain("routine.run_as_job === true");
    const edu = read('src/web/static/modules/studios/education.js');
    expect((edu.match(/runAsJob: true/g) || []).length).toBe(2);
  });
});
