/**
 * Chat Studio: Auto-run and Self-Verify runtime toggles [CARD-470].
 * Restores the remembered Auto-run choice, keeps state and chips in sync, and resets a
 * pre-fix saved 'run' to 'ask' once (the UI hid that value from 2026-09-20 to the fix).
 * Unchecked Auto-run always means approval_mode "ask" (fail safe).
 */

import { storageGet, storageSet } from '../../utils/storage.js';
import { subscribeAgentsLoaded } from '../../state/store.js';
import {
  APPROVAL_AUTORUN_STORAGE_KEY,
  readLastApprovalAutoRun,
  writeLastApprovalAutoRun,
} from './hitl.js';

export { APPROVAL_AUTORUN_STORAGE_KEY };
export const APPROVAL_RESET_MARKER_KEY = 'autoreiv_approval_autorun_reset_470';

/** One-time reset of a saved 'run' to 'ask' [REQ-470-007]. Returns true if it reset. */
export function resetSavedAutoRunOnce({ reader = storageGet, writer = storageSet } = {}) {
  try {
    if (reader(APPROVAL_RESET_MARKER_KEY, '')) return false;
    const wasRun = readLastApprovalAutoRun(reader);
    if (wasRun) writeLastApprovalAutoRun(false, writer);
    writer(APPROVAL_RESET_MARKER_KEY, '1');
    return wasRun;
  } catch {
    return false;
  }
}

function byId(id) {
  return typeof document !== 'undefined' && typeof document.getElementById === 'function' ? document.getElementById(id) : null;
}

function showChip(chip, on) {
  if (chip && chip.classList && typeof chip.classList.toggle === 'function') {
    chip.classList.toggle('hidden', !on);
  }
}

/** Wire #approvalToggle / #verifyToggle to state, storage and chips [REQ-470-003..006]. */
export function setupRuntimeModeToggles(
  state,
  { approvalToggle, verifyToggle, approvalBadge, verifyBadge, reader = storageGet, writer = storageSet } = {},
) {
  resetSavedAutoRunOnce({ reader, writer });
  const autoRun = Boolean(approvalToggle) && readLastApprovalAutoRun(reader);
  if (approvalToggle) approvalToggle.checked = autoRun;
  state.approvalAutoRun = autoRun;
  showChip(approvalBadge, autoRun);
  approvalToggle?.addEventListener('change', (e) => {
    state.approvalAutoRun = Boolean(e.target.checked);
    // CARD-573: with the agent's Always auto-run on, a change is this chat's choice only.
    if (state.autoRunFromAgent && state.activeSessionId) writeChatAutoRunChoice(state.activeSessionId, state.approvalAutoRun, { reader, writer });
    else writeLastApprovalAutoRun(state.approvalAutoRun, writer);
    showChip(approvalBadge, state.approvalAutoRun);
  });
  // CARD-573: re-apply the agent's Always auto-run when the roster (re)loads.
  subscribeAgentsLoaded(() => { if (state.activeSessionId) applySessionAutoRun(state, { approvalToggle, approvalBadge, reader }); });

  state.verifyEnabled = Boolean(verifyToggle && verifyToggle.checked);
  showChip(verifyBadge, state.verifyEnabled);
  verifyToggle?.addEventListener('change', (e) => {
    state.verifyEnabled = Boolean(e.target.checked);
    showChip(verifyBadge, state.verifyEnabled);
  });
}

/**
 * CARD-572 D1A: the Run as a job box. Never remembered, off on load, unticks itself after each send.
 * It is the only way a chat message becomes a standing Job (no keyword routing).
 */
export function setupRunAsJobToggle(state, { runAsJobToggle, runAsJobBadge } = {}) {
  if (runAsJobToggle) runAsJobToggle.checked = false;
  state.runAsJob = false;
  showChip(runAsJobBadge, false);
  runAsJobToggle?.addEventListener('change', (e) => {
    state.runAsJob = Boolean(e.target.checked);
    showChip(runAsJobBadge, state.runAsJob);
  });
}

/** Set the Run as a job box (restore after a refused send). */
export function setRunAsJob(state, on, { runAsJobToggle, runAsJobBadge } = {}) {
  const value = Boolean(on);
  if (runAsJobToggle) runAsJobToggle.checked = value;
  state.runAsJob = value;
  showChip(runAsJobBadge, value);
}

/** Read the box for one send and clear it [CARD-572 D1A]. */
export function takeRunAsJob(state, els = {}) {
  const toggle = els.runAsJobToggle;
  const on = Boolean(toggle ? toggle.checked : state.runAsJob);
  setRunAsJob(state, false, els);
  return on;
}

/** CARD-573: per-chat Auto-run choices for agents with Always auto-run ({sessionId: 'run'|'ask'}). */
export const AUTORUN_CHAT_CHOICES_KEY = 'autoreiv_autorun_chat_choices_573';
const MAX_CHAT_CHOICES = 200;

function readChatChoices(reader = storageGet) {
  try {
    const raw = reader(AUTORUN_CHAT_CHOICES_KEY, '');
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

export function writeChatAutoRunChoice(sessionId, on, { reader = storageGet, writer = storageSet } = {}) {
  const id = String(sessionId || '').trim();
  if (!id) return;
  const choices = readChatChoices(reader);
  delete choices[id];
  choices[id] = on ? 'run' : 'ask';
  const keys = Object.keys(choices);
  while (keys.length > MAX_CHAT_CHOICES) delete choices[keys.shift()];
  try { writer(AUTORUN_CHAT_CHOICES_KEY, JSON.stringify(choices)); } catch { /* storage full: choice lasts until reload */ }
}

/**
 * CARD-573: set the Auto-run box for the chat being shown.
 * Agent with Always auto-run: checked unless Jacob unticked it in this chat. Other agents: the remembered choice (CARD-470).
 */
export function applySessionAutoRun(state, {
  approvalToggle = byId('approvalToggle'),
  approvalBadge = byId('approvalBadge'),
  agent = (state.agents || []).find((a) => a && a.id === state.selectedAgentId),
  sessionId = state.activeSessionId,
  reader = storageGet,
} = {}) {
  const always = Boolean(agent && agent.always_auto_run === true);
  let on;
  if (always) {
    const choice = readChatChoices(reader)[String(sessionId || '')];
    on = choice ? choice === 'run' : true;
  } else {
    on = readLastApprovalAutoRun(reader);
  }
  if (approvalToggle) approvalToggle.checked = on;
  state.approvalAutoRun = on;
  state.autoRunFromAgent = always;
  showChip(approvalBadge, on);
  return on;
}
