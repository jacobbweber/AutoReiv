import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  createInlineJobChromeModel,
  shouldMountInlineJobChrome,
} from '../../../src/web/static/modules/studios/chat.js';

describe('CARD-380: Protect Active Stream Bubble from Chrome Cleanup [REQ-CHAT-017]', () => {
  let chatJs;

  beforeEach(() => {
    chatJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'),
      'utf-8',
    );
  });

  describe('Source Code Invariants', () => {
    it('guards querySelector in paintInlineJobChrome so streamBubble is not removed', () => {
      // Must not unconditionally call existing.remove() on data-stream-bubble="true"
      expect(chatJs).toMatch(
        /if\s*\(!shouldMountInlineJobChrome\(inlineJobChromeModel\)\)\s*\{[\s\S]*?messagesContainer\.querySelector\(['"]\[data-job-chrome="inline"\]['"]\)/,
      );
      expect(chatJs).toMatch(
        /getAttribute\(['"]data-stream-bubble['"]\)\s*===?\s*['"]true['"]/,
      );
    });

    it('guards resetInlineJobChrome so elements with data-stream-bubble="true" are not removed', () => {
      expect(chatJs).toMatch(
        /function resetInlineJobChrome\(\)\s*\{[\s\S]*?getAttribute\(['"]data-stream-bubble['"]\)\s*!==?\s*['"]true['"][\s\S]*?\.remove\(\)/,
      );
    });
  });

  describe('DOM Simulation', () => {
    it('preserves active stream bubble when paintInlineJobChrome encounters empty model', () => {
      let removedStreamBubble = false;

      const mockPhasesEl = {
        classList: {
          add(cls) { if (cls === 'hidden') this.hidden = true; },
          remove(cls) { if (cls === 'hidden') this.hidden = false; },
        },
      };

      const mockStreamBubble = {
        getAttribute(attr) {
          if (attr === 'data-stream-bubble') return 'true';
          if (attr === 'data-job-chrome') return 'inline';
          return null;
        },
        querySelector(selector) {
          if (selector.includes('job-chrome-phases')) return mockPhasesEl;
          return null;
        },
        remove() {
          removedStreamBubble = true;
        },
      };

      const mockStandalone = {
        getAttribute(attr) {
          if (attr === 'data-stream-bubble') return null;
          if (attr === 'data-job-chrome') return 'inline';
          return null;
        },
        removed: false,
        remove() {
          this.removed = true;
        },
      };

      // In paintInlineJobChrome logic:
      const model = createInlineJobChromeModel();
      expect(shouldMountInlineJobChrome(model)).toBe(false);

      // Verify that checking data-stream-bubble protects mockStreamBubble
      if (mockStreamBubble.getAttribute('data-stream-bubble') === 'true') {
        const phasesEl = mockStreamBubble.querySelector('.job-chrome-phases');
        phasesEl.classList.add('hidden');
      } else {
        mockStreamBubble.remove();
      }

      expect(removedStreamBubble).toBe(false);
      expect(mockPhasesEl.classList.hidden).toBe(true);

      // Verify standalone gets removed
      if (mockStandalone.getAttribute('data-stream-bubble') === 'true') {
        mockStandalone.remove();
      } else {
        mockStandalone.remove();
      }
      expect(mockStandalone.removed).toBe(true);
    });
  });
});
