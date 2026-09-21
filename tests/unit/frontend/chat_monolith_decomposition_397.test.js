/**
 * CARD-397: Chat Studio Monolith Decomposition Contract Test.
 * Asserts file size caps (<800 lines for submodules, <1000 lines for orchestrator)
 * and verifies complete backward compatibility of exported APIs.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-397: Chat Studio Monolith Decomposition and Submodule Hygiene', () => {
  const repoRoot = path.resolve(__dirname, '../../..');
  const chatJsPath = path.join(repoRoot, 'src/web/static/modules/studios/chat.js');
  const chatDir = path.join(repoRoot, 'src/web/static/modules/studios/chat');

  it('orchestrator chat.js is strictly under 1,000 lines', () => {
    const content = fs.readFileSync(chatJsPath, 'utf-8');
    const lines = content.split('\n').length;
    expect(lines).toBeLessThan(1000);
    // Sanity check: must be substantial enough to be the real orchestrator
    expect(lines).toBeGreaterThan(400);
  });

  it('all submodules under chat/ are strictly under 800 lines', () => {
    const files = fs.readdirSync(chatDir).filter((f) => f.endsWith('.js'));
    expect(files.length).toBeGreaterThanOrEqual(10);

    const oversized = [];
    files.forEach((file) => {
      const filePath = path.join(chatDir, file);
      const lines = fs.readFileSync(filePath, 'utf-8').split('\n').length;
      if (lines >= 800) {
        oversized.push({ file, lines });
      }
    });

    expect(oversized).toEqual([]);
  });

  it('re-exports required backward-compatible APIs and symbols', async () => {
    const chatModule = await import('../../../src/web/static/modules/studios/chat.js');

    // Controller entry point
    expect(typeof chatModule.initChatStudio).toBe('function');

    // Agent visibility helpers
    expect(typeof chatModule.isAgentVisibleInChat).toBe('function');
    expect(typeof chatModule.agentsVisibleInChat).toBe('function');
    expect(typeof chatModule.dualEngineAgentsVisibleInChat).toBe('function');
    expect(chatModule.RETIRED_LEGACY_AGENT_IDS).toBeDefined();

    // Job phase chrome helpers
    expect(typeof chatModule.isJobPhaseChromeEvent).toBe('function');
    expect(typeof chatModule.humanizeJobStatus).toBe('function');
    expect(typeof chatModule.formatJobPhaseStrip).toBe('function');
    expect(typeof chatModule.applyJobPhaseEvent).toBe('function');
    expect(typeof chatModule.isHitlParkSseEvent).toBe('function');
    expect(typeof chatModule.hydrateJobPhaseStateFromJourney).toBe('function');

    // Inline job chrome helpers
    expect(typeof chatModule.formatMilestoneGoalTitle).toBe('function');
    expect(typeof chatModule.createInlineJobChromeModel).toBe('function');
    expect(typeof chatModule.applyInlineJobChromeModel).toBe('function');
    expect(typeof chatModule.formatInlineJobChromeHtml).toBe('function');
    expect(typeof chatModule.applyInlineJobChromeEvent).toBe('function');
    expect(typeof chatModule.renderJobChromePhasesIntoElement).toBe('function');

    // Scroll helpers
    expect(typeof chatModule.isScrolledNearBottom).toBe('function');
    expect(typeof chatModule.shouldAutoscrollOnStream).toBe('function');
    expect(typeof chatModule.shouldShowJumpToLatest).toBe('function');
    expect(typeof chatModule.isChatSessionsDrawerOpen).toBe('function');
    expect(typeof chatModule.openChatSessionsDrawer).toBe('function');
    expect(typeof chatModule.collapseChatSessionsDrawer).toBe('function');
  });
});
