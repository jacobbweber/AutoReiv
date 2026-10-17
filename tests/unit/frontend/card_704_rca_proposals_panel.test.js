import { describe, expect, it } from 'vitest';
import { renderRcaProposalsHtml } from '../../../src/web/static/modules/studios/rca_proposals_panel.js';

describe('CARD-704 Staged RCA Self-Healing Proposals renderer', () => {
  it('returns empty string when no proposals are staged', () => {
    expect(renderRcaProposalsHtml([])).toBe('');
  });

  it('renders structured RCA proposal card with Repair in Chat and Dismiss actions', () => {
    const html = renderRcaProposalsHtml([
      {
        id: 'rca:tool:divide_metric',
        kind: 'tool',
        target_name: 'divide_metric',
        skill_id: 'rca-math-skill',
        file_path: 'tools/divide_metric.py',
        severity: 'high',
        failure_count: 2,
        latest_error: 'ZeroDivisionError: division by zero',
        trace_ids: ['trace-rca-102', 'trace-rca-101'],
        suggested_remediation: 'Inspect trace trace-rca-102 and update tools/divide_metric.py.',
      },
    ]);

    expect(html).toContain('data-testid="rca-proposal-card"');
    expect(html).toContain('data-proposal-id="rca:tool:divide_metric"');
    expect(html).toContain('rca-math-skill/tools/divide_metric.py');
    expect(html).toContain('2 failures');
    expect(html).toContain('trace: trace-rca-102');
    expect(html).toContain('ZeroDivisionError: division by zero');
    expect(html).toContain('data-rca-repair="rca:tool:divide_metric"');
    expect(html).toContain('data-rca-dismiss="rca:tool:divide_metric"');
    expect(html).toContain('Repair in Chat');
  });
});
