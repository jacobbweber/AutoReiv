import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * CARD-500 - Teach sends the lesson, /learn picks the latest reply, readable errors,
 * card shows name + plain_summary, needs-tool hides Adopt, history cards get session/agent/toast.
 * Node env with a tiny fake DOM (no jsdom in this repo).
 */

const ROOT = path.resolve(__dirname, '../../../src/web/static/modules/studios');
const chatJs = fs.readFileSync(path.join(ROOT, 'chat.js'), 'utf-8');
const teachSrc = fs.readFileSync(path.join(ROOT, 'chat/teach_modal.js'), 'utf-8');

function fakeEl(tag = 'div') {
  const listeners = {};
  const cls = new Set();
  const attrs = {};
  const kids = {};
  const e = {
    tagName: tag.toUpperCase(),
    textContent: '',
    innerHTML: '',
    value: '',
    disabled: false,
    dataset: {},
    style: {},
    classList: {
      add: (...c) => c.forEach((x) => cls.add(x)),
      remove: (...c) => c.forEach((x) => cls.delete(x)),
      contains: (c) => cls.has(c),
      toggle: (c, f) => { const on = f === undefined ? !cls.has(c) : Boolean(f); if (on) cls.add(c); else cls.delete(c); return on; },
    },
    setAttribute(k, v) { attrs[k] = String(v); },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; },
    addEventListener(t, f) { (listeners[t] = listeners[t] || []).push(f); },
    dispatch(t, ev = {}) { return Promise.all((listeners[t] || []).map((f) => f({ preventDefault() {}, stopPropagation() {}, target: e, ...ev }))); },
    click() { return e.dispatch('click'); },
    // querySelector returns a stable fake child only when its class appears in innerHTML
    querySelector(sel) {
      const m = /^\.([\w-]+)$/.exec(sel);
      if (!m || !e.innerHTML.includes(m[1])) return null;
      if (!kids[sel]) { kids[sel] = fakeEl(); kids[sel].innerHTML = e.innerHTML; }
      return kids[sel];
    },
    querySelectorAll() { return []; },
    appendChild(c) { (e.children = e.children || []).push(c); return c; },
    remove() {},
    focus() {},
    dispatchEvent() { return true; },
    closest() { return null; },
    hidden() { return cls.has('hidden'); },
  };
  return e;
}

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const flush = () => new Promise((r) => setTimeout(r, 0));
const VALIDATION_422 = { detail: [{ type: 'string_type', loc: ['body', 'message_id'], msg: 'Input should be a valid string', input: null }] };

let savedDocument;
beforeEach(() => {
  savedDocument = globalThis.document;
  globalThis.document = { createElement: (t) => fakeEl(t), getElementById: () => null, querySelector: () => null };
});
afterEach(() => {
  if (savedDocument === undefined) delete globalThis.document; else globalThis.document = savedDocument;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function teachEls() {
  const els = {};
  ['teachAgentModal', 'teachAgentTargetAgentBadge', 'teachAgentGuidanceInput', 'submitTeachAgentBtn',
    'cancelTeachAgentBtn', 'closeTeachAgentModalBtn'].forEach((k) => { els[k] = fakeEl(); });
  els.teachAgentModal.classList.add('hidden');
  return els;
}

const PROPOSAL = {
  status: 'ok', target_agent_id: 'autoreiv', needs_tool: false, skill_id: 'cite-sources', name: 'Cite Sources',
  plain_summary: { observed_slip: 'Answered without a source', remedy: 'Cite the source every time' },
  runbook_markdown: '---\nname: cite-sources\n---\n# Cite Sources', message_id: 'p1',
};

describe('CARD-500 Teach request', () => {
  it('REQ-500-001: submit posts exactly {session_id, message_id, guidance}', async () => {
    const { setupTeachAgentModal } = await import('../../../src/web/static/modules/studios/chat/teach_modal.js');
    const els = teachEls();
    const fetchFn = vi.fn(async () => json(200, PROPOSAL));
    const ctrl = setupTeachAgentModal({ selectedAgentId: 'autoreiv', activeSessionId: 's1' }, els, {
      showToastFn: vi.fn(), callbacks: {}, messagesContainer: fakeEl(), fetchFn,
    });
    ctrl.openTeachAgentModal({ messageId: 'm1' });
    els.teachAgentGuidanceInput.value = 'always cite the source';
    await els.submitTeachAgentBtn.click();
    await flush();
    expect(fetchFn).toHaveBeenCalledTimes(1);
    const [url, init] = fetchFn.mock.calls[0];
    expect(url).toBe('/api/skills/distill');
    expect(JSON.parse(init.body)).toEqual({ session_id: 's1', message_id: 'm1', guidance: 'always cite the source' });
  });

  it('REQ-500-004: /learn opens Teach for the latest assistant reply with the text filled in', async () => {
    const { setupComposerControls } = await import('../../../src/web/static/modules/studios/chat/composer.js');
    const chatForm = fakeEl('form');
    const promptInput = fakeEl('textarea');
    const onOpenTeachAgent = vi.fn();
    const onExecuteTurn = vi.fn();
    const state = {
      activeSessionId: 's1', selectedAgentId: 'autoreiv',
      messages: [
        { id: 'u1', role: 'user', content: 'q1' }, { id: 'a1', role: 'assistant', content: 'r1' },
        { id: 'u2', role: 'user', content: 'q2' }, { id: 'a2', role: 'assistant', content: 'r2' },
        { id: 'p1', role: 'skill_proposal', content: '{}' },
      ],
    };
    setupComposerControls({ chatForm, promptInput, stopBtn: fakeEl(), state, onExecuteTurn, onOpenTeachAgent });
    promptInput.value = '/learn be shorter';
    await chatForm.dispatch('submit');
    expect(onExecuteTurn).not.toHaveBeenCalled();
    expect(onOpenTeachAgent).toHaveBeenCalledWith(expect.objectContaining({ messageId: 'a2', guidance: 'be shorter' }));
  });

  it('REQ-500-004: with no reply yet, Teach says "Send a message first, then teach from the reply." and never distills', async () => {
    const { setupTeachAgentModal } = await import('../../../src/web/static/modules/studios/chat/teach_modal.js');
    const els = teachEls();
    const fetchFn = vi.fn();
    const showToastFn = vi.fn();
    const ctrl = setupTeachAgentModal({ selectedAgentId: 'autoreiv', activeSessionId: 's1' }, els, {
      showToastFn, callbacks: {}, messagesContainer: fakeEl(), fetchFn,
    });
    ctrl.openTeachAgentModal({ guidance: 'test' });
    await els.submitTeachAgentBtn.click();
    await flush();
    expect(showToastFn).toHaveBeenCalledWith('Send a message first, then teach from the reply.', expect.any(String));
    expect(els.teachAgentModal.hidden()).toBe(true);
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it('REQ-500-005: a 422 shows a readable reason, never [object Object] (Teach and Adopt)', async () => {
    const { setupTeachAgentModal } = await import('../../../src/web/static/modules/studios/chat/teach_modal.js');
    const { renderSkillProposalCard } = await import('../../../src/web/static/modules/studios/chat/render.js');
    const els = teachEls();
    const showToastFn = vi.fn();
    const ctrl = setupTeachAgentModal({ selectedAgentId: 'autoreiv', activeSessionId: 's1' }, els, {
      showToastFn, callbacks: {}, messagesContainer: fakeEl(), fetchFn: vi.fn(async () => json(422, VALIDATION_422)),
    });
    ctrl.openTeachAgentModal({ messageId: 'm1' });
    await els.submitTeachAgentBtn.click();
    await flush();
    const teachMsg = showToastFn.mock.calls.map((c) => c[0]).join(' | ');
    expect(teachMsg).toContain('Input should be a valid string');
    expect(teachMsg).not.toContain('[object Object]');

    vi.stubGlobal('fetch', vi.fn(async () => json(422, VALIDATION_422)));
    const adoptToast = vi.fn();
    const el = renderSkillProposalCard(PROPOSAL, { container: fakeEl(), sessionId: 's1', showToastFn: adoptToast });
    const card = el.querySelector('.skill-proposal-card');
    await card.querySelector('.btn-adopt-skill').click();
    await flush();
    const adoptMsg = adoptToast.mock.calls.map((c) => c[0]).join(' | ');
    expect(adoptMsg).toContain('Input should be a valid string');
    expect(adoptMsg).not.toContain('[object Object]');
  });
});

describe('CARD-500 proposal card', () => {
  it('REQ-500-006: shows the skill name and plain_summary slip and remedy', async () => {
    const { renderSkillProposalCard } = await import('../../../src/web/static/modules/studios/chat/render.js');
    const el = renderSkillProposalCard(PROPOSAL, { container: fakeEl() });
    expect(el.innerHTML).toContain('Cite Sources');
    expect(el.innerHTML).not.toContain('Synthesized Skill');
    expect(el.innerHTML).toContain('Answered without a source');
    expect(el.innerHTML).toContain('Cite the source every time');
  });

  it('REQ-500-007: a needs-tool card has no Adopt button, only Ask Developer and Dismiss', async () => {
    const { renderSkillProposalCard } = await import('../../../src/web/static/modules/studios/chat/render.js');
    const el = renderSkillProposalCard({
      ...PROPOSAL, needs_tool: true, skill_id: null, name: null, runbook_markdown: null,
      tool_escalation: { suggested_tool_name: 'get_city_weather', seed_intent: 'weather' }, // CARD-520
    }, { container: fakeEl() });
    expect(el.innerHTML).not.toContain('btn-adopt-skill');
    expect(el.innerHTML).toContain('btn-escalate-developer'); // CARD-496 D10
    expect(el.innerHTML).toContain('btn-dismiss-proposal');
  });

  it('REQ-500-008: history cards get the session, agent and toast function', async () => {
    const { renderMessageItem } = await import('../../../src/web/static/modules/studios/chat/render.js');
    const spy = vi.fn();
    const showToastFn = vi.fn();
    renderMessageItem({ id: 'p1', role: 'skill_proposal', content: JSON.stringify(PROPOSAL) }, 0, [], {
      messagesContainer: fakeEl(), renderSkillProposalCardFn: spy,
      proposalOptions: { sessionId: 's1', activeAgentId: 'autoreiv', showToastFn },
    });
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({ message_id: 'p1' }),
      expect.objectContaining({ sessionId: 's1', activeAgentId: 'autoreiv', showToastFn }));
    expect(chatJs).toMatch(/proposalOptions:\s*\{[^}]*sessionId[^}]*showToastFn[^}]*\}/);
  });

  it('REQ-500-009: the Teach flow never calls the Training Factory', () => {
    expect(teachSrc).not.toMatch(/agent_training_factory/);
  });
});
