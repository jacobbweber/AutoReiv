import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  createInlineJobChromeModel,
  applyInlineJobChromeModel,
  shouldMountInlineJobChrome,
} from '../../../src/web/static/modules/studios/chat.js';

describe('CARD-360: Prevent duplicate streaming tile in Chat Studio', () => {
  let chatJs;

  beforeEach(() => {
    chatJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'),
      'utf-8',
    );
  });

  describe('[REQ-CHAT-CHROME-001] shouldMountInlineJobChrome predicate', () => {
    it('returns false for null or undefined models', () => {
      expect(shouldMountInlineJobChrome(null)).toBe(false);
      expect(shouldMountInlineJobChrome(undefined)).toBe(false);
    });

    it('returns false for an empty initial inline job chrome model', () => {
      const model = createInlineJobChromeModel();
      expect(shouldMountInlineJobChrome(model)).toBe(false);
    });

    it('returns false when ambient react_state (e.g. THINKING) event is applied', () => {
      let model = createInlineJobChromeModel();
      model = applyInlineJobChromeModel(model, 'react_state', {
        react_state: 'THINKING',
        assigned_agent_id: 'developer',
      });
      expect(shouldMountInlineJobChrome(model)).toBe(false);
    });

    it('returns false when job_created event has 0 phases', () => {
      let model = createInlineJobChromeModel();
      model = applyInlineJobChromeModel(model, 'job_created', {
        job_id: 'job_single_turn',
        phase_count: 0,
      });
      expect(shouldMountInlineJobChrome(model)).toBe(false);
    });

    it('[REQ-CHAT-CHROME-002] returns true when phases exist', () => {
      let model = createInlineJobChromeModel();
      model = applyInlineJobChromeModel(model, 'phase_start', {
        phase_name: 'Formulate',
        index: 0,
        phase_count: 2,
      });
      expect(shouldMountInlineJobChrome(model)).toBe(true);
    });

    it('[REQ-CHAT-CHROME-002] returns true when plan steps exist', () => {
      let model = createInlineJobChromeModel();
      model = applyInlineJobChromeModel(model, 'plan_formulated', {
        goal: 'Multi-step task',
        steps: [{ title: 'Step 1' }, { title: 'Step 2' }],
      });
      expect(shouldMountInlineJobChrome(model)).toBe(true);
    });

    it('[REQ-CHAT-CHROME-002] returns true when job_created event specifies 2 or more phases', () => {
      let model = createInlineJobChromeModel();
      model = applyInlineJobChromeModel(model, 'job_created', {
        job_id: 'job_multi_1',
        phase_count: 2,
      });
      expect(shouldMountInlineJobChrome(model)).toBe(true);
    });
  });

  describe('[REQ-CHAT-CHROME-003] paintInlineJobChrome lifecycle guard in chat.js source', () => {
    it('guards paintInlineJobChrome with shouldMountInlineJobChrome before ensuring bubble', () => {
      expect(chatJs).toMatch(/shouldMountInlineJobChrome/);
      expect(chatJs).toMatch(
        /function paintInlineJobChrome\(\)\s*\{[\s\S]*?shouldMountInlineJobChrome\(inlineJobChromeModel\)[\s\S]*?ensureInlineJobChromeBubble\(\)/,
      );
    });

    it('cleans up any existing empty inline chrome bubble if phases and steps are empty', () => {
      expect(chatJs).toMatch(
        /if\s*\(!shouldMountInlineJobChrome\(inlineJobChromeModel\)\)\s*\{[\s\S]*?messagesContainer\.querySelector\(['"]\[data-job-chrome="inline"\]['"]\)/,
      );
    });
  });
});
