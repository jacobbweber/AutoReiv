/**
 * Agent Desktop - Desktop Chrome Scaffolding & Launchers
 * Defines dock manifests, tab view maps, edge definitions, and DOM scaffolding.
 */

import { $, $query, safeCreateIcons } from '../../dom.js';


/**
 * Ensure desktop stage wallpaper, window layer, and bottom dock chrome exist in DOM.
 */
export function ensureDesktopChrome() {
  const main = $query('main');

  if (!$('desktopStage') && main) {
    const stage = document.createElement('div');
    stage.id = 'desktopStage';
    stage.className = 'desktop-stage';
    stage.setAttribute('aria-label', 'Agent desktop wallpaper');
    stage.innerHTML = `
      <div class="desktop-wallpaper" aria-hidden="true"></div>
      <div id="desktopGridOverlay" class="desktop-grid-overlay" aria-hidden="true"></div>
      <div class="desktop-brand">
        <span class="desktop-brand-dot"></span>
        <span>AGENT DESKTOP</span>
        <span class="desktop-brand-hint">Dock launches studios as windows</span>
      </div>
    `;
    main.insertBefore(stage, main.firstChild);
  } else if ($('desktopStage') && !$('desktopGridOverlay')) {
    const stage = $('desktopStage');
    const overlay = document.createElement('div');
    overlay.id = 'desktopGridOverlay';
    overlay.className = 'desktop-grid-overlay';
    overlay.setAttribute('aria-hidden', 'true');
    stage.appendChild(overlay);
  }

  if (!$('desktopWindowLayer')) {
    const layer = document.createElement('div');
    layer.id = 'desktopWindowLayer';
    layer.className = 'desktop-window-layer';
    layer.setAttribute('aria-live', 'polite');
    const parent = $('appRoot') || document.body;
    parent.appendChild(layer);
  }

  if (!$('desktopDock')) {
    const dock = document.createElement('div');
    dock.id = 'desktopDock';
    dock.className = 'desktop-dock';
    dock.setAttribute('role', 'toolbar');
    dock.setAttribute('aria-label', 'Desktop dock launcher');
    dock.innerHTML = `
      <div class="desktop-dock-bar">
        <div class="desktop-dock-shell">
          <div class="desktop-dock-organize">
            <button type="button" id="desktopOrganizeBtn" class="desktop-organize-btn" title="Organize windows" aria-label="Organize windows" aria-haspopup="true" aria-expanded="false">
              <i data-lucide="layout-grid" class="w-4 h-4"></i>
            </button>
            <div id="desktopOrganizeMenu" class="desktop-organize-menu hidden" role="menu">
              <button type="button" role="menuitem" data-arrange="tile">Tile all</button>
              <button type="button" role="menuitem" data-arrange="cascade">Cascade</button>
              <button type="button" role="menuitem" data-arrange="snap-left">Snap left half</button>
              <button type="button" role="menuitem" data-arrange="snap-right">Snap right half</button>
              <button type="button" role="menuitem" data-arrange="maximize">Maximize / restore</button>
              <button type="button" role="menuitem" data-arrange="grid">Toggle grid overlay</button>
            </div>
          </div>
          <button type="button" id="desktopDockScrollPrev" class="desktop-dock-scroll" title="Scroll dock left" aria-label="Scroll dock left" hidden>
            <i data-lucide="chevron-left" class="w-4 h-4"></i>
          </button>
          <div id="desktopDockApps" class="desktop-dock-apps"></div>
          <button type="button" id="desktopDockScrollNext" class="desktop-dock-scroll" title="Scroll dock right" aria-label="Scroll dock right" hidden>
            <i data-lucide="chevron-right" class="w-4 h-4"></i>
          </button>
          <div class="desktop-dock-tray">
            <span id="desktopClock" class="desktop-clock" aria-live="off">--:--</span>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(dock);
    safeCreateIcons(dock);
  }
}

/**
 * Enhance known HITL dialogs to sit above the desktop window layer [CARD-344].
 */
export function enhanceHitlDialogs() {
  ['chatToolsModal', 'routineModal'].forEach((id) => {
    const modal = $(id);
    if (!modal) return;
    modal.classList.add('desktop-dialog-host');
    const panel = modal.firstElementChild;
    if (panel) panel.classList.add('desktop-dialog-window');
  });
}

/**
 * Update the bottom tray digital clock.
 * @param {HTMLElement|null} clockEl
 */
export function tickClock(clockEl) {
  if (!clockEl) return;
  const now = new Date();
  clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
