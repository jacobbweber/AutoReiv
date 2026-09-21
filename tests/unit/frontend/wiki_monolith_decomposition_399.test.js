/**
 * CARD-399: Wiki Studio Monolith Decomposition Contract Test.
 * Asserts file size caps (<800 lines for submodules, <1000 lines for orchestrator)
 * and verifies complete backward compatibility of exported APIs and symbols.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-399: Wiki Studio Monolith Decomposition and Submodule Hygiene', () => {
  const repoRoot = path.resolve(__dirname, '../../..');
  const wikiJsPath = path.join(repoRoot, 'src/web/static/modules/studios/wiki.js');
  const wikiDir = path.join(repoRoot, 'src/web/static/modules/studios/wiki');

  it('orchestrator wiki.js is strictly under 1,000 lines', () => {
    const content = fs.readFileSync(wikiJsPath, 'utf-8');
    const lines = content.split('\n').length;
    expect(lines).toBeLessThan(1000);
    expect(lines).toBeGreaterThan(100);
  });

  it('all submodules under wiki/ are strictly under 800 lines', () => {
    expect(fs.existsSync(wikiDir)).toBe(true);
    const files = fs.readdirSync(wikiDir).filter((f) => f.endsWith('.js'));
    expect(files.length).toBeGreaterThanOrEqual(5);

    const oversized = [];
    files.forEach((file) => {
      const filePath = path.join(wikiDir, file);
      const lines = fs.readFileSync(filePath, 'utf-8').split('\n').length;
      if (lines >= 800) {
        oversized.push({ file, lines });
      }
    });

    expect(oversized).toEqual([]);
  });

  it('re-exports required backward-compatible APIs and symbols', async () => {
    const wikiModule = await import('../../../src/web/static/modules/studios/wiki.js');

    // Primary controller entry point
    expect(typeof wikiModule.initWikiStudio).toBe('function');

    // Message export to wiki
    expect(typeof wikiModule.exportMessageToWiki).toBe('function');
  });
});
