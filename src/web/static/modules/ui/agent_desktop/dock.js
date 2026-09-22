/**
 * Agent Desktop - Bottom Dock Launcher & Scroll Controls
 * Renders launcher buttons, tracks open/minimized state, and handles horizontal dock scrolling.
 */

import { $queryAll, escapeHtml, safeCreateIcons } from '../../dom.js';

function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, '&#39;');
}

/**
 * Render all dock launcher buttons into #desktopDockApps.
 * @param {object} params
 */
export function renderDock({
  dockApps,
  windows,
  root,
  openWindow,
  minimizeWindow,
  toast,
  updateDockScrollChromeFn,
  dockLaunchers = [],
  hydrateStudioAgentPicker,
}) {
  if (!dockApps) return;
  dockApps.innerHTML = dockLaunchers.map(
    (d) => `
    <button type="button" id="${escapeAttr(d.id)}" class="desktop-dock-btn" data-dock-tab="${escapeAttr(d.tab)}" data-dock-id="${escapeAttr(d.id)}" title="${escapeAttr(d.label)}" aria-label="${escapeAttr(d.label)}" aria-pressed="false">
      <span class="desktop-dock-icon"><i data-lucide="${escapeAttr(d.icon)}" class="w-5 h-5"></i></span>
      <span class="desktop-dock-label">${escapeHtml(d.label)}</span>
      <span class="desktop-dock-indicator" aria-hidden="true"></span>
    </button>`
  ).join('');
  safeCreateIcons(dockApps);

  $queryAll('.desktop-dock-btn', dockApps).forEach((btn) => {
    btn.addEventListener('click', () => {
      const tab = btn.getAttribute('data-dock-tab');
      if (!tab) return;
      const win = windows.get(tab);
      if (win && !win.minimized && root.getAttribute('data-desktop-focus') === tab) {
        minimizeWindow(tab);
        return;
      }
      openWindow(tab, { focusComposer: tab === 'chat' });
      if (typeof hydrateStudioAgentPicker === 'function') hydrateStudioAgentPicker(tab);
      if (tab === 'chat' && typeof toast === 'function') toast('Chat window', 'info', 1000);
    });
  });

  if (typeof updateDockScrollChromeFn === 'function') {
    updateDockScrollChromeFn();
  }
}

/**
 * Update active, open, and minimized visual state on dock buttons.
 * @param {object} params
 */
export function updateDockActive({ dockApps, windows, updateDockScrollChromeFn }) {
  if (!dockApps) return;
  $queryAll('.desktop-dock-btn', dockApps).forEach((btn) => {
    const tab = btn.getAttribute('data-dock-tab');
    const win = tab ? windows.get(tab) : null;
    const open = !!(win && !win.minimized);
    const mini = !!(win && win.minimized);
    btn.classList.toggle('is-open', open);
    btn.classList.toggle('is-minimized', mini);
    btn.setAttribute('aria-pressed', open ? 'true' : 'false');
  });
  if (typeof updateDockScrollChromeFn === 'function') {
    updateDockScrollChromeFn();
  }
}

/**
 * Update horizontal scroll indicators on dock when overflowing viewport.
 * @param {object} params
 */
export function updateDockScrollChrome({ dock, dockApps, dockScrollPrev, dockScrollNext }) {
  if (!dockApps) return;
  const overflow = dockApps.scrollWidth > dockApps.clientWidth + 4;
  if (dockScrollPrev) {
    dockScrollPrev.hidden = !overflow;
    dockScrollPrev.disabled = dockApps.scrollLeft <= 2;
  }
  if (dockScrollNext) {
    dockScrollNext.hidden = !overflow;
    dockScrollNext.disabled = dockApps.scrollLeft + dockApps.clientWidth >= dockApps.scrollWidth - 2;
  }
  if (dock) dock.classList.toggle('has-overflow', overflow);
}

/**
 * Scroll the dock horizontally by a stepped delta.
 * @param {number} dir - Direction (-1 or 1)
 * @param {HTMLElement|null} dockApps
 */
export function scrollDockBy(dir, dockApps) {
  if (!dockApps) return;
  const step = Math.max(120, Math.floor(dockApps.clientWidth * 0.55));
  dockApps.scrollBy({ left: dir * step, behavior: 'smooth' });
}

/**
 * Bind click and scroll events to dock scroll prev/next buttons.
 * @param {object} params
 */
export function bindDockScroll({ dockApps, dockScrollPrev, dockScrollNext, updateDockScrollChromeFn }) {
  if (dockScrollPrev) {
    dockScrollPrev.addEventListener('click', () => scrollDockBy(-1, dockApps));
  }
  if (dockScrollNext) {
    dockScrollNext.addEventListener('click', () => scrollDockBy(1, dockApps));
  }
  if (dockApps) {
    dockApps.addEventListener('scroll', () => {
      if (typeof updateDockScrollChromeFn === 'function') updateDockScrollChromeFn();
    }, { passive: true });
  }
}
