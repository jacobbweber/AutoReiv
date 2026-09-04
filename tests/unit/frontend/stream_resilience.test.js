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

describe('Background Agent Work & Tab Wakeup Recovery [CARD-154, REQ-RESUME-001]', () => {
  it('querySessionStatus fetches active running state from /api/sessions/:id/status', async () => {
    const { querySessionStatus } = await import('../../../src/web/static/modules/studios/chat.js');
    const mockFetch = async (url) => {
      expect(url).toBe('/api/sessions/sess_123/status');
      return {
        ok: true,
        json: async () => ({ session_id: 'sess_123', is_running: true, active_agent: 'autoreiv' }),
      };
    };

    const status = await querySessionStatus('sess_123', mockFetch);
    expect(status.session_id).toBe('sess_123');
    expect(status.is_running).toBe(true);
    expect(status.active_agent).toBe('autoreiv');
  });

  it('querySessionStatus returns finished state when agent has completed turn', async () => {
    const { querySessionStatus } = await import('../../../src/web/static/modules/studios/chat.js');
    const mockFetch = async (url) => {
      expect(url).toBe('/api/sessions/sess_456/status');
      return {
        ok: true,
        json: async () => ({ session_id: 'sess_456', is_running: false, active_agent: null }),
      };
    };

    const status = await querySessionStatus('sess_456', mockFetch);
    expect(status.session_id).toBe('sess_456');
    expect(status.is_running).toBe(false);
    expect(status.active_agent).toBeNull();
  });

  it('querySessionStatus gracefully handles network failures and HTTP errors', async () => {
    const { querySessionStatus } = await import('../../../src/web/static/modules/studios/chat.js');
    const mockFailingFetch = async () => {
      throw new Error('Network disconnect');
    };

    const status = await querySessionStatus('sess_fail', mockFailingFetch);
    expect(status.session_id).toBe('sess_fail');
    expect(status.is_running).toBe(false);

    const mockHttp500 = async () => ({ ok: false, status: 500 });
    const status500 = await querySessionStatus('sess_500', mockHttp500);
    expect(status500.session_id).toBe('sess_500');
    expect(status500.is_running).toBe(false);
  });

  it('querySessionStatus returns default when sessionId is empty', async () => {
    const { querySessionStatus } = await import('../../../src/web/static/modules/studios/chat.js');
    const status = await querySessionStatus(null);
    expect(status.is_running).toBe(false);
    expect(status.active_agent).toBeNull();
  });
});

