/**
 * CARD-398: Agent Forge Studio Monolith Decomposition Contract Test.
 * Asserts file size caps (<800 lines for submodules, <1000 lines for orchestrator)
 * and verifies complete backward compatibility of exported APIs and symbols.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-398: Agent Forge Studio Monolith Decomposition and Submodule Hygiene', () => {
  const repoRoot = path.resolve(__dirname, '../../..');
  const forgeJsPath = path.join(repoRoot, 'src/web/static/modules/studios/forge.js');
  const forgeDir = path.join(repoRoot, 'src/web/static/modules/studios/forge');

  it('orchestrator forge.js is strictly under 1,000 lines', () => {
    const content = fs.readFileSync(forgeJsPath, 'utf-8');
    const lines = content.split('\n').length;
    expect(lines).toBeLessThan(1000);
    // Sanity check: must be substantial enough to be the real orchestrator
    expect(lines).toBeGreaterThan(400);
  });

  it('all submodules under forge/ are strictly under 800 lines', () => {
    const files = fs.readdirSync(forgeDir).filter((f) => f.endsWith('.js'));
    expect(files.length).toBeGreaterThanOrEqual(6);

    const oversized = [];
    files.forEach((file) => {
      const filePath = path.join(forgeDir, file);
      const lines = fs.readFileSync(filePath, 'utf-8').split('\n').length;
      if (lines >= 800) {
        oversized.push({ file, lines });
      }
    });

    expect(oversized).toEqual([]);
  });

  it('re-exports required backward-compatible APIs and symbols', async () => {
    const forgeModule = await import('../../../src/web/static/modules/studios/forge.js');

    // Controller entry point
    expect(typeof forgeModule.initAgentForge).toBe('function');

    // Agent picker and sorting helpers
    expect(typeof forgeModule.sortStudioAgentsAlphabetically).toBe('function');
    expect(typeof forgeModule.isStudioAgentVisible).toBe('function');
    expect(typeof forgeModule.populateForgeAgentSelectOptions).toBe('function');
    expect(typeof forgeModule.formatAgentSelectOption).toBe('function');

    // Tool badges & baseline tools
    expect(typeof forgeModule.renderToolBadgeHtml).toBe('function');
    expect(typeof forgeModule.baselineToolCardHtml).toBe('function');
    expect(typeof forgeModule.renderBaselineTools).toBe('function');
    expect(typeof forgeModule.loadAgentCapabilityGaps).toBe('function');
    expect(typeof forgeModule.loadAgentMcpServers).toBe('function');
    expect(typeof forgeModule.renderAgentMcpServers).toBe('function');
    expect(typeof forgeModule.loadAgentCredentialGrants).toBe('function');

    // Quick scaffold & presets
    expect(typeof forgeModule.startNewAgentPackFromStudio).toBe('function');
    expect(forgeModule.FORGE_QUICK_PRESETS).toBeDefined();
    expect(typeof forgeModule.buildQuickScaffoldPayload).toBe('function');
    expect(typeof forgeModule.openQuickScaffoldModal).toBe('function');
    expect(typeof forgeModule.closeQuickScaffoldModal).toBe('function');
    // CARD-496: the Agent Training Optimization queue is retired
    expect(forgeModule.loadForgeScaffoldQueue).toBeUndefined();
    expect(forgeModule.runForgeScaffoldAction).toBeUndefined();

    // Architectural proposals
    expect(typeof forgeModule.renderProposalBadgeHtml).toBe('function');
    expect(typeof forgeModule.renderProposalCardHtml).toBe('function');
    expect(typeof forgeModule.loadArchitecturalProposals).toBe('function');
    expect(typeof forgeModule.runArchitecturalProposalAction).toBe('function');
    expect(typeof forgeModule.scanAndSynthesizeProposals).toBe('function');

    // Lab training monitor drawer is retired with the Factory [CARD-496]
    for (const name of ['buildExpectedPackPaths', 'collectPacketArtifacts', 'formatLabPacketFeedLines', 'formatLabActivityFeedText',
      'populateTrainModalForRetry', 'updateLabRunsBadge', 'openLabMonitorDrawer', 'closeLabMonitorDrawer',
      'openLabArtifactPreview', 'closeLabArtifactPreview']) {
      expect(forgeModule[name], name).toBeUndefined();
    }

    // Skill rows: pills and Open in Skill Studio. Inline inspector is gone [CARD-419].
    expect(typeof forgeModule.skillRowHtml).toBe('function');
    expect(typeof forgeModule.applySkillChecks).toBe('function');
    expect(typeof forgeModule.bindSkillRowHandlers).toBe('function');
    expect(forgeModule.CANONICAL_RUNBOOK_TEMPLATE).toBeUndefined();
    expect(forgeModule.openRunbookEditor).toBeUndefined();
    expect(forgeModule.hideRunbookEditor).toBeUndefined();
    expect(forgeModule.validateActiveRunbook).toBeUndefined();
    expect(typeof forgeModule.renderAssignedSkills).toBe('function');
    expect(typeof forgeModule.assignedSkillListHtml).toBe('function');
    expect(forgeModule.renderPlatformSkills).toBeUndefined();
    expect(forgeModule.renderPackSkills).toBeUndefined();
    expect(typeof forgeModule.renderNestedHomes).toBe('function');
    expect(typeof forgeModule.loadPlatformSkills).toBe('function');

    // Agent configuration, model discovery & tone management
    expect(typeof forgeModule.populateAgentModelSelect).toBe('function');
    expect(typeof forgeModule.updateProviderConfigVisibility).toBe('function');
    expect(typeof forgeModule.discoverModelsForAgent).toBe('function');
    expect(typeof forgeModule.updateAvatarPreview).toBe('function');
    expect(typeof forgeModule.loadAgentAssignedRoutines).toBe('function');
    expect(typeof forgeModule.loadAgentTelemetry).toBe('function');
    expect(typeof forgeModule.loadAndRenderBrainDrawer).toBe('function');
    expect(typeof forgeModule.openBrainDrawer).toBe('function');
    expect(typeof forgeModule.closeBrainDrawer).toBe('function');
    expect(typeof forgeModule.loadTones).toBe('function');
    expect(typeof forgeModule.openManageTonesModal).toBe('function');
    expect(typeof forgeModule.closeManageTonesModal).toBe('function');
    expect(typeof forgeModule.renderManageTonesList).toBe('function');
  });
});
