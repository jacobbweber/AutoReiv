/**
 * Defensive DOM query and manipulation utilities [REQ-FE-003]
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
 * Defensive querySelector against target parent.
 * @param {string} selector 
 * @param {ParentNode} [parent=document] 
 * @returns {Element|null}
 */
export function $query(selector, parent = document) {
  if (!parent || typeof parent.querySelector !== 'function') return null;
  return parent.querySelector(selector);
}

/**
 * Defensive querySelectorAll returning standard Array.
 * @param {string} selector 
 * @param {ParentNode} [parent=document] 
 * @returns {Element[]}
 */
export function $queryAll(selector, parent = document) {
  if (!parent || typeof parent.querySelectorAll !== 'function') return [];
  return Array.from(parent.querySelectorAll(selector));
}

/**
 * Safe invocation of Lucide icon generator.
 */
export function safeCreateIcons() {
  if (typeof window !== 'undefined' && window.lucide && typeof window.lucide.createIcons === 'function') {
    try {
      window.lucide.createIcons();
    } catch (e) {
      console.warn('[AutoReiv UI] Lucide createIcons error:', e);
    }
  }
}
