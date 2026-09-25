/**
 * CARD-488: this tab's own reply, tracked apart from the chat on screen.
 *
 * `state.isStreaming` used to mean both "this tab is streaming" and "the open chat is streaming", so
 * picking another chat mid-reply kept the old chat on screen (render skipped while streaming) and the
 * composer ignored Enter. The tracker holds the running turn `{sessionId, controller, token}`:
 * - `begin` starts a turn and returns its token; `end(token)` finishes it only if still current;
 * - `detach()` (switching chat / New chat / agent) cancels only the browser request - the server
 *   keeps going [CARD-154, D1] - clears streaming, removes the stream bubble and restores Send;
 * - a retired token can no longer touch the view (`isCurrent` / `runIfCurrent`) [REQ-488-004].
 */

function restoreSend(sendBtn, stopBtn) {
  if (sendBtn) {
    sendBtn.disabled = false;
    sendBtn.classList.remove('hidden');
  }
  if (stopBtn) {
    stopBtn.disabled = true;
    stopBtn.classList.add('hidden');
  }
}

export function createOwnStreamTracker(state, { sendBtn = null, stopBtn = null, messagesContainer = null, onDetach = () => {} } = {}) {
  let current = null;
  let seq = 0;

  const isCurrent = (token) => Boolean(current) && current.token === token;

  function begin(sessionId, controller) {
    seq += 1;
    current = { sessionId: sessionId || null, controller: controller || null, token: seq };
    state.isStreaming = true;
    return seq;
  }

  function end(token) {
    if (!isCurrent(token)) return false;
    current = null;
    state.isStreaming = false;
    return true;
  }

  function detach() {
    if (!current) return null;
    const { sessionId, controller } = current;
    current = null;
    state.isStreaming = false;
    try {
      if (controller) controller.abort();
    } catch {
      // already aborted
    }
    if (messagesContainer && typeof messagesContainer.querySelectorAll === 'function') {
      messagesContainer.querySelectorAll('[data-stream-bubble]').forEach((el) => el.remove());
    }
    restoreSend(sendBtn, stopBtn);
    onDetach(sessionId);
    return sessionId;
  }

  return {
    begin,
    end,
    detach,
    isCurrent,
    runIfCurrent: (token, fn) => (isCurrent(token) ? fn() : undefined),
    sessionId: () => (current ? current.sessionId : null),
    controller: () => (current ? current.controller : null),
  };
}
