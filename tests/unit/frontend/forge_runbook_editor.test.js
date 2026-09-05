/**
 * CARD-167: Agent Studio Skill Runbook Editor Close and Cancel Dismiss Controls.
 * Verifies that #studioRunbookEditor provides top-right close 'x' and bottom Cancel button.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio Runbook Editor Dismiss Controls [CARD-167]', () => {
  it('index.html contains #studioRunbookCloseBtn and #studioRunbookCancelBtn inside #studioRunbookEditor', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="studioRunbookEditor"');
    expect(html).toContain('id="studioRunbookCloseBtn"');
    expect(html).toContain('id="studioRunbookCancelBtn"');
  });

  it('forge.js wires #studioRunbookCloseBtn and #studioRunbookCancelBtn to hideRunbookEditor()', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('studioRunbookCloseBtn');
    expect(forgeJs).toContain('studioRunbookCancelBtn');
    expect(forgeJs).toMatch(/studioRunbookCloseBtn.*addEventListener\(['"]click['"],\s*(?:\(\)\s*=>\s*\{?\s*)?hideRunbookEditor/);
    expect(forgeJs).toMatch(/studioRunbookCancelBtn.*addEventListener\(['"]click['"],\s*(?:\(\)\s*=>\s*\{?\s*)?hideRunbookEditor/);
  });
});
