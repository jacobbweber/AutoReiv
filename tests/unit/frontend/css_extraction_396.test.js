import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * CARD-396: Modular CSS Extraction and Index Template Hygiene
 * Verifies that the massive inline CSS block is extracted into modular stylesheets
 * and properly linked via standard HTML <link> elements.
 */
describe('CARD-396: Modular CSS Extraction and Index Template Hygiene', () => {
  const rootDir = path.resolve(__dirname, '../../../');
  const indexHtmlPath = path.join(rootDir, 'src/web/templates/index.html');
  const cssDir = path.join(rootDir, 'src/web/static/css');
  const indexHtml = fs.readFileSync(indexHtmlPath, 'utf-8');

  it('declares stylesheet links for base, components, desktop, and studios in index.html', () => {
    const requiredSheets = ['base.css', 'components.css', 'desktop.css', 'studios.css'];
    for (const sheet of requiredSheets) {
      const linkRegex = new RegExp(`<link\\s+rel=["']stylesheet["']\\s+href=["']/static/css/${sheet}\\?v=2\\.0\\.\\d+["']>`);
      expect(indexHtml).toMatch(linkRegex);
    }
  });

  it('eliminates massive monolithic inline <style> block from index.html (under 50 lines total inline styles)', () => {
    const styleMatches = indexHtml.match(/<style[^>]*>([\s\S]*?)<\/style>/gi) || [];
    let totalInlineStyleLines = 0;
    for (const styleTag of styleMatches) {
      const lines = styleTag.split('\n').length;
      totalInlineStyleLines += lines;
    }
    // Should be zero or tiny fallback under 50 lines
    expect(totalInlineStyleLines).toBeLessThan(50);
  });

  it('ensures all 4 extracted modular CSS files exist and contain substantive styles', () => {
    const expectedModules = [
      { file: 'base.css', minLines: 100 },
      { file: 'components.css', minLines: 50 },
      { file: 'desktop.css', minLines: 400 },
      { file: 'studios.css', minLines: 200 },
    ];

    for (const mod of expectedModules) {
      const filePath = path.join(cssDir, mod.file);
      expect(fs.existsSync(filePath)).toBe(true);
      const content = fs.readFileSync(filePath, 'utf-8');
      const lineCount = content.split('\n').length;
      expect(lineCount).toBeGreaterThanOrEqual(mod.minLines);
    }
  });

  it('keeps index.html significantly smaller than its monolithic baseline (> 1,200 lines excised)', () => {
    const lineCount = indexHtml.split('\n').length;
    // Originally 5,998 lines; now under 4,800 lines
    expect(lineCount).toBeLessThan(4800);
  });
});
