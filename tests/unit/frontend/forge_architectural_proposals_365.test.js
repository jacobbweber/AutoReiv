/**
 * CARD-365: Architectural Proposal Inbox in Agent Forge Studio & Observability Cross-Linking
 * [REQ-ARCH-013, REQ-ARCH-014]
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';
import { renderProposalBadgeHtml, renderProposalCardHtml } from '../../../src/web/static/modules/studios/forge.js';

const repoRoot = path.resolve(__dirname, '../../..');

function read(rel) {
  return fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
}

describe('CARD-365: Architectural Proposal Inbox UI', () => {
  it('index.html renders forgeArchitecturalSection with scan, refresh, and list containers', () => {
    const html = read('src/web/templates/index.html');
    expect(html).toContain('id="forgeArchitecturalSection"');
    expect(html).toContain('id="forgeProposalCountBadge"');
    expect(html).toContain('id="forgeProposalScanBtn"');
    expect(html).toContain('id="forgeProposalRefreshBtn"');
    expect(html).toContain('id="forgeProposalsList"');
    expect(html).toContain('id="obsArchitecturalInboxBtn"');
  });

  it('renderProposalBadgeHtml returns distinct styled badges for proposal categories', () => {
    const routineBadge = renderProposalBadgeHtml('promotion_routine');
    expect(routineBadge).toContain('ROUTINE PROMOTION');

    const toolBadge = renderProposalBadgeHtml('tool_pruning');
    expect(toolBadge).toContain('TOOL PRUNING');

    const contractBadge = renderProposalBadgeHtml('contract_reinforcement');
    expect(contractBadge).toContain('CONTRACT REINFORCEMENT');

    const secBadge = renderProposalBadgeHtml('security_isolation');
    expect(secBadge).toContain('SECURITY ISOLATION');

    const decompBadge = renderProposalBadgeHtml('skill_decomposition');
    expect(decompBadge).toContain('SKILL DECOMPOSITION');
  });

  it('renderProposalCardHtml outputs action buttons and formatted payload remedy details', () => {
    const proposal = {
      id: 'prop-unit-1',
      proposal_type: 'promotion_routine',
      title: 'Promote Polling to Routine',
      description: 'Long polling turns detected.',
      agent_id: 'sre-agent',
      impact_summary: 'Saves 12,000 prompt tokens.',
      action_payload: {
        routine_name: 'SRE Periodic Poller',
        schedule_type: 'interval',
        interval_seconds: 3600,
        approval_mode: 'ask',
      },
    };

    const cardHtml = renderProposalCardHtml(proposal);
    expect(cardHtml).toContain('data-proposal-id="prop-unit-1"');
    expect(cardHtml).toContain('data-proposal-action="apply"');
    expect(cardHtml).toContain('data-proposal-action="dismiss"');
    expect(cardHtml).toContain('Promote Polling to Routine');
    expect(cardHtml).toContain('SRE Periodic Poller');
    expect(cardHtml).toContain('Autonomic Impact:');
    expect(cardHtml).toContain('Saves 12,000 prompt tokens.');
  });
});
