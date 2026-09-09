/**
 * Unit tests for Quick-Scaffold Modal and Post-Creation Handoff Card [REQ-FACT-047, REQ-FACT-048].
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import { renderAgentHandoffCardHtml } from '../../../src/web/static/modules/studios/chat.js';
import { buildQuickScaffoldPayload } from '../../../src/web/static/modules/studios/forge.js';

const repoRoot = path.resolve(__dirname, '../../..');

function readIndexHtml() {
  return fs.readFileSync(path.join(repoRoot, 'src/web/templates/index.html'), 'utf-8');
}

describe('Quick Scaffold Modal Contract [REQ-FACT-047]', () => {
  it('index.html contains #forgeNewAgentModal and required input elements', () => {
    const html = readIndexHtml();
    expect(html).toContain('id="forgeNewAgentModal"');
    expect(html).toContain('id="forgeNewAgentIdInput"');
    expect(html).toContain('id="forgeNewAgentNameInput"');
    expect(html).toContain('id="forgeNewAgentDescInput"');
    expect(html).toContain('id="forgeNewAgentRoleInput"');
    expect(html).toContain('id="forgeNewAgentAvatarSelect"');
    expect(html).toContain('id="forgeNewAgentToneSelect"');
    expect(html).toContain('id="forgeNewAgentPurposeSelect"');
    expect(html).toContain('id="forgeNewAgentSubmitBtn"');
    expect(html).toContain('id="forgeNewAgentCancelBtn"');
    expect(html).toContain('id="forgeNewAgentCloseBtn"');
  });

  it('buildQuickScaffoldPayload constructs structured pack manifest with gold-standard sections', () => {
    const payload = buildQuickScaffoldPayload({
      id: 'k8s-specialist',
      name: 'Kubernetes Specialist',
      description: 'Manages clusters and pods',
      role: 'Kubernetes SRE',
      avatar: 'terminal',
      tone: 'analytical',
      purpose: 'execution',
    });

    expect(payload.id).toBe('k8s-specialist');
    expect(payload.name).toBe('Kubernetes Specialist');
    expect(payload.description).toBe('Manages clusters and pods');
    expect(payload.system_prompt).toContain('[IDENTITY & ROLE]');
    expect(payload.system_prompt).toContain('[DOMAIN BOUNDARIES & REFUSALS]');
    expect(payload.system_prompt).toContain('[EXECUTION PROTOCOL]');
    expect(payload.system_prompt).toContain('[SAFETY & APPROVALS]');
    expect(payload.system_prompt).toContain('[TOOL USAGE RULES]');
    expect(payload.system_prompt).toContain('[OUTPUT FORMAT]');
    expect(payload.skills).toBeInstanceOf(Array);
    expect(payload.skills.length).toBeGreaterThanOrEqual(1);
  });
});

describe('Post-Creation Handoff Card [REQ-FACT-048]', () => {
  it('renderAgentHandoffCardHtml generates interactive handoff card with Factory and Studio action buttons', () => {
    const cardHtml = renderAgentHandoffCardHtml({
      agentId: 'ansible-ops',
      agentName: 'Ansible Automation Lead',
      folder: 'packs/ansible-ops',
    });

    expect(cardHtml).toContain('Ansible Automation Lead');
    expect(cardHtml).toContain('packs/ansible-ops');
    expect(cardHtml).toContain('data-action="launch-factory"');
    expect(cardHtml).toContain('data-agent-id="ansible-ops"');
    expect(cardHtml).toContain('Launch Training in Factory');
    expect(cardHtml).toContain('data-action="open-studio"');
    expect(cardHtml).toContain('Open in Studio');
  });
});
