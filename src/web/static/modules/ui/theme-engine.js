/**
 * Theme Engine - Appearance Customizer & Preset Palettes [CARD-208 / enterprise retune]
 * Manages color variables on :root, preset swatches, slider calculations,
 * and browser persistence.
 *
 * Token model (enterprise dark UI):
 * - Structure (window frames, card borders, dock chrome) = neutral slate/zinc
 * - Accent (brand) = scarce: primary buttons, active dock, selected preset,
 *   focus rings, links, status highlights — not chrome borders or glows
 * - Elevation via soft dark shadow + brighter neutral border, not brand halo
 */

import { $, $queryAll } from '../dom.js';

export const THEME_STORAGE_KEY = 'autoreiv.theme.v2';
export const THEME_STORAGE_KEY_LEGACY = 'autoreiv.theme.v1';
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

/** Neutral structural border alpha range (~white at low opacity). */
function neutralBorderFromDarkness(darkness) {
  const d = Math.max(0, Math.min(100, Number(darkness) || 0));
  // Slightly more visible on lighter bases (higher darkness), clamped 0.08–0.14
  const alpha = Math.round((0.08 + (d / 100) * 0.06) * 1000) / 1000;
  return `rgba(255, 255, 255, ${alpha})`;
}

/** @type {Record<string, ThemeConfig>} */
export const PRESET_THEMES = {
  'autoreiv-indigo': {
    id: 'autoreiv-indigo',
    name: 'Indigo',
    subtitle: 'Restrained blue-indigo accent, neutral chrome',
    hue: 239,
    saturation: 58,
    darkness: 10,
    brand: '#6366f1',
    brandHover: '#4f46e5',
    brandGlow: 'rgba(99, 102, 241, 0.10)',
    bgBase: '#09090b',
    bgSurface: '#12141a',
    border: 'rgba(255, 255, 255, 0.10)',
  },
  'orbital-mono': {
    id: 'orbital-mono',
    name: 'Slate Graphite',
    subtitle: 'Near-mono with soft blue-gray accent',
    hue: 215,
    saturation: 18,
    darkness: 8,
    brand: '#94a3b8',
    brandHover: '#64748b',
    brandGlow: 'rgba(148, 163, 184, 0.10)',
    bgBase: '#09090b',
    bgSurface: '#111317',
    border: 'rgba(255, 255, 255, 0.09)',
  },
  'obsidian-slate': {
    id: 'obsidian-slate',
    name: 'Violet',
    subtitle: 'Muted amethyst accent on cool neutrals',
    hue: 263,
    saturation: 42,
    darkness: 10,
    brand: '#8b7cc9',
    brandHover: '#7c6db5',
    brandGlow: 'rgba(139, 124, 201, 0.10)',
    bgBase: '#0a0a0f',
    bgSurface: '#14131c',
    border: 'rgba(255, 255, 255, 0.10)',
  },
  'amber-phosphor': {
    id: 'amber-phosphor',
    name: 'Warm Sand',
    subtitle: 'Warm gray surfaces with muted amber accent',
    hue: 36,
    saturation: 48,
    darkness: 12,
    brand: '#c4a35a',
    brandHover: '#a8893f',
    brandGlow: 'rgba(196, 163, 90, 0.10)',
    bgBase: '#0c0b09',
    bgSurface: '#161410',
    border: 'rgba(255, 255, 255, 0.10)',
  },
  'emerald-matrix': {
    id: 'emerald-matrix',
    name: 'Teal',
    subtitle: 'Calm teal accent, professional forest calm',
    hue: 173,
    saturation: 45,
    darkness: 10,
    brand: '#2dd4bf',
    brandHover: '#14b8a6',
    brandGlow: 'rgba(45, 212, 191, 0.10)',
    bgBase: '#090b0b',
    bgSurface: '#111616',
    border: 'rgba(255, 255, 255, 0.10)',
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
 * Structural border stays neutral; brand glow is soft and scarce.
 * @param {number} hue 0-360
 * @param {number} saturation 0-100
 * @param {number} darkness 0-100 (0 = pitch black, 100 = slate gray)
 * @returns {ThemeConfig}
 */
export function buildThemeFromCustom(hue, saturation, darkness) {
  const h = Number(hue) || 0;
  const s = Number(saturation) || 0;
  const d = Math.max(0, Math.min(100, Number(darkness) || 0));

  // Accent balanced at lightness 55%
  const brand = s === 0 ? hslToHex(0, 0, 78) : hslToHex(h, s, 55);
  const brandHover = s === 0 ? hslToHex(0, 0, 65) : hslToHex(h, Math.max(0, s - 8), 45);
  // Soft glow only — never used as structural chrome halo
  const brandGlow = hexToRgba(brand, 0.10);

  // Mostly neutral grayscale from darkness; optional tiny accent tint ≤5% sat
  const baseLightness = Math.round((d / 100) * 10);
  const tintSat = s === 0 ? 0 : Math.min(5, Math.round(s * 0.05));
  const bgBase = hslToHex(h, tintSat, baseLightness);

  const surfaceLightness = Math.min(18, Math.round(baseLightness + 5));
  const bgSurface = hslToHex(h, tintSat, surfaceLightness);

  const border = neutralBorderFromDarkness(d);

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

  const brandClean = (theme.brand || '').replace('#', '');
  const r = parseInt(brandClean.substring(0, 2), 16) || 0;
  const g = parseInt(brandClean.substring(2, 4), 16) || 0;
  const b = parseInt(brandClean.substring(4, 6), 16) || 0;
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  const brandContrast = luminance > 0.65 ? '#09090b' : '#ffffff';
  target.style.setProperty('--theme-brand-contrast', brandContrast);
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
 * Load saved theme config from storage (v2 only — legacy neon v1 is ignored).
 * @param {Storage|any} [storage]
 * @returns {ThemeConfig|null}
 */
export function loadThemeFromStorage(storage) {
  try {
    const store = storage || (typeof localStorage !== 'undefined' ? localStorage : null);
    if (!store) return null;
    const raw = store.getItem(THEME_STORAGE_KEY);
    if (!raw) {
      // Drop legacy neon themes so they do not stick after the enterprise retune
      try { store.removeItem(THEME_STORAGE_KEY_LEGACY); } catch { /* ignore */ }
      return null;
    }
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
    if (hueSlider) hueSlider.value = String(t.hue ?? 239);
    if (satSlider) satSlider.value = String(t.saturation ?? 58);
    if (darkSlider) darkSlider.value = String(t.darkness ?? 10);
    if (hueVal) hueVal.textContent = `${t.hue ?? 239}°`;
    if (satVal) satVal.textContent = `${t.saturation ?? 58}%`;
    if (darkVal) darkVal.textContent = `${t.darkness ?? 10}%`;
  };

  syncSliders(initialTheme);

  let activeTheme = initialTheme;

  const updateFromSliders = () => {
    const h = hueSlider ? Number(hueSlider.value) : 239;
    const s = satSlider ? Number(satSlider.value) : 58;
    const d = darkSlider ? Number(darkSlider.value) : 10;

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
        saveStatus.textContent = 'Reset to Indigo';
        saveStatus.classList.remove('hidden');
        setTimeout(() => saveStatus.classList.add('hidden'), 2000);
      }
    });
  }
}
