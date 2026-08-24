/**
 * Defensive DOM query, event binding, and manipulation utilities [REQ-FE-003, REQ-DOM-001, REQ-DOM-002]
 */

/**
 * Null-safe getElementById with warning logging.
 * @param {string} id
 * @returns {HTMLElement|null}
 */
export function $(id) {
  if (typeof document === 'undefined') return null;
  const el = document.getElementById(id);
  if (!el) {
    console.warn(`[AutoReiv UI] Element #${id} not found in DOM.`);
    return null;
  }
  return el;
}

/**
 * Defensive querySelector against target parent or document.
 * @param {string} selector
 * @param {ParentNode} [parent=document]
 * @returns {Element|null}
 */
export function $query(selector, parent = typeof document !== 'undefined' ? document : null) {
  if (!parent || typeof parent.querySelector !== 'function') return null;
  return parent.querySelector(selector);
}

/**
 * Defensive querySelectorAll returning standard Array.
 * @param {string} selector
 * @param {ParentNode} [parent=document]
 * @returns {Element[]}
 */
export function $queryAll(selector, parent = typeof document !== 'undefined' ? document : null) {
  if (!parent || typeof parent.querySelectorAll !== 'function') return [];
  return Array.from(parent.querySelectorAll(selector));
}

/**
 * Ultra-safe event listener binding that automatically guards against null/undefined targets.
 * @param {HTMLElement|string|null} targetOrId
 * @param {string} event
 * @param {Function} handler
 * @param {boolean|AddEventListenerOptions} [options]
 * @returns {boolean} true if attached, false if target was missing
 */
export function $on(targetOrId, event, handler, options) {
  const target = typeof targetOrId === 'string' ? $(targetOrId) : targetOrId;
  if (!target || typeof target.addEventListener !== 'function') {
    return false;
  }
  target.addEventListener(event, handler, options);
  return true;
}

/**
 * Safe show element helper (removes 'hidden' class).
 * @param {HTMLElement|string|null} elOrId
 */
export function $show(elOrId) {
  const el = typeof elOrId === 'string' ? $(elOrId) : elOrId;
  if (el && el.classList) {
    el.classList.remove('hidden');
  }
}

/**
 * Safe hide element helper (adds 'hidden' class).
 * @param {HTMLElement|string|null} elOrId
 */
export function $hide(elOrId) {
  const el = typeof elOrId === 'string' ? $(elOrId) : elOrId;
  if (el && el.classList) {
    el.classList.add('hidden');
  }
}

/**
 * Safe toggle element helper.
 * @param {HTMLElement|string|null} elOrId
 * @param {boolean} [forceState]
 */
export function $toggle(elOrId, forceState) {
  const el = typeof elOrId === 'string' ? $(elOrId) : elOrId;
  if (el && el.classList) {
    if (typeof forceState === 'boolean') {
      el.classList.toggle('hidden', !forceState);
    } else {
      el.classList.toggle('hidden');
    }
  }
}

/**
 * Safe invocation of Lucide icon generator.
 * @param {HTMLElement} [root]
 */
export function safeCreateIcons(root) {
  if (typeof window !== 'undefined' && window.lucide && typeof window.lucide.createIcons === 'function') {
    try {
      window.lucide.createIcons(root ? { root } : undefined);
    } catch (e) {
      console.warn('[AutoReiv UI] Lucide createIcons error:', e);
    }
  }
}
