/**
 * CARD-165: Agent Studio Auto-Train Controls, capability gap backlog, and Chat Action.
 * CARD-496: the backlog is labelled "Capability gaps" and routes to Skill Studio / the Developer.
 * Verifies UI controls in index.html, forge.js, and chat.js [REQ-FACT-023, REQ-FACT-027, REQ-FACT-028].
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Autonomous Training UI & Capability Gap Backlog [CARD-165]', () => {
  const indexHtml = read('src/web/templates/index.html');
  const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/tools.js');
  const chatJs = read('src/web/static/modules/studios/chat.js');

  it('prunes auto-train inputs while keeping backlog queue in index.html [REQ-PRUNE-AUTO-001, REQ-FACT-027]', () => {
    expect(indexHtml).not.toContain('id="forgeAutoTrainCheckbox"');
    expect(indexHtml).not.toContain('id="forgeMaxTrainRetriesInput"');
    expect(indexHtml).toContain('id="agentTrainingBacklogCard"');
    expect(indexHtml).toContain('id="agentBacklogCountBadge"');
    expect(indexHtml).toContain('id="agentBacklogList"');
  });

  it('removes auto-train UI bindings from forge.js while preserving backlog list [REQ-PRUNE-AUTO-001, REQ-FACT-027]', () => {
    expect(forgeJs).not.toContain("forgeAutoTrainCheckbox");
    expect(forgeJs).not.toContain("forgeMaxTrainRetriesInput");
    expect(forgeJs).toContain("agentBacklogList");
  });

  it('drops the auto_train_progress SSE branch; Chat Train in Lab button stays removed [CARD-296, CARD-496]', () => {
    expect(chatJs).not.toContain("train-lab-msg-btn");
    expect(chatJs).not.toMatch(/>Train in Lab</);
    expect(chatJs).not.toContain("auto_train_progress");
  });

  it('never populates trainTargetLocation with agentId and resolves active agent correctly [REQ-FACT-028]', () => {
    // Invariant: Workspace location path must never be populated with an agent identifier
    expect(chatJs).not.toMatch(/targetLoc\.value\s*=\s*agentId/);
    expect(chatJs).not.toMatch(/trainTargetLocation\.value\s*=\s*agentId/);

    // Invariant: Chat Studio state uses selectedAgentId, not undefined activeAgentId
    expect(chatJs).not.toContain("state.activeAgentId");
  });

  it('Agent Studio lists capability gaps with Skill Studio / Developer actions, not training [CARD-496]', () => {
    expect(indexHtml).toContain('Capability gaps');
    expect(indexHtml).not.toContain('Needs Training Backlog');
    expect(forgeJs).toContain("identified_capability");
    expect(forgeJs).toContain("btn-gap-open-skill-studio");
    expect(forgeJs).not.toContain("btn-train-gap");
    expect(chatJs).not.toContain("train-lab-msg-btn");
  });
});




