/**
 * Chat Studio: session guard [CARD-476]
 * A chat always has a session before anything is sent or uploaded, and the last chat opened
 * on this device is reopened on load. The backend stays strict (a null session_id is a 422, D3).
 */

import { storageGet } from '../../utils/storage.js';

/** localStorage key holding this device's last opened chat (written by selectSession). */
export const LAST_SESSION_KEY = 'autoreiv_active_session_id';

export function readStoredSessionId() {
  return storageGet(LAST_SESSION_KEY, null);
}

/**
 * Which chat to open when none is active [REQ-476-004, D2/D5]: the stored id if it is in this
 * agent's list, otherwise the newest (the list comes newest first). Null for an empty list.
 */
export function pickSessionToOpen(sessions, storedId = null) {
  const list = Array.isArray(sessions) ? sessions : [];
  if (list.length === 0) return null;
  if (storedId && list.some((s) => s && s.id === storedId)) return storedId;
  return list[0].id;
}

/**
 * Run `run` once per key (and tag) at a time; callers that arrive while it is in flight share
 * the same promise [REQ-476-005]. The slot clears itself when the run settles.
 */
export function singleFlight(state, key, run, tag = null) {
  const current = state[key];
  if (current && current.tag === tag) return current.promise;
  const promise = Promise.resolve()
    .then(run)
    .finally(() => {
      if (state[key] && state[key].promise === promise) state[key] = null;
    });
  state[key] = { promise, tag };
  return promise;
}

/** Remember the latest session-list load so a send can wait for it [REQ-476-003]. */
export function trackSessionsLoad(state, promise) {
  const p = Promise.resolve(promise);
  state.sessionsLoading = p;
  const clear = () => {
    if (state.sessionsLoading === p) state.sessionsLoading = null;
  };
  p.then(clear, clear);
  return p;
}

/**
 * Make sure a chat session is active and return its id, or null if one could not be made
 * [REQ-476-001/003/005/006]. Waits for an in-flight load first, then creates at most one.
 */
export function ensureActiveSession(state, { createNewSession = null, showToastFn = null } = {}) {
  if (state.activeSessionId && !state.sessionsLoading) return Promise.resolve(state.activeSessionId);
  return singleFlight(state, 'sessionEnsuring', async () => {
    // Wait for any load in flight (it may switch the active chat, e.g. on agent switch).
    for (let i = 0; i < 5 && state.sessionsLoading; i += 1) {
      try {
        await state.sessionsLoading;
      } catch {
        /* a failed load falls through to create */
      }
    }
    if (!state.activeSessionId && typeof createNewSession === 'function') {
      try {
        await createNewSession();
      } catch (err) {
        console.error('[AutoReiv UI] Failed to create session:', err);
      }
    }
    if (state.activeSessionId) return state.activeSessionId;
    if (typeof showToastFn === 'function') showToastFn("Couldn't start a new chat. Please try again.", 'error');
    return null;
  }, state.selectedAgentId || null);
}

/**
 * Delete a chat session via DELETE /api/sessions/{id} and update state.sessions [CARD-696].
 */
export async function deleteSession(state, sessionId, opts = {}) {
  if (!sessionId) return false;
  const fetchFn = opts.fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
  const selectSessionFn = opts.selectSessionFn || opts.onSelectSession || null;
  const createNewSessionFn = opts.createNewSessionFn || null;
  const sessionList = opts.sessionList || null;
  const showToastFn = opts.showToastFn || null;
  const renderSessionListFn = opts.renderSessionListFn || null;
  try {
    const res = await fetchFn(`/api/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' });
    if (!res || !res.ok) throw new Error(`HTTP ${res ? res.status : 'error'}`);
    state.sessions = (state.sessions || []).filter((s) => s.id !== sessionId);
    if (state.activeSessionId === sessionId) {
      state.activeSessionId = null;
      const next = state.sessions[0];
      if (next && typeof selectSessionFn === 'function') {
        await selectSessionFn(next.id);
      } else if (typeof createNewSessionFn === 'function') {
        await createNewSessionFn();
      }
    }
    if (typeof renderSessionListFn === 'function') {
      renderSessionListFn({
        sessionList,
        sessions: state.sessions,
        activeSessionId: state.activeSessionId,
        onSelectSession: selectSessionFn,
      });
    }
    if (typeof showToastFn === 'function') showToastFn('Conversation deleted.', 'info');
    return true;
  } catch (err) {
    console.error('[AutoReiv UI] Failed to delete session:', err);
    if (typeof showToastFn === 'function') showToastFn(`Delete failed: ${err.message}`, 'error');
    return false;
  }
}

