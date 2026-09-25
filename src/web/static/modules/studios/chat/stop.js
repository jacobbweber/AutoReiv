/**
 * CARD-486: Stop tells the server to stop.
 *
 * Pre-split Stop (7b563003^ chat.js L3528-3556) POSTed `/api/chat/stream/{id}/abort`; the CARD-397
 * split dropped it, so the model kept generating after Stop (CARD-154 keeps work alive when the
 * browser disconnects) and held the only generation slot. One path for this tab's own reply and for
 * a reply running on another device (CARD-485 busy state) [REQ-486-001..003, 005, 008; D1, D2, D7].
 */

export const STOPPED_TOAST = 'Stopped';
export const STOP_FAILED_TOAST = "Couldn't reach the server to stop the reply. It may still finish.";

export function abortUrl(sessionId) {
  return `/api/chat/stream/${encodeURIComponent(sessionId)}/abort`;
}

/** POST the server abort. Resolves true on a 2xx answer, false on any failure (never throws). */
export async function postStreamAbort(sessionId, fetchFn = null) {
  try {
    const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
    const res = await fn(abortUrl(sessionId), { method: 'POST' });
    return Boolean(res && res.ok);
  } catch {
    return false;
  }
}

function showSend(sendBtn, stopBtn) {
  if (sendBtn) {
    sendBtn.disabled = false;
    sendBtn.classList.remove('hidden');
  }
  if (stopBtn) {
    stopBtn.disabled = true;
    stopBtn.classList.add('hidden');
  }
}

/**
 * Build the Stop handler. `stop()` is single-flight: presses while the abort is pending reuse it.
 * Order: cancel this tab's request, POST /abort, stop the status watch and clear busy, restore Send,
 * reload the chat, re-check status once, then toast.
 */
export function createStopHandler(state, deps = {}) {
  const {
    getController = () => null,
    getStreamSessionId = () => null, // CARD-488: Stop targets this tab's streaming chat first
    clearController = () => {},
    stopWatching = () => {},
    setBusy = () => {},
    sendBtn = null,
    stopBtn = null,
    loadMessages = async () => {},
    recheckStatus = async () => {},
    showToast = () => {},
    fetchFn = null,
  } = deps;
  let pending = null;

  async function run() {
    const sessionId = getStreamSessionId() || state.activeSessionId;
    const controller = getController();
    if (controller) {
      try {
        controller.abort();
      } catch {
        // already aborted
      }
      clearController();
    }
    if (!sessionId) {
      showSend(sendBtn, stopBtn);
      return false;
    }
    const ok = await postStreamAbort(sessionId, fetchFn);
    stopWatching();
    setBusy(false);
    showSend(sendBtn, stopBtn);
    if (state.activeSessionId === sessionId) {
      try {
        await loadMessages(sessionId);
        await recheckStatus(sessionId);
      } catch (err) {
        console.warn('[AutoReiv UI] CARD-486 reload after Stop soft-fail:', err);
      }
    }
    if (ok) showToast(STOPPED_TOAST, 'info');
    else showToast(STOP_FAILED_TOAST, 'warning');
    return ok;
  }

  function stop() {
    if (!pending) {
      pending = run().finally(() => {
        pending = null;
      });
    }
    return pending;
  }

  return { stop };
}
