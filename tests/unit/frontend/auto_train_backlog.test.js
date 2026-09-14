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

  it('renders auto-train controls and backlog queue in index.html [REQ-FACT-023, REQ-FACT-027]', () => {
    expect(indexHtml).toContain('id="forgeAutoTrainCheckbox"');
    expect(indexHtml).toContain('id="forgeMaxTrainRetriesInput"');
    expect(indexHtml).toContain('id="agentTrainingBacklogCard"');
    expect(indexHtml).toContain('id="agentBacklogCountBadge"');
    expect(indexHtml).toContain('id="agentBacklogList"');
  });

  it('binds auto-train controls and loads/saves auto-train state in forge.js [REQ-FACT-023, REQ-FACT-027]', () => {
    expect(forgeJs).toContain("forgeAutoTrainCheckbox");
    expect(forgeJs).toContain("forgeMaxTrainRetriesInput");
    expect(forgeJs).toContain("allow_autonomous_training");
    expect(forgeJs).toContain("max_training_retries");
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
    // Chat message Train in Lab removed; gap train remains in Factory/Forge studios.
    expect(forgeJs).toContain("btn-train-gap");
    expect(forgeJs).toContain("identified_capability");
    expect(forgeJs).toContain("data.gaps");
    expect(chatJs).not.toContain("train-lab-msg-btn");
  });
});




