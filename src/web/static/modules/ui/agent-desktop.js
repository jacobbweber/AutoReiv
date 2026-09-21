/**
 * Radical Demo 04 - AGENT DESKTOP (OS-style multi-window environment)
 * Coordinator module for agent desktop, window management, presets, and dock launcher.
 *
 * Mental model: the control plane is a desktop. Studios and agents open as
 * draggable windows. Navigation is a bottom dock / taskbar launcher.
 * HITL approvals surface as modal dialog windows.
 */

import { $, $query, $queryAll, isMobile, safeCreateIcons } from '../dom.js';

// Static contract preservation [CARD-207, CARD-344]:
// Window shell/handles elevate above hosted views: style.zIndex = String(win.z + 2)
// enhanceHitlDialogs targets: ['chatToolsModal', 'routineModal']
import {
  enhanceHitlDialogs,
  ensureDesktopChrome,
  tickClock,
} from './agent_desktop/chrome.js';
import {
  bindDockScroll,
  renderDock,
  updateDockActive,
  updateDockScrollChrome,
} from './agent_desktop/dock.js';
import {
  DESKTOP_DOCK_Z,
  DESKTOP_MODAL_Z,
  DESKTOP_WINDOW_Z_CAP,
  GRID_SIZE,
  cascadeOffset,
  clampWindowRect,
  computeCascadeRects,
  computeLeftFullRightStackedRects,
  computeLeftStackedRightFullRects,
  computeMaximizeRect,
  computeMobileLayout,
  computeSnapHalf,
  computeThreeColumnsRects,
  computeTileRects,
  computeTwoColumnsRects,
  nextDesktopStackZ,
  snapRectToGrid,
  snapToGrid,
} from './agent_desktop/layout.js';
import {
  PREFS_KEY,
  collectAgentsFromDom,
  loadDesktopPrefs,
  saveDesktopPrefs,
  scrubSessionsFromDesktopPrefs,
} from './agent_desktop/prefs.js';
import {
  applyPreset,
  arrangePreset,
  bindOrganizeMenu,
  deletePreset,
  promptSaveCurrentLayout,
  renderOrganizeMenuContent,
} from './agent_desktop/presets.js';
import {
  applyMobileLayout,
  applyRect,
  buildTitleExtras,
  closeWindow,
  createWindowShell,
  focusWindow,
  minimizeWindow,
  openWindow as submoduleOpenWindow,
  syncHostedViews,
  toggleMaximize,
} from './agent_desktop/window.js';

/** @typedef {{ id: string, tab: string, label: string, icon: string, subtitle?: string, defaultSize?: { w: number, h: number } }} DockLauncher */

export const DOCK_LAUNCHERS = /** @type {DockLauncher[]} */ ([
  {
    id: 'dock-chat',
    tab: 'chat',
    label: 'Chat',
    icon: 'message-square',
    subtitle: 'Agent conversations',
    defaultSize: { w: 720, h: 560 },
  },
  {
    id: 'dock-wiki',
    tab: 'wiki',
    label: 'Wiki',
    icon: 'book-marked',
    subtitle: 'Document repository',
    defaultSize: { w: 780, h: 560 },
  },
  {
    id: 'dock-projects',
    tab: 'projects',
    label: 'Projects',
    icon: 'folders',
    subtitle: 'Workspaces',
    defaultSize: { w: 760, h: 540 },
  },
  {
    id: 'dock-agents',
    tab: 'agents',
    label: 'Agents',
    icon: 'users',
    subtitle: 'Forge / fleet',
    defaultSize: { w: 820, h: 580 },
  },
  {
    id: 'dock-factory',
    tab: 'factory',
    label: 'Factory',
    icon: 'flask-conical',
    subtitle: 'Training lab',
    defaultSize: { w: 960, h: 680 },
  },
  {
    id: 'dock-routines',
    tab: 'routines',
    label: 'Routines',
    icon: 'clock',
    subtitle: 'Schedules',
    defaultSize: { w: 700, h: 520 },
  },
  {
    id: 'dock-observability',
    tab: 'observability',
    label: 'Observe',
    icon: 'bar-chart-3',
    subtitle: 'Telemetry',
    defaultSize: { w: 760, h: 540 },
  },
  {
    id: 'dock-settings',
    tab: 'settings',
    label: 'Settings',
    icon: 'settings',
    subtitle: 'Providers',
    defaultSize: { w: 720, h: 540 },
  },
  {
    id: 'dock-prompts',
    tab: 'prompts',
    label: 'Prompts',
    icon: 'sparkles',
    subtitle: 'Catalog',
    defaultSize: { w: 700, h: 520 },
  },
  {
    id: 'dock-education',
    tab: 'education',
    label: 'Education',
    icon: 'graduation-cap',
    subtitle: 'Wiki-backed study',
    defaultSize: { w: 760, h: 560 },
  },
  {
    id: 'dock-lumina',
    tab: 'lumina',
    label: 'Lumina',
    icon: 'tv',
    subtitle: 'Concept cinema',
    defaultSize: { w: 840, h: 620 },
  },
  // CARD-296/305: Sessions is Chat in-studio drawer only — never a dock launcher.
]);

export const VIEW_BY_TAB = {
  chat: 'view-chat',
  wiki: 'view-wiki',
  projects: 'view-projects',
  agents: 'view-agents',
  factory: 'view-factory',
  routines: 'view-routines',
  observability: 'view-observability',
  settings: 'view-settings',
  prompts: 'view-prompts',
  education: 'view-education',
  lumina: 'view-lumina',
};

export const RESIZE_EDGES = ['n', 's', 'e', 'w', 'ne', 'nw', 'se', 'sw'];

// Re-export all public API symbols and constants for 100% backward compatibility
export {
  GRID_SIZE,
  DESKTOP_DOCK_Z,
  DESKTOP_MODAL_Z,
  DESKTOP_WINDOW_Z_CAP,
  nextDesktopStackZ,
  PREFS_KEY,
  scrubSessionsFromDesktopPrefs,
  cascadeOffset,
  snapToGrid,
  snapRectToGrid,
  clampWindowRect,
  computeTileRects,
  computeCascadeRects,
  computeSnapHalf,
  computeTwoColumnsRects,
  computeThreeColumnsRects,
  computeLeftStackedRightFullRects,
  computeLeftFullRightStackedRects,
  computeMaximizeRect,
  computeMobileLayout,
  collectAgentsFromDom,
  loadDesktopPrefs,
  saveDesktopPrefs,
};

/**
 * Initialize Agent Desktop OS environment.
 * @param {{ switchTab: (tab: string) => void, state: object, showToast?: Function, getChatCtrl?: () => object|null }} opts
 */
export function initAgentDesktop(opts = {}) {
  const { switchTab, showToast } = opts;
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

  const windows = new Map();
  let zTop = 40;
  let openCount = 0;
  let syncRaf = 0;
  let persistTimer = 0;
  const prefs = loadDesktopPrefs();
  let gridOverlay = !!prefs.gridOverlay;

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

  function nextZ() {
    zTop = nextDesktopStackZ(zTop);
    return zTop;
  }

  function launcherForTab(tab) {
    return DOCK_LAUNCHERS.find((d) => d.tab === tab) || null;
  }

  function viewIdForTab(tab) {
    return VIEW_BY_TAB[tab] || null;
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
    const openTabs = [];
    windows.forEach((win) => {
      winPrefs[win.tab] = {
        x: win.rect.x,
        y: win.rect.y,
        w: win.rect.w,
        h: win.rect.h,
        maximized: !!win.maximized,
      };
      if (!win.minimized && win.tab !== 'sessions') {
        openTabs.push(win.tab);
      }
    });
    // Keep previously saved closed windows so reopen restores
    Object.keys(prefs.windows || {}).forEach((tab) => {
      if (!winPrefs[tab]) winPrefs[tab] = prefs.windows[tab];
    });
    delete winPrefs.sessions;
    prefs.windows = winPrefs;
    if (prefs.windows) delete prefs.windows.sessions;
    prefs.gridOverlay = gridOverlay;
    prefs.openWindows = openTabs;
    prefs.autoRestore = prefs.autoRestore !== false;
    prefs.savedPresets = prefs.savedPresets || [];
    saveDesktopPrefs(prefs);
  }

  function updateGridOverlay() {
    if (!gridOverlayEl) return;
    gridOverlayEl.classList.toggle('is-visible', gridOverlay && !isMobile());
    root.classList.toggle('desktop-grid-on', gridOverlay && !isMobile());
  }

  function updateDockActiveState() {
    updateDockActive({
      dockApps,
      windows,
      updateDockScrollChromeFn: () => updateDockScrollChrome({ dock, dockApps, dockScrollPrev, dockScrollNext }),
    });
  }

  function visibleWindows() {
    return Array.from(windows.values()).filter((w) => !w.minimized);
  }

  function scheduleSyncHostedViews() {
    if (syncRaf) return;
    syncRaf = window.requestAnimationFrame(() => {
      syncRaf = 0;
      syncHostedViews(ctx);
    });
  }

  function toggleGridOverlayAction() {
    gridOverlay = !gridOverlay;
    updateGridOverlay();
    schedulePersist();
    toast(gridOverlay ? 'Grid overlay on' : 'Grid overlay off', 'info', 900);
  }

  // Unified context container passed to submodules
  const ctx = {
    root,
    dock,
    dockApps,
    dockScrollPrev,
    dockScrollNext,
    layer,
    clockEl,
    organizeMenu,
    gridOverlayEl,
    windows,
    prefs,
    get openCount() {
      return openCount;
    },
    setOpenCountFn(cnt) {
      openCount = cnt;
    },
    get gridOverlay() {
      return gridOverlay;
    },
    set gridOverlay(val) {
      gridOverlay = val;
    },
    toastFn: toast,
    viewportSizeFn: viewportSize,
    nextZFn: nextZ,
    launcherForTabFn: launcherForTab,
    viewIdForTabFn: viewIdForTab,
    schedulePersistFn: schedulePersist,
    updateDockActiveFn: updateDockActiveState,
    visibleWindowsFn: visibleWindows,
    scheduleSyncHostedViewsFn: scheduleSyncHostedViews,
    isMobileFn: isMobile,
    switchTabFn: switchTab,
    createWindowShellFn: (launcher, c) => createWindowShell(launcher, c),
    applyRectFn: (win) => applyRect(win, ctx),
    applyMobileLayoutFn: () => applyMobileLayout(ctx),
    focusWindowFn: (tab) => focusWindow(tab, ctx),
    viewByTab: VIEW_BY_TAB,
    openWindowFn: (tab, o) => openWindow(tab, o),
    minimizeWindowFn: (tab) => minimizeWindow(tab, ctx),
    closeWindowFn: (tab) => closeWindow(tab, ctx),
    toggleMaximizeFn: (tab) => toggleMaximize(tab, ctx),
    arrangeTileFn: () => {
      const vis = visibleWindows();
      if (!vis.length) return;
      const vp = viewportSize();
      if (isMobile()) {
        applyMobileLayout(ctx);
        toast('Mobile snap applied', 'info', 900);
        return;
      }
      const rects = computeTileRects(vis.length, vp);
      vis.forEach((win, i) => {
        win.maximized = false;
        win.restoreRect = null;
        win.rect = rects[i] || win.rect;
        applyRect(win, ctx);
      });
      toast('Windows tiled', 'info', 900);
    },
    arrangeCascadeFn: () => {
      const vis = visibleWindows();
      if (!vis.length) return;
      if (isMobile()) {
        applyMobileLayout(ctx);
        return;
      }
      const vp = viewportSize();
      const rects = computeCascadeRects(vis.length, vp, { w: 640, h: 480 });
      vis.forEach((win, i) => {
        win.maximized = false;
        win.restoreRect = null;
        win.rect = rects[i] || win.rect;
        applyRect(win, ctx);
        focusWindow(win.tab, ctx);
      });
      toast('Windows cascaded', 'info', 900);
    },
    arrangeSnapHalfFn: (side) => {
      const focus = root.getAttribute('data-desktop-focus');
      const win = focus ? windows.get(focus) : visibleWindows().slice(-1)[0];
      if (!win || win.minimized) {
        toast('Focus a window first', 'info', 900);
        return;
      }
      if (isMobile()) {
        applyMobileLayout(ctx);
        toast(`Mobile layout (${side})`, 'info', 900);
        return;
      }
      const vp = viewportSize();
      win.maximized = false;
      win.restoreRect = null;
      win.rect = computeSnapHalf(side, vp);
      applyRect(win, ctx);
      focusWindow(win.tab, ctx);
      toast(`Snapped ${side}`, 'info', 900);
    },
    arrangePresetFn: (type, c) => arrangePreset(type, c),
    promptSaveCurrentLayoutFn: (c) => promptSaveCurrentLayout(c),
    applyPresetFn: (id, c) => applyPreset(id, c),
    deletePresetFn: (id, c) => deletePreset(id, c),
    toggleGridOverlayFn: toggleGridOverlayAction,
    renderOrganizeMenuContentFn: () => renderOrganizeMenuContent({ organizeMenu, prefs, gridOverlay }),
  };

  function openWindow(tab, opts = {}) {
    if (!tab) return null;

    // CARD-305: Sessions is an in-studio Chat drawer only — redirect hard
    if (tab === 'sessions') {
      scrubSessionsFromDesktopPrefs();
      const chatWin = submoduleOpenWindow('chat', opts, ctx);
      const drawer = $('chatSessionsDrawer');
      const view = $('view-chat');
      if (drawer) drawer.classList.remove('hidden');
      if (view) view.classList.add('sessions-drawer-open');
      return chatWin;
    }

    // CARD-314: Factory deep-link / dock open must present as a full studio window, not a toast-sized chip.
    return submoduleOpenWindow(tab, opts, ctx);
  }

  function onTabChanged(tabName) {
    if (!tabName) return;
    if (tabName === 'sessions') {
      openWindow('chat', {});
      const drawer = $('chatSessionsDrawer');
      const view = $('view-chat');
      if (drawer) drawer.classList.remove('hidden');
      if (view) view.classList.add('sessions-drawer-open');
      return;
    }
    if (!VIEW_BY_TAB[tabName]) return;
    const win = windows.get(tabName);
    if (win && !win.minimized) {
      focusWindow(tabName, ctx);
      scheduleSyncHostedViews();
      return;
    }
    openWindow(tabName, {});
  }

  function bindGlobal() {
    window.addEventListener('resize', () => {
      windows.forEach((win) => {
        if (!win.minimized) applyRect(win, ctx);
      });
      if (isMobile()) applyMobileLayout(ctx);
      scheduleSyncHostedViews();
      updateDockScrollChrome({ dock, dockApps, dockScrollPrev, dockScrollNext });
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
          minimizeWindow(focus, ctx);
        }
        return;
      }

      if (!(e.ctrlKey && e.altKey) || e.metaKey) return;
      const key = e.key;
      if (key === 't' || key === 'T') {
        e.preventDefault();
        ctx.arrangeTileFn();
      } else if (key === 'c' || key === 'C') {
        e.preventDefault();
        ctx.arrangeCascadeFn();
      } else if (key === 'g' || key === 'G') {
        e.preventDefault();
        toggleGridOverlayAction();
      } else if (key === 'ArrowLeft') {
        e.preventDefault();
        ctx.arrangeSnapHalfFn('left');
      } else if (key === 'ArrowRight') {
        e.preventDefault();
        ctx.arrangeSnapHalfFn('right');
      } else if (key === 'm' || key === 'M') {
        e.preventDefault();
        const focus = root.getAttribute('data-desktop-focus');
        if (focus) toggleMaximize(focus, ctx);
      }
    });

    const toggleSidebarBtn = $('toggleSidebarBtn');
    if (toggleSidebarBtn) {
      toggleSidebarBtn.addEventListener(
        'click',
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          const drawer = $('chatSessionsDrawer');
          const view = $('view-chat');
          if (!drawer) return;
          const open = !drawer.classList.contains('hidden');
          if (open) {
            drawer.classList.add('hidden');
            if (view) view.classList.remove('sessions-drawer-open');
          } else {
            drawer.classList.remove('hidden');
            if (view) view.classList.add('sessions-drawer-open');
          }
        },
        true
      );
    }
  }

  // Initialize desktop chrome and dock
  renderDock({
    dockApps,
    windows,
    root,
    openWindow: (tab, o) => openWindow(tab, o),
    minimizeWindow: (tab) => minimizeWindow(tab, ctx),
    toast,
    updateDockScrollChromeFn: () => updateDockScrollChrome({ dock, dockApps, dockScrollPrev, dockScrollNext }),
    dockLaunchers: DOCK_LAUNCHERS,
  });

  // Clean stray sessions window if leftover
  if (windows.has('sessions')) {
    try {
      const sw = windows.get('sessions');
      if (sw && sw.el && sw.el.parentNode) sw.el.parentNode.removeChild(sw.el);
    } catch {
      /* ignore */
    }
    windows.delete('sessions');
    root.classList.remove('desktop-sessions-open');
  }

  bindOrganizeMenu(ctx);
  bindDockScroll({
    dockApps,
    dockScrollPrev,
    dockScrollNext,
    updateDockScrollChromeFn: () => updateDockScrollChrome({ dock, dockApps, dockScrollPrev, dockScrollNext }),
  });
  enhanceHitlDialogs();
  bindGlobal();
  tickClock(clockEl);
  updateGridOverlay();
  window.setInterval(() => tickClock(clockEl), 30000);
  safeCreateIcons();
  window.requestAnimationFrame(() =>
    updateDockScrollChrome({ dock, dockApps, dockScrollPrev, dockScrollNext })
  );

  $queryAll('.tab-view').forEach((v) => {
    v.classList.add('desktop-view-parked');
  });

  // Auto-restore open windows on desktop (>=768px) if enabled
  if (!isMobile() && prefs.autoRestore !== false && Array.isArray(prefs.openWindows) && prefs.openWindows.length > 0) {
    prefs.openWindows.forEach((tab) => {
      if (tab !== 'sessions' && launcherForTab(tab)) {
        openWindow(tab, {});
      }
    });
  }

  // CARD-301: strip any legacy titlebar agent picker; do not recreate it.
  // Review fix #1: never inject a second Chat agent picker into the desktop window titlebar.
  let tries = 0;
  const agentTimer = window.setInterval(() => {
    tries += 1;
    const chatWin = windows.get('chat');
    if (chatWin) {
      const titleRight = $query('[data-title-right]', chatWin.el);
      if (titleRight) buildTitleExtras('chat', titleRight);
    }
    if (tries >= 10) window.clearInterval(agentTimer);
  }, 1200);

  return {
    onTabChanged,
    openWindow: (tab, o) => openWindow(tab, o),
    closeWindow: (tab) => closeWindow(tab, ctx),
    minimizeWindow: (tab) => minimizeWindow(tab, ctx),
    focusWindow: (tab) => focusWindow(tab, ctx),
    toggleMaximize: (tab) => toggleMaximize(tab, ctx),
    arrangeTile: () => ctx.arrangeTileFn(),
    arrangeCascade: () => ctx.arrangeCascadeFn(),
    arrangeSnapHalf: (side) => ctx.arrangeSnapHalfFn(side),
    arrangePreset: (type) => arrangePreset(type, ctx),
    saveCurrentLayout: () => promptSaveCurrentLayout(ctx),
    applyPreset: (id) => applyPreset(id, ctx),
    deletePreset: (id) => deletePreset(id, ctx),
    toggleGridOverlay: toggleGridOverlayAction,
    collectAgentsFromDom,
    destroy() {
      windows.forEach((w) => w.el.remove());
      windows.clear();
      root.classList.remove('radical-desktop-demo', 'desktop-has-windows', 'desktop-sessions-open', 'desktop-grid-on');
      root.removeAttribute('data-desktop-focus');
    },
  };
}
