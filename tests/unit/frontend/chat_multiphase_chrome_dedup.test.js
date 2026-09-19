import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  formatMilestoneGoalTitle,
  formatJobChromePhasesRowsHtml,
  renderJobChromePhasesIntoElement,
  createInlineJobChromeModel,
  applyInlineJobChromeModel,
  formatInlineJobChromeHtml,
} from '../../../src/web/static/modules/studios/chat.js';

describe('CARD-378: Multi-Phase Stream Chrome Deduplication & Milestone Goal Clean Header [REQ-CHAT-015]', () => {
  let chatJs;

  beforeEach(() => {
    chatJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'),
      'utf-8',
    );
  });

  describe('formatMilestoneGoalTitle', () => {
    it('returns default fallback "Execution Plan" for missing or empty goal', () => {
      expect(formatMilestoneGoalTitle(null)).toBe('Execution Plan');
      expect(formatMilestoneGoalTitle(undefined)).toBe('Execution Plan');
      expect(formatMilestoneGoalTitle('')).toBe('Execution Plan');
      expect(formatMilestoneGoalTitle('   ')).toBe('Execution Plan');
    });

    it('strips leading attachment tag and extracts meaningful first line', () => {
      const raw = '[Attachment: C:\\Users\\jacob\\AppData\\Local\\Temp\\floorplan.png]\nBuild a 3D floorplan with blender';
      expect(formatMilestoneGoalTitle(raw)).toBe('Build a 3D floorplan with blender');
    });

    it('returns "Execution Plan" if goal consists only of attachment tags', () => {
      const raw = '[Attachment: /path/to/floorplan.png]';
      expect(formatMilestoneGoalTitle(raw)).toBe('Execution Plan');
    });

    it('truncates long goal strings to max 80 characters with an ellipsis', () => {
      const longGoal = 'This is an extremely long user prompt that describes a complicated architectural structure and needs to be truncated so it fits neatly';
      const formatted = formatMilestoneGoalTitle(longGoal, 80);
      expect(formatted.length).toBeLessThanOrEqual(80);
      expect(formatted.endsWith('...')).toBe(true);
      expect(formatted).toBe('This is an extremely long user prompt that describes a complicated architectu...');
    });

    it('preserves short goals under 80 characters without modification', () => {
      const shortGoal = 'Create living room furniture';
      expect(formatMilestoneGoalTitle(shortGoal)).toBe(shortGoal);
    });
  });

  describe('formatJobChromePhasesRowsHtml & renderJobChromePhasesIntoElement', () => {
    it('generates structured phase rows with data-phase-chrome attributes', () => {
      let model = createInlineJobChromeModel();
      model = applyInlineJobChromeModel(model, 'phase_start', {
        phase_name: 'Formulate',
        index: 0,
        phase_count: 2,
      });
      model = applyInlineJobChromeModel(model, 'phase_start', {
        phase_name: 'Execute',
        index: 1,
        phase_count: 2,
      });

      const html = formatJobChromePhasesRowsHtml(model);
      expect(html).toContain('data-phase-chrome="Formulate"');
      expect(html).toContain('data-phase-chrome="Execute"');
      expect(html).toContain('Running...');
    });

    it('renders phase rows directly into a container element and unhides it', () => {
      let model = createInlineJobChromeModel();
      model = applyInlineJobChromeModel(model, 'phase_start', {
        phase_name: 'Formulate',
        index: 0,
        phase_count: 2,
      });

      const mockPhasesEl = {
        innerHTML: '',
        classList: {
          hidden: true,
          remove(cls) { if (cls === 'hidden') this.hidden = false; },
          add(cls) { if (cls === 'hidden') this.hidden = true; },
        },
      };

      const mockBubble = {
        querySelector(selector) {
          if (selector === '.job-chrome-phases' || selector === '[data-job-chrome-phases="1"]') {
            return mockPhasesEl;
          }
          return null;
        },
      };

      renderJobChromePhasesIntoElement(mockBubble, model);
      expect(mockPhasesEl.innerHTML).toContain('data-phase-chrome="Formulate"');
      expect(mockPhasesEl.classList.hidden).toBe(false);
    });

    it('renders truncated goal in formatInlineJobChromeHtml milestone header', () => {
      let model = createInlineJobChromeModel();
      model = applyInlineJobChromeModel(model, 'plan_formulated', {
        goal: 'Short goal',
        steps: [{ title: 'Do work' }],
      });
      const html = formatInlineJobChromeHtml(model);
      expect(html).toContain('Short goal');
      expect(html).toContain('plan-goal-title');
    });
  });

  describe('Single-Bubble Stream Chrome Deduplication in chat.js source', () => {
    it('ensures streamBubble is tagged with data-stream-bubble and data-job-chrome', () => {
      expect(chatJs).toMatch(/streamBubble\.setAttribute\(['"]data-stream-bubble['"],\s*['"]true['"]\)/);
      expect(chatJs).toMatch(/streamBubble\.setAttribute\(['"]data-job-chrome['"],\s*['"]inline['"]\)/);
    });

    it('embeds job-chrome-phases directly within the streamBubble template', () => {
      expect(chatJs).toMatch(/<div class="job-chrome-phases space-y-1\.5 hidden" data-job-chrome-phases="1"><\/div>/);
    });

    it('reuses active stream bubble in ensureInlineJobChromeBubble instead of appending duplicate', () => {
      expect(chatJs).toMatch(
        /const\s+streamBubble\s*=\s*messagesContainer\.querySelector\(['"]\[data-stream-bubble="true"\]['"]\);\s*if\s*\(streamBubble\)\s*return\s+streamBubble;/,
      );
    });

    it('updates streamBubble phase rows directly in paintInlineJobChrome without re-rendering entire bubble', () => {
      expect(chatJs).toMatch(/renderJobChromePhasesIntoElement\(el,\s*inlineJobChromeModel\)/);
    });

    it('uses formatMilestoneGoalTitle in formatInlineJobChromeHtml and plan_formulated handler', () => {
      expect(chatJs).toMatch(/formatMilestoneGoalTitle\(m\.goal\)/);
      expect(chatJs).toMatch(/formatMilestoneGoalTitle\(ev\.goal\)/);
    });
  });
});
