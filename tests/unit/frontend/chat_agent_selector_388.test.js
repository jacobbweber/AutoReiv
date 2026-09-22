/**
 * CARD-388: Restore Developer and Tutor as Unified Agent Packs.
 * Tests Chat Studio agent selector pills, visibility, and switching [REQ-388-002, REQ-388-003, REQ-388-005].
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  isAgentVisibleInChat,
  agentsVisibleInChat,
} from '../../../src/web/static/modules/studios/chat.js';

describe('CARD-388 Chat Studio Agent Selector & Restoration', () => {
  const indexHtml = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8'
  );
  const chatJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'),
    'utf-8'
  );

  it('index.html provides dropdown agent selector matching Agent Studio [REQ-388-003]', () => {
    expect(indexHtml).toContain('id="chatEngineSelector"');
    expect(indexHtml).toContain('id="agentSelect"');
    expect(indexHtml).toMatch(/<select\s+id="agentSelect"[^>]*class="[^"]*min-w-\[150px\]/);
    expect(indexHtml).not.toContain('id="engineBtnCore"');
    expect(indexHtml).not.toContain('id="engineBtnDeveloper"');
    expect(indexHtml).not.toContain('id="engineBtnTutor"');
    expect(indexHtml).not.toContain('id="engineBtnDirect"');
  });

  it('allows Developer and Tutor in isAgentVisibleInChat [REQ-388-002]', () => {
    const dev = { id: 'developer', name: 'Developer', show_in_chat: true };
    const tutor = { id: 'tutor', name: 'Tutor', show_in_chat: true };
    const devPack = { id: 'developer', name: 'Developer', origin: 'pack', show_in_chat: true };
    const tutorPack = { id: 'tutor', name: 'Tutor', origin: 'pack', show_in_chat: true };

    expect(isAgentVisibleInChat(dev)).toBe(true);
    expect(isAgentVisibleInChat(tutor)).toBe(true);
    expect(isAgentVisibleInChat(devPack)).toBe(true);
    expect(isAgentVisibleInChat(tutorPack)).toBe(true);

    const agents = [
      { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
      { id: 'developer', name: 'Developer', show_in_chat: true },
      { id: 'tutor', name: 'Tutor', show_in_chat: true },
      { id: 'direct', name: 'Direct', show_in_chat: true },
      { id: 'wiki', name: 'Wiki', show_in_chat: true },
      { id: 'conductor', name: 'Conductor', show_in_chat: true },
    ];

    const visible = agentsVisibleInChat(agents);
    expect(visible.map((a) => a.id)).toEqual(['autoreiv', 'developer', 'tutor', 'direct']);
  });

  it('chat.js populates agentSelect dropdown cleanly and handles agent switching [REQ-388-003, REQ-388-005, CARD-410]', () => {
    const pickerJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/agent_picker.js'),
      'utf-8'
    );
    expect(pickerJs).toMatch(/agentsVisibleInChat\(list\)/);
    expect(pickerJs).toMatch(/formatAgentSelectOption/);
    expect(pickerJs).toContain("getElementById('agentSelect')");
    expect(pickerJs).not.toMatch(/dualEngineAgentsVisibleInChat/);
    expect(chatJs).toMatch(/publishAgentsLoaded\(/);
    expect(chatJs).toMatch(/agentSelect\.addEventListener\('change'/);
    expect(chatJs).not.toMatch(/agentSelect\.innerHTML/);
    expect(chatJs).not.toMatch(/renderEngineSelectorPills/);
    expect(chatJs).not.toMatch(/dualEngineAgentsVisibleInChat\(state\.agents\)/);
  });
});
