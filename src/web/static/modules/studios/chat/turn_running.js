/**
 * Chat Studio: turn already running [CARD-530 REQ-530-003]
 * POST /api/chat/stream answers 409 {reason: "turn_running"} while this session still has a live turn.
 * That is not a failed reply: drop the empty bubble, give the typed text back, say so gently, reload.
 */

export const TURN_RUNNING_MESSAGE = 'A reply is still running in this chat. Wait for it to finish, or press Stop.';

export async function handleTurnRunning({
  state, streamBubble = null, isResume = false, userPrompt = '', restoreComposer = null, showToast = null, loadMessages = null,
} = {}) {
  if (streamBubble && typeof streamBubble.remove === 'function') streamBubble.remove();
  if (!isResume && userPrompt) {
    if (state && Array.isArray(state.messages)) state.messages.pop();
    if (typeof restoreComposer === 'function') restoreComposer(userPrompt);
  }
  if (typeof showToast === 'function') showToast(TURN_RUNNING_MESSAGE, 'warning');
  if (state && state.activeSessionId && typeof loadMessages === 'function') await loadMessages(state.activeSessionId);
}
