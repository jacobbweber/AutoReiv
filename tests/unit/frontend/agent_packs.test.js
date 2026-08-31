/**
 * CARD-119: Agent Packs UI — Import/Export, Show in Chat, pack-owned tools.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  isAgentVisibleInChat,
  agentsVisibleInChat,
  prepareNewAgentAuthoringSession,
  NEW_AGENT_STARTER_PROMPT,
  AUTOREIV_AGENT_ID,
} from '../../../src/web/static/modules/studios/chat.js';
import { startNewAgentPackFromStudio } from '../../../src/web/static/modules/studios/forge.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Show in Chat filter [CARD-119]', () => {
  it('hides agents with show_in_chat false from picker lists', () => {
    const agents = [
      { id: 'assistant', name: 'Assistant' },
      { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
      { id: 'hidden-bot', name: 'Hidden Bot', show_in_chat: false },
    ];
    expect(isAgentVisibleInChat(agents[0])).toBe(true);
    expect(isAgentVisibleInChat(agents[2])).toBe(false);
    const visible = agentsVisibleInChat(agents);
    expect(visible.map((a) => a.id)).toEqual(['assistant', 'autoreiv']);
    expect(visible.map((a) => a.id)).not.toContain('hidden-bot');
  });
});

describe('Agent Studio pack UI [CARD-119]', () => {
  it('docs/agent-packs.md is the how-to and names no inspiration products', () => {
    const docs = read('docs/agent-packs.md');
    expect(docs).toContain('pack.json');
    expect(docs).toContain('show_in_chat');
    expect(docs).toContain('Hand export');
    expect(docs).toContain('Hand import');
    expect(docs).not.toContain('Hermes');
    expect(docs).not.toContain('Pack Studio');
  });

  it('has Import and Export on Agent Studio, no Pack Studio', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('forgeImportPackBtn');
    expect(html).toContain('forgeExportPackBtn');
    expect(html).toContain('Show in Chat');
    expect(html).toContain('forgeShowInChat');
    expect(html).not.toContain('Pack Studio');
    expect(html).not.toContain('Skills Studio');
    expect(html).not.toContain('Hermes');
  });

  it('forge.js saves show_in_chat and fills pack-owned from pack_tool_names', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('show_in_chat');
    expect(forgeJs).toContain('pack_tool_names');
    expect(forgeJs).toContain('/api/agents/import-pack');
    expect(forgeJs).toContain('/pack.zip');
    expect(forgeJs).toContain('No pack-owned tools yet.');
    expect(forgeJs).not.toContain('Pack Studio');
    expect(forgeJs).not.toContain('Hermes');
  });

  it('chat.js filters both pickers with show_in_chat !== false', () => {
    const chatJs = read('src/web/static/modules/studios/chat.js');
    expect(chatJs).toContain('agentsVisibleInChat');
    expect(chatJs).toContain('isAgentVisibleInChat');
    expect(chatJs).toContain('show_in_chat !== false');
  });
});


describe('New Agent AutoReiv handoff [CARD-119]', () => {
  it('studio helper calls onStartNewAgentPack and does not POST', () => {
    const calls = [];
    const handed = startNewAgentPackFromStudio({
      onStartNewAgentPack: () => calls.push('handoff'),
    });
    expect(handed).toBe(true);
    expect(calls).toEqual(['handoff']);
    expect(startNewAgentPackFromStudio({})).toBe(false);
  });

  it('fills AutoReiv starter prompt without sending', async () => {
    const switchCalls = [];
    const sessionCalls = [];
    const promptInput = { value: '', focusCalls: 0, focus() { this.focusCalls += 1; } };
    const sendCalls = [];
    const result = await prepareNewAgentAuthoringSession({
      switchSelectedAgent: async (id) => { switchCalls.push(id); },
      createNewSession: async () => { sessionCalls.push('new'); },
      promptInput,
    });
    expect(switchCalls).toEqual([AUTOREIV_AGENT_ID]);
    expect(sessionCalls).toEqual(['new']);
    expect(promptInput.value).toBe(NEW_AGENT_STARTER_PROMPT);
    expect(promptInput.value).toBe('I am ready to create a new agent.');
    expect(promptInput.focusCalls).toBe(1);
    expect(result.filled).toBe(true);
    expect(result.sent).toBe(false);
    expect(sendCalls).toEqual([]);
  });

  it('forge New Agent hands off instead of blanking a custom agent', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).toContain('startNewAgentPackFromStudio');
    expect(forgeJs).toContain('onStartNewAgentPack');
    expect(forgeJs).toContain('Talk to AutoReiv to build the pack.');
    expect(forgeJs).not.toContain('Creating new custom agent');
    expect(forgeJs).not.toContain("textContent = 'New Custom'");
    const appJs = read('src/web/static/app.js');
    expect(appJs).toContain("onStartNewAgentPack");
    expect(appJs).toContain("switchTab('chat')");
    expect(appJs).toContain('startNewAgentAuthoring');
    const chatJs = read('src/web/static/modules/studios/chat.js');
    expect(chatJs).toContain('startNewAgentAuthoring');
    expect(chatJs).toContain('I am ready to create a new agent.');
    expect(chatJs).not.toContain("sendBtn.click()");
  });

  it('nested pack how-to describes tools under skills', () => {
    const docs = read('docs/agent-packs.md');
    expect(docs).toContain('schema_version');
    expect(docs).toContain('1.1');
    expect(docs).toContain('"tools": ["system_info"]');
    expect(docs).toContain('Talk to AutoReiv');
    expect(docs).not.toContain('Hermes');
    const runbook = read('src/infrastructure/skills/seeds/build-agent-pack/SKILL.md');
    expect(runbook).toContain('which tools belong to that skill');
    expect(runbook).toContain('agent details');
    expect(runbook).not.toContain('Hermes');
  });
});
