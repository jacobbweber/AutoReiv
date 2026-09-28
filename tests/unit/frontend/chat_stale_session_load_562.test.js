import { describe, it, expect, vi } from 'vitest';

import { loadSessions } from '../../../src/web/static/modules/studios/chat/chrome.js';

/**
 * CARD-562 - an API-created Developer chat vanished: the startup AutoReiv load (no chats) finished
 * after the switch to Developer and created "Developer Chat" for the new agent. A stale load
 * (the selected agent changed while it was in flight) must not render, open or create a chat.
 */
describe('loadSessions ignores a stale load after an agent switch (CARD-562)', () => {
  it('does not create or open a chat when the agent changed mid-load', async () => {
    const state = { selectedAgentId: 'autoreiv', activeSessionId: null, sessions: [] };
    let release;
    const gate = new Promise((r) => { release = r; });
    const fetchFn = vi.fn(async () => { await gate; return { ok: true, json: async () => [] }; });
    const createNewSessionFn = vi.fn();
    const selectSessionFn = vi.fn();
    const pending = loadSessions(state, { fetchFn, createNewSessionFn, selectSessionFn, storedSessionId: null });
    state.selectedAgentId = 'developer'; // user switched while the autoreiv list was loading
    release();
    await pending;
    expect(fetchFn.mock.calls[0][0]).toContain('agent_id=autoreiv');
    expect(createNewSessionFn).not.toHaveBeenCalled();
    expect(selectSessionFn).not.toHaveBeenCalled();
    expect(state.sessions).toEqual([]);
  });

  it('still opens the newest chat, e.g. one created through the API, when nothing changed', async () => {
    const state = { selectedAgentId: 'developer', activeSessionId: null, sessions: [] };
    const list = [{ id: 'api-made', title: 'QA 562' }, { id: 'old', title: 'Developer Chat' }];
    const fetchFn = vi.fn(async () => ({ ok: true, json: async () => list }));
    const createNewSessionFn = vi.fn();
    const selectSessionFn = vi.fn();
    await loadSessions(state, { fetchFn, createNewSessionFn, selectSessionFn, storedSessionId: null });
    expect(selectSessionFn).toHaveBeenCalledWith('api-made');
    expect(createNewSessionFn).not.toHaveBeenCalled();
  });
});
