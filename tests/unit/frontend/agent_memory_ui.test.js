/**
 * CARD-116: Agent Cognitive Memory UI Controls and Brain Inspector Drawer.
 * Verifies UI elements in index.html and event wiring in forge.js.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio Cognitive Memory UI [CARD-116]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js');

  it('renders memory controls in index.html [REQ-MEM-009, REQ-MEM-010]', () => {
    expect(indexHtml).toContain('id="forgeMemoryEnabled"');
    expect(indexHtml).toContain('id="forgeMemoryRetentionDays"');
    expect(indexHtml).toContain('id="forgeMemoryRetentionDaysLabel"');
    expect(indexHtml).toContain('id="forgePinnedMemory"');
    expect(indexHtml).toContain('id="btnOpenBrainDrawer"');
    expect(indexHtml).toContain('id="btnPurgeBrain"');
    expect(indexHtml).toContain('id="agentBrainDrawer"');
    expect(indexHtml).toContain('id="brainSearchInput"');
  });

  it('binds memory controls and handles payload in forge.js [REQ-MEM-009, REQ-MEM-010]', () => {
    expect(forgeJs).toContain("const forgeMemoryEnabled = $('forgeMemoryEnabled');");
    expect(forgeJs).toContain("const forgeMemoryRetentionDays = $('forgeMemoryRetentionDays');");
    expect(forgeJs).toContain("const forgePinnedMemory = $('forgePinnedMemory');");
    expect(forgeJs).toContain("const btnOpenBrainDrawer = $('btnOpenBrainDrawer');");
    expect(forgeJs).toContain("const btnPurgeBrain = $('btnPurgeBrain');");
    expect(forgeJs).toContain("memory_enabled: Boolean(forgeMemoryEnabled && forgeMemoryEnabled.checked)");
    expect(forgeJs).toContain("memory_retention_days:");
    expect(forgeJs).toContain("pinned_memory:");
  });
});
