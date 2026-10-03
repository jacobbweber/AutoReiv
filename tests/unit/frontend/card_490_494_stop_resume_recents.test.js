/**
 * CARD-490..494 (browser side): Resume on a stopped job, Stop leaves non-chat work alone and says so,
 * "Stopped" on the device that started a reply stopped elsewhere, Recent Chats markers, waiting note.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import * as stream from '../../../src/web/static/modules/studios/chat/stream.js';
import { requestStreamAbort, stopToast, createStopHandler, STOPPED_TOAST } from '../../../src/web/static/modules/studios/chat/stop.js';
import {
  sessionActivityMarker, applySessionActivity, createSessionActivityPoller, SESSION_ACTIVITY_URL,
} from '../../../src/web/static/modules/studios/chat/session_activity.js';
import { formatJobPhaseStrip, applyJobPhaseEvent, reactStateToneClass } from '../../../src/web/static/modules/studios/chat/job_strip.js';
import { hydrateJobPhaseStateFromJourney } from '../../../src/web/static/modules/studios/chat/session_select.js';
import { renderSessionList } from '../../../src/web/static/modules/studios/chat/chrome.js';
import * as chat from '../../../src/web/static/modules/studios/chat.js';

const ROOT = path.resolve(__dirname, '../../..');
const json = (body, ok = true) => ({ ok, status: ok ? 200 : 500, json: async () => body });

function fakeClassList(initial = []) {
  const set = new Set(initial);
  return {
    add: (c) => set.add(c), remove: (c) => set.delete(c), contains: (c) => set.has(c),
    toggle: (c, on) => { if (on === undefined ? !set.has(c) : on) set.add(c); else set.delete(c); },
  };
}
const fakeDoc = () => ({ createElement: (tag) => ({ tag, className: '', textContent: '', attrs: {}, setAttribute(k, v) { this.attrs[k] = v; } }) });
const fakeContainer = () => ({ children: [], appendChild(el) { this.children.push(el); return el; }, querySelectorAll: () => [] });

describe('CARD-492 a reply stopped elsewhere says Stopped', () => {
  it('turn_end aborted before any words: no "Reply failed", a Stopped notice instead', () => {
    const o = stream.trackStreamOutcome();
    o.note('turn_end', { status: 'aborted', reason: 'kill_checkpointed', is_finished: true });
    expect(o.stopped()).toBe(true);
    expect(o.failureMessage()).toBeNull();
    expect(o.stoppedNotice()).toBe('Stopped');
    const box = fakeContainer();
    const toasts = [];
    expect(stream.reportStreamOutcome(o, { messagesContainer: box, showToastFn: (m) => toasts.push(m), doc: fakeDoc() })).toBe(false);
    expect(box.children).toHaveLength(1);
    expect(box.children[0].textContent).toBe('Stopped');
    expect(box.children[0].attrs['data-stream-stopped']).toBe('true');
    expect(box.children[0].className).toContain('chat-attachment-notice'); // CARD-475 style
    expect(toasts).toEqual([]);
  });

  it('stopped after some words: the saved reply ends "(Stopped)", so no extra notice and no failure', () => {
    const o = stream.trackStreamOutcome();
    o.note('token', { text: 'Hel' });
    o.note('turn_end', { status: 'aborted' });
    expect(o.failureMessage()).toBeNull();
    expect(o.stoppedNotice()).toBeNull();
  });

  it('a stream with no events at all is still a failure (CARD-469 unchanged)', () => {
    expect(stream.trackStreamOutcome().failureMessage()).toBe('The reply ended without a response.');
  });
});

describe('CARD-494 waiting for another reply', () => {
  it('queued shows the note; dequeued or the first word hides it', () => {
    const el = { textContent: '', classList: fakeClassList(['hidden']) };
    expect(stream.applyQueueNote(el, 'queued')).toBe(true);
    expect(el.textContent).toBe('Waiting for another reply to finish.');
    expect(stream.applyQueueNote(el, 'dequeued')).toBe(false);
    stream.applyQueueNote(el, 'queued');
    expect(stream.applyQueueNote(el, 'token')).toBe(false);
    expect(stream.applyQueueNote(null, 'queued')).toBe(false);
  });

  it('the reply bubble has the note and chat.js feeds it every event', () => {
    const src = fs.readFileSync(path.join(ROOT, 'src/web/static/modules/studios/chat.js'), 'utf-8');
    expect(src).toContain('data-stream-queue-note="1"');
    expect(src).toContain('applyQueueNote(queueNoteEl, eventType)');
  });
});

describe('CARD-491 Stop and work it cannot end', () => {
  it('requestStreamAbort returns the server body', async () => {
    const r = await requestStreamAbort('S1', async () => json({ status: 'aborted', reason: 'nothing_running' }));
    expect(r).toEqual({ ok: true, body: { status: 'aborted', reason: 'nothing_running' } });
    expect((await requestStreamAbort('S1', async () => { throw new Error('down'); })).ok).toBe(false);
  });

  it('not_started_by_chat is a warning with the server message, not "Stopped"', () => {
    expect(stopToast(true, { reason: 'not_started_by_chat', message: 'This work was not started by a chat reply...' }))
      .toEqual({ text: 'This work was not started by a chat reply...', level: 'warning' });
    expect(stopToast(true, { reason: 'operator_kill_mid_llm' })).toEqual({ text: STOPPED_TOAST, level: 'info' });
    expect(stopToast(false, null).level).toBe('warning');
  });

  it('the Stop handler calls afterStop with the abort body (CARD-490 re-reads the strip)', async () => {
    const body = { status: 'aborted', checkpointed: true, job_id: 'job_1', task_cancelled: true };
    const afterStop = vi.fn(async () => {});
    const showToast = vi.fn();
    const h = createStopHandler({ activeSessionId: 'S1' }, { fetchFn: async () => json(body), afterStop, showToast });
    await h.stop();
    expect(afterStop).toHaveBeenCalledWith('S1', body);
    expect(showToast).toHaveBeenCalledWith('Stopped', 'info');
  });
});

describe('CARD-490 Resume on a stopped job', () => {
  const journey = {
    jobs: [{
      id: 'job_1', status: 'running', stopped: true,
      phases: [
        { id: 'p0', index: 0, name: 'Research', status: 'done', assigned_agent_id: 'autoreiv' },
        { id: 'p1', index: 1, name: 'Write', status: 'queued', assigned_agent_id: 'autoreiv' },
      ],
    }],
  };

  it('a journey job marked stopped hydrates as stopped on the stopped phase', () => {
    const s = hydrateJobPhaseStateFromJourney(journey);
    expect(s).toMatchObject({ jobId: 'job_1', stopped: true, reactState: 'STOPPED', phaseId: 'p1', phaseName: 'Write' });
  });

  it('the strip says Job stopped; running again clears it', () => {
    const view = formatJobPhaseStrip({ jobId: 'job_1', jobStatus: 'running', stopped: true });
    expect(view).toMatchObject({ jobStatusLabel: 'Job stopped', reactState: 'STOPPED', stopped: true });
    expect(reactStateToneClass('STOPPED')).toContain('text-amber-200');
    expect(applyJobPhaseEvent({ jobId: 'job_1', stopped: true }, 'phase_start', { job_id: 'job_1', phase_id: 'p1' }).stopped).toBe(false);
    expect(applyJobPhaseEvent({ jobId: 'job_1', stopped: true }, 'resumed_from_checkpoint', { job_id: 'job_1' }).stopped).toBe(false);
  });

  it('a running or finished job is not stopped', () => {
    const running = hydrateJobPhaseStateFromJourney({ jobs: [{ id: 'j', status: 'running', phases: [{ id: 'p', index: 0, status: 'running' }] }] });
    expect(running.stopped).toBeUndefined();
    expect(formatJobPhaseStrip({ jobId: 'j', jobStatus: 'failed', stopped: true }).stopped).toBe(false);
  });

  it('the job strip has a Resume button and pressing it sends a resume turn', () => {
    const html = fs.readFileSync(path.join(ROOT, 'src/web/templates/index.html'), 'utf-8');
    const strip = html.slice(html.indexOf('id="jobPhaseStatusStrip"'), html.indexOf('id="chatEducationModeStrip"'));
    expect(strip).toContain('data-job-phase="resume"');
    expect(strip).toContain('<span>Resume</span>');
    const src = fs.readFileSync(path.join(ROOT, 'src/web/static/modules/studios/chat.js'), 'utf-8');
    expect(src).toContain("closest('[data-job-phase=\"resume\"]')");
    expect(src).toContain("executeChatTurn('', { isResume: true })");
  });

  it('chat.js still re-exports the strip helpers', () => {
    expect(typeof chat.formatJobPhaseStrip).toBe('function');
    expect(typeof chat.applyJobPhaseEvent).toBe('function');
    expect(Array.isArray(chat.JOB_PHASE_CHROME_EVENTS)).toBe(true);
  });
});

describe('CARD-493 Recent Chats markers', () => {
  afterEach(() => { delete globalThis.document; });

  it('marker: needs approval wins over replying', () => {
    expect(sessionActivityMarker({ is_running: true })).toMatchObject({ key: 'running', label: 'Replying' });
    expect(sessionActivityMarker({ is_running: true, waiting_approval: true })).toMatchObject({ key: 'waiting', label: 'Needs approval' });
    expect(sessionActivityMarker({})).toBeNull();
  });

  it('applySessionActivity sets and clears flags and reports a change', () => {
    const sessions = [{ id: 'A' }, { id: 'B', is_running: true }];
    expect(applySessionActivity(sessions, { running: ['A'], waiting_approval: [] })).toBe(true);
    expect(sessions.map((s) => [s.is_running, s.waiting_approval])).toEqual([[true, false], [false, false]]);
    expect(applySessionActivity(sessions, { running: ['A'], waiting_approval: [] })).toBe(false);
  });

  it('the poller refreshes every 5 s only while a chat replies, and stops when none does', async () => {
    const state = { sessions: [{ id: 'A' }, { id: 'B' }] };
    const answers = [{ running: ['A'], waiting_approval: [] }, { running: [], waiting_approval: ['A'] }];
    const urls = [];
    const timers = [];
    const onChange = vi.fn();
    const p = createSessionActivityPoller(state, {
      fetchFn: async (u) => { urls.push(u); return json(answers.shift()); },
      onChange,
      setTimeoutFn: (fn, ms) => { timers.push({ fn, ms }); return timers.length; },
      clearTimeoutFn: () => {},
    });
    await p.kick();
    expect(urls).toEqual([SESSION_ACTIVITY_URL]);
    expect(state.sessions[0].is_running).toBe(true);
    expect(timers).toHaveLength(1);
    expect(timers[0].ms).toBe(5000);
    expect(p.isPolling()).toBe(true);
    timers[0].fn();
    await new Promise((r) => setTimeout(r, 0));
    await new Promise((r) => setTimeout(r, 0));
    expect(state.sessions[0]).toMatchObject({ is_running: false, waiting_approval: true });
    expect(timers).toHaveLength(1); // nothing replying: no further poll
    expect(onChange).toHaveBeenCalledTimes(2);
  });

  it('renderSessionList draws the marker dot and label', () => {
    const made = [];
    globalThis.document = { createElement: () => { const el = { attrs: {}, className: '', innerHTML: '', setAttribute(k, v) { this.attrs[k] = v; }, addEventListener() {} }; made.push(el); return el; } };
    const list = { innerHTML: '', items: [], appendChild(el) { this.items.push(el); } };
    renderSessionList({ sessionList: list, sessions: [
      { id: 'A', title: 'Long job', is_running: true },
      { id: 'B', title: 'Needs me', waiting_approval: true },
      { id: 'C', title: 'Quiet' },
    ], activeSessionId: 'C' });
    expect(list.items.map((el) => el.attrs['data-session-activity'])).toEqual(['running', 'waiting', undefined]);
    expect(list.items[0].innerHTML).toContain('animate-pulse');
    expect(list.items[0].innerHTML).toContain('Replying');
    expect(list.items[1].innerHTML).toContain('bg-amber-400');
    expect(list.items[1].innerHTML).toContain('Needs approval');
    expect(list.items[2].innerHTML).not.toContain('data-activity-dot');
  });
});
