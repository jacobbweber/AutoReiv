/**
 * CARD-165: Agent Studio Auto-Train Controls, Needs Training Backlog, and Chat Action.
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
  const forgeJs = read('src/web/static/modules/studios/forge.js');
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

  it('keeps auto_train_progress SSE; Chat Train in Lab button removed [CARD-296]', () => {
    // CARD-296 design lock: remove Chat "Train in Lab" message action (Factory/Forge retain train gap).
    expect(chatJs).not.toContain("train-lab-msg-btn");
    expect(chatJs).not.toMatch(/>Train in Lab</);
    expect(chatJs).toContain("auto_train_progress");
  });

  it('never populates trainTargetLocation with agentId and resolves active agent correctly [REQ-FACT-028]', () => {
    // Invariant: Workspace location path must never be populated with an agent identifier
    expect(chatJs).not.toMatch(/targetLoc\.value\s*=\s*agentId/);
    expect(chatJs).not.toMatch(/trainTargetLocation\.value\s*=\s*agentId/);

    // Invariant: Chat Studio state uses selectedAgentId, not undefined activeAgentId
    expect(chatJs).not.toContain("state.activeAgentId");
  });

  it('Factory/Forge still queue capability gaps; Chat no longer exposes Train in Lab [CARD-296]', () => {
    const factoryJs = read('src/web/static/modules/studios/factory.js');
    // Chat message Train in Lab removed; gap train remains in Factory studio.
    expect(factoryJs).toContain("btn-train-gap");
    expect(factoryJs).toContain("identified_capability");
    expect(chatJs).not.toContain("train-lab-msg-btn");
  });
});




