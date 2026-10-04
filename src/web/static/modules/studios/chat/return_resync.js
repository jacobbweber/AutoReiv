/**
 * Chat Studio: catch up when the tab or window comes back [CARD-473, REQ-MOB-STREAM-002, CARD-154].
 * Pre-split chat.js L3884-3903 listened for visibilitychange (visible) and window focus, re-checked the
 * running status, then reloaded messages and pending approvals unless this tab was streaming.
 */

export const RETURN_RESYNC_GAP_MS = 1500; // visibilitychange and focus usually fire together

export function setupReturnResync(state, {
  watchStatus = async () => null,
  loadMessages = async () => {},
  refreshPendingHitl = async () => {},
  doc = typeof document !== 'undefined' ? document : null,
  win = typeof window !== 'undefined' ? window : null,
  now = () => Date.now(),
  gapMs = RETURN_RESYNC_GAP_MS,
} = {}) {
  let last = -Infinity;

  async function resync() {
    if (doc && doc.visibilityState === 'hidden') return false;
    const sessionId = state.activeSessionId;
    if (!sessionId) return false;
    const t = now();
    if (t - last < gapMs) return false;
    last = t;
    try {
      await watchStatus(sessionId); // busy + 2 s poll while a reply still runs elsewhere (CARD-485)
      if (state.isStreaming || state.activeSessionId !== sessionId) return false; // REQ-473-002
      await loadMessages(sessionId);
      await refreshPendingHitl();
      return true;
    } catch (err) {
      console.warn('Chat resync after return failed:', err);
      return false;
    }
  }

  if (doc) doc.addEventListener('visibilitychange', () => { resync(); });
  if (win) win.addEventListener('focus', () => { resync(); });
  return { resync };
}
