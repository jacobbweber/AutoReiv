/**
 * CARD-629: friction recommendation header puts summary on its own full-width line; badges do not wrap.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

function fakeEl() {
  return {
    innerHTML: '', className: '', id: '', dataset: {}, children: [],
    classList: { add() {}, remove() {}, contains: () => false },
    setAttribute() {}, getAttribute: () => null, addEventListener() {},
    querySelector: () => null, querySelectorAll: () => [],
    appendChild(c) { this.children.push(c); return c; },
  };
}

const LONG = 'This is a long friction summary that must not squeeze into a ninety-pixel column on a phone.';

const RECS = [
  {
    id: 'rec_patch', agent_id: 'autoreiv', skill_path: 'skills/wiki/SKILL.md', friction_type: 'search_thrashing',
    remedy_kind: 'runbook_patch', tool_name: 'wiki_note_search', status: 'pending',
    summary: LONG, proposed_patch: '- limit 10', created_at: '2026-10-04T12:00:00Z',
  },
  {
    id: 'rec_tool', agent_id: 'autoreiv', skill_path: null, friction_type: 'payload_bloat',
    remedy_kind: 'tool_escalation', tool_name: 'get_dump', payload_bytes: 20000, status: 'pending',
    summary: LONG, proposed_patch: 'Ask Developer to add pagination.', created_at: '2026-10-04T12:00:00Z',
  },
  {
    id: 'rec_code', agent_id: 'autoreiv', skill_path: null, friction_type: 'payload_bloat',
    remedy_kind: 'code_change', tool_name: 'builtin_dump', status: 'pending',
    summary: LONG, proposed_patch: 'Built-in tool needs a code change.', created_at: '2026-10-04T12:00:00Z',
  },
];

describe('CARD-629 friction phone header', () => {
  let list;
  beforeEach(() => {
    list = { innerHTML: '', addEventListener() {} };
    vi.stubGlobal('document', {
      getElementById: (id) => (id === 'frictionRecommendationsList' ? list : null),
      querySelector: () => null, querySelectorAll: () => [], createElement: () => fakeEl(), body: fakeEl(),
    });
  });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('puts summary on basis-full and badges on whitespace-nowrap for every remedy kind', async () => {
    const { renderFrictionRecommendations } = await import('../../../src/web/static/modules/studios/observability.js');
    renderFrictionRecommendations(RECS);
    expect(list.innerHTML).toContain('friction-rec-summary');
    expect(list.innerHTML).toContain('basis-full');
    const summaries = (list.innerHTML.match(/friction-rec-summary/g) || []).length;
    expect(summaries).toBe(3);
    expect(list.innerHTML).toContain('whitespace-nowrap');
    expect(list.innerHTML).toContain('Built-in tool: code change');
    expect(list.innerHTML).toContain('Needs a tool');
    expect(list.innerHTML).toContain('Runbook SOP Patch');
    expect(list.innerHTML).toMatch(/whitespace-nowrap[\s\S]*friction-rec-summary/);
  });
});
