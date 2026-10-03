/**
 * CARD-493: Recent Chats shows which chats are replying or waiting for approval.
 * GET /api/sessions carries `is_running` / `waiting_approval`; between list loads, GET /api/sessions/activity
 * refreshes them, once every 5 s at most, only while a listed chat is replying and the page is visible.
 */

export const SESSION_ACTIVITY_URL = '/api/sessions/activity';
export const SESSION_ACTIVITY_POLL_MS = 5000;

export const ACTIVITY_MARKERS = Object.freeze({
  running: { key: 'running', label: 'Replying', cls: 'bg-brand-400 animate-pulse' },
  waiting: { key: 'waiting', label: 'Needs approval', cls: 'bg-amber-400' },
});

/** The marker for one listed chat, or null. Needs approval wins: it is the one that needs you. */
export function sessionActivityMarker(sess) {
  if (!sess) return null;
  if (sess.waiting_approval) return ACTIVITY_MARKERS.waiting;
  if (sess.is_running) return ACTIVITY_MARKERS.running;
  return null;
}

/** Copy an activity answer onto the listed chats. Returns true when any flag changed. */
export function applySessionActivity(sessions, activity) {
  if (!Array.isArray(sessions) || !activity) return false;
  const running = new Set(Array.isArray(activity.running) ? activity.running : []);
  const waiting = new Set(Array.isArray(activity.waiting_approval) ? activity.waiting_approval : []);
  let changed = false;
  sessions.forEach((s) => {
    if (!s) return;
    const r = running.has(s.id);
    const w = waiting.has(s.id);
    if (Boolean(s.is_running) !== r || Boolean(s.waiting_approval) !== w) changed = true;
    s.is_running = r;
    s.waiting_approval = w;
  });
  return changed;
}

export function anySessionRunning(sessions) {
  return Array.isArray(sessions) && sessions.some((s) => s && s.is_running);
}

const pageVisible = () => typeof document === 'undefined' || document.visibilityState !== 'hidden';

/**
 * `kick()` refreshes now (single-flight); while any listed chat is replying it refreshes again every
 * `intervalMs`. `onChange()` re-renders the list.
 */
export function createSessionActivityPoller(state, {
  fetchFn = null,
  onChange = () => {},
  intervalMs = SESSION_ACTIVITY_POLL_MS,
  isPageVisible = pageVisible,
  setTimeoutFn = (fn, ms) => setTimeout(fn, ms),
  clearTimeoutFn = (id) => clearTimeout(id),
} = {}) {
  let timer = null;
  let inFlight = null;

  function schedule() {
    if (timer != null) return;
    timer = setTimeoutFn(() => {
      timer = null;
      if (isPageVisible()) kick();
      else schedule();
    }, intervalMs);
  }

  function stop() {
    if (timer != null) clearTimeoutFn(timer);
    timer = null;
  }

  function kick() {
    if (inFlight) return inFlight;
    inFlight = (async () => {
      try {
        const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
        const res = await fn(SESSION_ACTIVITY_URL);
        if (!res || !res.ok) return false;
        const data = await res.json();
        if (applySessionActivity(state.sessions, data)) onChange();
        return true;
      } catch {
        return false;
      } finally {
        if (anySessionRunning(state.sessions)) schedule();
        else stop();
      }
    })().finally(() => {
      inFlight = null;
    });
    return inFlight;
  }

  return { kick, stop, isPolling: () => timer != null };
}
