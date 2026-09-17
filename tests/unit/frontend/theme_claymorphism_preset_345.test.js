import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  PRESET_THEMES,
  applyTheme,
  saveThemeToStorage,
  loadThemeFromStorage,
} from '../../../src/web/static/modules/ui/theme-engine.js';

describe('CARD-345 Claymorphism Theme Prototype Unit & Contract Tests', () => {
  const indexPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const indexHtml = fs.readFileSync(indexPath, 'utf-8');

  it('defines the claymorphism theme preset in PRESET_THEMES', () => {
    expect(PRESET_THEMES).toHaveProperty('claymorphism');
    const clay = PRESET_THEMES['claymorphism'];
    expect(clay.id).toBe('claymorphism');
    expect(clay.name).toBe('Claymorphism');
    expect(clay.brand).toMatch(/^#[0-9a-fA-F]{6}$/);
    expect(clay.bgBase).toMatch(/^#[0-9a-fA-F]{6}$/);
    expect(clay.bgSurface).toMatch(/^#[0-9a-fA-F]{6}$/);
  });

  it('sets data-theme="claymorphism" on root when claymorphism theme is applied', () => {
    const fakeRoot = {
      dataset: {},
      style: {
        properties: {},
        setProperty(k, v) { this.properties[k] = v; },
        getPropertyValue(k) { return this.properties[k] || ''; },
      },
      setAttribute(k, v) { this[k] = v; if (k === 'data-theme') this.dataset.theme = v; },
      removeAttribute(k) { delete this[k]; if (k === 'data-theme') delete this.dataset.theme; },
    };

    const clay = PRESET_THEMES['claymorphism'];
    applyTheme(clay, fakeRoot);
    expect(fakeRoot.dataset.theme).toBe('claymorphism');

    // Switching to standard theme clears data-theme
    const indigo = PRESET_THEMES['autoreiv-indigo'];
    applyTheme(indigo, fakeRoot);
    expect(fakeRoot.dataset.theme).toBeUndefined();
  });

  it('persists and reloads claymorphism theme from storage', () => {
    const mockStorage = {
      data: {},
      setItem(k, v) { this.data[k] = String(v); },
      getItem(k) { return this.data[k] || null; },
      removeItem(k) { delete this.data[k]; },
    };

    const clay = PRESET_THEMES['claymorphism'];
    saveThemeToStorage(clay, mockStorage);

    const loaded = loadThemeFromStorage(mockStorage);
    expect(loaded).toBeTruthy();
    expect(loaded.id).toBe('claymorphism');
    expect(loaded.brand).toBe(clay.brand);
  });

  it('contains Claymorphism preset button in index.html #themePresetsList', () => {
    expect(indexHtml).toContain('data-theme-preset="claymorphism"');
    expect(indexHtml).toMatch(/data-theme-preset="claymorphism"[\s\S]*?Claymorphism/);
  });

  it('defines scoped claymorphism CSS rules with compound inset bevel shadows', () => {
    expect(indexHtml).toContain('[data-theme="claymorphism"]');
    // Dock icon clay styling with inset bevel
    expect(indexHtml).toMatch(/\[data-theme="claymorphism"\]\s+\.desktop-dock-icon[\s\S]*?box-shadow:[\s\S]*?inset/);
    // Dock button tactile active state
    expect(indexHtml).toMatch(/\[data-theme="claymorphism"\]\s+\.desktop-dock-btn:active/);
    // Desktop window clay styling
    expect(indexHtml).toMatch(/\[data-theme="claymorphism"\]\s+\.desktop-window[\s\S]*?border-radius:\s*(1[6-9]|2\d)px/);
    expect(indexHtml).toMatch(/\[data-theme="claymorphism"\]\s+\.desktop-window[\s\S]*?box-shadow:[\s\S]*?inset/);
  });
});
