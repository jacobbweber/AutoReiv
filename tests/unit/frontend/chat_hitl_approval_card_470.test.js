import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

import * as hitl from '../../../src/web/static/modules/studios/chat/hitl.js';

/**
 * CARD-470 follow-up - approval cards lost in the CARD-397 split.
 * Live test 2026-09-25 ~12:09 AM ET: the backend parked wiki_note_create (pending_approvals rows
 * appr_36d481b04e49 / appr_7512d98f94b6) but Chat showed no Approve/Reject card:
 *  - setupPendingHitl fetched pendingApprovalsUrl(sessionId) -> ?agent_id=<session id> (args shifted);
 *  - it read data.pending, but the API returns a bare array;
 *  - it looked for .hitl-approve-btn buttons that buildHitlCardInnerHtml never renders;
 *  - the inline stream card had no button listeners and was wiped by the finalize reload.
 */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

class FakeClassList {
  constructor(initial = []) { this.set = new Set(initial); }
  add(...c) { c.forEach((x) => this.set.add(x)); }
  remove(...c) { c.forEach((x) => this.set.delete(x)); }
  contains(c) { return this.set.has(c); }
  toggle(c, force) { const on = force === undefined ? !this.set.has(c) : !!force; if (on) this.set.add(c); else this.set.delete(c); return on; }
}

class FakeButton {
  constructor(decision) { this.decision = decision; this.listeners = []; this.disabled = false; this.classList = new FakeClassList(); }
  getAttribute(k) { return k === 'data-hitl-decision' ? this.decision : null; }
  addEventListener(type, fn) { if (type === 'click') this.listeners.push(fn); }
  async click() { for (const fn of this.listeners) await fn({ type: 'click' }); }
}

class FakeEl {
  constructor(tag = 'div', classes = []) {
    this.tag = tag; this.attrs = {}; this.children = []; this.parent = null;
    this.classList = new FakeClassList(classes); this._html = ''; this._buttons = []; this.status = { textContent: '' };
    this.scrolled = false; this.className = '';
  }
  set innerHTML(v) {
    this._html = String(v);
    this._buttons = [...this._html.matchAll(/<button[^>]*>/g)].map((m) => m[0]).filter((tag) => !/\sdisabled[\s>]/.test(tag)).map((tag) => tag.match(/data-hitl-decision="(\w+)"/)).filter(Boolean).map((m) => new FakeButton(m[1]));
  }
  get innerHTML() { return this._html; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  appendChild(el) { el.parent = this; this.children.push(el); return el; }
  remove() { if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this); this.parent = null; }
  scrollIntoView() { this.scrolled = true; }
  querySelector(sel) {
    if (sel === '.hitl-card-status') return this.status;
    const m = sel.match(/^\[data-approval-id="(.+)"\]$/);
    if (m) return this.children.find((c) => c.attrs['data-approval-id'] === m[1]) || null;
    return null;
  }
  querySelectorAll(sel) {
    if (sel === '[data-hitl-decision]') return this._buttons;
    if (sel === '[data-approval-id]') return this.children.filter((c) => 'data-approval-id' in c.attrs);
    return [];
  }
}

const fakeDoc = { createElement: (tag) => new FakeEl(tag) };

let calls;
let pendingRows;
let decisionBody;
const savedFetch = globalThis.fetch;

beforeEach(() => {
  calls = [];
  pendingRows = [];
  decisionBody = { status: 'APPROVED', execution: null };
  globalThis.fetch = async (url, opts = {}) => {
    calls.push({ url, opts });
    if (String(url).startsWith('/api/approvals/pending')) return { ok: true, json: async () => pendingRows };
    return { ok: true, json: async () => decisionBody };
  };
});
afterEach(() => { globalThis.fetch = savedFetch; });

const row = (over = {}) => ({
  id: 'appr_1', session_id: 's1', agent_id: 'autoreiv', routine_id: null, tool_name: 'wiki_note_create',
  arguments: { title: 'test470', content: 'hello' }, status: 'pending', ...over,
});

function setup(stateOver = {}) {
  const state = { selectedAgentId: 'autoreiv', activeSessionId: 's1', isStreaming: false, ...stateOver };
  const host = new FakeEl('div');
  const messages = new FakeEl('div');
  const resumes = [];
  const ctl = hitl.setupPendingHitl(state, messages, {
    pendingHitlHost: host,
    onResumeTurn: async (...a) => { resumes.push(a); },
    doc: fakeDoc,
  });
  return { state, host, messages, resumes, ctl };
}

describe('CARD-470 pending approval tray (#pendingHitlHost)', () => {
  it('asks the API for the open session, not agent_id=<session id>', async () => {
    const t = setup();
    await t.ctl.refreshPendingHitl();
    expect(calls[0].url).toBe('/api/approvals/pending?session_id=s1');
  });

  it('renders a card for each pending row from the bare-array response', async () => {
    pendingRows = [row()];
    const t = setup();
    await t.ctl.refreshPendingHitl();
    expect(t.host.children).toHaveLength(1);
    const card = t.host.children[0];
    expect(card.getAttribute('data-approval-id')).toBe('appr_1');
    expect(card.innerHTML).toContain('wiki_note_create');
    expect(card.innerHTML).toContain('test470');
    expect(card.querySelectorAll('[data-hitl-decision]').map((b) => b.decision)).toEqual(['APPROVED', 'REJECTED']);
  });

  it('does not duplicate on the next poll and drops resolved rows', async () => {
    pendingRows = [row()];
    const t = setup();
    await t.ctl.refreshPendingHitl();
    await t.ctl.refreshPendingHitl();
    expect(t.host.children).toHaveLength(1);
    pendingRows = [];
    await t.ctl.refreshPendingHitl();
    expect(t.host.children).toHaveLength(0);
  });

  it('Approve posts the decision and resumes the chat turn', async () => {
    pendingRows = [row()];
    const t = setup();
    await t.ctl.refreshPendingHitl();
    const approve = t.host.children[0].querySelectorAll('[data-hitl-decision]')[0];
    await approve.click();
    const post = calls.find((c) => c.url === '/api/approvals/appr_1/decision');
    expect(post).toBeTruthy();
    expect(JSON.parse(post.opts.body)).toEqual({ decision: 'APPROVED', session_id: 's1' });
    expect(t.resumes).toEqual([['', { isResume: true }]]);
  });

  it('Reject posts REJECTED; no resume when the backend already resumed', async () => {
    pendingRows = [row()];
    decisionBody = { status: 'REJECTED', resumed: true };
    const t = setup();
    await t.ctl.refreshPendingHitl();
    await t.host.children[0].querySelectorAll('[data-hitl-decision]')[1].click();
    const post = calls.find((c) => c.url === '/api/approvals/appr_1/decision');
    expect(JSON.parse(post.opts.body).decision).toBe('REJECTED');
    expect(t.resumes).toEqual([]);
  });

  it('while streaming, skips a row already shown inline in the thread', async () => {
    pendingRows = [row()];
    const t = setup({ isStreaming: true });
    const inline = new FakeEl('div');
    inline.setAttribute('data-approval-id', 'appr_1');
    t.messages.appendChild(inline);
    await t.ctl.refreshPendingHitl();
    expect(t.host.children).toHaveLength(0);
  });
});

describe('CARD-470 inline approval card in the reply bubble', () => {
  const ev = { type: 'approval_required', approval_id: 'appr_9', tool_name: 'wiki_note_create', arguments: { title: 'x' }, message: 'Parked for operator approval' };

  it('shows tool, args and working Approve/Reject buttons', async () => {
    const card = new FakeEl('div', ['hitl-approval-card', 'hidden']);
    const state = { activeSessionId: 's1' };
    const resumes = [];
    const done = [];
    expect(hitl.renderInlineHitlCard(card, ev, { state, onResumeTurn: async (...a) => resumes.push(a), onDone: async () => done.push(1) })).toBe(true);
    expect(card.classList.contains('hidden')).toBe(false);
    expect(card.getAttribute('data-approval-id')).toBe('appr_9');
    expect(card.innerHTML).toContain('wiki_note_create');
    expect(card.innerHTML).toContain('Parked for operator approval');
    await card.querySelectorAll('[data-hitl-decision]')[0].click();
    expect(calls.find((c) => c.url === '/api/approvals/appr_9/decision')).toBeTruthy();
    expect(resumes).toEqual([['', { isResume: true }]]);
    expect(done).toHaveLength(1);
  });

  it('leaves goal_plan_review to the plan card', () => {
    const card = new FakeEl('div', ['hitl-approval-card', 'hidden']);
    expect(hitl.renderInlineHitlCard(card, { ...ev, tool_name: 'goal_plan_review' }, { state: {} })).toBe(false);
    expect(card.classList.contains('hidden')).toBe(true);
  });
});

describe('CARD-470 chat.js wiring contracts', () => {
  const chatSrc = read('src/web/static/modules/studios/chat.js');
  it('passes the pinned tray host to setupPendingHitl', () => {
    expect(chatSrc).toMatch(/setupPendingHitl\(state, messagesContainer, \{[^}]*pendingHitlHost: \$\('pendingHitlHost'\)/);
  });
  it('renders the inline card through the wired helper and refreshes the tray on park events', () => {
    expect(chatSrc).toMatch(/renderInlineHitlCard\(hitlCard, ev,/);
    expect(chatSrc).toMatch(/isHitlParkSseEvent\(eventType, ev\)\) refreshPendingHitl\(\)/);
    expect(chatSrc).not.toMatch(/hitlCard\.innerHTML = buildHitlCardInnerHtml\(ev/);
  });
  it('hitl.js no longer looks for buttons the card never renders', () => {
    const src = read('src/web/static/modules/studios/chat/hitl.js');
    expect(src).not.toMatch(/hitl-approve-btn|hitl-reject-btn/);
    expect(src).not.toMatch(/data\.pending \|\|/);
  });
  it('a tap on the approval tray is not lost to the composer shrink (pressRegions)', () => {
    expect(chatSrc).toMatch(/pressRegions: \[\$\('pendingHitlHost'\)\]/);
  });
  it('chat.js stays within its cap', () => {
    expect(chatSrc.split('\n').length).toBeLessThanOrEqual(1045);
  });
});
