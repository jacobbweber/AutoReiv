/**
 * CARD-116 / CARD-405: Agent Cognitive Memory UI Controls and Brain Inspector Drawer.
 * Verifies UI elements in index.html and event wiring in forge.js and forge/config.js.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Agent Studio Cognitive Memory UI [CARD-116 / CARD-405]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js');
  const forgeConfigJs = read('src/web/static/modules/studios/forge/config.js');
  const combinedJs = forgeJs + forgeConfigJs;

  it('renders memory controls and brain drawer in index.html [REQ-405-001]', () => {
    expect(indexHtml).toContain('id="forgeMemoryEnabled"');
    expect(indexHtml).toContain('id="forgeMemoryRetentionDays"');
    expect(indexHtml).toContain('id="forgeMemoryRetentionDaysLabel"');
    expect(indexHtml).toContain('id="forgePinnedMemory"');
    expect(indexHtml).toContain('id="btnOpenBrainDrawer"');
    expect(indexHtml).toContain('id="btnPurgeBrain"');
    expect(indexHtml).toContain('id="agentBrainDrawer"');
    expect(indexHtml).toContain('id="brainSearchInput"');
    expect(indexHtml).toContain('id="brainDrawerAgentName"');
    expect(indexHtml).toContain('id="brainShelfPinnedContainer"');
    expect(indexHtml).toContain('id="brainShelfSummariesContainer"');
    expect(indexHtml).toContain('id="brainShelfFactsContainer"');
  });

  it('binds memory controls and handles payload in forge.js / forge/config.js [REQ-405-001]', () => {
    expect(combinedJs).toContain("const forgeMemoryEnabled = $('forgeMemoryEnabled');");
    expect(combinedJs).toContain("const forgeMemoryRetentionDays = $('forgeMemoryRetentionDays');");
    expect(combinedJs).toContain("const forgePinnedMemory = $('forgePinnedMemory');");
    expect(combinedJs).toContain("const btnOpenBrainDrawer = $('btnOpenBrainDrawer');");
    expect(combinedJs).toContain("const btnPurgeBrain = $('btnPurgeBrain');");
    expect(combinedJs).toContain("memory_enabled: Boolean(forgeMemoryEnabled && forgeMemoryEnabled.checked)");
    expect(combinedJs).toContain('memory_retention_days:');
    expect(combinedJs).toContain('pinned_memory:');
  });

  it('handles Shelf 1 pinned directives with fallback to agent profile string [REQ-405-002]', () => {
    expect(forgeConfigJs).toContain('brainShelfPinnedContainer.textContent');
    expect(forgeConfigJs).toContain('data.pinned');
    expect(forgeConfigJs).toContain('data.pinned_memory');
  });

  it('renders Shelf 2 episodic summaries and Shelf 3 semantic facts robustly [REQ-405-003, REQ-405-004]', () => {
    // Dual key fallback for summaries
    expect(forgeConfigJs).toContain('data.session_summaries || data.summaries || []');
    expect(forgeConfigJs).toContain('s.summary_text || s.summary || \'\'');

    // Dual key fallback for facts and formatted factText
    expect(forgeConfigJs).toContain('data.semantic_facts || data.facts || []');
    expect(forgeConfigJs).toContain('f.category');
    expect(forgeConfigJs).toContain('f.confidence');
    expect(forgeConfigJs).toContain('f.access_count');
    expect(forgeConfigJs).toContain('btn-forget-fact');
  });

  it('executes DELETE on fact forget and DELETE on brain purge [REQ-405-001]', () => {
    // Fact forget calls DELETE
    expect(forgeConfigJs).toContain('/api/agents/${encodeURIComponent(agentId)}/memory/facts/${encodeURIComponent(factId)}');
    expect(forgeConfigJs).toContain("method: 'DELETE'");

    // Brain purge calls DELETE
    expect(forgeConfigJs).toContain('/api/agents/${encodeURIComponent(id)}/memory');
  });
});
