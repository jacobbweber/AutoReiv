/**
 * CARD-188: Settings Studio Edit and Unmask Controls Unit Tests.
 * Verifies UI controls and bindings in index.html and settings.js.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Settings Studio Edit and Unmask Controls [CARD-188]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const settingsJs = read('src/web/static/modules/studios/settings.js');

  it('renders secret unmask toggle in index.html [REQ-VAULT-008]', () => {
    expect(indexHtml).toContain('id="toggleCredSecretVisibilityBtn"');
  });

  it('binds credential unmask and edit logic in settings.js [REQ-VAULT-007, REQ-VAULT-008]', () => {
    expect(settingsJs).toContain('/reveal');
    expect(settingsJs).toContain('data-reveal-cred');
    expect(settingsJs).toContain('data-edit-cred');
    expect(settingsJs).toContain('toggleCredSecretVisibilityBtn');
  });

  it('binds remote host edit logic in settings.js [REQ-REMOTE-006]', () => {
    expect(settingsJs).toContain('data-edit-host');
  });
});
