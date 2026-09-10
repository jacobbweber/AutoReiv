import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  PRESET_THEMES,
  THEME_STORAGE_KEY,
  hslToHex,
  buildThemeFromCustom,
  applyTheme,
  saveThemeToStorage,
  loadThemeFromStorage,
} from '../../../src/web/static/modules/ui/theme-engine.js';

describe('CARD-208 Theme Engine Unit & Contract Tests', () => {
  const indexPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const indexHtml = fs.readFileSync(indexPath, 'utf-8');

  it('defines the 5 core prebuilt theme presets with enterprise names', () => {
    expect(PRESET_THEMES).toHaveProperty('autoreiv-indigo');
    expect(PRESET_THEMES).toHaveProperty('orbital-mono');
    expect(PRESET_THEMES).toHaveProperty('obsidian-slate');
    expect(PRESET_THEMES).toHaveProperty('amber-phosphor');
    expect(PRESET_THEMES).toHaveProperty('emerald-matrix');

    const indigo = PRESET_THEMES['autoreiv-indigo'];
    expect(indigo.id).toBe('autoreiv-indigo');
    expect(indigo.name).toBe('Indigo');
    expect(indigo.brand).toMatch(/^#[0-9a-fA-F]{6}$/);
    expect(indigo.border).toMatch(/^rgba\(255,\s*255,\s*255,/);
    expect(indigo.brandGlow).toMatch(/,\s*0\.1\d?\)$/);

    const mono = PRESET_THEMES['orbital-mono'];
    expect(mono.id).toBe('orbital-mono');
    expect(mono.name).toBe('Slate Graphite');
    expect(mono.brand).toBe('#94a3b8');
    expect(mono.border).toMatch(/^rgba\(255,\s*255,\s*255,/);

    expect(PRESET_THEMES['obsidian-slate'].name).toBe('Violet');
    expect(PRESET_THEMES['amber-phosphor'].name).toBe('Warm Sand');
    expect(PRESET_THEMES['emerald-matrix'].name).toBe('Teal');
  });

  it('persists under autoreiv.theme.v2 storage key', () => {
    expect(THEME_STORAGE_KEY).toBe('autoreiv.theme.v2');
  });

  it('correctly converts HSL values to HEX strings via hslToHex', () => {
    expect(hslToHex(0, 0, 100).toLowerCase()).toBe('#ffffff');
    expect(hslToHex(0, 0, 0).toLowerCase()).toBe('#000000');
    expect(hslToHex(0, 100, 50).toLowerCase()).toBe('#ff0000');
    expect(hslToHex(120, 100, 50).toLowerCase()).toBe('#00ff00');
    expect(hslToHex(240, 100, 50).toLowerCase()).toBe('#0000ff');
  });

  it('builds a custom theme object from slider values', () => {
    const custom = buildThemeFromCustom(200, 80, 10);
    expect(custom.id).toBe('custom');
    expect(custom.hue).toBe(200);
    expect(custom.saturation).toBe(80);
    expect(custom.darkness).toBe(10);
    expect(custom.brand).toMatch(/^#[0-9a-fA-F]{6}$/);
    expect(custom.brandHover).toMatch(/^#[0-9a-fA-F]{6}$/);
    expect(custom.bgBase).toMatch(/^#[0-9a-fA-F]{6}$/);
    expect(custom.bgSurface).toMatch(/^#[0-9a-fA-F]{6}$/);
    expect(custom.border).toContain('rgba(');
  });

  it('custom border is neutral white alpha, not brand-tinted', () => {
    const custom = buildThemeFromCustom(200, 80, 10);
    const brandRgb = [
      parseInt(custom.brand.slice(1, 3), 16),
      parseInt(custom.brand.slice(3, 5), 16),
      parseInt(custom.brand.slice(5, 7), 16),
    ].join(', ');
    expect(custom.border).toMatch(/^rgba\(255,\s*255,\s*255,\s*0\.(0[8-9]\d?|1[0-4]\d?)\)$/);
    expect(custom.border).not.toContain(brandRgb);
    expect(custom.brandGlow).toMatch(/,\s*0\.1\d?\)$/);
  });

  it('applies CSS variables to target element', () => {
    const fakeRoot = {
      style: {
        properties: {},
        setProperty(k, v) {
          this.properties[k] = v;
        },
        getPropertyValue(k) {
          return this.properties[k] || '';
        },
      },
    };

    const theme = PRESET_THEMES['orbital-mono'];
    applyTheme(theme, fakeRoot);

    expect(fakeRoot.style.getPropertyValue('--theme-brand')).toBe(theme.brand);
    expect(fakeRoot.style.getPropertyValue('--theme-bg-base')).toBe(theme.bgBase);
    expect(fakeRoot.style.getPropertyValue('--theme-border')).toBe(theme.border);
  });

  it('saves and loads theme configs from storage', () => {
    const mockStorage = {
      data: {},
      setItem(k, v) { this.data[k] = String(v); },
      getItem(k) { return this.data[k] || null; },
      removeItem(k) { delete this.data[k]; },
    };

    expect(loadThemeFromStorage(mockStorage)).toBeNull();

    const sample = PRESET_THEMES['amber-phosphor'];
    saveThemeToStorage(sample, mockStorage);

    const loaded = loadThemeFromStorage(mockStorage);
    expect(loaded).toBeTruthy();
    expect(loaded.id).toBe('amber-phosphor');
    expect(loaded.brand).toBe(sample.brand);
    expect(Object.keys(mockStorage.data)).toContain('autoreiv.theme.v2');
  });

  it('ignores legacy v1 neon themes so they do not stick', () => {
    const mockStorage = {
      data: {
        'autoreiv.theme.v1': JSON.stringify({
          id: 'legacy-neon',
          brand: '#ff00ff',
          border: 'rgba(255, 0, 255, 0.5)',
        }),
      },
      setItem(k, v) { this.data[k] = String(v); },
      getItem(k) { return this.data[k] || null; },
      removeItem(k) { delete this.data[k]; },
    };

    expect(loadThemeFromStorage(mockStorage)).toBeNull();
    expect(mockStorage.data['autoreiv.theme.v1']).toBeUndefined();
  });

  it('contains #settingsThemeCard with presets, sliders, and preview in index.html', () => {
    expect(indexHtml).toContain('id="settingsThemeCard"');
    expect(indexHtml).toContain('id="themePresetsList"');
    expect(indexHtml).toContain('id="themeHueSlider"');
    expect(indexHtml).toContain('id="themeSaturationSlider"');
    expect(indexHtml).toContain('id="themeDarknessSlider"');
    expect(indexHtml).toContain('id="themePreviewBox"');
    expect(indexHtml).toContain('id="saveThemeBtn"');
    expect(indexHtml).toContain('id="resetThemeBtn"');
    expect(indexHtml).toContain('Window Border (neutral)');
    expect(indexHtml).not.toContain('Window Border & Glow');
  });

  describe('CARD-209 Deep Desktop & Studio Theme Skinning Invariants', () => {
    it('wallpaper references theme brand glow, base, and surface tokens', () => {
      expect(indexHtml).toContain('--theme-brand-glow');
      expect(indexHtml).toMatch(/\.desktop-wallpaper[\s\S]*?var\(--theme-brand-glow/);
      expect(indexHtml).toMatch(/\.desktop-wallpaper[\s\S]*?var\(--theme-bg-base/);
      expect(indexHtml).toMatch(/\.desktop-brand-dot[\s\S]*?var\(--theme-brand\)/);
    });

    it('window shells use neutral borders and elevation shadows without brand halo', () => {
      expect(indexHtml).toMatch(/\.desktop-window\s*\{[\s\S]*?var\(--theme-border/);
      expect(indexHtml).toMatch(/\.desktop-window\.is-focused\s*\{[\s\S]*?rgba\(255,\s*255,\s*255,\s*0\.18\)/);
      const winBlock = indexHtml.match(/\.desktop-window\s*\{[\s\S]*?\n\s*\}/);
      expect(winBlock).toBeTruthy();
      expect(winBlock[0]).not.toMatch(/--theme-brand-glow/);
      expect(indexHtml).toMatch(/\.desktop-win-titlebar[\s\S]*?var\(--theme-bg-surface/);
      expect(indexHtml).toMatch(/\.desktop-win-icon[\s\S]*?#94a3b8/);
    });

    it('studio cards and panels in hosted desktop windows inherit theme surface and borders', () => {
      expect(indexHtml).toMatch(/body\.radical-desktop-demo\s+\.tab-view\.desktop-view-hosted[\s\S]*?\.bg-slate-900[\s\S]*?var\(--theme-bg-surface\)/);
      expect(indexHtml).toMatch(/body\.radical-desktop-demo\s+\.tab-view\.desktop-view-hosted[\s\S]*?var\(--theme-border\)/);
    });

    it('studio primary action buttons and KPI text accents inherit theme brand colors', () => {
      expect(indexHtml).toMatch(/body\.radical-desktop-demo\s+\.tab-view\.desktop-view-hosted[\s\S]*?button\.bg-indigo-600[\s\S]*?var\(--theme-brand\)/);
      expect(indexHtml).toMatch(/body\.radical-desktop-demo\s+\.tab-view\.desktop-view-hosted[\s\S]*?\.text-indigo-400[\s\S]*?var\(--theme-brand\)/);
    });

    it('preset themes provide neutral chrome borders and restrained accents', () => {
      const amber = PRESET_THEMES['amber-phosphor'];
      expect(amber.bgBase).toBe('#0c0b09');
      expect(amber.bgSurface).toBe('#161410');
      expect(amber.brand).toBe('#c4a35a');
      expect(amber.border).toMatch(/^rgba\(255,\s*255,\s*255,/);

      const matrix = PRESET_THEMES['emerald-matrix'];
      expect(matrix.bgBase).toBe('#090b0b');
      expect(matrix.bgSurface).toBe('#111616');
      expect(matrix.brand).toBe('#2dd4bf');
      expect(matrix.border).toMatch(/^rgba\(255,\s*255,\s*255,/);

      const mono = PRESET_THEMES['orbital-mono'];
      expect(mono.bgBase).toBe('#09090b');
      expect(mono.bgSurface).toBe('#111317');

      const obsidian = PRESET_THEMES['obsidian-slate'];
      expect(obsidian.bgBase).toBe('#0a0a0f');
      expect(obsidian.bgSurface).toBe('#14131c');
      expect(obsidian.brand).toBe('#8b7cc9');
    });
  });
});
