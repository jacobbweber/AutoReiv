/**
 * Modal Manager: Centralized Modal Lifecycle, Stack & Accessibility [REQ-ARCH-004]
 * Eliminates repetitive backdrop, class toggling, and fragile escape-key handlers across studios.
 */

import { $, $query, $queryAll } from '../dom.js';
import { handleFocusTrapKeydown } from '../utils/accessibility.js';

let modalStack = [];
let isEscapeListenerAttached = false;

/**
 * Resolve target element or element by ID.
 * @param {HTMLElement|string|null} elOrId
 * @returns {HTMLElement|null}
 */
function resolveElement(elOrId) {
  if (typeof elOrId === 'string') {
    return $(elOrId);
  }
  return elOrId || null;
}

/**
 * Handle Escape key press to dismiss the topmost modal on the stack.
 * @returns {HTMLElement|null} The modal that was closed, or null
 */
export function handleEscapeKey() {
  const closeSelector =
    '[data-modal-close], .modal-close-btn, #closeRoutineModalBtn, #cancelRoutineModalBtn, #wikiNewNoteCloseBtn, #wikiNewNoteCancelBtn, #wikiMindMapCloseBtn, button[aria-label="Close"]';

  if (modalStack.length > 0) {
    const topModal = modalStack[modalStack.length - 1];
    if (topModal) {
      const closeBtn = $query(closeSelector, topModal);
      if (closeBtn && typeof closeBtn.click === 'function') {
        closeBtn.click();
      }
      closeModal(topModal);
      return topModal;
    }
  }
  // Fallback for unmanaged DOM modals opened via classList manipulation
  const visibleModal = $query(
    '.modal:not(.hidden), [role="dialog"]:not(.hidden), [aria-modal="true"]:not(.hidden), #routineModal:not(.hidden), #wikiNewNoteModal:not(.hidden)',
  );
  if (visibleModal) {
    const closeBtn = $query(closeSelector, visibleModal);
    if (closeBtn && typeof closeBtn.click === 'function') {
      closeBtn.click();
    }
    closeModal(visibleModal);
    return visibleModal;
  }
  return null;
}

function ensureEscapeListener() {
  if (isEscapeListenerAttached || typeof window === 'undefined') return;
  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      handleEscapeKey();
    }
  });
  isEscapeListenerAttached = true;
}

/**
 * Open a modal dialog.
 * @param {HTMLElement|string} elOrId
 * @param {Object} [options]
 * @param {boolean} [options.trapFocus=true]
 */
export function openModal(elOrId, options = {}) {
  const el = resolveElement(elOrId);
  if (!el) return;

  el.classList.remove('hidden');
  el.classList.add('flex');
  el.setAttribute('aria-modal', 'true');
  el.setAttribute('role', 'dialog');

  // Push to stack if not already present
  if (!modalStack.includes(el)) {
    modalStack.push(el);
  }

  ensureEscapeListener();

  if (options.trapFocus !== false) {
    el._focusTrapHandler = (event) => handleFocusTrapKeydown(event, el);
    el.addEventListener('keydown', el._focusTrapHandler);
  }
}

/**
 * Close a modal dialog.
 * @param {HTMLElement|string} elOrId
 */
export function closeModal(elOrId) {
  const el = resolveElement(elOrId);
  if (!el) return;

  el.classList.add('hidden');
  el.classList.remove('flex');

  // Remove from stack
  modalStack = modalStack.filter((m) => m !== el);

  if (el._focusTrapHandler) {
    el.removeEventListener('keydown', el._focusTrapHandler);
    delete el._focusTrapHandler;
  }
}

/**
 * Toggle modal open/close state.
 * @param {HTMLElement|string} elOrId
 * @param {boolean} [forceState]
 */
export function toggleModal(elOrId, forceState) {
  const el = resolveElement(elOrId);
  if (!el) return;

  const shouldOpen = typeof forceState === 'boolean' ? forceState : el.classList.contains('hidden');
  if (shouldOpen) {
    openModal(el);
  } else {
    closeModal(el);
  }
}

/**
 * Check if a modal is currently open.
 * @param {HTMLElement|string} elOrId
 * @returns {boolean}
 */
export function isModalOpen(elOrId) {
  const el = resolveElement(elOrId);
  if (!el) return false;
  return !el.classList.contains('hidden');
}

/**
 * Returns the currently active (topmost) modal.
 * @returns {HTMLElement|null}
 */
export function getActiveModal() {
  return modalStack.length > 0 ? modalStack[modalStack.length - 1] : null;
}

/**
 * Returns a copy of the current modal stack.
 * @returns {HTMLElement[]}
 */
export function getModalStack() {
  return [...modalStack];
}

/**
 * Clear the modal stack (for test teardown or reset).
 */
export function clearModals() {
  modalStack = [];
}

/**
 * Set up automated close handlers on buttons and backdrop for a modal.
 * @param {HTMLElement|string} elOrId
 * @param {Object} [options]
 * @param {string} [options.closeSelector='[data-modal-close], .modal-close-btn']
 * @param {boolean} [options.closeOnBackdrop=true]
 */
export function setupModal(elOrId, options = {}) {
  const el = resolveElement(elOrId);
  if (!el) return;

  ensureEscapeListener();

  const closeSelector =
    options.closeSelector ||
    '[data-modal-close], .modal-close-btn, #closeRoutineModalBtn, #cancelRoutineModalBtn, #wikiNewNoteCloseBtn, #wikiNewNoteCancelBtn, #wikiMindMapCloseBtn, button[aria-label="Close"]';
  const closeBtns = $queryAll(closeSelector, el);
  closeBtns.forEach((btn) => {
    btn.addEventListener('click', () => closeModal(el));
  });

  if (options.closeOnBackdrop !== false) {
    el.addEventListener('click', (event) => {
      // If clicking directly on the outer backdrop container (not the inner modal card)
      if (event.target === el) {
        closeModal(el);
      }
    });
  }
}
