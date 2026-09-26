/**
 * Agent Desktop - Preferences & Storage Persistence
 * Manages localStorage synchronization, schema migration, and session scrubbing.
 */

import { $ } from '../../dom.js';

export const PREFS_KEY = 'autoreiv.agentDesktop.v1';

/** Tabs that are no longer desktop windows: Sessions (CARD-305) and the retired Factory (CARD-496, ADR-0060). */
export const RETIRED_DESKTOP_TABS = Object.freeze(['sessions', 'factory']);

/**
 * CARD-305/CARD-279/CARD-496: drop retired windows (Sessions, Factory) from stale prefs and normalize schema.
 * @param {object} prefs
 * @returns {object}
 */
export function scrubSessionsFromDesktopPrefs(prefs) {
  if (!prefs || typeof prefs !== 'object') {
    return {
      windows: {},
      gridOverlay: false,
      autoRestore: true,
      openWindows: [],
      savedPresets: [],
    };
  }
  const windows = { ...(prefs.windows || {}) };
  RETIRED_DESKTOP_TABS.forEach((tab) => {
    if (windows[tab]) delete windows[tab];
  });
  const openWindows = Array.isArray(prefs.openWindows)
    ? prefs.openWindows.filter((t) => typeof t === 'string' && !RETIRED_DESKTOP_TABS.includes(t))
    : [];
  const savedPresets = Array.isArray(prefs.savedPresets)
    ? prefs.savedPresets.map((p) => ({
        ...p,
        windows: Array.isArray(p.windows)
          ? p.windows.filter((w) => w && typeof w === 'object' && !RETIRED_DESKTOP_TABS.includes(w.tab))
          : [],
      }))
    : [];
  return {
    ...prefs,
    windows,
    openWindows,
    savedPresets,
    autoRestore: prefs.autoRestore !== false,
    gridOverlay: !!prefs.gridOverlay,
  };
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
  const select = $('agentSelect');
  if (!select) return [];
  return Array.from(select.options || [])
    .filter((o) => o.value)
    .map((o) => ({ id: o.value, name: (o.textContent || o.value).trim() }));
}

/**
 * Load persisted window prefs (positions/sizes/presets). Schema v1 + v2.
 * @returns {{ windows: Record<string, {x:number,y:number,w:number,h:number, maximized?: boolean}>, gridOverlay?: boolean, autoRestore?: boolean, openWindows?: string[], savedPresets?: Array<object> }}
 */
export function loadDesktopPrefs() {
  const empty = {
    windows: {},
    gridOverlay: false,
    autoRestore: true,
    openWindows: [],
    savedPresets: [],
  };
  if (typeof localStorage === 'undefined') return empty;
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return empty;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return empty;
    const windows = parsed.windows && typeof parsed.windows === 'object' ? parsed.windows : {};
    return scrubSessionsFromDesktopPrefs({
      windows,
      gridOverlay: !!parsed.gridOverlay,
      autoRestore: parsed.autoRestore !== false,
      openWindows: Array.isArray(parsed.openWindows) ? parsed.openWindows : [],
      savedPresets: Array.isArray(parsed.savedPresets) ? parsed.savedPresets : [],
    });
  } catch {
    return empty;
  }
}

/**
 * @param {{ windows: Record<string, object>, gridOverlay?: boolean, autoRestore?: boolean, openWindows?: string[], savedPresets?: Array<object> }} prefs
 */
export function saveDesktopPrefs(prefs) {
  if (typeof localStorage === 'undefined') return;
  try {
    const clean = scrubSessionsFromDesktopPrefs(prefs);
    localStorage.setItem(
      PREFS_KEY,
      JSON.stringify({
        windows: clean.windows || {},
        gridOverlay: !!clean.gridOverlay,
        autoRestore: clean.autoRestore !== false,
        openWindows: Array.isArray(clean.openWindows) ? clean.openWindows : [],
        savedPresets: Array.isArray(clean.savedPresets) ? clean.savedPresets : [],
      })
    );
  } catch {
    /* quota / private mode */
  }
}
