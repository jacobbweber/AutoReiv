/**
 * CARD-527: a built-in tool's friction card says it needs a code change in AutoReiv and offers only Dismiss.
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

const CODE = {
  id: 'rec_code', agent_id: 'autoreiv', skill_path: null, friction_type: 'payload_bloat', remedy_kind: 'code_change',
  tool_name: 'c527_builtin_dump', payload_bytes: 20146, status: 'pending',
  summary: 'Built-in tool c527_builtin_dump needs a code change in AutoReiv (unbounded payload).',
  proposed_patch: 'Built-in tool: c527_builtin_dump needs a code change in AutoReiv (pagination, a limit or a filter).',
};

describe('CARD-527: code_change friction card', () => {
  let list;
  beforeEach(() => {
    list = { innerHTML: '', addEventListener() {} };
    vi.stubGlobal('document', {
      getElementById: (id) => (id === 'frictionRecommendationsList' ? list : null),
      querySelector: () => null, querySelectorAll: () => [], createElement: () => fakeEl(), body: fakeEl(),
    });
  });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('isCodeChangeRemedy matches only code_change', async () => {
    const { isCodeChangeRemedy, isToolEscalationRemedy, CODE_CHANGE } = await import('../../../src/web/static/modules/studios/tool_escalation.js');
    expect(CODE_CHANGE).toBe('code_change');
    expect(isCodeChangeRemedy('code_change')).toBe(true);
    expect(isCodeChangeRemedy('tool_escalation')).toBe(false);
    expect(isToolEscalationRemedy('code_change')).toBe(false);
  });

  it('shows the built-in badge, the note and Dismiss; never Ask Developer or Apply', async () => {
    const { renderFrictionRecommendations } = await import('../../../src/web/static/modules/studios/observability.js');
    renderFrictionRecommendations([CODE]);
    expect(list.innerHTML).toContain('Built-in tool: code change');
    expect(list.innerHTML).toContain('Needs a code change in AutoReiv');
    expect(list.innerHTML).toContain('dismiss-friction-btn');
    expect(list.innerHTML).not.toContain('ask-developer-friction-btn');
    expect(list.innerHTML).not.toContain('apply-friction-btn');
    expect(list.innerHTML).toContain('Tool: c527_builtin_dump');
  });

  it('a dismissed code_change card has no buttons', async () => {
    const { renderFrictionRecommendations } = await import('../../../src/web/static/modules/studios/observability.js');
    renderFrictionRecommendations([{ ...CODE, status: 'dismissed' }]);
    expect(list.innerHTML).toContain('Built-in tool: code change');
    expect(list.innerHTML).not.toContain('<button');
  });
});
