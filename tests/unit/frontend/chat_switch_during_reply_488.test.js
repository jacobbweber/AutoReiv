import { describe, it, expect, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * CARD-488 - switching chats (pick, New chat, agent switch) while this tab streams its own reply:
 * detach the browser stream only (server keeps going), render the picked chat, send there; Stop
 * targets this tab's streaming chat, else the open chat. D1-D7 accepted as recommended.
 */

async function load(rel) {
  try {
    return await import(`../../../src/web/static/modules/studios/chat/${rel}`);
  } catch {
    return {};
  }
}

async function need(rel, name) {
  const m = await load(rel);
  expect(typeof m[name], `chat/${rel} must export ${name}`).toBe('function');
  return m[name];
}

const json = (body, ok = true) => ({ ok, status: ok ? 200 : 500, json: async () => body });

function selectDeps(state, extra = {}) {
  return {
    loadMessages: vi.fn(async () => {}),
    refreshPendingHitl: vi.fn(async () => {}),
    refreshWorkbenchArtifactCount: vi.fn(async () => {}),
    setJobPhaseState: vi.fn(),
    setInlineJobChromeModel: vi.fn(),
    jumpToLatest: vi.fn(),
    fetchFn: vi.fn(async () => json({ jobs: [] })),
    queryStatusFn: vi.fn(async (id) => ({ session_id: id, is_running: false })),
    getEl: () => null,
    ...extra,
  };
}

describe('CARD-488 switching chats during your own reply', () => {
  it('REQ-488-001/004: the tracker detaches only the browser stream and retires the turn', async () => {
    const createOwnStreamTracker = await need('own_stream.js', 'createOwnStreamTracker');
    const state = { isStreaming: false };
    const onDetach = vi.fn();
    const tracker = createOwnStreamTracker(state, { onDetach });
    const controller = { abort: vi.fn() };
    const token = tracker.begin('A', controller);
    expect(state.isStreaming).toBe(true);
    expect(tracker.isCurrent(token)).toBe(true);
    expect(tracker.sessionId()).toBe('A');
    expect(tracker.controller()).toBe(controller);
    expect(tracker.detach()).toBe('A');
    expect(controller.abort).toHaveBeenCalledTimes(1);
    expect(onDetach).toHaveBeenCalledTimes(1);
    expect(state.isStreaming).toBe(false);
    expect(tracker.isCurrent(token)).toBe(false);
    expect(tracker.sessionId()).toBe(null);
    expect(tracker.detach()).toBe(null); // nothing attached: no second abort
    expect(controller.abort).toHaveBeenCalledTimes(1);
  });

  it('REQ-488-001: picking another chat detaches before loading it, with streaming cleared', async () => {
    const createSessionSelect = await need('session_select.js', 'createSessionSelect');
    const state = { activeSessionId: 'B', sessions: [], isStreaming: true };
    const order = [];
    const deps = selectDeps(state, {
      getStreamSessionId: () => (state.isStreaming ? 'A' : null),
      detachOwnStream: vi.fn(() => { order.push('detach'); state.isStreaming = false; }),
      loadMessages: vi.fn(async (id) => { order.push(`load ${id} streaming=${state.isStreaming}`); }),
    });
    await createSessionSelect(state, deps).afterSelect('B', { userPick: true });
    expect(deps.detachOwnStream).toHaveBeenCalledTimes(1);
    expect(order[0]).toBe('detach');
    expect(order).toContain('load B streaming=false');
  });

  it('REQ-488-008: re-selecting the chat that is streaming keeps the stream attached', async () => {
    const createSessionSelect = await need('session_select.js', 'createSessionSelect');
    const state = { activeSessionId: 'A', sessions: [], isStreaming: true };
    const deps = selectDeps(state, { getStreamSessionId: () => 'A', detachOwnStream: vi.fn() });
    await createSessionSelect(state, deps).afterSelect('A');
    expect(deps.detachOwnStream).not.toHaveBeenCalled();
  });

  it('REQ-488-004: a detached turn cannot touch the view any more', async () => {
    const createOwnStreamTracker = await need('own_stream.js', 'createOwnStreamTracker');
    const state = { isStreaming: false };
    const tracker = createOwnStreamTracker(state);
    const old = tracker.begin('A', { abort: () => {} });
    tracker.detach();
    const fresh = tracker.begin('B', { abort: () => {} });
    const write = vi.fn(() => 'wrote');
    expect(tracker.runIfCurrent(old, write)).toBeUndefined();
    expect(write).not.toHaveBeenCalled();
    expect(tracker.end(old)).toBe(false); // the old turn's finally must not reset the new turn
    expect(state.isStreaming).toBe(true);
    expect(tracker.sessionId()).toBe('B');
    expect(tracker.runIfCurrent(fresh, write)).toBe('wrote');
    expect(tracker.end(fresh)).toBe(true);
    expect(state.isStreaming).toBe(false);
  });

  it('REQ-488-006: Stop aborts this tab\'s streaming chat, else the open chat', async () => {
    const createStopHandler = await need('stop.js', 'createStopHandler');
    const fetchFn = vi.fn(async () => json({ status: 'aborted' }));
    const base = { fetchFn, loadMessages: vi.fn(async () => {}), recheckStatus: vi.fn(async () => {}), showToast: vi.fn() };
    await createStopHandler({ activeSessionId: 'B', isStreaming: true }, {
      ...base, getStreamSessionId: () => 'A', getController: () => ({ abort: () => {} }),
    }).stop();
    expect(fetchFn.mock.calls[0][0]).toBe('/api/chat/stream/A/abort');
    await createStopHandler({ activeSessionId: 'B', sessionBusy: true }, { ...base, getStreamSessionId: () => null }).stop();
    expect(fetchFn.mock.calls[1][0]).toBe('/api/chat/stream/B/abort');
  });

  it('REQ-488-005: back on the chat whose reply was detached, the running reply shows busy', async () => {
    const createOwnStreamTracker = await need('own_stream.js', 'createOwnStreamTracker');
    const { createSessionStatusWatcher } = await load('session_select.js');
    const state = { activeSessionId: 'A', isStreaming: false };
    const tracker = createOwnStreamTracker(state);
    tracker.begin('A', { abort: () => {} });
    tracker.detach();
    const setBusy = vi.fn();
    const watcher = createSessionStatusWatcher(state, {
      queryStatusFn: async () => ({ is_running: true }), setBusy,
      setIntervalFn: () => 1, clearIntervalFn: () => {},
    });
    await watcher.watch('A');
    expect(setBusy).toHaveBeenCalledWith(true);
  });

  it('REQ-488-007: switching agent during a reply opens that agent\'s chat', async () => {
    const loadSessions = await need('chrome.js', 'loadSessions');
    const state = { selectedAgentId: 'x-agent', activeSessionId: 'A', isStreaming: true, sessions: [] };
    const selectSessionFn = vi.fn(async () => {});
    const fetchFn = vi.fn(async () => json([{ id: 'X1', agent_id: 'x-agent', title: 'x chat', created_at: '2026-09-25T10:00:00', updated_at: '2026-09-25T10:00:00' }]));
    await loadSessions(state, { sessionList: null, selectSessionFn, fetchFn, storedSessionId: null });
    expect(selectSessionFn).toHaveBeenCalledWith('X1');
  });

  it('wiring: chat.js tracks its own stream and passes detach + stream id to select and Stop', () => {
    const root = path.resolve(__dirname, '../../../src/web/static/modules/studios');
    const chat = fs.readFileSync(path.join(root, 'chat.js'), 'utf8');
    const chrome = fs.readFileSync(path.join(root, 'chat/chrome.js'), 'utf8');
    expect(chat).toMatch(/import\s*\{[^}]*createOwnStreamTracker[^}]*\}\s*from\s*'\.\/chat\/own_stream\.js'/);
    expect(chat).toMatch(/detachOwnStream:/);
    expect(chat).toMatch(/getStreamSessionId:/);
    expect(chat).not.toMatch(/let activeAbortController/);
    expect(chrome).not.toMatch(/stillThere \|\| state\.isStreaming/);
    expect(chat.split('\n').length).toBeLessThanOrEqual(1045);
  });
});
