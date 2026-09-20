import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  isAgentVisibleInChat,
  agentsVisibleInChat,
  RETIRED_LEGACY_AGENT_IDS,
} from '../../../src/web/static/modules/studios/chat.js';

describe('CARD-383 Schema-driven agent visibility & clean filtering', () => {
  it('RETIRED_LEGACY_AGENT_IDS contains expected retired agent keys', () => {
    expect(RETIRED_LEGACY_AGENT_IDS.has('agent-builder')).toBe(true);
    expect(RETIRED_LEGACY_AGENT_IDS.has('coding')).toBe(true);
    expect(RETIRED_LEGACY_AGENT_IDS.has('review')).toBe(true);
    expect(RETIRED_LEGACY_AGENT_IDS.has('conductor')).toBe(true);
    expect(RETIRED_LEGACY_AGENT_IDS.has('hyperv')).toBe(true);
    expect(RETIRED_LEGACY_AGENT_IDS.has('assistant')).toBe(true);
    expect(RETIRED_LEGACY_AGENT_IDS.has('wiki')).toBe(true);
  });

  it('filters out retired agents even if show_in_chat is true', () => {
    expect(isAgentVisibleInChat({ id: 'assistant', show_in_chat: true })).toBe(false);
    expect(isAgentVisibleInChat({ id: 'wiki', show_in_chat: true })).toBe(false);
    expect(isAgentVisibleInChat({ id: 'conductor', show_in_chat: true })).toBe(false);
  });

  it('allows active platform and user-created custom agents without hardcoding', () => {
    const autoreiv = { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true };
    const direct = { id: 'direct', name: 'Direct', show_in_chat: true };
    const customAgent = { id: 'quantum_researcher', name: 'Quantum Researcher', show_in_chat: true };

    expect(isAgentVisibleInChat(autoreiv)).toBe(true);
    expect(isAgentVisibleInChat(direct)).toBe(true);
    expect(isAgentVisibleInChat(customAgent)).toBe(true);

    const visible = agentsVisibleInChat([autoreiv, direct, customAgent]);
    expect(visible.map((a) => a.id)).toEqual(['autoreiv', 'direct', 'quantum_researcher']);
  });

  it('hides system agents other than platform entry channels', () => {
    const hiddenSystemAgent = { id: 'daemon_sync', name: 'Daemon Sync', origin: 'system', show_in_chat: true };
    expect(isAgentVisibleInChat(hiddenSystemAgent)).toBe(false);
  });

  it('negative assertion: chat.js does not contain chained hardcoded string check', () => {
    const chatJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'),
      'utf-8'
    );
    expect(chatJs).not.toContain("agent.id === 'agent-builder' || agent.id === 'coding'");
    expect(chatJs).toContain('RETIRED_LEGACY_AGENT_IDS');
  });
});
