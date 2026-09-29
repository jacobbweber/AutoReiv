/**
 * CARD-119: Agent Packs UI — Import/Export, Show in Chat, pack-owned tools.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  isAgentVisibleInChat,
  agentsVisibleInChat,
} from '../../../src/web/static/modules/studios/chat.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('Show in Chat filter [CARD-119, CARD-339]', () => {
  it('hides agents with show_in_chat false from picker lists', () => {
    const agents = [
      { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
      { id: 'direct', name: 'Direct', show_in_chat: true },
      { id: 'hidden-bot', name: 'Hidden Bot', show_in_chat: false },
    ];
    expect(isAgentVisibleInChat(agents[0])).toBe(true);
    expect(isAgentVisibleInChat(agents[1])).toBe(true);
    expect(isAgentVisibleInChat(agents[2])).toBe(false);
    const visible = agentsVisibleInChat(agents);
    expect(visible.map((a) => a.id)).toEqual(['autoreiv', 'direct']);
    expect(visible.map((a) => a.id)).not.toContain('hidden-bot');
  });

  it('hides agent-builder when show_in_chat is false', () => {
    const agents = [
      { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
      { id: 'direct', name: 'Direct', show_in_chat: true },
      { id: 'agent-builder', name: 'Agent Builder', show_in_chat: false },
    ];
    expect(agentsVisibleInChat(agents).map((a) => a.id)).toEqual(['autoreiv', 'direct']);
  });

  it('never lists agent-builder in Chat pickers even if show_in_chat is true', () => {
    const agents = [
      { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
      { id: 'direct', name: 'Direct', show_in_chat: true },
      { id: 'agent-builder', name: 'Agent Builder', show_in_chat: true },
    ];
    expect(isAgentVisibleInChat(agents[2])).toBe(false);
    expect(agentsVisibleInChat(agents).map((a) => a.id)).toEqual(['autoreiv', 'direct']);
    expect(agentsVisibleInChat(agents).map((a) => a.id)).not.toContain('agent-builder');
  });

  it('hides retired specialists (Assistant, Wiki) and legacy personas from Chat while keeping Developer [CARD-339, CARD-359]', () => {
    const agents = [
      { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
      { id: 'direct', name: 'Direct', show_in_chat: true },
      { id: 'assistant', name: 'Assistant', show_in_chat: true },
      { id: 'developer', name: 'Developer', show_in_chat: true },
      { id: 'wiki', name: 'Wiki', show_in_chat: true },
      { id: 'conductor', name: 'Conductor', show_in_chat: true },
      { id: 'coding', name: 'Coding', show_in_chat: true },
      { id: 'review', name: 'Review', show_in_chat: true },
    ];
    expect(isAgentVisibleInChat(agents[0])).toBe(true);
    expect(isAgentVisibleInChat(agents[1])).toBe(true);
    expect(isAgentVisibleInChat(agents[2])).toBe(false);
    expect(isAgentVisibleInChat(agents[3])).toBe(true);
    expect(isAgentVisibleInChat(agents[4])).toBe(false);
    expect(isAgentVisibleInChat(agents[5])).toBe(false);
    expect(isAgentVisibleInChat(agents[6])).toBe(false);
    expect(isAgentVisibleInChat(agents[7])).toBe(false);
    expect(agentsVisibleInChat(agents).map((a) => a.id)).toEqual(['autoreiv', 'direct', 'developer']);
  });
});

describe('Agent Studio pack UI [CARD-119]', () => {
  it('docs/archive_artifacts/specs/agent-packs.md is the how-to and names no inspiration products', () => {
    const docs = read('docs/archive_artifacts/specs/agent-packs.md');
    expect(docs).toContain('pack.json');
    expect(docs).toContain('show_in_chat');
    expect(docs).toContain('Hand export');
    expect(docs).toContain('Hand import');
    expect(docs).not.toContain('Hermes');
    expect(docs).not.toContain('Pack Studio');
  });

  it('has no Import/Export pack buttons on Agent Studio, no Pack Studio [CARD-569]', () => {
    const html = read('src/web/templates/index.html');
    expect(html).not.toContain('forgeImportPackBtn');
    expect(html).not.toContain('forgeExportPackBtn');
    expect(html).toContain('Show in Chat');
    expect(html).toContain('forgeShowInChat');
    expect(html).not.toContain('Pack Studio');
    expect(html).not.toContain('Skills Studio');
    expect(html).not.toContain('Hermes');
    expect(html).not.toContain('value="agent-builder"');
  });

  it('forge.js saves show_in_chat; tool lists are not sent (CARD-539)', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/runbook.js');
    const pickerJs = read('src/web/static/modules/studios/agent_picker.js');
    expect(forgeJs).toContain('show_in_chat');
    expect(forgeJs).not.toMatch(/pack_tool_names\s*:/);
    expect(forgeJs).not.toContain('/api/agents/import-pack');
    expect(forgeJs).not.toContain('/pack.zip');
    expect(forgeJs).toContain('assignedSkillListHtml');
    expect(forgeJs).not.toContain('No pack-owned skills yet.');
    expect(forgeJs).not.toContain('Pack Studio');
    expect(forgeJs).not.toContain('Hermes');
    expect(forgeJs).toContain('isStudioAgentVisible');
    expect(pickerJs).toContain("a.id !== 'agent-builder'");
  });

  it('chat.js filters both pickers with show_in_chat !== false and skips hidden ids [CARD-383]', () => {
    const chatJs = read('src/web/static/modules/studios/chat.js');
    expect(chatJs).toContain('agentsVisibleInChat');
    expect(chatJs).toContain('isAgentVisibleInChat');
    expect(chatJs).toContain('show_in_chat !== false');
    expect(chatJs).toContain('RETIRED_LEGACY_AGENT_IDS');
  });
});


describe('New Agent opens the Agent Studio form [CARD-569]', () => {
  it('New Agent opens the new-agent form and creates via POST /api/agents, no AutoReiv handoff', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js') + read('src/web/static/modules/studios/forge/scaffold.js');
    expect(forgeJs).toContain('openQuickScaffoldModal');
    expect(forgeJs).toContain("fetch('/api/agents'");
    expect(forgeJs).not.toContain('startNewAgentPackFromStudio');
    expect(forgeJs).not.toContain('onStartNewAgentPack');
    expect(forgeJs).not.toContain('Talk to AutoReiv to build the pack.');
    const appJs = read('src/web/static/app.js');
    expect(appJs).not.toContain('onStartNewAgentPack');
    const chatJs = read('src/web/static/modules/studios/chat.js') + read('src/web/static/modules/studios/chat/stream.js');
    expect(chatJs).not.toContain('startNewAgentAuthoring');
    expect(chatJs).not.toContain('I am ready to create a new agent.');
    const html = read('src/web/templates/index.html');
    expect(html).not.toContain('forgeNewAgentChatInsteadBtn');
  });

  it('proposals runbook has no pack scaffolding', () => {
    const recommend = read('platform/skills/proposals/SKILL.md');
    expect(recommend).toContain('Capability Proposals');
    expect(recommend).toContain('Do not commit until approved');
    expect(recommend).not.toContain('scaffold_agent_pack');
    expect(recommend).not.toContain('Hermes');
  });
});
