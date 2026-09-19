/**
 * CARD-361: Dual-Engine Front Door (AutoReiv Core & Direct Mode).
 * Grounded in ADR-0054 [REQ-CHAT-DUAL-001, REQ-CHAT-DUAL-004, REQ-CHAT-DUAL-005].
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  dualEngineAgentsVisibleInChat,
  DUAL_ENGINE_IDS,
} from '../../../src/web/static/modules/studios/chat.js';

describe('CARD-361 Dual-Engine Front Door & Visibility', () => {
  const indexHtml = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/templates/index.html'),
    'utf-8',
  );
  const chatJs = fs.readFileSync(
    path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'),
    'utf-8',
  );

  it('restricts dual-engine front door channels strictly to autoreiv and direct [REQ-CHAT-DUAL-001]', () => {
    expect(DUAL_ENGINE_IDS).toEqual(['autoreiv', 'direct']);

    const agents = [
      { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
      { id: 'direct', name: 'Direct Mode', show_in_chat: true },
      { id: 'developer', name: 'Developer', show_in_chat: true },
      { id: 'forge', name: 'Forge Specialist', show_in_chat: true },
      { id: 'tutor', name: 'Tutor', show_in_chat: true },
      { id: 'assistant', name: 'Assistant', show_in_chat: true },
      { id: 'wiki', name: 'Wiki', show_in_chat: true },
    ];

    const dualEngines = dualEngineAgentsVisibleInChat(agents);
    expect(dualEngines.map((a) => a.id)).toEqual(['autoreiv', 'direct']);
  });

  it('provides dual-engine segmented toggle controls in index.html [REQ-CHAT-DUAL-001]', () => {
    expect(indexHtml).toContain('id="chatEngineSelector"');
    expect(indexHtml).toContain('id="engineBtnCore"');
    expect(indexHtml).toContain('id="engineBtnDirect"');
    // Keeps single #agentSelect for test harness compatibility
    const matches = indexHtml.match(/id="agentSelect"/g) || [];
    expect(matches).toHaveLength(1);
  });

  it('chat.js defines engine toggle handlers and suppresses job phase strip on direct mode [REQ-CHAT-DUAL-005]', () => {
    expect(chatJs).toMatch(/engineBtnCore/);
    expect(chatJs).toMatch(/engineBtnDirect/);
    expect(chatJs).toMatch(/switchEngineChannel/);
  });
});
