/**
 * Theme Engine - Appearance Customizer & Preset Palettes [CARD-208]
 * Manages color variables on :root, preset swatches, slider calculations,
 * and browser persistence.
 */

import { $, $queryAll } from '../dom.js';

export const THEME_STORAGE_KEY = 'autoreiv.theme.v1';
export const DEFAULT_THEME_ID = 'autoreiv-indigo';

/**
 * @typedef {{
 *   id: string,
 *   name: string,
 *   subtitle: string,
 *   hue: number,
 *   saturation: number,
 *   darkness: number,
 *   brand: string,
 *   brandHover: string,
 *   brandGlow: string,
 *   bgBase: string,
 *   bgSurface: string,
 *   border: string
 * }} ThemeConfig
 */

/** @type {Record<string, ThemeConfig>} */
export const PRESET_THEMES = {
  'autoreiv-indigo': {
    id: 'autoreiv-indigo',
    name: 'AutoReiv Indigo',
    subtitle: 'High-tech violet & indigo glow',
    hue: 245,
    saturation: 85,
    darkness: 12,
    brand: '#6366f1',
    brandHover: '#4f46e5',
    brandGlow: 'rgba(99, 102, 241, 0.35)',
    bgBase: '#020617',
    bgSurface: '#0f172a',
    border: 'rgba(99, 102, 241, 0.35)',
  },
  'orbital-mono': {
    id: 'orbital-mono',
    name: 'Orbital Monochrome',
    subtitle: 'Spaceflight stark black & titanium white',
    hue: 0,
    saturation: 0,
    darkness: 0,
    brand: '#f8fafc',
    brandHover: '#e2e8f0',
    brandGlow: 'rgba(248, 250, 252, 0.25)',
    bgBase: '#000000',
    bgSurface: '#09090b',
    border: 'rgba(255, 255, 255, 0.28)',
  },
  'obsidian-slate': {
    id: 'obsidian-slate',
    name: 'Obsidian Slate',
    subtitle: 'Graphite vault with amethyst accents',
    hue: 268,
    saturation: 60,
    darkness: 8,
    brand: '#9333ea',
    brandHover: '#7e22ce',
    brandGlow: 'rgba(147, 51, 234, 0.35)',
    bgBase: '#090a0f',
    bgSurface: '#12141c',
    border: 'rgba(147, 51, 234, 0.3)',
  },
  'amber-phosphor': {
    id: 'amber-phosphor',
    name: 'Amber Phosphor',
    subtitle: 'Retro terminal warm amber & deep bronze',
    hue: 38,
    saturation: 95,
    darkness: 6,
    brand: '#f59e0b',
    brandHover: '#d97706',
    brandGlow: 'rgba(245, 158, 11, 0.35)',
    bgBase: '#070604',
    bgSurface: '#12100a',
    border: 'rgba(245, 158, 11, 0.35)',
  },
  'emerald-matrix': {
    id: 'emerald-matrix',
    name: 'Emerald Matrix',
    subtitle: 'Cyber green & pitch dark void',
    hue: 155,
    saturation: 85,
    darkness: 5,
    brand: '#10b981',
    brandHover: '#059669',
    brandGlow: 'rgba(16, 185, 129, 0.35)',
    bgBase: '#010905',
    bgSurface: '#08140e',
    border: 'rgba(16, 185, 129, 0.35)',
  },
};

/**
 * Convert HSL to 6-character hex string.
 * @param {number} h 0-360
 * @param {number} s 0-100
 * @param {number} l 0-100
 * @returns {string} Hex color with leading #
 */
export function hslToHex(h, s, l) {
  const normH = ((Number(h) % 360) + 360) % 360;
  const sat = Math.max(0, Math.min(100, Number(s))) / 100;
  const light = Math.max(0, Math.min(100, Number(l))) / 100;

  const c = (1 - Math.abs(2 * light - 1)) * sat;
  const x = c * (1 - Math.abs(((normH / 60) % 2) - 1));
  const m = light - c / 2;
  let r;
  let g;
  let b;

  if (normH >= 0 && normH < 60) {
    r = c; g = x; b = 0;
  } else if (normH >= 60 && normH < 120) {
    r = x; g = c; b = 0;
  } else if (normH >= 120 && normH < 180) {
    r = 0; g = c; b = x;
  } else if (normH >= 180 && normH < 240) {
    r = 0; g = x; b = c;
  } else if (normH >= 240 && normH < 300) {
    r = x; g = 0; b = c;
  } else {
    r = c; g = 0; b = x;
  }

  const toHex = (n) => {
    const hex = Math.round((n + m) * 255).toString(16);
    return hex.length === 1 ? `0${hex}` : hex;
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

/**
 * Convert hex to rgba string.
 * @param {string} hex
 * @param {number} alpha
 * @returns {string}
 */
function hexToRgba(hex, alpha = 1) {
  const clean = hex.replace('#', '');
  const r = parseInt(clean.substring(0, 2), 16) || 0;
  const g = parseInt(clean.substring(2, 4), 16) || 0;
  const b = parseInt(clean.substring(4, 6), 16) || 0;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Build dynamic theme object from custom sliders.
 * @param {number} hue 0-360
 * @param {number} saturation 0-100
 * @param {number} darkness 0-100 (0 = pitch black, 100 = slate gray)
 * @returns {ThemeConfig}
 */
export function buildThemeFromCustom(hue, saturation, darkness) {
  const h = Number(hue) || 0;
  const s = Number(saturation) || 0;
  const d = Math.max(0, Math.min(100, Number(darkness) || 0));

  // Accent is balanced at lightness 55%
  const brand = s === 0 ? hslToHex(0, 0, 95) : hslToHex(h, s, 55);
  const brandHover = s === 0 ? hslToHex(0, 0, 85) : hslToHex(h, s, 45);
  const brandGlow = hexToRgba(brand, 0.35);

  // Background base scales with darkness: 0% = pure #000000, 100% = #1e293b
  const baseLightness = Math.round((d / 100) * 10);
  const bgBase = s === 0 ? hslToHex(0, 0, baseLightness) : hslToHex(h, Math.round(s * 0.25), baseLightness);

  const surfaceLightness = Math.round(baseLightness + 5);
  const bgSurface = s === 0 ? hslToHex(0, 0, surfaceLightness) : hslToHex(h, Math.round(s * 0.2), surfaceLightness);

  const border = hexToRgba(brand, 0.32);

  return {
    id: 'custom',
    name: 'Custom Theme',
    subtitle: `${h}° Hue, ${s}% Saturation`,
    hue: h,
    saturation: s,
    darkness: d,
    brand,
    brandHover,
    brandGlow,
    bgBase,
    bgSurface,
    border,
  };
}

/**
 * Apply theme variables directly to :root or provided element.
 * @param {ThemeConfig} theme
 * @param {HTMLElement|any} [rootEl]
 */
export function applyTheme(theme, rootEl) {
  if (!theme) return;
  const target = rootEl || (typeof document !== 'undefined' ? document.documentElement : null);
  if (!target || !target.style) return;

  target.style.setProperty('--theme-brand', theme.brand);
  target.style.setProperty('--theme-brand-hover', theme.brandHover);
  target.style.setProperty('--theme-brand-glow', theme.brandGlow);
  target.style.setProperty('--theme-bg-base', theme.bgBase);
  target.style.setProperty('--theme-bg-surface', theme.bgSurface);
  target.style.setProperty('--theme-border', theme.border);
}

/**
 * Save theme config to browser storage.
 * @param {ThemeConfig} theme
 * @param {Storage|any} [storage]
 */
export function saveThemeToStorage(theme, storage) {
  try {
    const store = storage || (typeof localStorage !== 'undefined' ? localStorage : null);
    if (!store) return;
    store.setItem(THEME_STORAGE_KEY, JSON.stringify(theme));
  } catch {
    /* ignore storage quota/security errors */
  }
}

/**
 * Load saved theme config from storage.
 * @param {Storage|any} [storage]
 * @returns {ThemeConfig|null}
 */
export function loadThemeFromStorage(storage) {
  try {
    const store = storage || (typeof localStorage !== 'undefined' ? localStorage : null);
    if (!store) return null;
    const raw = store.getItem(THEME_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Initialize Settings Studio Theme Customizer UI & Boot Listener.
 */
export function initThemeEngine() {
  const initialTheme = loadThemeFromStorage() || PRESET_THEMES[DEFAULT_THEME_ID];
  applyTheme(initialTheme);

  const hueSlider = /** @type {HTMLInputElement|null} */ ($('themeHueSlider'));
  const satSlider = /** @type {HTMLInputElement|null} */ ($('themeSaturationSlider'));
  const darkSlider = /** @type {HTMLInputElement|null} */ ($('themeDarknessSlider'));
  const hueVal = $('themeHueVal');
  const satVal = $('themeSatVal');
  const darkVal = $('themeDarkVal');
  const saveBtn = $('saveThemeBtn');
  const resetBtn = $('resetThemeBtn');
  const saveStatus = $('themeSaveStatus');
  const presetsList = $('themePresetsList');

  // Update slider inputs to match current theme
  const syncSliders = (t) => {
    if (hueSlider) hueSlider.value = String(t.hue ?? 245);
    if (satSlider) satSlider.value = String(t.saturation ?? 85);
    if (darkSlider) darkSlider.value = String(t.darkness ?? 12);
    if (hueVal) hueVal.textContent = `${t.hue ?? 245}°`;
    if (satVal) satVal.textContent = `${t.saturation ?? 85}%`;
    if (darkVal) darkVal.textContent = `${t.darkness ?? 12}%`;
  };

  syncSliders(initialTheme);

  let activeTheme = initialTheme;

  const updateFromSliders = () => {
    const h = hueSlider ? Number(hueSlider.value) : 245;
    const s = satSlider ? Number(satSlider.value) : 85;
    const d = darkSlider ? Number(darkSlider.value) : 12;

    if (hueVal) hueVal.textContent = `${h}°`;
    if (satVal) satVal.textContent = `${s}%`;
    if (darkVal) darkVal.textContent = `${d}%`;

    activeTheme = buildThemeFromCustom(h, s, d);
    applyTheme(activeTheme);
    highlightActivePreset(null);
  };

  const highlightActivePreset = (presetId) => {
    if (!presetsList) return;
    $queryAll('[data-theme-preset]', presetsList).forEach((btn) => {
      const isMatch = btn.getAttribute('data-theme-preset') === presetId;
      btn.classList.toggle('border-brand-500', isMatch);
      btn.classList.toggle('ring-2', isMatch);
      btn.classList.toggle('ring-brand-500/40', isMatch);
    });
  };

  highlightActivePreset(initialTheme.id !== 'custom' ? initialTheme.id : null);

  // Bind slider events
  [hueSlider, satSlider, darkSlider].forEach((slider) => {
    if (!slider) return;
    slider.addEventListener('input', updateFromSliders);
  });

  // Bind preset clicks
  if (presetsList) {
    presetsList.addEventListener('click', (e) => {
      const btn = e.target && e.target.closest ? e.target.closest('[data-theme-preset]') : null;
      if (!btn) return;
      const id = btn.getAttribute('data-theme-preset');
      if (id && PRESET_THEMES[id]) {
        activeTheme = PRESET_THEMES[id];
        applyTheme(activeTheme);
        syncSliders(activeTheme);
        highlightActivePreset(id);
        saveThemeToStorage(activeTheme);
        if (saveStatus) {
          saveStatus.textContent = `Applied ${activeTheme.name}`;
          saveStatus.classList.remove('hidden');
          setTimeout(() => saveStatus.classList.add('hidden'), 2000);
        }
      }
    });
  }

  // Save custom theme
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      saveThemeToStorage(activeTheme);
      if (saveStatus) {
        saveStatus.textContent = 'Custom theme saved!';
        saveStatus.classList.remove('hidden');
        setTimeout(() => saveStatus.classList.add('hidden'), 2500);
      }
    });
  }

  // Reset to default
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      activeTheme = PRESET_THEMES[DEFAULT_THEME_ID];
      applyTheme(activeTheme);
      syncSliders(activeTheme);
      highlightActivePreset(DEFAULT_THEME_ID);
      saveThemeToStorage(activeTheme);
      if (saveStatus) {
        saveStatus.textContent = 'Reset to AutoReiv Indigo';
        saveStatus.classList.remove('hidden');
        setTimeout(() => saveStatus.classList.add('hidden'), 2000);
      }
    });
  }
}
