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

  it('includes [Train in Lab] message button and auto_train_progress in chat.js [REQ-FACT-024, REQ-FACT-028]', () => {
    expect(chatJs).toContain("train-lab-msg-btn");
    expect(chatJs).toContain("Train in Lab");
    expect(chatJs).toContain("auto_train_progress");
  });
});
