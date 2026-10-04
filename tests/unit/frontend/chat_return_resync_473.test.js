import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import { setupReturnResync, RETURN_RESYNC_GAP_MS } from '../../../src/web/static/modules/studios/chat/return_resync.js';

/**
 * CARD-473 - Chat catches up when the phone tab or window comes back (REQ-473-001..003, REQ-MOB-STREAM-002).
 */

const ROOT = path.resolve(__dirname, '../../..');

class FakeTarget {
  constructor() { this.listeners = {}; this.visibilityState = 'visible'; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  async fire(type) { await Promise.all((this.listeners[type] || []).map((fn) => fn({ type }))); }
}

const flush = () => new Promise((r) => setTimeout(r, 0));

function env({ sessionId = 's1', isStreaming = false } = {}) {
  const doc = new FakeTarget();
  const win = new FakeTarget();
  const calls = [];
  let clock = 10_000;
  const state = { activeSessionId: sessionId, isStreaming };
  const api = setupReturnResync(state, {
    doc, win, now: () => clock,
    watchStatus: async (sid) => calls.push(['status', sid]),
    loadMessages: async (sid) => calls.push(['messages', sid]),
    refreshPendingHitl: async () => calls.push(['approvals']),
  });
  return { doc, win, calls, state, api, tick: (ms) => { clock += ms; } };
}

describe('CARD-473 return resync', () => {
  it('coming back to the tab re-checks the run, reloads messages and pending approvals', async () => {
    const e = env();
    e.doc.visibilityState = 'hidden';
    await e.doc.fire('visibilitychange');
    await flush();
    expect(e.calls).toEqual([]); // hiding does nothing
    e.doc.visibilityState = 'visible';
    await e.doc.fire('visibilitychange');
    await flush();
    expect(e.calls).toEqual([['status', 's1'], ['messages', 's1'], ['approvals']]);
  });

  it('window focus resyncs too, but focus right after visibilitychange runs once', async () => {
    const e = env();
    await e.doc.fire('visibilitychange');
    await e.win.fire('focus');
    await flush();
    expect(e.calls.filter((c) => c[0] === 'messages')).toHaveLength(1);
    e.tick(RETURN_RESYNC_GAP_MS + 1);
    await e.win.fire('focus');
    await flush();
    expect(e.calls.filter((c) => c[0] === 'messages')).toHaveLength(2);
  });

  it('while this tab is streaming a reply it only re-checks status and does not reload over the stream (REQ-473-002)', async () => {
    const e = env({ isStreaming: true });
    await e.win.fire('focus');
    await flush();
    expect(e.calls).toEqual([['status', 's1']]);
  });

  it('with no open chat it does nothing', async () => {
    const e = env({ sessionId: null });
    await e.doc.fire('visibilitychange');
    await flush();
    expect(e.calls).toEqual([]);
  });

  it('does not reload a chat Jacob switched away from during the status check', async () => {
    const e = env();
    const doc = new FakeTarget();
    const calls = [];
    const state = { activeSessionId: 'a', isStreaming: false };
    setupReturnResync(state, {
      doc, win: new FakeTarget(), now: () => 1,
      watchStatus: async () => { state.activeSessionId = 'b'; },
      loadMessages: async (sid) => calls.push(sid),
    });
    await doc.fire('visibilitychange');
    await flush();
    expect(calls).toEqual([]);
    expect(e.calls).toEqual([]);
  });

  it('a failing reload is logged, not thrown', async () => {
    const doc = new FakeTarget();
    const state = { activeSessionId: 's1', isStreaming: false };
    const api = setupReturnResync(state, {
      doc, win: new FakeTarget(), now: () => 1,
      loadMessages: async () => { throw new Error('offline'); },
    });
    const origWarn = console.warn;
    console.warn = () => {};
    try {
      await expect(api.resync()).resolves.toBe(false);
    } finally {
      console.warn = origWarn;
    }
  });

  it('chat.js wires it with the CARD-485 status watcher, loadMessages and pending approvals', () => {
    const src = fs.readFileSync(path.join(ROOT, 'src/web/static/modules/studios/chat.js'), 'utf-8');
    expect(src).toContain("import { setupReturnResync } from './chat/return_resync.js'");
    expect(src).toMatch(/setupReturnResync\(state, \{ watchStatus: sessionSelect\.watchSessionStatus, loadMessages, refreshPendingHitl \}\)/);
  });
});
