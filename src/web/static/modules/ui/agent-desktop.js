/**
 * Radical Demo 04 — AGENT DESKTOP (OS-style multi-window environment)
 * Branch: demo/ui-radical-04-agent-desktop
 *
 * Hard bans (zero shared DNA with radical 01–03 as primary nav):
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
  const select = document.getElementById('agentSelect') || document.getElementById('chatTopBarAgentSelect');
  if (!select) return [];
  return Array.from(select.options || [])
    .filter((o) => o.value)
    .map((o) => ({ id: o.value, name: (o.textContent || o.value).trim() }));
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
  const layer = $('desktopWindowLayer');
  const clockEl = $('desktopClock');

  /** @type {Map<string, DesktopWindow>} */
  const windows = new Map();
  let zTop = 40;
  let openCount = 0;
  let syncRaf = 0;

  /**
   * @typedef {{
   *   id: string,
   *   tab: string,
   *   label: string,
   *   el: HTMLElement,
   *   bodyEl: HTMLElement,
   *   minimized: boolean,
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
  }

  function focusWindow(tab) {
    const win = windows.get(tab);
    if (!win || win.minimized) return;
    win.z = nextZ();
    win.el.style.zIndex = String(win.z);
    windows.forEach((w) => w.el.classList.toggle('is-focused', w.tab === tab));
    root.setAttribute('data-desktop-focus', tab);
    scheduleSyncHostedViews();
  }

  function applyRect(win) {
    const vp = viewportSize();
    if (isMobile()) {
      win.el.style.left = '0px';
      win.el.style.top = '0px';
      win.el.style.width = '100%';
      win.el.style.height = `calc(100% - ${vp.dockH}px)`;
      win.el.classList.add('is-mobile-fs');
    } else {
      const r = clampWindowRect(win.rect, vp);
      win.rect = r;
      win.el.style.left = `${r.x}px`;
      win.el.style.top = `${r.y}px`;
      win.el.style.width = `${r.w}px`;
      win.el.style.height = `${r.h}px`;
      win.el.classList.remove('is-mobile-fs');
    }
    scheduleSyncHostedViews();
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
   * Preserves DOM IDs (messagesContainer, chatForm, etc.) — no clone.
   */
  function syncHostedViews() {
    // Hide all hosted views first
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
        // Sessions hosts #sidebar via CSS class on body
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
    });

    // Sessions sidebar window
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
    } else if (sidebar) {
      sidebar.style.removeProperty('--dw-l');
      sidebar.style.removeProperty('--dw-t');
      sidebar.style.removeProperty('--dw-w');
      sidebar.style.removeProperty('--dw-h');
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
      opt.textContent = 'Agents…';
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
          <button type="button" class="desktop-win-btn desktop-win-close" title="Close" aria-label="Close">
            <i data-lucide="x" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      </div>
      <div class="desktop-win-body" data-win-body="1"></div>
      <div class="desktop-win-resize" data-resize="se" title="Resize"></div>
    `;

    const bodyEl = /** @type {HTMLElement} */ ($query('[data-win-body]', el));
    const titleRight = $query('[data-title-right]', el);
    buildTitleExtras(tab, titleRight);

    const vp = viewportSize();
    const def = launcher.defaultSize || { w: 720, h: 520 };
    const off = cascadeOffset(openCount);
    const rect = clampWindowRect(
      { x: off.x, y: off.y, w: Math.min(def.w, vp.width - 32), h: Math.min(def.h, vp.height - vp.dockH - 24) },
      vp,
    );

    /** @type {DesktopWindow} */
    const win = {
      id: `win-${tab}`,
      tab,
      label: launcher.label,
      el,
      bodyEl,
      minimized: false,
      rect,
      z: nextZ(),
    };

    el.style.zIndex = String(win.z);
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
    const closeBtn = $query('.desktop-win-close', win.el);
    const resizeHandle = $query('[data-resize]', win.el);

    win.el.addEventListener('mousedown', () => focusWindow(win.tab));
    win.el.addEventListener('touchstart', () => focusWindow(win.tab), { passive: true });

    if (minBtn) {
      minBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        minimizeWindow(win.tab);
      });
    }
    if (closeBtn) {
      closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        closeWindow(win.tab);
      });
    }

    // Drag
    if (titlebar) {
      let dragging = false;
      let startX = 0;
      let startY = 0;
      let origX = 0;
      let origY = 0;

      const onMove = (clientX, clientY) => {
        if (!dragging || isMobile()) return;
        win.rect.x = origX + (clientX - startX);
        win.rect.y = origY + (clientY - startY);
        applyRect(win);
      };

      titlebar.addEventListener('pointerdown', (e) => {
        if (e.button != null && e.button !== 0) return;
        if (e.target && e.target.closest && e.target.closest('.desktop-win-btn, select, button, a')) return;
        if (isMobile()) return;
        dragging = true;
        startX = e.clientX;
        startY = e.clientY;
        origX = win.rect.x;
        origY = win.rect.y;
        focusWindow(win.tab);
        win.el.classList.add('is-dragging');
        try {
          titlebar.setPointerCapture(e.pointerId);
        } catch {
          /* ignore */
        }
      });
      titlebar.addEventListener('pointermove', (e) => onMove(e.clientX, e.clientY));
      const endDrag = () => {
        if (!dragging) return;
        dragging = false;
        win.el.classList.remove('is-dragging');
      };
      titlebar.addEventListener('pointerup', endDrag);
      titlebar.addEventListener('pointercancel', endDrag);
    }

    // Resize (SE)
    if (resizeHandle) {
      let resizing = false;
      let startX = 0;
      let startY = 0;
      let origW = 0;
      let origH = 0;

      resizeHandle.addEventListener('pointerdown', (e) => {
        if (isMobile()) return;
        e.preventDefault();
        e.stopPropagation();
        resizing = true;
        startX = e.clientX;
        startY = e.clientY;
        origW = win.rect.w;
        origH = win.rect.h;
        focusWindow(win.tab);
        win.el.classList.add('is-resizing');
        try {
          resizeHandle.setPointerCapture(e.pointerId);
        } catch {
          /* ignore */
        }
      });
      resizeHandle.addEventListener('pointermove', (e) => {
        if (!resizing) return;
        win.rect.w = origW + (e.clientX - startX);
        win.rect.h = origH + (e.clientY - startY);
        applyRect(win);
      });
      const endResize = () => {
        if (!resizing) return;
        resizing = false;
        win.el.classList.remove('is-resizing');
      };
      resizeHandle.addEventListener('pointerup', endResize);
      resizeHandle.addEventListener('pointercancel', endResize);
    }
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
      applyRect(win);
      focusWindow(tab);
      updateDockActive();
    } else {
      // Mobile: close other windows (one-at-a-time)
      if (isMobile()) {
        Array.from(windows.keys()).forEach((t) => {
          if (t !== tab) closeWindow(t);
        });
      }
      win = createWindowShell(launcher);
      focusWindow(tab);
      updateDockActive();
    }

    root.classList.add('desktop-has-windows');

    if (tab !== 'sessions' && typeof switchTab === 'function') {
      switchTab(tab);
    }

    if (tab === 'chat' && doFocus) {
      focusComposer();
    }

    scheduleSyncHostedViews();
    return win;
  }

  function minimizeWindow(tab) {
    const win = windows.get(tab);
    if (!win) return;
    win.minimized = true;
    win.el.classList.add('is-minimized');
    win.el.setAttribute('aria-hidden', 'true');
    updateDockActive();
    scheduleSyncHostedViews();
    toast(`${win.label} minimized`, 'info', 900);
  }

  function closeWindow(tab) {
    const win = windows.get(tab);
    if (!win) return;
    win.el.remove();
    windows.delete(tab);
    updateDockActive();
    if (!windows.size) {
      root.classList.remove('desktop-has-windows');
      root.removeAttribute('data-desktop-focus');
    }
    scheduleSyncHostedViews();

    // Park view
    const viewId = viewIdForTab(tab);
    const view = viewId ? $(viewId) : null;
    if (view) {
      view.classList.add('desktop-view-parked', 'hidden');
      view.classList.remove('desktop-view-hosted', 'flex');
      view.setAttribute('aria-hidden', 'true');
    }
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
    // Keep window title-bar select in sync
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
    // External switchTab (rail remnants, deep links) → open/focus that window
    if (tabName === 'sessions') {
      openWindow('sessions');
      return;
    }
    if (!VIEW_BY_TAB[tabName]) return;
    // If already hosting, just sync; else open
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
      <button type="button" class="desktop-dock-btn" data-dock-tab="${escapeAttr(d.tab)}" data-dock-id="${escapeAttr(d.id)}" title="${escapeAttr(d.label)}" aria-label="${escapeAttr(d.label)}" aria-pressed="false">
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
  }

  function tickClock() {
    if (!clockEl) return;
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function enhanceHitlDialogs() {
    // Style stock modals as desktop dialog windows (HITL / tools / deliverables)
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
      scheduleSyncHostedViews();
    });
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const focus = root.getAttribute('data-desktop-focus');
        if (focus && windows.has(focus)) {
          // Don't steal Escape from nested modal dialogs
          const openModal = $query('.desktop-dialog-host:not(.hidden)');
          if (openModal) return;
          e.preventDefault();
          minimizeWindow(focus);
        }
      }
    });
    // Hide stock toggle that would fight desktop
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
  enhanceHitlDialogs();
  bindGlobal();
  tickClock();
  window.setInterval(tickClock, 30000);
  safeCreateIcons();

  // Park all tab views until a window hosts them
  $queryAll('.tab-view').forEach((v) => {
    v.classList.add('desktop-view-parked');
  });

  // First paint: empty desktop + dock (no auto-open chat) — user launches from dock
  // Soft-open Chat after a beat so streaming IDs are ready when they need it? Spec says dock launches.
  // Stay on empty desktop.

  // Refresh agent switcher options when agents hydrate
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
    collectAgentsFromDom,
    destroy() {
      windows.forEach((w) => w.el.remove());
      windows.clear();
      root.classList.remove('radical-desktop-demo', 'desktop-has-windows', 'desktop-sessions-open');
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
      <div class="desktop-brand">
        <span class="desktop-brand-dot"></span>
        <span>AGENT DESKTOP</span>
        <span class="desktop-brand-hint">Dock launches studios as windows</span>
      </div>
    `;
    main.insertBefore(stage, main.firstChild);
  }

  if (!$('desktopWindowLayer')) {
    const layer = document.createElement('div');
    layer.id = 'desktopWindowLayer';
    layer.className = 'desktop-window-layer';
    layer.setAttribute('aria-live', 'polite');
    document.body.appendChild(layer);
  }

  if (!$('desktopDock')) {
    const dock = document.createElement('div');
    dock.id = 'desktopDock';
    dock.className = 'desktop-dock';
    dock.setAttribute('role', 'toolbar');
    dock.setAttribute('aria-label', 'Desktop dock launcher');
    dock.innerHTML = `
      <div class="desktop-dock-shell">
        <div id="desktopDockApps" class="desktop-dock-apps"></div>
        <div class="desktop-dock-tray">
          <span id="desktopClock" class="desktop-clock" aria-live="off">--:--</span>
        </div>
      </div>
    `;
    document.body.appendChild(dock);
  }
}

