/**
 * Accessibility & Keyboard Navigation Utilities [REQ-A11Y-001, REQ-A11Y-002, REQ-A11Y-003].
 * Provides focus trapping, keyboard navigation, and ARIA state synchronization.
 */

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

/**
 * Returns the global document safely across browser and test environments.
 * @returns {Document|null}
 */
function getDocument() {
  if (typeof document !== 'undefined') return document;
  if (typeof globalThis !== 'undefined' && globalThis.document) return globalThis.document;
  return null;
}

/**
 * Returns all currently focusable and visible elements inside a container.
 * @param {HTMLElement} container
 * @returns {HTMLElement[]}
 */
export function getFocusableElements(container) {
  if (!container || typeof container.querySelectorAll !== 'function') {
    return [];
  }
  const elements = Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR));
  return elements.filter((el) => {
    return (
      el.offsetWidth > 0 ||
      el.offsetHeight > 0 ||
      (typeof el.getClientRects === 'function' && el.getClientRects().length > 0)
    );
  });
}

/**
 * Handles Tab and Shift+Tab keydown events to trap focus within container.
 * @param {KeyboardEvent} event
 * @param {HTMLElement} container
 * @returns {boolean} True if tab was trapped/handled, false otherwise.
 */
export function handleFocusTrapKeydown(event, container) {
  if (!event || event.key !== 'Tab') {
    return false;
  }

  const focusable = getFocusableElements(container);
  if (focusable.length === 0) {
    if (typeof event.preventDefault === 'function') event.preventDefault();
    return true;
  }

  const firstElement = focusable[0];
  const lastElement = focusable[focusable.length - 1];
  const doc = getDocument();
  const activeElement = doc ? doc.activeElement : null;

  if (event.shiftKey) {
    if (activeElement === firstElement || !container.contains(activeElement)) {
      if (typeof event.preventDefault === 'function') event.preventDefault();
      if (typeof lastElement.focus === 'function') lastElement.focus();
      return true;
    }
  } else {
    if (activeElement === lastElement || !container.contains(activeElement)) {
      if (typeof event.preventDefault === 'function') event.preventDefault();
      if (typeof firstElement.focus === 'function') firstElement.focus();
      return true;
    }
  }

  return false;
}

/**
 * Handles arrow key navigation across tab buttons in a tablist.
 * @param {KeyboardEvent} event
 * @param {HTMLElement[]} tabButtons
 * @param {function(string): void} onSelectTab
 * @returns {boolean} True if navigation was handled.
 */
export function handleTablistKeydown(event, tabButtons, onSelectTab) {
  if (!event || !Array.isArray(tabButtons) || tabButtons.length === 0) {
    return false;
  }

  const keys = ['ArrowRight', 'ArrowDown', 'ArrowLeft', 'ArrowUp', 'Home', 'End'];
  if (!keys.includes(event.key)) {
    return false;
  }

  const doc = getDocument();
  const activeElement = doc ? doc.activeElement : null;

  let activeIndex = tabButtons.findIndex((btn) => btn === activeElement);
  if (activeIndex === -1) {
    activeIndex = tabButtons.findIndex((btn) => btn.getAttribute('aria-selected') === 'true');
  }

  let targetIndex = activeIndex === -1 ? 0 : activeIndex;

  switch (event.key) {
    case 'ArrowRight':
    case 'ArrowDown':
      targetIndex = (targetIndex + 1) % tabButtons.length;
      break;
    case 'ArrowLeft':
    case 'ArrowUp':
      targetIndex = (targetIndex - 1 + tabButtons.length) % tabButtons.length;
      break;
    case 'Home':
      targetIndex = 0;
      break;
    case 'End':
      targetIndex = tabButtons.length - 1;
      break;
  }

  if (typeof event.preventDefault === 'function') {
    event.preventDefault();
  }

  const targetBtn = tabButtons[targetIndex];
  if (targetBtn) {
    if (typeof targetBtn.focus === 'function') {
      targetBtn.focus();
    }
    const tabId = targetBtn.dataset?.tab || targetBtn.id?.replace('tab-', '');
    if (tabId && typeof onSelectTab === 'function') {
      onSelectTab(tabId);
    }
  }

  return true;
}

/**
 * Synchronizes aria-selected, tabindex, and aria-hidden attributes across tab buttons and panels.
 * @param {string} activeTabId
 * @param {HTMLElement[]|NodeListOf<HTMLElement>} tabButtons
 * @param {HTMLElement[]|NodeListOf<HTMLElement>} [tabPanels=[]]
 */
export function syncTabAria(activeTabId, tabButtons, tabPanels = []) {
  if (tabButtons && typeof tabButtons[Symbol.iterator] === 'function') {
    Array.from(tabButtons).forEach((btn) => {
      const tabId = btn.dataset?.tab || btn.id?.replace('tab-', '');
      const isSelected = tabId === activeTabId;
      btn.setAttribute('aria-selected', isSelected ? 'true' : 'false');
      btn.setAttribute('tabindex', isSelected ? '0' : '-1');
    });
  }

  if (tabPanels && typeof tabPanels[Symbol.iterator] === 'function') {
    Array.from(tabPanels).forEach((panel) => {
      const panelTabId = panel.dataset?.tab || panel.id?.replace('View', '');
      const isVisible = panelTabId === activeTabId;
      panel.setAttribute('aria-hidden', isVisible ? 'false' : 'true');
    });
  }
}
