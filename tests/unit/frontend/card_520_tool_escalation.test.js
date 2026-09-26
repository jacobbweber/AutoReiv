/**
 * CARD-520: tool_escalation rename, Observability Ask Developer (real send), truthful Apply, top-level sections.
 * Node env with a tiny fake DOM (no jsdom in this repo).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

const repoRoot = path.resolve(__dirname, '../../..');
const STATIC = 'src/web/static/modules/studios';
const read = (rel) => fs.readFileSync(path.join(repoRoot, rel), 'utf-8');
const OLD = 'factory' + '_escalation';

function fakeList() {
  return { innerHTML: '', addEventListener() {} };
}
function fakeEl() {
  return {
    innerHTML: '', className: '', id: '', dataset: {}, children: [],
    classList: { add() {}, remove() {}, contains: () => false },
    setAttribute() {}, getAttribute: () => null, addEventListener() {},
    querySelector: () => null, querySelectorAll: () => [],
    appendChild(c) { this.children.push(c); return c; },
  };
}
function withDocument(els) {
  vi.stubGlobal('document', {
    getElementById: (id) => els[id] || null,
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: () => fakeEl(),
    body: fakeEl(),
  });
}
const json = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const flush = () => new Promise((r) => setTimeout(r, 0));

const ESC = {
  id: 'rec_esc', agent_id: 'autoreiv', skill_path: null, friction_type: 'payload_bloat', remedy_kind: 'tool_escalation',
  tool_name: 'c520_inventory_dump', payload_bytes: 20790, session_id: 'sess_c520',
  summary: 'c520_inventory_dump needs pagination or a filter (unbounded payload).',
  proposed_patch: 'Ask Developer to add pagination or a filter to c520_inventory_dump: it returned 20790 bytes (limit 8 KB).', status: 'pending',
};
const PATCH = { ...ESC, id: 'rec_patch', remedy_kind: 'runbook_patch', tool_name: 'wiki_note_search', skill_path: 'skills/wiki/SKILL.md', summary: 'Enforce pagination', proposed_patch: '- limit 10' };

describe('REQ-520-006: Teach card uses data-tool-escalation, with a fallback for old cards', () => {
  afterEach(() => { vi.unstubAllGlobals(); });

  it('render.js writes data-tool-escalation from tool_escalation', async () => {
    withDocument({});
    const { renderSkillProposalCard } = await import('../../../src/web/static/modules/studios/chat/render.js');
    const container = { appendChild() {}, querySelector: () => null, scrollTop: 0, scrollHeight: 0 };
    const el = renderSkillProposalCard({
      status: 'ok', needs_tool: true, target_agent_id: 'autoreiv', plain_summary: { observed_slip: 'a', remedy: 'b' },
      tool_escalation: { suggested_tool_name: 'get_city_weather', seed_intent: 'weather' },
    }, { container });
    expect(el.innerHTML).toContain('data-tool-escalation=');
    expect(el.innerHTML).toContain('get_city_weather');
    expect(el.innerHTML).not.toContain('data-factory-escalation');
  });

  it('readToolEscalation reads the new key, then the old key', async () => {
    const { readToolEscalation, escalationFromCard } = await import('../../../src/web/static/modules/studios/tool_escalation.js');
    expect(readToolEscalation({ tool_escalation: { seed_intent: 'n' } }).seed_intent).toBe('n');
    expect(readToolEscalation({ [OLD]: { seed_intent: 'o' } }).seed_intent).toBe('o');
    expect(readToolEscalation({})).toEqual({});
    const attrs = { ['data-' + 'factory-escalation']: JSON.stringify({ suggested_tool_name: 'old_tool' }) };
    const oldCard = { getAttribute: (k) => attrs[k] ?? null };
    expect(escalationFromCard(oldCard).suggested_tool_name).toBe('old_tool');
    const newCard = { getAttribute: (k) => (k === 'data-tool-escalation' ? JSON.stringify({ suggested_tool_name: 'new_tool' }) : null) };
    expect(escalationFromCard(newCard).suggested_tool_name).toBe('new_tool');
  });
});

describe('REQ-520-007/009: Observability friction cards', () => {
  let list;
  beforeEach(() => { list = fakeList(); withDocument({ frictionRecommendationsList: list }); });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('a tool escalation (new or old name) shows Needs a tool, Ask Developer and Dismiss, never Apply', async () => {
    const { renderFrictionRecommendations } = await import('../../../src/web/static/modules/studios/observability.js');
    for (const kind of ['tool_escalation', OLD]) {
      renderFrictionRecommendations([{ ...ESC, remedy_kind: kind }]);
      expect(list.innerHTML).toContain('Needs a tool');
      expect(list.innerHTML).toContain('ask-developer-friction-btn');
      expect(list.innerHTML).toContain('dismiss-friction-btn');
      expect(list.innerHTML).not.toContain('apply-friction-btn');
      expect(list.innerHTML).not.toContain('Factory');
    }
  });

  it('a runbook patch keeps Apply Patch and Dismiss', async () => {
    const { renderFrictionRecommendations } = await import('../../../src/web/static/modules/studios/observability.js');
    renderFrictionRecommendations([PATCH]);
    expect(list.innerHTML).toContain('apply-friction-btn');
    expect(list.innerHTML).not.toContain('ask-developer-friction-btn');
  });

  it('an escalated card shows Asked Developer and no buttons', async () => {
    const { renderFrictionRecommendations } = await import('../../../src/web/static/modules/studios/observability.js');
    renderFrictionRecommendations([{ ...ESC, status: 'escalated', developer_session_id: 'dev1' }]);
    expect(list.innerHTML).toContain('Asked Developer');
    expect(list.innerHTML).not.toContain('<button');
  });
});

describe('REQ-520-008/009/010: Ask Developer and Apply handlers', () => {
  let list;
  beforeEach(() => { list = fakeList(); withDocument({ frictionRecommendationsList: list, toastContainer: null }); });
  afterEach(() => { vi.unstubAllGlobals(); });

  function clickOn(cls, recId) {
    const btn = { dataset: { recId }, disabled: false };
    return { btn, ev: { target: { closest: (sel) => (sel === `.${cls}` ? btn : null) } } };
  }

  it('Ask Developer posts talk (modify + draft), opens the Developer chat once, then marks the card escalated', async () => {
    const obs = await import('../../../src/web/static/modules/studios/observability.js');
    obs.renderFrictionRecommendations([ESC]);
    const calls = [];
    const fetchFn = vi.fn(async (url, init = {}) => {
      calls.push([url, init.body ? JSON.parse(init.body) : null]);
      if (url.endsWith('/authoring/talk')) {
        const b = JSON.parse(init.body);
        return json(200, { session_id: 'dev-520', agent_id: 'developer', opened_job: false, job_id: null, prompt: `Modify ${b.draft.tool_name}: ${b.draft.behavior}` });
      }
      if (url.endsWith('/escalate')) return json(200, { success: true });
      return json(200, []);
    });
    vi.stubGlobal('fetch', fetchFn);
    const openDeveloperSession = vi.fn(async () => 'dev-520');
    const switchTab = vi.fn();
    const callbacks = { switchTab, getChatCtrl: () => ({ openDeveloperSession }) };
    const { btn, ev } = clickOn('ask-developer-friction-btn', 'rec_esc');
    const first = obs.handleFrictionAction(ev, callbacks);
    const second = obs.handleFrictionAction(ev, callbacks); // double click
    await first; await second; await flush();
    const talks = calls.filter(([u]) => u.endsWith('/authoring/talk'));
    expect(talks).toHaveLength(1);
    expect(talks[0][1].intent).toBe('modify');
    expect(talks[0][1].draft.tool_name).toBe('c520_inventory_dump');
    expect(talks[0][1].draft.behavior).toContain('20790 bytes');
    expect(talks[0][1].draft.behavior).toContain('8 KB');
    expect(switchTab).toHaveBeenCalledWith('chat');
    expect(openDeveloperSession).toHaveBeenCalledTimes(1);
    expect(openDeveloperSession).toHaveBeenCalledWith('dev-520', expect.stringContaining('c520_inventory_dump'));
    const esc = calls.find(([u]) => u.endsWith('/recommendations/rec_esc/escalate'));
    expect(esc && esc[1]).toEqual({ developer_session_id: 'dev-520' });
    expect(btn.disabled).toBe(true);
  });

  it('if talk fails, it toasts why and the card stays pending (no escalate)', async () => {
    const obs = await import('../../../src/web/static/modules/studios/observability.js');
    obs.renderFrictionRecommendations([ESC]);
    const fetchFn = vi.fn(async (url) => (url.endsWith('/authoring/talk') ? json(503, { detail: 'Developer agent is unavailable.' }) : json(200, [])));
    vi.stubGlobal('fetch', fetchFn);
    const { btn, ev } = clickOn('ask-developer-friction-btn', 'rec_esc');
    await obs.handleFrictionAction(ev, { switchTab() {}, getChatCtrl: () => ({ openDeveloperSession: vi.fn() }) });
    expect(fetchFn.mock.calls.some(([u]) => String(u).endsWith('/escalate'))).toBe(false);
    expect(btn.disabled).toBe(false);
  });

  it('Apply shows the route message, not HTTP 409', async () => {
    const obs = await import('../../../src/web/static/modules/studios/observability.js');
    vi.stubGlobal('fetch', vi.fn(async () => json(409, { detail: 'No skill lists x, so there is nothing to patch.' })));
    const { ev } = clickOn('apply-friction-btn', 'rec_patch');
    await obs.handleFrictionAction(ev, {});
    const src = read(`${STATIC}/observability.js`);
    expect(src).toMatch(/detail/);
    expect(src).not.toMatch(/Failed to apply patch: \$\{err/);
  });
});

describe('REQ-520-011: one Ask Developer helper for gap, Teach and Observability', () => {
  it('the helper exists and the three entry points use it', async () => {
    const auth = await import('../../../src/web/static/modules/studios/tools_studio_authoring.js');
    expect(typeof auth.askDeveloperWithDraft).toBe('function');
    for (const rel of ['forge/tools.js', 'chat/teach_modal.js', 'observability.js']) {
      expect(read(`${STATIC}/${rel}`), rel).toContain('askDeveloperWithDraft(');
    }
  });

  it('askDeveloperWithDraft posts talk and opens the Developer chat through openDeveloperSession', async () => {
    const { askDeveloperWithDraft } = await import('../../../src/web/static/modules/studios/tools_studio_authoring.js');
    const fetchFn = vi.fn(async (url, init) => {
      const b = JSON.parse(init.body);
      return json(200, { session_id: 'd1', agent_id: 'developer', opened_job: false, job_id: null, prompt: `X ${b.draft.tool_name} ${b.draft.behavior}` });
    });
    const open = vi.fn(async () => {});
    const plan = await askDeveloperWithDraft({ tool_name: 't1', behavior: 'do it' }, { intent: 'modify', fetchFn, openDeveloperSessionFn: open });
    expect(JSON.parse(fetchFn.mock.calls[0][1].body).intent).toBe('modify');
    expect(open).toHaveBeenCalledWith('d1', expect.stringContaining('t1'));
    expect(plan.sessionId).toBe('d1');
  });
});

describe('REQ-520-013: Observability sections are all top level', () => {
  it('no details.obs-section is nested in another, and friction is top level', () => {
    const html = read('src/web/templates/index.html');
    const start = html.indexOf('id="view-observability"');
    const end = html.indexOf('</section>', start);
    const body = html.slice(start, end);
    const re = /<details\b[^>]*>|<\/details>/g;
    const stack = [];
    const nested = [];
    let m;
    while ((m = re.exec(body))) {
      if (m[0].startsWith('</')) { stack.pop(); continue; }
      const sec = (m[0].match(/data-obs-section="([^"]+)"/) || [])[1];
      const isObs = /class="[^"]*obs-section/.test(m[0]);
      if (isObs && stack.some((s) => s.obs)) nested.push(sec);
      stack.push({ obs: isObs, sec });
    }
    expect(nested).toEqual([]);
    expect(stack.filter((s) => s.obs)).toEqual([]);
  });
});
