/**
 * CARD-119: Agent Packs UI — Import/Export, Show in Chat, pack-owned tools.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { isAgentVisibleInChat, agentsVisibleInChat } from '../../../src/web/static/modules/studios/chat.js';

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
