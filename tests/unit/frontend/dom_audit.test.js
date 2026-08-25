import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * Static DOM Architecture & Defensive Query Audit [REQ-DOM-004]
 * Verifies that all modules under src/web/static/modules/ and src/web/static/app.js
 * adhere to defensive DOM query architecture and avoid direct raw document queries outside dom.js.
 */
describe('DOM Architecture & Null-Safety Static Audit', () => {
  const staticDir = path.resolve(__dirname, '../../../src/web/static');

  function getJsFiles(dir) {
    let results = [];
    const list = fs.readdirSync(dir);
    list.forEach((file) => {
      const fullPath = path.join(dir, file);
      const stat = fs.statSync(fullPath);
      if (stat && stat.isDirectory()) {
        results = results.concat(getJsFiles(fullPath));
      } else if (file.endsWith('.js')) {
        results.push(fullPath);
      }
    });
    return results;
  }

  it('prohibits direct document.getElementById outside dom.js [REQ-DOM-001]', () => {
    const jsFiles = getJsFiles(staticDir);
    const violations = [];

    jsFiles.forEach((filePath) => {
      const relPath = path.relative(staticDir, filePath).replace(/\\/g, '/');
      if (relPath === 'modules/dom.js') return; // Allowed only in dom.js

      const content = fs.readFileSync(filePath, 'utf-8');
      const lines = content.split('\n');
      lines.forEach((line, lineIdx) => {
        if (line.includes('document.getElementById(')) {
          violations.push(`${relPath}:${lineIdx + 1}: ${line.trim()}`);
        }
      });
    });

    expect(violations, `Direct document.getElementById found in:\n${violations.join('\n')}`).toEqual([]);
  });

  it('prohibits direct document.querySelector and document.querySelectorAll outside dom.js [REQ-DOM-001]', () => {
    const jsFiles = getJsFiles(staticDir);
    const violations = [];

    jsFiles.forEach((filePath) => {
      const relPath = path.relative(staticDir, filePath).replace(/\\/g, '/');
      if (relPath === 'modules/dom.js') return; // Allowed only in dom.js

      const content = fs.readFileSync(filePath, 'utf-8');
      const lines = content.split('\n');
      lines.forEach((line, lineIdx) => {
        if (line.includes('document.querySelector(') || line.includes('document.querySelectorAll(')) {
          violations.push(`${relPath}:${lineIdx + 1}: ${line.trim()}`);
        }
      });
    });

    expect(violations, `Direct document.querySelector/querySelectorAll found in:\n${violations.join('\n')}`).toEqual(
      []
    );
  });
});
