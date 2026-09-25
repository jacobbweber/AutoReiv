/**
 * Chat Studio: Auto-run and Self-Verify runtime toggles [CARD-470].
 * Restores the remembered Auto-run choice, keeps state and chips in sync, and resets a
 * pre-fix saved 'run' to 'ask' once (the UI hid that value from 2026-09-20 to the fix).
 * Unchecked Auto-run always means approval_mode "ask" (fail safe).
 */

import { storageGet, storageSet } from '../../utils/storage.js';
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
    writeLastApprovalAutoRun(state.approvalAutoRun, writer);
    showChip(approvalBadge, state.approvalAutoRun);
  });

  state.verifyEnabled = Boolean(verifyToggle && verifyToggle.checked);
  showChip(verifyBadge, state.verifyEnabled);
  verifyToggle?.addEventListener('change', (e) => {
    state.verifyEnabled = Boolean(e.target.checked);
    showChip(verifyBadge, state.verifyEnabled);
  });
}
