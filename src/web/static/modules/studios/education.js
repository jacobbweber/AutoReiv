/**
 * Education Studio [CARD-315, ADR-0059]: the operator bar (CARD-447) and the Flashcard / Quiz / Test
 * players (CARD-448). Study conversations happen with Tutor (Pair Tutor, CARD-437).
 *
 * CARD-463 (Jacob, 2026-09-30): the legacy Learning OS panels are gone - Study Launcher, course chrome,
 * Jump to step, Delivery Profile, Pedagogy Style, Wiki Grounding, the eight lab sections and the
 * browser-only Education Jobs list. The Learning OS APIs and Tutor tools stay.
 */

import { safeCreateIcons } from '../dom.js';

/** Browser-only list the removed launcher kept; cleared once on Studio init [REQ-463-006]. */
export const LEGACY_EDUCATION_SESSIONS_KEY = 'autoreiv.education.sessions.v1';

export function clearLegacyEducationSessions(storage = (typeof localStorage !== 'undefined' ? localStorage : null)) {
  try {
    if (storage && storage.getItem(LEGACY_EDUCATION_SESSIONS_KEY) !== null) {
      storage.removeItem(LEGACY_EDUCATION_SESSIONS_KEY);
      return true;
    }
  } catch {
    /* storage unavailable (private mode): nothing to clear */
  }
  return false;
}

function loadModule(label, loader, start) {
  try {
    loader().then(start).catch((err) => console.warn(`[Education Studio] ${label} module failed to load`, err));
  } catch (err) {
    console.warn(`[Education Studio] ${label} init skipped`, err);
  }
}

export function initEducationStudio(state, callbacks = {}) {
  clearLegacyEducationSessions();

  // CARD-447: operator bar (topic box, Set active, Pair Tutor, Due, Progress, Wiki curate).
  loadModule('operator', () => import('./education_operator.js'), (mod) => {
    if (mod && typeof mod.initEducationStudioOperator === 'function') {
      mod.initEducationStudioOperator({
        showToast: callbacks.showToast,
        switchTab: callbacks.switchTab,
        getChatCtrl: callbacks.getChatCtrl,
      });
    }
  });

  // CARD-448: flashcard / quiz / test players (durable Learning OS grades).
  loadModule('players', () => import('./education_players.js'), (mod) => {
    if (mod && typeof mod.initEducationStudioPlayers === 'function') {
      mod.initEducationStudioPlayers({ showToast: callbacks.showToast });
    }
  });

  return {
    loadEducationStudio: () => {
      safeCreateIcons();
    },
  };
}
