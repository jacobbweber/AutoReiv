/**
 * Radical Demo 04 - AGENT DESKTOP (OS-style multi-window environment)
 * Branch: demo/ui-radical-04-agent-desktop
 *
 * Hard bans (zero shared DNA with radical 01-03 as primary nav):
 * - NO persistent left sidebar / app rail as primary nav
 * - NO orb+pie, NO void-palette-only, NO infinite graph cosmos home
 * - NO fighter HUD FABs as primary
 * - NO single-column SaaS app shell
 *
 * Mental model: the control plane is a desktop. Studios and agents open as
 * draggable windows. Navigation is a bottom dock / taskbar launcher.
 * HITL approvals surface as modal dialog windows.
 */

import { $, $query, $queryAll, safeCreateIcons } from '../dom.js';

/** @typedef {{ id: string, tab: string, label: string, icon: string, subtitle?: string, defaultSize?: { w: number, h: number } }} DockLauncher */

export const DOCK_LAUNCHERS = /** @type {DockLauncher[]} */ ([
  { id: 'dock-chat', tab: 'chat', label: 'Chat', icon: 'message-square', subtitle: 'Agent conversations', defaultSize: { w: 720, h: 560 } },
  { id: 'dock-wiki', tab: 'wiki', label: 'Wiki', icon: 'book-marked', subtitle: 'Knowledge vault', defaultSize: { w: 780, h: 560 } },
  { id: 'dock-projects', tab: 'projects', label: 'Projects', icon: 'folders', subtitle: 'Workspaces', defaultSize: { w: 760, h: 540 } },
  { id: 'dock-agents', tab: 'agents', label: 'Agents', icon: 'users', subtitle: 'Forge / fleet', defaultSize: { w: 820, h: 580 } },
  { id: 'dock-factory', tab: 'factory', label: 'Factory', icon: 'flask-conical', subtitle: 'Training lab', defaultSize: { w: 860, h: 600 } },
  { id: 'dock-routines', tab: 'routines', label: 'Routines', icon: 'clock', subtitle: 'Schedules', defaultSize: { w: 700, h: 520 } },
  { id: 'dock-observability', tab: 'observability', label: 'Observe', icon: 'bar-chart-3', subtitle: 'Telemetry', defaultSize: { w: 760, h: 540 } },
  { id: 'dock-settings', tab: 'settings', label: 'Settings', icon: 'settings', subtitle: 'Providers', defaultSize: { w: 720, h: 540 } },
  { id: 'dock-prompts', tab: 'prompts', label: 'Prompts', icon: 'sparkles', subtitle: 'Catalog', defaultSize: { w: 700, h: 520 } },
  { id: 'dock-sessions', tab: 'sessions', label: 'Sessions', icon: 'panel-left', subtitle: 'Chat sessions', defaultSize: { w: 320, h: 520 } },
]);

const VIEW_BY_TAB = {
  chat: 'view-chat',
  wiki: 'view-wiki',
  projects: 'view-projects',
  agents: 'view-agents',
  factory: 'view-factory',
  routines: 'view-routines',
  observability: 'view-observability',
  settings: 'view-settings',
  prompts: 'view-prompts',
};

const MIN_W = 320;
const MIN_H = 240;
export const GRID_SIZE = 16;
export const PREFS_KEY = 'autoreiv.agentDesktop.v1';

const RESIZE_EDGES = ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'];

/**
 * Cascade offset for newly opened windows (deterministic, no RNG).
 * @param {number} index
 * @returns {{ x: number, y: number }}
 */
export function cascadeOffset(index) {
  const i = Math.max(0, Number(index) || 0);
  const step = 28;
  return { x: 48 + (i % 8) * step, y: 36 + (i % 8) * step };
}

/**
 * Snap a numeric value to the desktop grid.
 * @param {number} value
 * @param {number} [grid]
 * @param {boolean} [disable]
 * @returns {number}
 */
export function snapToGrid(value, grid = GRID_SIZE, disable = false) {
  if (disable) return value;
  const g = Math.max(1, Number(grid) || GRID_SIZE);
  return Math.round(Number(value) / g) * g;
}

/**
 * Snap a window rect to the grid (position + size).
 * @param {{ x: number, y: number, w: number, h: number }} rect
 * @param {number} [grid]
 * @param {boolean} [disable]
 * @returns {{ x: number, y: number, w: number, h: number }}
 */
export function snapRectToGrid(rect, grid = GRID_SIZE, disable = false) {
  if (disable) return { ...rect };
  return {
    x: snapToGrid(rect.x, grid, false),
    y: snapToGrid(rect.y, grid, false),
    w: Math.max(MIN_W, snapToGrid(rect.w, grid, false)),
    h: Math.max(MIN_H, snapToGrid(rect.h, grid, false)),
  };
}

/**
 * Clamp a window rect inside the desktop viewport (leaves room for dock).
 * @param {{ x: number, y: number, w: number, h: number }} rect
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {{ x: number, y: number, w: number, h: number }}
 */
export function clampWindowRect(rect, viewport) {
  const dockH = viewport.dockH ?? 72;
  const maxW = Math.max(MIN_W, viewport.width - 16);
  const maxH = Math.max(MIN_H, viewport.height - dockH - 16);
  const w = Math.min(Math.max(MIN_W, rect.w || MIN_W), maxW);
  const h = Math.min(Math.max(MIN_H, rect.h || MIN_H), maxH);
  const maxX = Math.max(0, viewport.width - w);
  const maxY = Math.max(0, viewport.height - dockH - h);
  const x = Math.min(Math.max(0, rect.x || 0), maxX);
  const y = Math.min(Math.max(0, rect.y || 0), maxY);
  return { x, y, w, h };
}

/**
 * Compute tiled grid rects for N windows.
 * @param {number} count
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {Array<{ x: number, y: number, w: number, h: number }>}
 */
export function computeTileRects(count, viewport) {
  const n = Math.max(0, Math.floor(Number(count) || 0));
  if (!n) return [];
  const dockH = viewport.dockH ?? 72;
  const areaW = Math.max(MIN_W, viewport.width - 16);
  const areaH = Math.max(MIN_H, viewport.height - dockH - 16);
  const cols = Math.ceil(Math.sqrt(n));
  const rows = Math.ceil(n / cols);
  const cellW = Math.floor(areaW / cols);
  const cellH = Math.floor(areaH / rows);
  /** @type {Array<{ x: number, y: number, w: number, h: number }>} */
  const rects = [];
  for (let i = 0; i < n; i += 1) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    rects.push(
      clampWindowRect(
        {
          x: 8 + col * cellW,
          y: 8 + row * cellH,
          w: Math.max(MIN_W, cellW - 8),
          h: Math.max(MIN_H, cellH - 8),
        },
        viewport,
      ),
    );
  }
  return rects;
}

/**
 * Cascade layout rects for N windows.
 * @param {number} count
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @param {{ w?: number, h?: number }} [size]
 * @returns {Array<{ x: number, y: number, w: number, h: number }>}
 */
export function computeCascadeRects(count, viewport, size = {}) {
  const n = Math.max(0, Math.floor(Number(count) || 0));
  const w = size.w || 640;
  const h = size.h || 480;
  /** @type {Array<{ x: number, y: number, w: number, h: number }>} */
  const rects = [];
  for (let i = 0; i < n; i += 1) {
    const off = cascadeOffset(i);
    rects.push(clampWindowRect({ x: off.x, y: off.y, w, h }, viewport));
  }
  return rects;
}

/**
 * Snap focused window to left or right half of the desktop.
 * @param {'left'|'right'} side
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {{ x: number, y: number, w: number, h: number }}
 */
export function computeSnapHalf(side, viewport) {
  const dockH = viewport.dockH ?? 72;
  const gap = 8;
  const halfW = Math.floor((viewport.width - gap * 3) / 2);
  const h = Math.max(MIN_H, viewport.height - dockH - gap * 2);
  const x = side === 'right' ? gap * 2 + halfW : gap;
  return clampWindowRect({ x, y: gap, w: halfW, h }, viewport);
}

/**
 * Maximize rect filling space above the dock.
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {{ x: number, y: number, w: number, h: number }}
 */
export function computeMaximizeRect(viewport) {
  const dockH = viewport.dockH ?? 72;
  return clampWindowRect(
    {
      x: 8,
      y: 8,
      w: viewport.width - 16,
      h: viewport.height - dockH - 16,
    },
    viewport,
  );
}

/**
 * Mobile layout: every focused window fills the area above the dock (no 50/50 stack).
 * openCount/index retained for API compatibility; always returns full maximize rect.
 * @param {number} _openCount
 * @param {number} _index
 * @param {{ width: number, height: number, dockH?: number }} viewport
 * @returns {{ x: number, y: number, w: number, h: number, mode: 'full' }}
 */
export function computeMobileLayout(_openCount, _index, viewport) {
  const dockH = viewport.dockH ?? 72;
  const w = viewport.width;
  const usableH = Math.max(MIN_H, viewport.height - dockH);
  return { x: 0, y: 0, w, h: usableH, mode: 'full' };
}

/**
 * @param {object} [state]
 * @returns {Array<{id:string,name:string}>}
 */
export function collectAgentsFromDom(state) {
  const fromState = Array.isArray(state?.agents)
    ? state.agents
        .map((a) => ({
          id: a.id || a.agent_id || a.name,
          name: a.name || a.label || a.id,
        }))
        .filter((a) => a.id)
    : [];
  if (fromState.length) return fromState;

  if (typeof document === 'undefined') return [];
  const select = $('agentSelect') || $('chatTopBarAgentSelect');
  if (!select) return [];
  return Array.from(select.options || [])
    .filter((o) => o.value)
    .map((o) => ({ id: o.value, name: (o.textContent || o.value).trim() }));
}

/**
 * Load persisted window prefs (positions/sizes). Schema v1.
 * @returns {{ windows: Record<string, {x:number,y:number,w:number,h:number, maximized?: boolean}>, gridOverlay?: boolean }}
 */
export function loadDesktopPrefs() {
  const empty = { windows: {}, gridOverlay: false };
  if (typeof localStorage === 'undefined') return empty;
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return empty;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return empty;
    const windows = parsed.windows && typeof parsed.windows === 'object' ? parsed.windows : {};
    return {
      windows,
      gridOverlay: !!parsed.gridOverlay,
    };
  } catch {
    return empty;
  }
}

/**
 * @param {{ windows: Record<string, object>, gridOverlay?: boolean }} prefs
 */
export function saveDesktopPrefs(prefs) {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(
      PREFS_KEY,
      JSON.stringify({
        windows: prefs.windows || {},
        gridOverlay: !!prefs.gridOverlay,
      }),
    );
  } catch {
    /* quota / private mode */
  }
}

/**
 * @param {{ switchTab: (tab: string) => void, state: object, showToast?: Function, getChatCtrl?: () => object|null }} opts
 */
export function initAgentDesktop(opts = {}) {
  const { switchTab, state, showToast, getChatCtrl } = opts;
  if (typeof document === 'undefined') return null;

  const root = document.body;
  root.classList.add('radical-desktop-demo');

  ensureDesktopChrome();

  const dock = $('desktopDock');
  const dockApps = $('desktopDockApps');
  const dockScrollPrev = $('desktopDockScrollPrev');
  const dockScrollNext = $('desktopDockScrollNext');
  const layer = $('desktopWindowLayer');
  const clockEl = $('desktopClock');
  const organizeMenu = $('desktopOrganizeMenu');
  const gridOverlayEl = $('desktopGridOverlay');

  /** @type {Map<string, DesktopWindow>} */
  const windows = new Map();
  let zTop = 40;
  let openCount = 0;
  let syncRaf = 0;
  let persistTimer = 0;
  let gridOverlay = false;
  const prefs = loadDesktopPrefs();
  gridOverlay = !!prefs.gridOverlay;

  /**
   * @typedef {{
   *   id: string,
   *   tab: string,
   *   label: string,
   *   el: HTMLElement,
   *   bodyEl: HTMLElement,
   *   minimized: boolean,
   *   maximized: boolean,
   *   restoreRect: { x:number, y:number, w:number, h:number }|null,
   *   rect: { x:number, y:number, w:number, h:number },
   *   z: number,
   * }} DesktopWindow
   */

  function toast(msg, type = 'info', dur) {
    if (typeof showToast === 'function') showToast(msg, type, dur);
  }

  function viewportSize() {
    const dockH = dock ? dock.getBoundingClientRect().height : 72;
    return {
      width: window.innerWidth || document.documentElement.clientWidth || 1280,
      height: window.innerHeight || document.documentElement.clientHeight || 800,
      dockH,
    };
  }

  function isMobile() {
    return window.matchMedia && window.matchMedia('(max-width: 767px)').matches;
  }

  function nextZ() {
    zTop += 1;
    return zTop;
  }

  function launcherForTab(tab) {
    return DOCK_LAUNCHERS.find((d) => d.tab === tab) || null;
  }

  function viewIdForTab(tab) {
    return VIEW_BY_TAB[tab] || null;
  }

  function altHeld(e) {
    return !!(e && e.altKey);
  }

  function schedulePersist() {
    if (persistTimer) window.clearTimeout(persistTimer);
    persistTimer = window.setTimeout(() => {
      persistTimer = 0;
      persistPrefs();
    }, 200);
  }

  function persistPrefs() {
    /** @type {Record<string, object>} */
    const winPrefs = {};
    windows.forEach((win) => {
      winPrefs[win.tab] = {
        x: win.rect.x,
        y: win.rect.y,
        w: win.rect.w,
        h: win.rect.h,
        maximized: !!win.maximized,
      };
    });
    // Keep previously saved closed windows so reopen restores
    Object.keys(prefs.windows || {}).forEach((tab) => {
      if (!winPrefs[tab]) winPrefs[tab] = prefs.windows[tab];
    });
    prefs.windows = winPrefs;
    prefs.gridOverlay = gridOverlay;
    saveDesktopPrefs(prefs);
  }

  function updateGridOverlay() {
    if (!gridOverlayEl) return;
    gridOverlayEl.classList.toggle('is-visible', gridOverlay && !isMobile());
    root.classList.toggle('desktop-grid-on', gridOverlay && !isMobile());
  }

  function updateDockActive() {
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
    updateDockScrollChrome();
  }

  function updateDockScrollChrome() {
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

  function scrollDockBy(dir) {
    if (!dockApps) return;
    const step = Math.max(120, Math.floor(dockApps.clientWidth * 0.55));
    dockApps.scrollBy({ left: dir * step, behavior: 'smooth' });
  }

  function focusWindow(tab) {
    const win = windows.get(tab);
    if (!win || win.minimized) return;
    win.z = nextZ();
    win.el.style.zIndex = String(win.z + 2);
    windows.forEach((w) => w.el.classList.toggle('is-focused', w.tab === tab));
    root.setAttribute('data-desktop-focus', tab);
    if (isMobile()) {
      applyMobileLayout();
      return;
    }
    scheduleSyncHostedViews();
  }

  function visibleWindows() {
    return Array.from(windows.values()).filter((w) => !w.minimized);
  }

  function applyMobileLayout() {
    const vis = visibleWindows().sort((a, b) => a.z - b.z);
    const vp = viewportSize();
    if (!vis.length) {
      scheduleSyncHostedViews();
      return;
    }
    // Focused = highest z. Maximize it above the dock; minimize others (app-switcher style).
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
    updateDockActive();
    scheduleSyncHostedViews();
  }

  function applyRect(win) {
    const vp = viewportSize();
    if (isMobile()) {
      applyMobileLayout();
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
    scheduleSyncHostedViews();
    schedulePersist();
  }

  function scheduleSyncHostedViews() {
    if (syncRaf) return;
    syncRaf = window.requestAnimationFrame(() => {
      syncRaf = 0;
      syncHostedViews();
    });
  }

  /**
   * Position real studio/chat tab-views inside their window bodies.
   * Preserves DOM IDs (messagesContainer, chatForm, etc.) - no clone.
   */
  function syncHostedViews() {
    Object.keys(VIEW_BY_TAB).forEach((tab) => {
      const view = $(VIEW_BY_TAB[tab]);
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
      if (win.tab === 'sessions') {
        return;
      }
      const viewId = viewIdForTab(win.tab);
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
        view.addEventListener('pointerdown', () => focusWindow(win.tab));
      }
    });

    const sessionsWin = windows.get('sessions');
    root.classList.toggle('desktop-sessions-open', !!(sessionsWin && !sessionsWin.minimized));
    const sidebar = $('sidebar');
    if (sidebar && sessionsWin && !sessionsWin.minimized && sessionsWin.bodyEl) {
      const rect = sessionsWin.bodyEl.getBoundingClientRect();
      sidebar.style.setProperty('--dw-l', `${Math.round(rect.left)}px`);
      sidebar.style.setProperty('--dw-t', `${Math.round(rect.top)}px`);
      sidebar.style.setProperty('--dw-w', `${Math.round(rect.width)}px`);
      sidebar.style.setProperty('--dw-h', `${Math.round(rect.height)}px`);
      sidebar.style.zIndex = String(sessionsWin.z + 1);
      sidebar.style.setProperty('--dw-z', String(sessionsWin.z + 1));
      if (!sidebar.dataset.desktopFocusBound) {
        sidebar.dataset.desktopFocusBound = 'true';
        sidebar.addEventListener('pointerdown', () => focusWindow('sessions'));
      }
    } else if (sidebar) {
      sidebar.style.removeProperty('--dw-l');
      sidebar.style.removeProperty('--dw-t');
      sidebar.style.removeProperty('--dw-w');
      sidebar.style.removeProperty('--dw-h');
      sidebar.style.removeProperty('--dw-z');
      sidebar.style.removeProperty('z-index');
    }
  }

  function buildTitleExtras(tab, titleRight) {
    if (tab !== 'chat' || !titleRight) return;
    const agents = collectAgentsFromDom(state);
    const wrap = document.createElement('div');
    wrap.className = 'desktop-win-agent-switch';
    const sel = document.createElement('select');
    sel.className = 'desktop-win-agent-select';
    sel.title = 'Switch active agent';
    sel.setAttribute('aria-label', 'Switch active agent');
    if (!agents.length) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'Agents.';
      sel.appendChild(opt);
    } else {
      agents.forEach((a) => {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = a.name;
        sel.appendChild(opt);
      });
    }
    const stock = $('chatTopBarAgentSelect') || $('agentSelect');
    if (stock && stock.value) sel.value = stock.value;
    sel.addEventListener('change', () => {
      selectAgent(sel.value);
    });
    wrap.appendChild(sel);
    titleRight.appendChild(wrap);
  }

  function createWindowShell(launcher) {
    const tab = launcher.tab;
    const el = document.createElement('div');
    el.className = 'desktop-window';
    el.id = `desktopWin-${tab}`;
    el.setAttribute('data-desktop-tab', tab);
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-label', launcher.label);

    const handles = RESIZE_EDGES.map((edge) => `<div class="desktop-win-resize desktop-win-resize-${edge}" data-resize="${edge}" title="Resize"></div>`).join('');

    el.innerHTML = `
      <div class="desktop-win-titlebar" data-drag-handle="1">
        <div class="desktop-win-title-left">
          <span class="desktop-win-icon"><i data-lucide="${escapeAttr(launcher.icon)}" class="w-3.5 h-3.5"></i></span>
          <span class="desktop-win-title">${escapeHtmlLite(launcher.label)}</span>
          <span class="desktop-win-sub">${escapeHtmlLite(launcher.subtitle || '')}</span>
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

    const vp = viewportSize();
    const def = launcher.defaultSize || { w: 720, h: 520 };
    const saved = prefs.windows && prefs.windows[tab];
    const off = cascadeOffset(openCount);
    let rect;
    let maximized = false;
    if (saved && typeof saved.w === 'number' && typeof saved.h === 'number') {
      rect = clampWindowRect(
        { x: saved.x ?? off.x, y: saved.y ?? off.y, w: saved.w, h: saved.h },
        vp,
      );
      maximized = !!saved.maximized;
    } else {
      rect = clampWindowRect(
        { x: off.x, y: off.y, w: Math.min(def.w, vp.width - 32), h: Math.min(def.h, vp.height - vp.dockH - 24) },
        vp,
      );
    }

    /** @type {DesktopWindow} */
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
      z: nextZ(),
    };

    el.style.zIndex = String(win.z + 2);
    layer.appendChild(el);
    safeCreateIcons(el);
    bindWindowChrome(win);
    applyRect(win);
    openCount += 1;
    windows.set(tab, win);
    return win;
  }

  function bindWindowChrome(win) {
    const titlebar = $query('[data-drag-handle]', win.el);
    const minBtn = $query('.desktop-win-min', win.el);
    const maxBtn = $query('.desktop-win-max', win.el);
    const closeBtn = $query('.desktop-win-close', win.el);
    const resizeHandles = $queryAll('[data-resize]', win.el);

    win.el.addEventListener('mousedown', () => focusWindow(win.tab));
    win.el.addEventListener('touchstart', () => focusWindow(win.tab), { passive: true });

    if (minBtn) {
      minBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        minimizeWindow(win.tab);
      });
    }
    if (maxBtn) {
      maxBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleMaximize(win.tab);
      });
    }
    if (closeBtn) {
      closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        closeWindow(win.tab);
      });
    }

    if (titlebar) {
      titlebar.addEventListener('dblclick', (e) => {
        if (e.target && e.target.closest && e.target.closest('.desktop-win-btn, select, button, a')) return;
        if (isMobile()) return;
        toggleMaximize(win.tab);
      });

      let dragging = false;
      let startX = 0;
      let startY = 0;
      let origX = 0;
      let origY = 0;
      let disableSnap = false;

      const onMove = (clientX, clientY) => {
        if (!dragging || isMobile()) return;
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
        applyRect(win);
      };

      const onTitlePointerMove = (e) => {
        if (!dragging || isMobile()) return;
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
        schedulePersist();
      };

      titlebar.addEventListener('pointerdown', (e) => {
        if (e.button != null && e.button !== 0) return;
        if (e.target && e.target.closest && e.target.closest('.desktop-win-btn, select, button, a')) return;
        if (isMobile()) return;
        dragging = true;
        disableSnap = altHeld(e);
        startX = e.clientX;
        startY = e.clientY;
        origX = win.rect.x;
        origY = win.rect.y;
        focusWindow(win.tab);
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
        applyRect(win);
      };

      const endResize = () => {
        if (!resizing) return;
        resizing = false;
        win.el.classList.remove('is-resizing');
        window.removeEventListener('pointermove', onResizePointerMove);
        window.removeEventListener('pointerup', endResize);
        window.removeEventListener('pointercancel', endResize);
        schedulePersist();
      };

      resizeHandle.addEventListener('pointerdown', (e) => {
        if (isMobile()) return;
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
        focusWindow(win.tab);
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

  function openWindow(tab, { focusComposer: doFocus = false } = {}) {
    const launcher = launcherForTab(tab);
    if (!launcher) return null;

    let win = windows.get(tab);
    if (win) {
      if (win.minimized) {
        win.minimized = false;
        win.el.classList.remove('is-minimized');
        win.el.setAttribute('aria-hidden', 'false');
      }
      // Focus first so mobile maximize targets this window (highest z).
      focusWindow(tab);
      if (!isMobile()) applyRect(win);
      updateDockActive();
    } else {
      win = createWindowShell(launcher);
      focusWindow(tab);
      updateDockActive();
      if (isMobile()) applyMobileLayout();
    }

    root.classList.add('desktop-has-windows');

    if (tab !== 'sessions' && typeof switchTab === 'function') {
      switchTab(tab);
    }

    if (tab === 'chat' && doFocus) {
      focusComposer();
    }

    scheduleSyncHostedViews();
    schedulePersist();
    return win;
  }

  function minimizeWindow(tab) {
    const win = windows.get(tab);
    if (!win) return;
    win.minimized = true;
    win.el.classList.add('is-minimized');
    win.el.setAttribute('aria-hidden', 'true');
    updateDockActive();
    if (isMobile()) applyMobileLayout();
    scheduleSyncHostedViews();
    toast(`${win.label} minimized`, 'info', 900);
  }

  function closeWindow(tab) {
    const win = windows.get(tab);
    if (!win) return;
    // Persist last rect before close
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
    updateDockActive();
    if (!windows.size) {
      root.classList.remove('desktop-has-windows');
      root.removeAttribute('data-desktop-focus');
    }
    if (isMobile()) applyMobileLayout();
    scheduleSyncHostedViews();
    schedulePersist();

    const viewId = viewIdForTab(tab);
    const view = viewId ? $(viewId) : null;
    if (view) {
      view.classList.add('desktop-view-parked', 'hidden');
      view.classList.remove('desktop-view-hosted', 'flex');
      view.setAttribute('aria-hidden', 'true');
    }
  }

  function toggleMaximize(tab) {
    const win = windows.get(tab);
    if (!win || isMobile()) return;
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
    applyRect(win);
    focusWindow(tab);
  }

  function arrangeTile() {
    const vis = visibleWindows();
    if (!vis.length) return;
    const vp = viewportSize();
    if (isMobile()) {
      applyMobileLayout();
      toast('Mobile snap applied', 'info', 900);
      return;
    }
    const rects = computeTileRects(vis.length, vp);
    vis.forEach((win, i) => {
      win.maximized = false;
      win.restoreRect = null;
      win.rect = rects[i] || win.rect;
      applyRect(win);
    });
    toast('Windows tiled', 'info', 900);
  }

  function arrangeCascade() {
    const vis = visibleWindows();
    if (!vis.length) return;
    if (isMobile()) {
      applyMobileLayout();
      return;
    }
    const vp = viewportSize();
    const rects = computeCascadeRects(vis.length, vp, { w: 640, h: 480 });
    vis.forEach((win, i) => {
      win.maximized = false;
      win.restoreRect = null;
      win.rect = rects[i] || win.rect;
      applyRect(win);
      focusWindow(win.tab);
    });
    toast('Windows cascaded', 'info', 900);
  }

  function arrangeSnapHalf(side) {
    const focus = root.getAttribute('data-desktop-focus');
    const win = focus ? windows.get(focus) : visibleWindows().slice(-1)[0];
    if (!win || win.minimized) {
      toast('Focus a window first', 'info', 900);
      return;
    }
    if (isMobile()) {
      // Mobile: snap presets full / half via layout
      applyMobileLayout();
      toast(`Mobile layout (${side})`, 'info', 900);
      return;
    }
    const vp = viewportSize();
    win.maximized = false;
    win.restoreRect = null;
    win.rect = computeSnapHalf(side, vp);
    applyRect(win);
    focusWindow(win.tab);
    toast(`Snapped ${side}`, 'info', 900);
  }

  function toggleGridOverlay() {
    gridOverlay = !gridOverlay;
    updateGridOverlay();
    schedulePersist();
    toast(gridOverlay ? 'Grid overlay on' : 'Grid overlay off', 'info', 900);
  }

  function selectAgent(agentId) {
    if (!agentId) return;
    if (state && typeof state === 'object') {
      state.selectedAgentId = agentId;
    }
    const selects = [$('agentSelect'), $('chatTopBarAgentSelect')].filter(Boolean);
    selects.forEach((sel) => {
      if (sel.value !== agentId) {
        sel.value = agentId;
        sel.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });
    windows.forEach((win) => {
      const sel = $query('.desktop-win-agent-select', win.el);
      if (sel && sel.value !== agentId) sel.value = agentId;
    });
    const chat = typeof getChatCtrl === 'function' ? getChatCtrl() : null;
    if (chat && typeof chat.updateActiveAgentHeader === 'function') {
      try {
        chat.updateActiveAgentHeader();
      } catch {
        /* ignore */
      }
    }
  }

  function focusComposer() {
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

  function onTabChanged(tabName) {
    if (!tabName) return;
    if (tabName === 'sessions') {
      openWindow('sessions');
      return;
    }
    if (!VIEW_BY_TAB[tabName]) return;
    const win = windows.get(tabName);
    if (win && !win.minimized) {
      focusWindow(tabName);
      scheduleSyncHostedViews();
      return;
    }
    openWindow(tabName);
  }

  function renderDock() {
    if (!dockApps) return;
    dockApps.innerHTML = DOCK_LAUNCHERS.map(
      (d) => `
      <button type="button" id="${escapeAttr(d.id)}" class="desktop-dock-btn" data-dock-tab="${escapeAttr(d.tab)}" data-dock-id="${escapeAttr(d.id)}" title="${escapeAttr(d.label)}" aria-label="${escapeAttr(d.label)}" aria-pressed="false">
        <span class="desktop-dock-icon"><i data-lucide="${escapeAttr(d.icon)}" class="w-5 h-5"></i></span>
        <span class="desktop-dock-label">${escapeHtmlLite(d.label)}</span>
        <span class="desktop-dock-indicator" aria-hidden="true"></span>
      </button>`,
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
        if (tab === 'chat') toast('Chat window', 'info', 1000);
      });
    });
    updateDockScrollChrome();
  }

  function bindOrganizeMenu() {
    const toggleBtn = $('desktopOrganizeBtn');
    if (!toggleBtn || !organizeMenu) return;

    const closeMenu = () => {
      organizeMenu.classList.add('hidden');
      toggleBtn.setAttribute('aria-expanded', 'false');
    };

    toggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const open = organizeMenu.classList.contains('hidden');
      organizeMenu.classList.toggle('hidden', !open);
      toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    organizeMenu.addEventListener('click', (e) => {
      const btn = e.target && e.target.closest ? e.target.closest('[data-arrange]') : null;
      if (!btn) return;
      const action = btn.getAttribute('data-arrange');
      if (action === 'tile') arrangeTile();
      else if (action === 'cascade') arrangeCascade();
      else if (action === 'snap-left') arrangeSnapHalf('left');
      else if (action === 'snap-right') arrangeSnapHalf('right');
      else if (action === 'maximize') {
        const focus = root.getAttribute('data-desktop-focus');
        if (focus) toggleMaximize(focus);
      } else if (action === 'grid') toggleGridOverlay();
      closeMenu();
    });

    document.addEventListener('click', (e) => {
      if (!organizeMenu.classList.contains('hidden')) {
        if (e.target && (toggleBtn.contains(e.target) || organizeMenu.contains(e.target))) return;
        closeMenu();
      }
    });
  }

  function bindDockScroll() {
    if (dockScrollPrev) {
      dockScrollPrev.addEventListener('click', () => scrollDockBy(-1));
    }
    if (dockScrollNext) {
      dockScrollNext.addEventListener('click', () => scrollDockBy(1));
    }
    if (dockApps) {
      dockApps.addEventListener('scroll', () => updateDockScrollChrome(), { passive: true });
    }
  }

  function tickClock() {
    if (!clockEl) return;
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function enhanceHitlDialogs() {
    ['factoryDeliverableModal', 'chatToolsModal'].forEach((id) => {
      const modal = $(id);
      if (!modal) return;
      modal.classList.add('desktop-dialog-host');
      const panel = modal.firstElementChild;
      if (panel) panel.classList.add('desktop-dialog-window');
    });
  }

  function bindGlobal() {
    window.addEventListener('resize', () => {
      windows.forEach((win) => {
        if (!win.minimized) applyRect(win);
      });
      if (isMobile()) applyMobileLayout();
      scheduleSyncHostedViews();
      updateDockScrollChrome();
    });
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const focus = root.getAttribute('data-desktop-focus');
        if (focus && windows.has(focus)) {
          const openModal = $query('.desktop-dialog-host:not(.hidden)');
          if (openModal) return;
          if (organizeMenu && !organizeMenu.classList.contains('hidden')) {
            organizeMenu.classList.add('hidden');
            return;
          }
          e.preventDefault();
          minimizeWindow(focus);
        }
        return;
      }

      // Arrange shortcuts: Ctrl+Alt+…
      if (!(e.ctrlKey && e.altKey) || e.metaKey) return;
      const key = e.key;
      if (key === 't' || key === 'T') {
        e.preventDefault();
        arrangeTile();
      } else if (key === 'c' || key === 'C') {
        e.preventDefault();
        arrangeCascade();
      } else if (key === 'g' || key === 'G') {
        e.preventDefault();
        toggleGridOverlay();
      } else if (key === 'ArrowLeft') {
        e.preventDefault();
        arrangeSnapHalf('left');
      } else if (key === 'ArrowRight') {
        e.preventDefault();
        arrangeSnapHalf('right');
      } else if (key === 'm' || key === 'M') {
        e.preventDefault();
        const focus = root.getAttribute('data-desktop-focus');
        if (focus) toggleMaximize(focus);
      }
    });

    const toggleSidebarBtn = $('toggleSidebarBtn');
    if (toggleSidebarBtn) {
      toggleSidebarBtn.addEventListener(
        'click',
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          openWindow('sessions');
        },
        true,
      );
    }
  }

  function escapeHtmlLite(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
  function escapeAttr(s) {
    return escapeHtmlLite(s).replace(/'/g, '&#39;');
  }

  renderDock();
  bindOrganizeMenu();
  bindDockScroll();
  enhanceHitlDialogs();
  bindGlobal();
  tickClock();
  updateGridOverlay();
  window.setInterval(tickClock, 30000);
  safeCreateIcons();
  window.requestAnimationFrame(() => updateDockScrollChrome());

  $queryAll('.tab-view').forEach((v) => {
    v.classList.add('desktop-view-parked');
  });

  let tries = 0;
  const agentTimer = window.setInterval(() => {
    tries += 1;
    const chatWin = windows.get('chat');
    if (chatWin) {
      const titleRight = $query('[data-title-right]', chatWin.el);
      const existing = $query('.desktop-win-agent-switch', chatWin.el);
      if (titleRight && existing) existing.remove();
      if (titleRight) buildTitleExtras('chat', titleRight);
      safeCreateIcons(chatWin.el);
    }
    const agents = collectAgentsFromDom(state);
    if (agents.length || tries >= 10) {
      window.clearInterval(agentTimer);
    }
  }, 1200);

  const agentSelect = $('agentSelect');
  if (agentSelect && typeof MutationObserver !== 'undefined') {
    const mo = new MutationObserver(() => {
      const chatWin = windows.get('chat');
      if (!chatWin) return;
      const titleRight = $query('[data-title-right]', chatWin.el);
      const existing = $query('.desktop-win-agent-switch', chatWin.el);
      if (existing) existing.remove();
      if (titleRight) buildTitleExtras('chat', titleRight);
    });
    mo.observe(agentSelect, { childList: true, subtree: true });
  }

  return {
    onTabChanged,
    openWindow,
    closeWindow,
    minimizeWindow,
    focusWindow,
    toggleMaximize,
    arrangeTile,
    arrangeCascade,
    arrangeSnapHalf,
    toggleGridOverlay,
    collectAgentsFromDom,
    destroy() {
      windows.forEach((w) => w.el.remove());
      windows.clear();
      root.classList.remove('radical-desktop-demo', 'desktop-has-windows', 'desktop-sessions-open', 'desktop-grid-on');
      root.removeAttribute('data-desktop-focus');
    },
  };
}

function ensureDesktopChrome() {
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
