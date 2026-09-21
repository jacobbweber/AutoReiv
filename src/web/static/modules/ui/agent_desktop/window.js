/**
 * Agent Desktop - Window Management & Interaction
 * Window shell creation, drag & resize pointer handling, z-stack ordering, and window state transitions.
 */

import { $, $query, $queryAll, escapeHtml, isMobile, safeCreateIcons } from '../../dom.js';
import {
  MIN_H,
  MIN_W,
  cascadeOffset,
  clampWindowRect,
  computeCascadeRects,
  computeMaximizeRect,
  computeMobileLayout,
  computeSnapHalf,
  computeTileRects,
  snapRectToGrid,
  snapToGrid,
} from './layout.js';

const RESIZE_EDGES = ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'];

function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, '&#39;');
}

function altHeld(e) {
  return !!(e && e.altKey);
}

/**
 * Focus the chat prompt composer input.
 */
export function focusComposer() {
  const input = $('promptInput');
  if (!input) return;
  window.setTimeout(() => {
    try {
      input.focus();
    } catch {
      /* ignore */
    }
  }, 40);
}

/**
 * Remove legacy titlebar agent pickers; the only picker is #agentSelect.
 * @param {string} tab
 * @param {HTMLElement|null} titleRight
 */
export function buildTitleExtras(tab, titleRight) {
  if (tab !== 'chat' || !titleRight) return;
  const existing = $query('.desktop-win-agent-switch', titleRight) || $query('.desktop-win-agent-select', titleRight);
  if (existing) {
    const wrap = existing.closest ? existing.closest('.desktop-win-agent-switch') : null;
    (wrap || existing).remove();
  }
}

/**
 * Create a new window shell element, configure default rect, append to layer, and bind chrome events.
 * @param {object} launcher
 * @param {object} ctx
 * @returns {object} DesktopWindow
 */
export function createWindowShell(launcher, ctx) {
  const {
    layer,
    prefs,
    openCount,
    setOpenCountFn,
    nextZFn,
    viewportSizeFn,
    windows,
  } = ctx;

  const tab = launcher.tab;
  const el = document.createElement('div');
  el.className = 'desktop-window';
  el.id = `desktopWin-${tab}`;
  el.setAttribute('data-desktop-tab', tab);
  el.setAttribute('role', 'dialog');
  el.setAttribute('aria-label', launcher.label);

  const handles = RESIZE_EDGES.map(
    (edge) => `<div class="desktop-win-resize desktop-win-resize-${edge}" data-resize="${edge}" title="Resize"></div>`
  ).join('');

  el.innerHTML = `
    <div class="desktop-win-titlebar" data-drag-handle="1">
      <div class="desktop-win-title-left">
        <span class="desktop-win-icon"><i data-lucide="${escapeAttr(launcher.icon)}" class="w-3.5 h-3.5"></i></span>
        <span class="desktop-win-title">${escapeHtml(launcher.label)}</span>
        <span class="desktop-win-sub">${escapeHtml(launcher.subtitle || '')}</span>
      </div>
      <div class="desktop-win-title-right" data-title-right="1"></div>
      <div class="desktop-win-controls">
        <button type="button" class="desktop-win-btn desktop-win-min" title="Minimize" aria-label="Minimize">
          <i data-lucide="minus" class="w-3.5 h-3.5"></i>
        </button>
        <button type="button" class="desktop-win-btn desktop-win-max" title="Maximize" aria-label="Maximize">
          <i data-lucide="square" class="w-3.5 h-3.5"></i>
        </button>
        <button type="button" class="desktop-win-btn desktop-win-close" title="Close" aria-label="Close">
          <i data-lucide="x" class="w-3.5 h-3.5"></i>
        </button>
      </div>
    </div>
    <div class="desktop-win-body" data-win-body="1"></div>
    ${handles}
  `;

  const bodyEl = /** @type {HTMLElement} */ ($query('[data-win-body]', el));
  const titleRight = $query('[data-title-right]', el);
  buildTitleExtras(tab, titleRight);

  const vp = viewportSizeFn();
  const def = launcher.defaultSize || { w: 720, h: 520 };
  const saved = prefs.windows && prefs.windows[tab];
  const off = cascadeOffset(openCount);
  let rect;
  let maximized = false;
  if (saved && typeof saved.w === 'number' && typeof saved.h === 'number') {
    rect = clampWindowRect({ x: saved.x ?? off.x, y: saved.y ?? off.y, w: saved.w, h: saved.h }, vp);
    maximized = !!saved.maximized;
  } else {
    rect = clampWindowRect(
      { x: off.x, y: off.y, w: Math.min(def.w, vp.width - 32), h: Math.min(def.h, vp.height - vp.dockH - 24) },
      vp
    );
  }

  const win = {
    id: `win-${tab}`,
    tab,
    label: launcher.label,
    el,
    bodyEl,
    minimized: false,
    maximized,
    restoreRect: maximized ? { ...rect } : null,
    rect,
    z: nextZFn(),
  };

  el.style.zIndex = String(win.z + 2);
  layer.appendChild(el);
  safeCreateIcons(el);
  bindWindowChrome(win, ctx);
  applyRect(win, ctx);
  if (typeof setOpenCountFn === 'function') setOpenCountFn(openCount + 1);
  windows.set(tab, win);
  return win;
}

/**
 * Bind pointer drag, resize handles, and header buttons to a window element.
 * @param {object} win
 * @param {object} ctx
 */
export function bindWindowChrome(win, ctx) {
  const {
    isMobileFn = isMobile,
    focusWindowFn,
    minimizeWindowFn,
    toggleMaximizeFn,
    closeWindowFn,
    schedulePersistFn,
  } = ctx;

  const titlebar = $query('[data-drag-handle]', win.el);
  const minBtn = $query('.desktop-win-min', win.el);
  const maxBtn = $query('.desktop-win-max', win.el);
  const closeBtn = $query('.desktop-win-close', win.el);
  const resizeHandles = $queryAll('[data-resize]', win.el);

  win.el.addEventListener('mousedown', () => focusWindowFn(win.tab));
  win.el.addEventListener('touchstart', () => focusWindowFn(win.tab), { passive: true });

  if (minBtn) {
    minBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      minimizeWindowFn(win.tab);
    });
  }
  if (maxBtn) {
    maxBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleMaximizeFn(win.tab);
    });
  }
  if (closeBtn) {
    closeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      closeWindowFn(win.tab);
    });
  }

  if (titlebar) {
    titlebar.addEventListener('dblclick', (e) => {
      if (e.target && e.target.closest && e.target.closest('.desktop-win-btn, select, button, a')) return;
      if (isMobileFn()) return;
      toggleMaximizeFn(win.tab);
    });

    let dragging = false;
    let startX = 0;
    let startY = 0;
    let origX = 0;
    let origY = 0;
    let disableSnap = false;

    const onMove = (clientX, clientY) => {
      if (!dragging || isMobileFn()) return;
      let nx = origX + (clientX - startX);
      let ny = origY + (clientY - startY);
      if (!disableSnap) {
        nx = snapToGrid(nx);
        ny = snapToGrid(ny);
      }
      win.rect.x = nx;
      win.rect.y = ny;
      if (win.maximized) {
        win.maximized = false;
        win.restoreRect = null;
        win.el.classList.remove('is-maximized');
      }
      applyRect(win, ctx);
    };

    const onTitlePointerMove = (e) => {
      if (!dragging || isMobileFn()) return;
      disableSnap = altHeld(e);
      onMove(e.clientX, e.clientY);
    };

    const endDrag = () => {
      if (!dragging) return;
      dragging = false;
      win.el.classList.remove('is-dragging');
      window.removeEventListener('pointermove', onTitlePointerMove);
      window.removeEventListener('pointerup', endDrag);
      window.removeEventListener('pointercancel', endDrag);
      if (typeof schedulePersistFn === 'function') schedulePersistFn();
    };

    titlebar.addEventListener('pointerdown', (e) => {
      if (e.button != null && e.button !== 0) return;
      if (e.target && e.target.closest && e.target.closest('.desktop-win-btn, select, button, a')) return;
      if (isMobileFn()) return;
      dragging = true;
      disableSnap = altHeld(e);
      startX = e.clientX;
      startY = e.clientY;
      origX = win.rect.x;
      origY = win.rect.y;
      focusWindowFn(win.tab);
      win.el.classList.add('is-dragging');
      window.addEventListener('pointermove', onTitlePointerMove);
      window.addEventListener('pointerup', endDrag);
      window.addEventListener('pointercancel', endDrag);
      try {
        titlebar.setPointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
    });
  }

  resizeHandles.forEach((resizeHandle) => {
    const edge = resizeHandle.getAttribute('data-resize') || 'se';
    let resizing = false;
    let startX = 0;
    let startY = 0;
    let orig = { x: 0, y: 0, w: 0, h: 0 };
    let disableSnap = false;

    const onResizePointerMove = (e) => {
      if (!resizing) return;
      disableSnap = altHeld(e);
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      let { x, y, w, h } = orig;
      if (edge.includes('e')) w = orig.w + dx;
      if (edge.includes('s')) h = orig.h + dy;
      if (edge.includes('w')) {
        w = orig.w - dx;
        x = orig.x + dx;
      }
      if (edge.includes('n')) {
        h = orig.h - dy;
        y = orig.y + dy;
      }
      if (w < MIN_W) {
        if (edge.includes('w')) x = orig.x + orig.w - MIN_W;
        w = MIN_W;
      }
      if (h < MIN_H) {
        if (edge.includes('n')) y = orig.y + orig.h - MIN_H;
        h = MIN_H;
      }
      let next = { x, y, w, h };
      if (!disableSnap) next = snapRectToGrid(next);
      win.rect = next;
      applyRect(win, ctx);
    };

    const endResize = () => {
      if (!resizing) return;
      resizing = false;
      win.el.classList.remove('is-resizing');
      window.removeEventListener('pointermove', onResizePointerMove);
      window.removeEventListener('pointerup', endResize);
      window.removeEventListener('pointercancel', endResize);
      if (typeof schedulePersistFn === 'function') schedulePersistFn();
    };

    resizeHandle.addEventListener('pointerdown', (e) => {
      if (isMobileFn()) return;
      e.preventDefault();
      e.stopPropagation();
      if (win.maximized) {
        win.maximized = false;
        win.restoreRect = null;
        win.el.classList.remove('is-maximized');
      }
      resizing = true;
      disableSnap = altHeld(e);
      startX = e.clientX;
      startY = e.clientY;
      orig = { ...win.rect };
      focusWindowFn(win.tab);
      win.el.classList.add('is-resizing');
      window.addEventListener('pointermove', onResizePointerMove);
      window.addEventListener('pointerup', endResize);
      window.addEventListener('pointercancel', endResize);
      try {
        resizeHandle.setPointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
    });
  });
}

/**
 * Apply position and size rect styles to a window element and schedule hosted views sync.
 * @param {object} win
 * @param {object} ctx
 */
export function applyRect(win, ctx) {
  const {
    viewportSizeFn,
    isMobileFn = isMobile,
    applyMobileLayoutFn,
    scheduleSyncHostedViewsFn,
    schedulePersistFn,
  } = ctx;

  const vp = viewportSizeFn();
  if (isMobileFn()) {
    if (typeof applyMobileLayoutFn === 'function') applyMobileLayoutFn();
    return;
  }
  if (win.maximized) {
    const maxR = computeMaximizeRect(vp);
    win.rect = maxR;
    win.el.style.left = `${maxR.x}px`;
    win.el.style.top = `${maxR.y}px`;
    win.el.style.width = `${maxR.w}px`;
    win.el.style.height = `${maxR.h}px`;
    win.el.classList.add('is-maximized');
    win.el.classList.remove('is-mobile-fs', 'is-mobile-half');
  } else {
    const r = clampWindowRect(win.rect, vp);
    win.rect = r;
    win.el.style.left = `${r.x}px`;
    win.el.style.top = `${r.y}px`;
    win.el.style.width = `${r.w}px`;
    win.el.style.height = `${r.h}px`;
    win.el.classList.remove('is-maximized', 'is-mobile-fs', 'is-mobile-half');
  }
  if (typeof scheduleSyncHostedViewsFn === 'function') scheduleSyncHostedViewsFn();
  if (typeof schedulePersistFn === 'function') schedulePersistFn();
}

/**
 * Focus and bring a window to top z-index.
 * @param {string} tab
 * @param {object} ctx
 */
export function focusWindow(tab, ctx) {
  const {
    windows,
    nextZFn,
    root,
    isMobileFn = isMobile,
    applyMobileLayoutFn,
    scheduleSyncHostedViewsFn,
  } = ctx;

  const win = windows.get(tab);
  if (!win || win.minimized) return;
  win.z = nextZFn();
  win.el.style.zIndex = String(win.z + 2);
  windows.forEach((w) => w.el.classList.toggle('is-focused', w.tab === tab));
  root.setAttribute('data-desktop-focus', tab);
  if (isMobileFn()) {
    if (typeof applyMobileLayoutFn === 'function') applyMobileLayoutFn();
    return;
  }
  if (typeof scheduleSyncHostedViewsFn === 'function') scheduleSyncHostedViewsFn();
}

/**
 * Apply full-viewport mobile layout for the highest z-stack window.
 * @param {object} ctx
 */
export function applyMobileLayout(ctx) {
  const {
    visibleWindowsFn,
    viewportSizeFn,
    updateDockActiveFn,
    scheduleSyncHostedViewsFn,
  } = ctx;

  const vis = visibleWindowsFn().sort((a, b) => a.z - b.z);
  const vp = viewportSizeFn();
  if (!vis.length) {
    if (typeof scheduleSyncHostedViewsFn === 'function') scheduleSyncHostedViewsFn();
    return;
  }
  const focused = vis[vis.length - 1];
  vis.forEach((win) => {
    if (win.tab === focused.tab) return;
    win.minimized = true;
    win.el.classList.add('is-minimized');
    win.el.setAttribute('aria-hidden', 'true');
    win.el.classList.remove('is-mobile-fs', 'is-mobile-half');
    delete win.el.dataset.mobileMode;
  });
  const layout = computeMobileLayout(1, 0, vp);
  focused.minimized = false;
  focused.el.classList.remove('is-minimized');
  focused.el.setAttribute('aria-hidden', 'false');
  focused.rect = { x: layout.x, y: layout.y, w: layout.w, h: layout.h };
  focused.el.style.left = `${layout.x}px`;
  focused.el.style.top = `${layout.y}px`;
  focused.el.style.width = `${layout.w}px`;
  focused.el.style.height = `${layout.h}px`;
  focused.el.classList.add('is-mobile-fs');
  focused.el.classList.remove('is-mobile-half');
  focused.el.dataset.mobileMode = 'full';
  if (typeof updateDockActiveFn === 'function') updateDockActiveFn();
  if (typeof scheduleSyncHostedViewsFn === 'function') scheduleSyncHostedViewsFn();
}

/**
 * Open or restore a window for a tab launcher.
 * @param {string} tab
 * @param {object} [opts]
 * @param {object} ctx
 * @returns {object|null}
 */
export function openWindow(tab, { focusComposer: doFocus = false } = {}, ctx) {
  const {
    windows,
    launcherForTabFn,
    createWindowShellFn,
    focusWindowFn,
    applyRectFn,
    applyMobileLayoutFn,
    updateDockActiveFn,
    root,
    viewportSizeFn,
    switchTabFn,
    scheduleSyncHostedViewsFn,
    schedulePersistFn,
    isMobileFn = isMobile,
  } = ctx;

  // CARD-305: Sessions is not a dock/desktop studio window
  if (tab === 'sessions') {
    openWindow('chat', { focusComposer: doFocus }, ctx);
    const drawer = $('chatSessionsDrawer');
    const view = $('view-chat');
    if (drawer) drawer.classList.remove('hidden');
    if (view) view.classList.add('sessions-drawer-open');
    return windows.get('chat') || null;
  }
  const launcher = launcherForTabFn(tab);
  if (!launcher) return null;

  let win = windows.get(tab);
  if (win) {
    if (win.minimized) {
      win.minimized = false;
      win.el.classList.remove('is-minimized');
      win.el.setAttribute('aria-hidden', 'false');
    }
    focusWindowFn(tab);
    if (!isMobileFn()) applyRectFn(win);
    updateDockActiveFn();
  } else {
    win = createWindowShellFn(launcher, ctx);
    focusWindowFn(tab);
    updateDockActiveFn();
    if (isMobileFn()) applyMobileLayoutFn();
  }

  root.classList.add('desktop-has-windows');

  // CARD-314: Factory deep-link / dock open must present as a full studio window, not a toast-sized chip.
  if (tab === 'factory' && win && !win.maximized) {
    const l = launcherForTabFn('factory');
    const def = (l && l.defaultSize) || { w: 960, h: 680 };
    const vp = viewportSizeFn();
    const tooSmall = (win.rect.w || 0) < 560 || (win.rect.h || 0) < 420;
    if (tooSmall) {
      win.rect = clampWindowRect(
        {
          x: win.rect.x,
          y: win.rect.y,
          w: Math.min(def.w, vp.width - 32),
          h: Math.min(def.h, vp.height - vp.dockH - 24),
        },
        vp
      );
      applyRectFn(win);
    }
  }

  if (tab !== 'sessions' && typeof switchTabFn === 'function') {
    switchTabFn(tab);
  }

  if (tab === 'chat' && doFocus) {
    focusComposer();
  }

  if (typeof scheduleSyncHostedViewsFn === 'function') scheduleSyncHostedViewsFn();
  if (typeof schedulePersistFn === 'function') schedulePersistFn();
  return win;
}

/**
 * Minimize a window.
 * @param {string} tab
 * @param {object} ctx
 */
export function minimizeWindow(tab, ctx) {
  const {
    windows,
    updateDockActiveFn,
    isMobileFn = isMobile,
    applyMobileLayoutFn,
    scheduleSyncHostedViewsFn,
    toastFn,
  } = ctx;

  const win = windows.get(tab);
  if (!win) return;
  win.minimized = true;
  win.el.classList.add('is-minimized');
  win.el.setAttribute('aria-hidden', 'true');
  if (typeof updateDockActiveFn === 'function') updateDockActiveFn();
  if (isMobileFn()) {
    if (typeof applyMobileLayoutFn === 'function') applyMobileLayoutFn();
  }
  if (typeof scheduleSyncHostedViewsFn === 'function') scheduleSyncHostedViewsFn();
  if (typeof toastFn === 'function') toastFn(`${win.label} minimized`, 'info', 900);
}

/**
 * Close and destroy a window.
 * @param {string} tab
 * @param {object} ctx
 */
export function closeWindow(tab, ctx) {
  const {
    windows,
    prefs,
    root,
    viewIdForTabFn,
    updateDockActiveFn,
    isMobileFn = isMobile,
    applyMobileLayoutFn,
    scheduleSyncHostedViewsFn,
    schedulePersistFn,
  } = ctx;

  const win = windows.get(tab);
  if (!win) return;
  prefs.windows = prefs.windows || {};
  prefs.windows[tab] = {
    x: win.rect.x,
    y: win.rect.y,
    w: win.rect.w,
    h: win.rect.h,
    maximized: !!win.maximized,
  };
  win.el.remove();
  windows.delete(tab);
  if (typeof updateDockActiveFn === 'function') updateDockActiveFn();
  if (!windows.size) {
    root.classList.remove('desktop-has-windows');
    root.removeAttribute('data-desktop-focus');
  }
  if (isMobileFn()) {
    if (typeof applyMobileLayoutFn === 'function') applyMobileLayoutFn();
  }
  if (typeof scheduleSyncHostedViewsFn === 'function') scheduleSyncHostedViewsFn();
  if (typeof schedulePersistFn === 'function') schedulePersistFn();

  const viewId = viewIdForTabFn(tab);
  const view = viewId ? $(viewId) : null;
  if (view) {
    view.classList.add('desktop-view-parked', 'hidden');
    view.classList.remove('desktop-view-hosted', 'flex');
    view.setAttribute('aria-hidden', 'true');
  }
}

/**
 * Toggle maximize / restore for a window.
 * @param {string} tab
 * @param {object} ctx
 */
export function toggleMaximize(tab, ctx) {
  const { windows, isMobileFn = isMobile, applyRectFn, focusWindowFn } = ctx;
  const win = windows.get(tab);
  if (!win || isMobileFn()) return;
  if (win.maximized) {
    win.maximized = false;
    if (win.restoreRect) win.rect = { ...win.restoreRect };
    win.restoreRect = null;
    win.el.classList.remove('is-maximized');
    const maxBtn = $query('.desktop-win-max', win.el);
    if (maxBtn) maxBtn.title = 'Maximize';
  } else {
    win.restoreRect = { ...win.rect };
    win.maximized = true;
    win.el.classList.add('is-maximized');
    const maxBtn = $query('.desktop-win-max', win.el);
    if (maxBtn) maxBtn.title = 'Restore';
  }
  applyRectFn(win);
  focusWindowFn(tab);
}

/**
 * Arrange visible windows in a tiled grid.
 * @param {object} ctx
 */
export function arrangeTile(ctx) {
  const { visibleWindowsFn, viewportSizeFn, isMobileFn = isMobile, applyMobileLayoutFn, toastFn, applyRectFn } = ctx;
  const vis = visibleWindowsFn();
  if (!vis.length) return;
  const vp = viewportSizeFn();
  if (isMobileFn()) {
    if (typeof applyMobileLayoutFn === 'function') applyMobileLayoutFn();
    if (typeof toastFn === 'function') toastFn('Mobile snap applied', 'info', 900);
    return;
  }
  const rects = computeTileRects(vis.length, vp);
  vis.forEach((win, i) => {
    win.maximized = false;
    win.restoreRect = null;
    win.rect = rects[i] || win.rect;
    applyRectFn(win);
  });
  if (typeof toastFn === 'function') toastFn('Windows tiled', 'info', 900);
}

/**
 * Arrange visible windows in a cascading stack.
 * @param {object} ctx
 */
export function arrangeCascade(ctx) {
  const { visibleWindowsFn, viewportSizeFn, isMobileFn = isMobile, applyMobileLayoutFn, toastFn, applyRectFn, focusWindowFn } = ctx;
  const vis = visibleWindowsFn();
  if (!vis.length) return;
  if (isMobileFn()) {
    if (typeof applyMobileLayoutFn === 'function') applyMobileLayoutFn();
    return;
  }
  const vp = viewportSizeFn();
  const rects = computeCascadeRects(vis.length, vp, { w: 640, h: 480 });
  vis.forEach((win, i) => {
    win.maximized = false;
    win.restoreRect = null;
    win.rect = rects[i] || win.rect;
    applyRectFn(win);
    focusWindowFn(win.tab);
  });
  if (typeof toastFn === 'function') toastFn('Windows cascaded', 'info', 900);
}

/**
 * Snap focused window to left or right half of desktop.
 * @param {'left'|'right'} side
 * @param {object} ctx
 */
export function arrangeSnapHalf(side, ctx) {
  const { root, windows, visibleWindowsFn, viewportSizeFn, isMobileFn = isMobile, applyMobileLayoutFn, toastFn, applyRectFn, focusWindowFn } = ctx;
  const focus = root.getAttribute('data-desktop-focus');
  const win = focus ? windows.get(focus) : visibleWindowsFn().slice(-1)[0];
  if (!win || win.minimized) {
    if (typeof toastFn === 'function') toastFn('Focus a window first', 'info', 900);
    return;
  }
  if (isMobileFn()) {
    if (typeof applyMobileLayoutFn === 'function') applyMobileLayoutFn();
    if (typeof toastFn === 'function') toastFn(`Mobile layout (${side})`, 'info', 900);
    return;
  }
  const vp = viewportSizeFn();
  win.maximized = false;
  win.restoreRect = null;
  win.rect = computeSnapHalf(side, vp);
  applyRectFn(win);
  focusWindowFn(win.tab);
  if (typeof toastFn === 'function') toastFn(`Snapped ${side}`, 'info', 900);
}

/**
 * Position real studio tab-views inside their window body elements.
 * @param {object} ctx
 */
export function syncHostedViews(ctx) {
  const { windows, viewIdForTabFn, focusWindowFn, viewByTab = {} } = ctx;

  Object.keys(viewByTab).forEach((tab) => {
    const view = $(viewByTab[tab]);
    if (!view) return;
    const win = windows.get(tab);
    const show = !!(win && !win.minimized);
    if (!show) {
      view.classList.add('desktop-view-parked');
      view.classList.remove('desktop-view-hosted');
      view.style.removeProperty('--dw-l');
      view.style.removeProperty('--dw-t');
      view.style.removeProperty('--dw-w');
      view.style.removeProperty('--dw-h');
      view.style.removeProperty('z-index');
    }
  });

  windows.forEach((win) => {
    if (win.minimized) return;
    if (win.tab === 'sessions') return;
    const viewId = viewIdForTabFn(win.tab);
    const view = viewId ? $(viewId) : null;
    if (!view || !win.bodyEl) return;
    const rect = win.bodyEl.getBoundingClientRect();
    view.classList.remove('desktop-view-parked', 'hidden');
    view.classList.add('desktop-view-hosted', 'flex');
    view.setAttribute('aria-hidden', 'false');
    view.style.setProperty('--dw-l', `${Math.round(rect.left)}px`);
    view.style.setProperty('--dw-t', `${Math.round(rect.top)}px`);
    view.style.setProperty('--dw-w', `${Math.round(rect.width)}px`);
    view.style.setProperty('--dw-h', `${Math.round(rect.height)}px`);
    view.style.zIndex = String(win.z + 1);
    if (!view.dataset.desktopFocusBound) {
      view.dataset.desktopFocusBound = 'true';
      view.addEventListener('pointerdown', () => focusWindowFn(win.tab));
    }
  });
}
