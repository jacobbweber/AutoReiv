/**
 * Chat Studio: a failed send keeps the typed text [CARD-484].
 * The composer is cleared before the turn starts. If the turn then fails before any reply streams
 * (server error, network drop, 422), put the sent text back so it does not have to be retyped.
 * Stop (AbortError) and resumes never restore, and text the operator has typed since is never overwritten.
 */

import { escapeHtml } from '../../utils/formatters.js';

export function shouldRestoreFailedSend({ err = null, isResume = false, userPrompt = '', replyStarted = false, composerText = '' } = {}) {
  if (!err || err.name === 'AbortError') return false; // REQ-484-002: Stop keeps the box as it is
  if (isResume || replyStarted) return false;
  if (!String(userPrompt || '').trim()) return false;
  return !String(composerText || '').trim(); // REQ-484-001: only into an empty composer
}

export function restoreFailedSend({ err, isResume = false, userPrompt = '', replyStarted = false, promptInput = null, setText = null } = {}) {
  if (!promptInput || typeof setText !== 'function') return false;
  if (!shouldRestoreFailedSend({ err, isResume, userPrompt, replyStarted, composerText: promptInput.value })) return false;
  setText(promptInput, userPrompt);
  return true;
}

/** The failed-turn path of executeChatTurn: error toast, inline error in the reply bubble, then the text goes back. */
export function showFailedTurn({ err, showToast = null, streamContentEl = null, ...restore } = {}) {
  const message = (err && err.message) || 'unknown error';
  if (typeof showToast === 'function') showToast(`Chat turn failed: ${message}`, 'error');
  if (streamContentEl) streamContentEl.innerHTML = `<span class="text-rose-400">Error: ${escapeHtml(message)}</span>`;
  return restoreFailedSend({ err, ...restore });
}
