import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

import { wireHitlCardButtons } from '../../../src/web/static/modules/studios/chat/hitl.js';
import { applyJobPhaseEvent, formatJobPhaseStrip } from '../../../src/web/static/modules/studios/chat.js';

/**
 * CARD-530: Approve while the Developer reply is still streaming started a resume stream that killed the live
 * turn (job_3bdef1802655, 2026-09-26 ~2:32 PM ET). Approve must only record the decision during a live reply;
 * a parked turn resumes once after the stream ends; a draft proposal never resumes.
 */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

class FakeButton {
  constructor(decision) { this.decision = decision; this.listeners = []; this.disabled = false; this.classList = { add() {}, remove() {} }; }
  getAttribute(k) { return k === 'data-hitl-decision' ? this.decision : null; }
  addEventListener(type, fn) { if (type === 'click') this.listeners.push(fn); }
  async click() { for (const fn of this.listeners) await fn({ type: 'click' }); }
}

function fakeCard() {
  const buttons = [new FakeButton('APPROVED'), new FakeButton('REJECTED')];
  const status = { textContent: '' };
  return {
    buttons,
    innerHTML: '',
    classList: { add() {}, remove() {} },
    querySelectorAll: (sel) => (sel === '[data-hitl-decision]' ? buttons : []),
    querySelector: (sel) => (sel === '.hitl-card-status' ? status : null),
  };
}

let decisionBody;
const savedFetch = globalThis.fetch;
beforeEach(() => {
  vi.useFakeTimers();
  decisionBody = { status: 'approved', execution: { ran: false } };
  globalThis.fetch = async () => ({ ok: true, json: async () => decisionBody });
});
afterEach(() => { vi.useRealTimers(); globalThis.fetch = savedFetch; });

function wire(stateOver = {}) {
  const state = { activeSessionId: 's1', isStreaming: false, ...stateOver };
  const card = fakeCard();
  const onResumeTurn = vi.fn(async () => {});
  const onDone = vi.fn(async () => {});
  wireHitlCardButtons(card, { approvalId: 'appr_1', approvalSessionId: 's1::phase::p1', state, onResumeTurn, onDone });
  return { state, card, onResumeTurn, onDone };
}

describe('REQ-530-001/002: Approve during a live reply', () => {
  it('does not resume while this tab is streaming; resumes once after the stream ends (parked turn)', async () => {
    const { state, card, onResumeTurn, onDone } = wire({ isStreaming: true });
    await card.buttons[0].click();
    expect(onResumeTurn).not.toHaveBeenCalled();
    expect(onDone).toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(2000);
    expect(onResumeTurn).not.toHaveBeenCalled();
    state.isStreaming = false;
    await vi.advanceTimersByTimeAsync(1000);
    expect(onResumeTurn).toHaveBeenCalledTimes(1);
    expect(onResumeTurn).toHaveBeenCalledWith('', { isResume: true });
  });

  it('never resumes for a draft proposal (resume_chat false), idle', async () => {
    decisionBody = { status: 'approved', resume_chat: false, execution: { ran: false, tool_name: 'propose_tool' } };
    const { card, onResumeTurn } = wire();
    await card.buttons[0].click();
    await vi.advanceTimersByTimeAsync(2000);
    expect(onResumeTurn).not.toHaveBeenCalled();
  });

  it('never resumes for a draft proposal approved mid-stream, even after the stream ends', async () => {
    decisionBody = { status: 'approved', resume_chat: false, execution: { ran: false, tool_name: 'propose_tool' } };
    const { state, card, onResumeTurn } = wire({ isStreaming: true });
    await card.buttons[0].click();
    state.isStreaming = false;
    await vi.advanceTimersByTimeAsync(3000);
    expect(onResumeTurn).not.toHaveBeenCalled();
  });

  it('fence (CARD-470): an idle parked turn still resumes at once', async () => {
    const { card, onResumeTurn } = wire();
    await card.buttons[0].click();
    expect(onResumeTurn).toHaveBeenCalledTimes(1);
  });

  it('a deferred resume is dropped when the operator switched to another chat', async () => {
    const { state, card, onResumeTurn } = wire({ isStreaming: true });
    await card.buttons[0].click();
    state.activeSessionId = 'other';
    state.isStreaming = false;
    await vi.advanceTimersByTimeAsync(3000);
    expect(onResumeTurn).not.toHaveBeenCalled();
  });
});

describe('REQ-530-007: the job strip tells the truth', () => {
  const live = { jobId: 'job_1', jobStatus: 'running', phaseName: 'Formulate', phaseIndex: 0, phaseCount: 2, reactState: 'DONE', resumedFromCheckpoint: true };

  it('an error event shows Failed with the reason, never DONE or Resumed', () => {
    const next = applyJobPhaseEvent(live, 'error', { error: 'Cannot complete phase phase_1: still queued.' });
    const view = formatJobPhaseStrip(next);
    expect(view.jobStatusLabel).toMatch(/failed/i);
    expect(view.jobStatusLabel).toContain('still queued');
    expect(view.reactState).toBe('FAILED');
    expect(view.jobStatusLabel).not.toContain('Resumed');
  });

  it('turn_done with job_failed shows Failed', () => {
    const next = applyJobPhaseEvent(live, 'turn_done', { content: 'x', job_failed: true, reason: 'Interrupted' });
    expect(formatJobPhaseStrip(next).reactState).toBe('FAILED');
  });

  it('Resumed clears once the resumed phase completes', () => {
    const next = applyJobPhaseEvent(live, 'phase_complete', { job_id: 'job_1', status: 'done', react_state: 'DONE' });
    expect(formatJobPhaseStrip(next).jobStatusLabel).not.toContain('Resumed');
  });
});

describe('REQ-530-003: a 409 turn_running is a gentle notice, not a failed reply', () => {
  it('executeChatTurn handles 409 without the red error', () => {
    const src = read('src/web/static/modules/studios/chat.js');
    expect(src).toContain('response.status === 409');
    expect(src).toContain('handleTurnRunning');
    expect(read('src/web/static/modules/studios/chat/turn_running.js')).toContain('still running');
  });

  it('handleTurnRunning removes the bubble, restores the text and warns (no red error)', async () => {
    const { handleTurnRunning } = await import('../../../src/web/static/modules/studios/chat/turn_running.js');
    const state = { messages: [{ role: 'user', content: 'hi' }], activeSessionId: 's1' };
    const bubble = { remove: vi.fn() };
    const restore = vi.fn(); const toast = vi.fn(); const load = vi.fn(async () => {});
    await handleTurnRunning({ state, streamBubble: bubble, userPrompt: 'hi', restoreComposer: restore, showToast: toast, loadMessages: load });
    expect(bubble.remove).toHaveBeenCalled();
    expect(state.messages).toHaveLength(0);
    expect(restore).toHaveBeenCalledWith('hi');
    expect(toast.mock.calls[0][1]).toBe('warning');
    expect(load).toHaveBeenCalledWith('s1');
  });
});
