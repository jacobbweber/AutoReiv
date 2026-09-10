import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  PRESET_THEMES,
  hslToHex,
  buildThemeFromCustom,
  applyTheme,
  saveThemeToStorage,
  loadThemeFromStorage,
} from '../../../src/web/static/modules/ui/theme-engine.js';

describe('CARD-208 Theme Engine Unit & Contract Tests', () => {
  const indexPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const indexHtml = fs.readFileSync(indexPath, 'utf-8');

  it('defines the 5 core prebuilt theme presets', () => {
    expect(PRESET_THEMES).toHaveProperty('autoreiv-indigo');
    expect(PRESET_THEMES).toHaveProperty('orbital-mono');
    expect(PRESET_THEMES).toHaveProperty('obsidian-slate');
    expect(PRESET_THEMES).toHaveProperty('amber-phosphor');
    expect(PRESET_THEMES).toHaveProperty('emerald-matrix');

    const indigo = PRESET_THEMES['autoreiv-indigo'];
    expect(indigo.id).toBe('autoreiv-indigo');
    expect(indigo.name).toContain('Indigo');
    expect(indigo.brand).toMatch(/^#[0-9a-fA-F]{6}$/);

    const mono = PRESET_THEMES['orbital-mono'];
    expect(mono.id).toBe('orbital-mono');
    expect(mono.bgBase).toBe('#000000');
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
  });
});
