import { describe, it, expect, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { setupComposerControls, setupComposerAttachments } from '../../../src/web/static/modules/studios/chat/composer.js';
import { loadSessions } from '../../../src/web/static/modules/studios/chat/chrome.js';

/**
 * CARD-476 - the first Chat message with no session must not post `session_id: null` (422).
 * D1: create on load / agent switch plus a send guard. D2/D5: restore this device's last chat
 * when it is in the current agent's list, else newest. D3: the backend stays strict.
 */

const here = dirname(fileURLToPath(import.meta.url));
const CHAT_JS = resolve(here, '../../../src/web/static/modules/studios/chat.js');

// Loaded lazily so a missing module fails each test, not the whole file.
async function guardModule() {
  try {
    return await import('../../../src/web/static/modules/studios/chat/session_guard.js');
  } catch {
    return {};
  }
}

async function ensure(state, opts) {
  const mod = await guardModule();
  expect(typeof mod.ensureActiveSession, 'session_guard.js must export ensureActiveSession').toBe('function');
  return mod.ensureActiveSession(state, opts);
}

const tick = (ms = 0) => new Promise((r) => setTimeout(r, ms));

function fakeForm() {
  const handlers = {};
  return {
    handlers,
    addEventListener(type, fn) { handlers[type] = fn; },
    submit: () => handlers.submit({ preventDefault() {} }),
  };
}

function fakeInput(value) {
  return { value, dispatchEvent() {}, focus() {} };
}

function jsonResponse(body, ok = true) {
  return { ok, status: ok ? 200 : 500, json: async () => body };
}

describe('CARD-476 ensureActiveSession', () => {
  it('1. returns the active session without creating one', async () => {
    const createNewSession = vi.fn();
    const state = { selectedAgentId: 'autoreiv', activeSessionId: 'live-1' };
    expect(await ensure(state, { createNewSession })).toBe('live-1');
    expect(createNewSession).not.toHaveBeenCalled();
  });

  it('2. waits for an in-flight session load and uses what it selected (REQ-476-003)', async () => {
    const createNewSession = vi.fn();
    const state = { selectedAgentId: 'autoreiv', activeSessionId: null };
    state.sessionsLoading = tick(20).then(() => { state.activeSessionId = 'loaded-1'; });
    expect(await ensure(state, { createNewSession })).toBe('loaded-1');
    expect(createNewSession).not.toHaveBeenCalled();
  });

  it('3. creates a session when none is active and nothing is loading (REQ-476-001)', async () => {
    const state = { selectedAgentId: 'autoreiv', activeSessionId: null };
    const createNewSession = vi.fn(async () => { state.activeSessionId = 'new-1'; });
    expect(await ensure(state, { createNewSession })).toBe('new-1');
    expect(createNewSession).toHaveBeenCalledTimes(1);
  });

  it('4. two concurrent sends create exactly one session (REQ-476-005)', async () => {
    const state = { selectedAgentId: 'autoreiv', activeSessionId: null };
    const createNewSession = vi.fn(async () => { await tick(20); state.activeSessionId = 'new-2'; });
    const [a, b] = await Promise.all([ensure(state, { createNewSession }), ensure(state, { createNewSession })]);
    expect([a, b]).toEqual(['new-2', 'new-2']);
    expect(createNewSession).toHaveBeenCalledTimes(1);
  });

  it('5. a failed create returns null and shows an error toast (REQ-476-006)', async () => {
    const state = { selectedAgentId: 'autoreiv', activeSessionId: null };
    const createNewSession = vi.fn(async () => null);
    const showToastFn = vi.fn();
    expect(await ensure(state, { createNewSession, showToastFn })).toBe(null);
    expect(showToastFn).toHaveBeenCalledWith(expect.stringMatching(/couldn.t start a new chat/i), 'error');
  });
});

describe('CARD-476 composer submit', () => {
  it('6. submit with no session runs the guard before the turn, or keeps the text if it fails', async () => {
    const order = [];
    const form = fakeForm();
    const input = fakeInput('hi');
    const state = { selectedAgentId: 'autoreiv', activeSessionId: null, isStreaming: false, stagedAttachments: [] };
    const ensureSession = vi.fn(async () => { order.push('ensure'); state.activeSessionId = 's-1'; return 's-1'; });
    const onExecuteTurn = vi.fn(async () => { order.push('turn'); });
    setupComposerControls({ chatForm: form, promptInput: input, state, onExecuteTurn, ensureSession });
    await form.submit();
    expect(order).toEqual(['ensure', 'turn']);
    expect(onExecuteTurn).toHaveBeenCalledWith('hi');

    const form2 = fakeForm();
    const input2 = fakeInput('keep me');
    const state2 = { selectedAgentId: 'autoreiv', activeSessionId: null, isStreaming: false, stagedAttachments: [] };
    const onExecuteTurn2 = vi.fn();
    setupComposerControls({ chatForm: form2, promptInput: input2, state: state2, onExecuteTurn: onExecuteTurn2, ensureSession: async () => null });
    await form2.submit();
    expect(onExecuteTurn2).not.toHaveBeenCalled();
    expect(input2.value).toBe('keep me');
  });
});

describe('CARD-476 session list load', () => {
  it('7. an empty list creates a session, and chat.js wires createNewSessionFn (REQ-476-002)', async () => {
    const state = { selectedAgentId: 'autoreiv', activeSessionId: null, sessions: [] };
    const createNewSessionFn = vi.fn(async () => {});
    await loadSessions(state, { fetchFn: async () => jsonResponse([]), createNewSessionFn });
    expect(createNewSessionFn).toHaveBeenCalledTimes(1);

    const src = readFileSync(CHAT_JS, 'utf8');
    const call = src.slice(src.indexOf('loadSessionsDirect(state'), src.indexOf('loadSessionsDirect(state') + 400);
    expect(call).toMatch(/createNewSessionFn:\s*createNewSession/);
  });

  it('8. restores the stored session when it is in the list, else the newest (REQ-476-004)', async () => {
    const list = [{ id: 'newest' }, { id: 'older' }];
    const picked = [];
    const state = { selectedAgentId: 'autoreiv', activeSessionId: null, sessions: [] };
    await loadSessions(state, {
      fetchFn: async () => jsonResponse(list),
      onSelectSession: async (id) => { picked.push(id); },
      storedSessionId: 'older',
    });
    const state2 = { selectedAgentId: 'autoreiv', activeSessionId: null, sessions: [] };
    await loadSessions(state2, {
      fetchFn: async () => jsonResponse(list),
      onSelectSession: async (id) => { picked.push(id); },
      storedSessionId: 'other-agents-session',
    });
    expect(picked).toEqual(['older', 'newest']);
  });
});

describe('CARD-476 attach', () => {
  it('9. attaching with no session waits for the guard, so the upload carries the session (REQ-476-007)', async () => {
    const state = { activeSessionId: null };
    const handlers = {};
    const chatFileInput = { value: '', click() {}, addEventListener(t, fn) { handlers[t] = fn; } };
    const chatAttachBtn = { addEventListener() {} };
    const sent = [];
    const fetchFn = vi.fn(async (_url, init) => {
      sent.push(init.body.get('session_id'));
      return jsonResponse({ id: 'u1', filename: 'a.png', size_bytes: 1, content_type: 'image/png', url: '/x', path: '/x' });
    });
    setupComposerAttachments({
      chatAttachBtn,
      chatFileInput,
      chatAttachmentsPreviewList: null,
      getStagedAttachments: () => [],
      getSessionId: () => state.activeSessionId,
      onBeforeAttach: async () => { await tick(20); state.activeSessionId = 'att-1'; },
      fetchFn,
    });
    await handlers.change({ target: { files: [new Blob(['x'], { type: 'image/png' })] } });
    expect(sent).toEqual(['att-1']);
  });
});
