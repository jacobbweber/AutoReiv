/**
 * Chat Studio: Autoscroll & Drawer Visibility Submodule [REQ-ARCH-003]
 * Encapsulates scroll math, sticky follow-tail logic, jump-to-latest visibility, and drawer state.
 */

export const CHAT_SCROLL_BOTTOM_THRESHOLD_PX = 96;

/**
 * True when the scroll container is within threshold of the bottom (sticky follow-tail).
 * @param {{ scrollHeight: number, scrollTop: number, clientHeight: number } | null} el
 * @param {number} [thresholdPx]
 */
export function isScrolledNearBottom(el, thresholdPx = CHAT_SCROLL_BOTTOM_THRESHOLD_PX) {
  if (!el) return true;
  const distance = Number(el.scrollHeight || 0) - Number(el.scrollTop || 0) - Number(el.clientHeight || 0);
  return distance <= Number(thresholdPx || CHAT_SCROLL_BOTTOM_THRESHOLD_PX);
}

/** @param {boolean} stickToBottom */
export function shouldAutoscrollOnStream(stickToBottom) {
  return Boolean(stickToBottom);
}

/**
 * @param {{ stickToBottom?: boolean, hasOverflow?: boolean }} opts
 */
export function shouldShowJumpToLatest({ stickToBottom = true, hasOverflow = false } = {}) {
  return Boolean(hasOverflow) && !stickToBottom;
}

/**
 * @param {{ classList?: { contains?: Function } } | null} drawerEl
 */
export function isChatSessionsDrawerOpen(drawerEl) {
  if (!drawerEl || !drawerEl.classList || typeof drawerEl.classList.contains !== 'function') {
    return false;
  }
  return !drawerEl.classList.contains('hidden');
}

/**
 * @param {{ classList?: { remove?: Function } } | null} drawerEl
 * @param {{ classList?: { add?: Function } } | null} viewEl
 */
export function openChatSessionsDrawer(drawerEl, viewEl = null) {
  if (drawerEl && drawerEl.classList && typeof drawerEl.classList.remove === 'function') {
    drawerEl.classList.remove('hidden');
  }
  if (viewEl && viewEl.classList && typeof viewEl.classList.add === 'function') {
    viewEl.classList.add('sessions-drawer-open');
  }
  return true;
}

/**
 * @param {{ classList?: { add?: Function } } | null} drawerEl
 * @param {{ classList?: { remove?: Function } } | null} viewEl
 */
export function collapseChatSessionsDrawer(drawerEl, viewEl = null) {
  if (drawerEl && drawerEl.classList && typeof drawerEl.classList.add === 'function') {
    drawerEl.classList.add('hidden');
  }
  if (viewEl && viewEl.classList && typeof viewEl.classList.remove === 'function') {
    viewEl.classList.remove('sessions-drawer-open');
  }
  return true;
}
