import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-352 In-Situ Skill Workshop: /learn Distillation & Chat Proposal UI', () => {
  const htmlPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const chatJsPath = path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js');
  const renderJsPath = path.resolve(__dirname, '../../../src/web/static/modules/studios/chat/render.js');
  const teachModalJsPath = path.resolve(__dirname, '../../../src/web/static/modules/studios/chat/teach_modal.js');
  const composerJsPath = path.resolve(__dirname, '../../../src/web/static/modules/studios/chat/composer.js');
  const html = fs.readFileSync(htmlPath, 'utf-8');
  const chatJs = fs.readFileSync(chatJsPath, 'utf-8') + fs.readFileSync(renderJsPath, 'utf-8') + fs.readFileSync(teachModalJsPath, 'utf-8') + fs.readFileSync(composerJsPath, 'utf-8');

  describe('Modal Markup in index.html [REQ-SKIL-011]', () => {
    it('contains #teachAgentModal with guidance textarea and action buttons', () => {
      expect(html).toContain('id="teachAgentModal"');
      expect(html).toContain('id="teachAgentTargetAgentBadge"');
      expect(html).toContain('id="teachAgentGuidanceInput"');
      expect(html).toContain('id="submitTeachAgentBtn"');
      expect(html).toContain('id="cancelTeachAgentBtn"');
    });

    it('has bumped cache-buster to at least v=2.0.71', () => {
      expect(html).toMatch(/src="\/static\/app\.js\?v=2\.0\.(7[1-9]|[8-9]\d|\d{3,})"/);
    });
  });

  describe('Chat Studio Logic in chat.js [REQ-SKIL-011, REQ-SKIL-012, REQ-SKIL-014]', () => {
    it('renders msg-teach-agent-btn on assistant message bubbles', () => {
      expect(chatJs).toContain('msg-teach-agent-btn');
      expect(chatJs).toContain('Teach Agent');
      expect(chatJs).toContain('data-message-id');
    });

    it('handles /learn command in chat composer', () => {
      expect(chatJs).toMatch(/\/learn/);
    });

    it('renders .skill-proposal-card with plain summary and accordion preview [REQ-SKIL-012]', () => {
      expect(chatJs).toContain('skill-proposal-card');
      expect(chatJs).toContain('Observed Slip');
      expect(chatJs).toContain('Remedy');
      expect(chatJs).toContain('View Raw Runbook (SKILL.md)');
    });

    it('provides one-click adopt and factory escalation actions [REQ-SKIL-013, REQ-SKIL-014]', () => {
      expect(chatJs).toContain('btn-adopt-skill');
      expect(chatJs).toContain('btn-escalate-developer'); // CARD-496 D10
      expect(chatJs).toContain('btn-dismiss-proposal');
      expect(chatJs).toContain('/api/skills/adopt');
      expect(chatJs).toContain('/api/skills/distill');
    });
  });
});
