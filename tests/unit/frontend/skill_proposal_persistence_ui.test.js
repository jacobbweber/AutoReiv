import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-358 Persistent Skill Proposal Cards in Chat History [REQ-SKIL-015, REQ-SKIL-016]', () => {
  const htmlPath = path.resolve(__dirname, '../../../src/web/templates/index.html');
  const chatJsPath = path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js');
  const renderJsPath = path.resolve(__dirname, '../../../src/web/static/modules/studios/chat/render.js');
  const html = fs.readFileSync(htmlPath, 'utf-8');
  const chatJs = fs.readFileSync(chatJsPath, 'utf-8') + fs.readFileSync(renderJsPath, 'utf-8');

  it('has bumped frontend cache-buster to at least v=2.0.72 [REQ-SKIL-016]', () => {
    expect(html).toMatch(/src="\/static\/app\.js\?v=2\.0\.(7[2-9]|[8-9]\d|\d{3,})"/);
  });

  describe('Chat Studio Proposal Message Hydration [REQ-SKIL-016]', () => {
    it('handles role === "skill_proposal" in renderMessageItem', () => {
      expect(chatJs).toMatch(/role\s*===?\s*['"]skill_proposal['"]/);
    });

    it('attaches data-message-id to .skill-proposal-card elements', () => {
      expect(chatJs).toContain('el.dataset.messageId');
    });

    it('renders adopted state receipt when proposal adoption_state is adopted', () => {
      expect(chatJs).toMatch(/adoption_state\s*===?\s*['"]adopted['"]/);
      expect(chatJs).toContain('Skill mounted to');
    });

    it('passes message_id in adopt request payload to persist adoption state', () => {
      expect(chatJs).toMatch(/message_id:\s*messageId/);
    });
  });
});
