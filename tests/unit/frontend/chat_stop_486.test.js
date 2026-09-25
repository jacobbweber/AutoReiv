import { describe, it, expect, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * CARD-486 - Stop tells the server to stop: POST /api/chat/stream/{id}/abort for the open chat,
 * for this tab's own reply and for a reply running elsewhere (CARD-485 busy state). D1-D7 accepted.
 */

async function need(name) {
  let m = {};
  try {
    m = await import('../../../src/web/static/modules/studios/chat/stop.js');
  } catch {
    m = {};
  }
  expect(typeof m[name], `chat/stop.js must export ${name}`).toBe('function');
  return m[name];
}

const json = (body, ok = true, status = ok ? 200 : 500) => ({ ok, status, json: async () => body });

function fakeClassList(initial = []) {
  const set = new Set(initial);
  return {
    add: (c) => set.add(c),
    remove: (c) => set.delete(c),
    contains: (c) => set.has(c),
    toggle: (c, on) => { if (on === undefined ? !set.has(c) : on) set.add(c); else set.delete(c); },
  };
}

function setup(stateExtra = {}, depsExtra = {}) {
  const calls = [];
  const state = { activeSessionId: 'S1', isStreaming: false, sessionBusy: false, ...stateExtra };
  const controller = { abort: vi.fn(() => calls.push('abort')) };
  const sendBtn = { disabled: true, classList: fakeClassList(['hidden']) };
  const stopBtn = { disabled: false, classList: fakeClassList([]) };
  const deps = {
    getController: () => null,
    clearController: vi.fn(),
    stopWatching: vi.fn(() => calls.push('stopWatching')),
    setBusy: vi.fn(),
    sendBtn,
    stopBtn,
    loadMessages: vi.fn(async () => { calls.push('loadMessages'); }),
    recheckStatus: vi.fn(async () => {}),
    showToast: vi.fn(),
    fetchFn: vi.fn(async (url) => { calls.push(`fetch ${url}`); return json({ status: 'aborted', task_cancelled: true }); }),
    ...depsExtra,
  };
  return { state, deps, controller, calls, sendBtn, stopBtn };
}

describe('CARD-486 Stop tells the server to stop', () => {
  it('REQ-486-001: own reply - cancels the browser request, then POSTs /abort for the open chat once', async () => {
    const createStopHandler = await need('createStopHandler');
    const t = setup({ isStreaming: true });
    t.deps.getController = () => t.controller;
    await createStopHandler(t.state, t.deps).stop();
    expect(t.controller.abort).toHaveBeenCalledTimes(1);
    expect(t.deps.clearController).toHaveBeenCalled();
    expect(t.deps.fetchFn).toHaveBeenCalledTimes(1);
    expect(t.deps.fetchFn.mock.calls[0][0]).toBe('/api/chat/stream/S1/abort');
    expect(t.deps.fetchFn.mock.calls[0][1]).toMatchObject({ method: 'POST' });
    expect(t.calls.indexOf('abort')).toBeLessThan(t.calls.indexOf('fetch /api/chat/stream/S1/abort'));
  });

  it('REQ-486-002: busy elsewhere (no browser request) - still POSTs /abort for the open chat', async () => {
    const createStopHandler = await need('createStopHandler');
    const t = setup({ sessionBusy: true, activeSessionId: 'phone chat' });
    await createStopHandler(t.state, t.deps).stop();
    expect(t.deps.fetchFn).toHaveBeenCalledTimes(1);
    expect(t.deps.fetchFn.mock.calls[0][0]).toBe('/api/chat/stream/phone%20chat/abort');
  });

  it('REQ-486-003: on success - stops watching, clears busy, restores Send, reloads the chat, toasts "Stopped"', async () => {
    const createStopHandler = await need('createStopHandler');
    const t = setup({ sessionBusy: true });
    await createStopHandler(t.state, t.deps).stop();
    expect(t.deps.stopWatching).toHaveBeenCalled();
    expect(t.deps.setBusy).toHaveBeenCalledWith(false);
    expect(t.sendBtn.disabled).toBe(false);
    expect(t.sendBtn.classList.contains('hidden')).toBe(false);
    expect(t.stopBtn.disabled).toBe(true);
    expect(t.stopBtn.classList.contains('hidden')).toBe(true);
    expect(t.deps.loadMessages).toHaveBeenCalledWith('S1');
    expect(t.deps.recheckStatus).toHaveBeenCalledWith('S1');
    expect(t.deps.showToast).toHaveBeenCalledWith('Stopped', 'info');
    expect(t.calls.indexOf('fetch /api/chat/stream/S1/abort')).toBeLessThan(t.calls.indexOf('loadMessages'));
  });

  it('REQ-486-005: abort fails (network error or 500) - warning toast, Send still restored', async () => {
    const createStopHandler = await need('createStopHandler');
    for (const fetchFn of [vi.fn(async () => { throw new Error('offline'); }), vi.fn(async () => json({ detail: 'boom' }, false, 500))]) {
      const t = setup({ sessionBusy: true }, { fetchFn });
      await createStopHandler(t.state, t.deps).stop();
      expect(t.deps.showToast).toHaveBeenCalledWith(expect.stringMatching(/Couldn't reach the server to stop the reply/), 'warning');
      expect(t.deps.showToast).not.toHaveBeenCalledWith('Stopped', 'info');
      expect(t.sendBtn.classList.contains('hidden')).toBe(false);
      expect(t.sendBtn.disabled).toBe(false);
      expect(t.stopBtn.classList.contains('hidden')).toBe(true);
    }
  });

  it('REQ-486-008: a second press while the abort is in flight sends nothing more', async () => {
    const createStopHandler = await need('createStopHandler');
    let release;
    const fetchFn = vi.fn(() => new Promise((r) => { release = () => r(json({ status: 'aborted' })); }));
    const t = setup({ sessionBusy: true }, { fetchFn });
    const handler = createStopHandler(t.state, t.deps);
    const first = handler.stop();
    const second = handler.stop();
    await Promise.resolve();
    release();
    await Promise.all([first, second]);
    expect(fetchFn).toHaveBeenCalledTimes(1);
    const third = handler.stop();
    await Promise.resolve();
    release();
    await third;
    expect(fetchFn).toHaveBeenCalledTimes(2); // single-flight only while pending
  });

  it('no open chat - no POST and no throw; a browser request is still cancelled', async () => {
    const createStopHandler = await need('createStopHandler');
    const t = setup({ activeSessionId: null, isStreaming: true });
    t.deps.getController = () => t.controller;
    await createStopHandler(t.state, t.deps).stop();
    expect(t.controller.abort).toHaveBeenCalledTimes(1);
    expect(t.deps.fetchFn).not.toHaveBeenCalled();
  });

  it('wiring: chat.js builds onCancelStream from createStopHandler and drops the client-only toast', () => {
    const src = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'), 'utf8');
    expect(src).toMatch(/import\s*\{[^}]*createStopHandler[^}]*\}\s*from\s*'\.\/chat\/stop\.js'/);
    expect(src).toMatch(/onCancelStream:\s*stopHandler\.stop/);
    expect(src).not.toContain("'Generation cancelled'");
    expect(src.split('\n').length).toBeLessThanOrEqual(1045);
  });
});
