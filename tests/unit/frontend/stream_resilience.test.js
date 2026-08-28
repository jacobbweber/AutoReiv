/**
 * Frontend Unit Tests for Stream Resilience and JSON Fallback Formatting [REQ-MOB-STREAM-002, REQ-MOB-STREAM-004].
 */

import { describe, it, expect } from 'vitest';
import { formatJsonDeliverableToMarkdown } from '../../../src/web/static/modules/utils/formatters.js';

describe('Stream Resilience & JSON Fallback Formatting [REQ-MOB-STREAM-004]', () => {
  it('converts raw JSON deliverable with goal and action plan into formatted markdown', () => {
    const rawJson = JSON.stringify({
      goal: 'Review wiki and plan weekly notes',
      status: 'completed',
      wiki_inventory_summary: {
        active_weekly_notes: 1,
        template: 'templates/weekly.md',
        key_gaps: ['Missing tags', 'No template prompts'],
      },
      action_plan: {
        title: 'Weekly Notes 3-Step Action Plan',
        steps: [
          { step_number: 1, title: 'Standardize template', objective: 'Create template file' },
          { step_number: 2, title: 'Daily review ritual', objective: 'Log daily tasks' },
        ],
      },
    });

    const md = formatJsonDeliverableToMarkdown(rawJson);
    expect(md).toContain('Goal: Review wiki and plan weekly notes');
    expect(md).toContain('Inventory Summary');
    expect(md).toContain('templates/weekly.md');
    expect(md).toContain('Action Plan: Weekly Notes 3-Step Action Plan');
    expect(md).toContain('**Step 1: Standardize template**');
    expect(md).toContain('**Step 2: Daily review ritual**');
  });

  it('leaves standard markdown untouched', () => {
    const standardMd = '# Standard Heading\n\n- Bullet 1\n- Bullet 2';
    expect(formatJsonDeliverableToMarkdown(standardMd)).toBe(standardMd);
  });

  it('handles invalid JSON gracefully by returning original string', () => {
    const broken = '{ "groap": "unclosed json';
    expect(formatJsonDeliverableToMarkdown(broken)).toBe(broken);
  });
});
