/**
 * CARD-148: Per-Agent Persistent Storage in Agent Studio
 * Verifies UI controls and bindings for agent storage toggle and database type selector.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio Persistent Storage UI [CARD-148]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js');

  it('renders forgeStorageEnabled and forgeStorageType in index.html [REQ-STORAGE-002]', () => {
    expect(indexHtml).toContain('id="forgeStorageEnabled"');
    expect(indexHtml).toContain('id="forgeStorageTypeContainer"');
    expect(indexHtml).toContain('id="forgeStorageType"');
    expect(indexHtml).toContain('Persistent Storage');
    expect(indexHtml).toContain('SQLite (Isolated File)');
    expect(indexHtml).toContain('packs/&lt;agent_id&gt;/storage.db');
  });

  it('binds storage toggle and handles payload in forge.js [REQ-STORAGE-002]', () => {
    expect(forgeJs).toContain("const forgeStorageEnabled = $('forgeStorageEnabled');");
    expect(forgeJs).toContain("const forgeStorageTypeContainer = $('forgeStorageTypeContainer');");
    expect(forgeJs).toContain("const forgeStorageType = $('forgeStorageType');");
    expect(forgeJs).toContain("storage_enabled: Boolean(forgeStorageEnabled && forgeStorageEnabled.checked)");
    expect(forgeJs).toContain("storage_type: forgeStorageType ? forgeStorageType.value : 'sqlite'");
  });
});
