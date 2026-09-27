/**
 * CARD-539 (ADR-0061): Agent Studio saves skill ticks only and shows pending attach proposals.
 */

import { describe, it, expect, vi } from 'vitest';
import fs from 'fs';
import path from 'path';
import {
  ATTACH_TOOL_PROPOSAL,
  loadPendingProposals,
  renderPendingProposalsHtml,
} from '../../../src/web/static/modules/studios/forge/pending_proposals.js';
import { pillsFromPersistedAgent } from '../../../src/web/static/modules/studios/forge/skill_pills.js';

const repoRoot = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(repoRoot, rel), 'utf-8');

const proposal = {
  id: 'appr_1',
  tool_name: ATTACH_TOOL_PROPOSAL,
  agent_id: 'autoreiv',
  arguments: { tool: 'get_weather', skill_id: 'get-weather', new_skill: true, description: 'Weather for a city' },
};

describe('Studio Save sends skills only [CARD-539]', () => {
  it('drops tool lists and the wiki flag and sends the skills version', () => {
    const forgeJs = read('src/web/static/modules/studios/forge.js');
    expect(forgeJs).not.toMatch(/allowed_tool_names\s*:/);
    expect(forgeJs).not.toMatch(/pack_tool_names\s*:/);
    expect(forgeJs).not.toMatch(/allow_wiki_access\s*:/);
    expect(forgeJs).toContain('expected_skills_version');
  });

  it('pills ignore the retired allow_wiki_access flag (D3)', () => {
    expect(pillsFromPersistedAgent({ allowed_skill: ['wiki'], allow_wiki_access: false })).toContain('wiki');
  });
});

describe('Pending proposals in Agent Studio [CARD-539]', () => {
  it('renders only attach proposals with Accept and Reject', () => {
    const html = renderPendingProposalsHtml([proposal, { id: 'x', tool_name: 'cli_exec', arguments: {} }]);
    expect(html).toContain('Pending proposals (1)');
    expect(html).toContain('get_weather');
    expect(html).toContain('data-attach-decision="APPROVED"');
    expect(html).toContain('data-attach-decision="REJECTED"');
    expect(renderPendingProposalsHtml([])).toBe('');
  });

  it('loads the agent pending list into the host', async () => {
    const fetchImpl = vi.fn(async () => ({ ok: true, json: async () => [proposal] }));
    const host = { innerHTML: '', classList: { toggle: vi.fn() }, querySelectorAll: () => [] };
    const rows = await loadPendingProposals('autoreiv', host, { fetchImpl });
    expect(fetchImpl).toHaveBeenCalledWith('/api/approvals/pending?agent_id=autoreiv');
    expect(rows).toHaveLength(1);
    expect(host.innerHTML).toContain('get-weather');
    expect(host.classList.toggle).toHaveBeenCalledWith('hidden', false);
  });
});
