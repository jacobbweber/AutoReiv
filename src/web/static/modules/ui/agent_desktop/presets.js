/**
 * Agent Desktop - Canvas Presets & Organize Menu
 * Window arrangement presets (cockpit 3-window, 50/50 split, columns), custom saved layouts, and organize popup menu.
 */

import { $, escapeHtml, isMobile, safeCreateIcons } from '../../dom.js';
import {
  clampWindowRect,
  computeLeftFullRightStackedRects,
  computeLeftStackedRightFullRects,
  computeThreeColumnsRects,
  computeTwoColumnsRects,
} from './layout.js';
import { saveDesktopPrefs } from './prefs.js';

function escapeAttr(s) {
  return escapeHtml(s).replace(/'/g, '&#39;');
}

const PRIORITY_TABS = [
  'chat',
  'wiki',
  'agents',
  'projects',
  'factory',
  'routines',
  'observability',
  'settings',
  'prompts',
  'education',
  'lumina',
];

/**
 * Apply canvas layout presets across active windows.
 * @param {string} type
 * @param {object} ctx
 */
export function arrangePreset(type, ctx) {
  const {
    isMobileFn = isMobile,
    applyMobileLayoutFn,
    viewportSizeFn,
    visibleWindowsFn,
    windows,
    openWindowFn,
    minimizeWindowFn,
    applyRectFn,
    focusWindowFn,
    schedulePersistFn,
    toastFn,
  } = ctx;

  if (isMobileFn()) {
    if (typeof applyMobileLayoutFn === 'function') applyMobileLayoutFn();
    if (typeof toastFn === 'function') toastFn('Mobile snap applied', 'info', 900);
    return;
  }
  const vp = viewportSizeFn();

  let targetCount = 3;
  if (type === 'two-columns') targetCount = 2;
  else if (type === 'three-columns' || type === 'left-stacked-right-full' || type === 'left-full-right-stacked')
    targetCount = 3;

  // Current visible windows sorted by z-index descending (focused first)
  let vis = visibleWindowsFn().sort((a, b) => b.z - a.z);

  // If fewer than needed, open priority windows that aren't currently visible
  if (vis.length < targetCount) {
    for (const tab of PRIORITY_TABS) {
      if (!windows.has(tab) || windows.get(tab).minimized) {
        openWindowFn(tab);
        vis = visibleWindowsFn().sort((a, b) => b.z - a.z);
        if (vis.length >= targetCount) break;
      }
    }
  }

  // Windows to position: the top targetCount windows
  const targetWins = vis.slice(0, targetCount);

  // Minimize any excess windows beyond targetCount
  if (vis.length > targetCount) {
    vis.slice(targetCount).forEach((w) => minimizeWindowFn(w.tab));
  }

  let rects = [];
  let label = '';
  if (type === 'left-stacked-right-full') {
    rects = computeLeftStackedRightFullRects(vp);
    label = '3-Window (Left Stacked, Right Full)';
  } else if (type === 'left-full-right-stacked') {
    rects = computeLeftFullRightStackedRects(vp);
    label = '3-Window (Left Full, Right Stacked)';
  } else if (type === 'two-columns') {
    rects = computeTwoColumnsRects(vp);
    label = 'Split 50 / 50';
  } else if (type === 'three-columns') {
    rects = computeThreeColumnsRects(vp);
    label = '3 Columns Equal';
  }

  targetWins.forEach((win, i) => {
    win.maximized = false;
    win.restoreRect = null;
    if (rects[i]) {
      win.rect = rects[i];
    }
    applyRectFn(win);
  });

  if (targetWins[0]) focusWindowFn(targetWins[0].tab);
  if (typeof schedulePersistFn === 'function') schedulePersistFn();
  if (typeof toastFn === 'function') toastFn(`Applied ${label}`, 'info', 1000);
}

/**
 * Prompt operator to save current open window positions and sizes as a layout preset.
 * @param {object} ctx
 */
export function promptSaveCurrentLayout(ctx) {
  const { visibleWindowsFn, prefs, toastFn, renderOrganizeMenuContentFn } = ctx;
  const vis = visibleWindowsFn();
  if (!vis.length) {
    if (typeof toastFn === 'function') toastFn('Open at least one window to save a layout', 'warning', 1500);
    return;
  }
  const defaultName = vis.map((w) => w.label).join(' + ');
  const name = window.prompt('Save Layout Preset\nEnter a name for this layout preset:', defaultName);
  if (name === null) return;
  const cleanName = (name || defaultName).trim() || defaultName;

  const newPreset = {
    id: `preset-${Date.now()}`,
    name: cleanName,
    createdAt: Date.now(),
    windows: vis.map((w) => ({
      tab: w.tab,
      rect: { ...w.rect },
      maximized: !!w.maximized,
      z: w.z,
    })),
  };

  prefs.savedPresets = prefs.savedPresets || [];
  prefs.savedPresets.push(newPreset);
  saveDesktopPrefs(prefs);
  if (typeof renderOrganizeMenuContentFn === 'function') renderOrganizeMenuContentFn();
  if (typeof toastFn === 'function') toastFn(`Saved layout "${cleanName}"`, 'success', 1500);
}

/**
 * Restore an operator-saved layout preset.
 * @param {string} presetId
 * @param {object} ctx
 */
export function applyPreset(presetId, ctx) {
  const {
    prefs,
    toastFn,
    isMobileFn = isMobile,
    applyMobileLayoutFn,
    viewportSizeFn,
    windows,
    minimizeWindowFn,
    openWindowFn,
    applyRectFn,
    focusWindowFn,
    schedulePersistFn,
  } = ctx;

  prefs.savedPresets = prefs.savedPresets || [];
  const preset = prefs.savedPresets.find((p) => p.id === presetId);
  if (!preset || !Array.isArray(preset.windows)) {
    if (typeof toastFn === 'function') toastFn('Preset not found', 'error', 1200);
    return;
  }

  if (isMobileFn()) {
    if (typeof applyMobileLayoutFn === 'function') applyMobileLayoutFn();
    if (typeof toastFn === 'function') toastFn('Mobile snap applied', 'info', 900);
    return;
  }

  const vp = viewportSizeFn();
  const presetTabs = new Set(preset.windows.map((w) => w.tab));

  // Minimize windows that are NOT in the preset
  windows.forEach((win, tab) => {
    if (!presetTabs.has(tab) && !win.minimized) {
      minimizeWindowFn(tab);
    }
  });

  // Open and size preset windows
  preset.windows.forEach((saved) => {
    const win = openWindowFn(saved.tab);
    if (win) {
      win.maximized = !!saved.maximized;
      win.restoreRect = saved.maximized ? { ...saved.rect } : null;
      win.rect = clampWindowRect(saved.rect, vp);
      applyRectFn(win);
    }
  });

  if (preset.windows[0]) {
    focusWindowFn(preset.windows[0].tab);
  }
  if (typeof schedulePersistFn === 'function') schedulePersistFn();
  if (typeof toastFn === 'function') toastFn(`Loaded "${preset.name}"`, 'info', 1200);
}

/**
 * Delete a saved layout preset.
 * @param {string} presetId
 * @param {object} ctx
 */
export function deletePreset(presetId, ctx) {
  const { prefs, toastFn, renderOrganizeMenuContentFn } = ctx;
  prefs.savedPresets = prefs.savedPresets || [];
  const idx = prefs.savedPresets.findIndex((p) => p.id === presetId);
  if (idx === -1) return;
  const removed = prefs.savedPresets.splice(idx, 1)[0];
  saveDesktopPrefs(prefs);
  if (typeof renderOrganizeMenuContentFn === 'function') renderOrganizeMenuContentFn();
  if (typeof toastFn === 'function') toastFn(`Deleted layout "${removed.name}"`, 'info', 1000);
}

/**
 * Render organize menu items, canvas presets, and saved layout cards into #desktopOrganizeMenu.
 * @param {object} params
 */
export function renderOrganizeMenuContent({ organizeMenu, prefs, gridOverlay }) {
  if (!organizeMenu) return;
  const presetsList = prefs.savedPresets || [];
  const autoRestoreActive = prefs.autoRestore !== false;

  const presetsHtml = presetsList.length
    ? presetsList
        .map(
          (p) => `
      <div class="desktop-preset-row">
        <button type="button" class="desktop-preset-load-btn" data-preset-id="${escapeAttr(p.id)}" title="Apply ${escapeAttr(p.name)}">
          <i data-lucide="monitor" class="w-3.5 h-3.5"></i>
          <span class="desktop-preset-name">${escapeHtml(p.name)}</span>
        </button>
        <button type="button" class="desktop-preset-del-btn" data-delete-preset="${escapeAttr(p.id)}" title="Delete preset" aria-label="Delete preset">
          <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
        </button>
      </div>`
        )
        .join('')
    : '<div class="desktop-preset-empty">No saved presets yet</div>';

  organizeMenu.innerHTML = `
    <div class="desktop-organize-section-title">Canvas Presets</div>
    <button type="button" role="menuitem" data-arrange="preset-3-stacked-right">
      <i data-lucide="columns-3" class="w-3.5 h-3.5"></i>
      <span>3-Window: Left Stacked, Right Full</span>
    </button>
    <button type="button" role="menuitem" data-arrange="preset-3-left-stacked">
      <i data-lucide="columns-3" class="w-3.5 h-3.5"></i>
      <span>3-Window: Left Full, Right Stacked</span>
    </button>
    <button type="button" role="menuitem" data-arrange="preset-2-cols">
      <i data-lucide="columns-2" class="w-3.5 h-3.5"></i>
      <span>Split 50 / 50</span>
    </button>
    <button type="button" role="menuitem" data-arrange="preset-3-cols">
      <i data-lucide="columns" class="w-3.5 h-3.5"></i>
      <span>3 Columns Equal</span>
    </button>
    <button type="button" role="menuitem" data-arrange="tile">
      <i data-lucide="grid" class="w-3.5 h-3.5"></i>
      <span>Tile All</span>
    </button>
    <button type="button" role="menuitem" data-arrange="cascade">
      <i data-lucide="copy" class="w-3.5 h-3.5"></i>
      <span>Cascade</span>
    </button>

    <div class="desktop-organize-divider"></div>
    <div class="desktop-organize-section-title">Window Actions</div>
    <button type="button" role="menuitem" data-arrange="snap-left">
      <i data-lucide="arrow-left-to-line" class="w-3.5 h-3.5"></i>
      <span>Snap Left Half</span>
    </button>
    <button type="button" role="menuitem" data-arrange="snap-right">
      <i data-lucide="arrow-right-to-line" class="w-3.5 h-3.5"></i>
      <span>Snap Right Half</span>
    </button>
    <button type="button" role="menuitem" data-arrange="maximize">
      <i data-lucide="maximize" class="w-3.5 h-3.5"></i>
      <span>Maximize / Restore</span>
    </button>
    <button type="button" role="menuitem" data-arrange="grid">
      <i data-lucide="hash" class="w-3.5 h-3.5"></i>
      <span>Toggle Grid Overlay (${gridOverlay ? 'On' : 'Off'})</span>
    </button>

    <div class="desktop-organize-divider"></div>
    <div class="desktop-organize-section-title">Saved Layouts</div>
    <button type="button" role="menuitem" data-arrange="save-layout" class="desktop-organize-save-btn">
      <i data-lucide="bookmark-plus" class="w-3.5 h-3.5"></i>
      <span>Save Current Layout...</span>
    </button>
    <button type="button" role="menuitem" data-arrange="toggle-auto-restore" class="desktop-organize-toggle-btn">
      <i data-lucide="${autoRestoreActive ? 'check-square' : 'square'}" class="w-3.5 h-3.5"></i>
      <span>Auto-Restore on Startup: <strong>${autoRestoreActive ? 'Active' : 'Disabled'}</strong></span>
    </button>
    <div class="desktop-preset-list">
      ${presetsHtml}
    </div>
  `;
  safeCreateIcons(organizeMenu);
}

/**
 * Bind click and selection handlers to #desktopOrganizeBtn and #desktopOrganizeMenu.
 * @param {object} ctx
 */
export function bindOrganizeMenu(ctx) {
  const {
    organizeMenu,
    root,
    prefs,
    renderOrganizeMenuContentFn,
    arrangePresetFn,
    arrangeTileFn,
    arrangeCascadeFn,
    arrangeSnapHalfFn,
    toggleMaximizeFn,
    toggleGridOverlayFn,
    promptSaveCurrentLayoutFn,
    applyPresetFn,
    deletePresetFn,
    toastFn,
  } = ctx;

  const toggleBtn = $('desktopOrganizeBtn');
  if (!toggleBtn || !organizeMenu) return;

  const closeMenu = () => {
    organizeMenu.classList.add('hidden');
    toggleBtn.setAttribute('aria-expanded', 'false');
  };

  renderOrganizeMenuContentFn();

  toggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const open = organizeMenu.classList.contains('hidden');
    if (open) {
      renderOrganizeMenuContentFn();
    }
    organizeMenu.classList.toggle('hidden', !open);
    toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  });

  organizeMenu.addEventListener('click', (e) => {
    // 1. Delete preset
    const delBtn = e.target && e.target.closest ? e.target.closest('[data-delete-preset]') : null;
    if (delBtn) {
      e.stopPropagation();
      const presetId = delBtn.getAttribute('data-delete-preset');
      deletePresetFn(presetId, ctx);
      return;
    }

    // 2. Load preset
    const loadBtn = e.target && e.target.closest ? e.target.closest('[data-preset-id]') : null;
    if (loadBtn) {
      e.stopPropagation();
      const presetId = loadBtn.getAttribute('data-preset-id');
      applyPresetFn(presetId, ctx);
      closeMenu();
      return;
    }

    // 3. Arrange actions
    const btn = e.target && e.target.closest ? e.target.closest('[data-arrange]') : null;
    if (!btn) return;
    const action = btn.getAttribute('data-arrange');
    if (action === 'preset-3-stacked-right') arrangePresetFn('left-stacked-right-full', ctx);
    else if (action === 'preset-3-left-stacked') arrangePresetFn('left-full-right-stacked', ctx);
    else if (action === 'preset-2-cols') arrangePresetFn('two-columns', ctx);
    else if (action === 'preset-3-cols') arrangePresetFn('three-columns', ctx);
    else if (action === 'tile') arrangeTileFn(ctx);
    else if (action === 'cascade') arrangeCascadeFn(ctx);
    else if (action === 'snap-left') arrangeSnapHalfFn('left', ctx);
    else if (action === 'snap-right') arrangeSnapHalfFn('right', ctx);
    else if (action === 'maximize') {
      const focus = root.getAttribute('data-desktop-focus');
      if (focus) toggleMaximizeFn(focus, ctx);
    } else if (action === 'grid') {
      toggleGridOverlayFn(ctx);
      renderOrganizeMenuContentFn();
      return;
    } else if (action === 'save-layout') {
      promptSaveCurrentLayoutFn(ctx);
    } else if (action === 'toggle-auto-restore') {
      prefs.autoRestore = prefs.autoRestore === false;
      saveDesktopPrefs(prefs);
      if (typeof toastFn === 'function') toastFn(`Auto-restore ${prefs.autoRestore ? 'enabled' : 'disabled'}`, 'info', 1000);
      renderOrganizeMenuContentFn();
      return;
    }
    closeMenu();
  });

  document.addEventListener('click', (e) => {
    if (!organizeMenu.classList.contains('hidden')) {
      if (e.target && (toggleBtn.contains(e.target) || organizeMenu.contains(e.target))) return;
      closeMenu();
    }
  });
}
