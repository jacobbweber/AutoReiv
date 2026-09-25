import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

/**
 * CARD-502 - Adopt message comes from the server answer (active / already_adopted / resets_on_restart).
 * Node env with a tiny fake DOM (same helper shape as teach_distill_contract_500.test.js).
 */

const RENDER = path.resolve(__dirname, '../../../src/web/static/modules/studios/chat/render.js');

function fakeEl(tag = 'div') {
  const listeners = {};
  const cls = new Set();
  const attrs = {};
  const kids = {};
  const e = {
    tagName: tag.toUpperCase(), textContent: '', innerHTML: '', value: '', disabled: false, dataset: {}, style: {},
    classList: { add: (...c) => c.forEach((x) => cls.add(x)), remove: (...c) => c.forEach((x) => cls.delete(x)), contains: (c) => cls.has(c) },
    setAttribute(k, v) { attrs[k] = String(v); },
    getAttribute(k) { return Object.prototype.hasOwnProperty.call(attrs, k) ? attrs[k] : null; },
    addEventListener(t, f) { (listeners[t] = listeners[t] || []).push(f); },
    dispatch(t, ev = {}) { return Promise.all((listeners[t] || []).map((f) => f({ preventDefault() {}, stopPropagation() {}, target: e, ...ev }))); },
    click() { return e.dispatch('click'); },
    querySelector(sel) {
      const m = /^\.([\w-]+)$/.exec(sel);
      if (!m || !e.innerHTML.includes(m[1])) return null;
      if (!kids[sel]) { kids[sel] = fakeEl(); kids[sel].innerHTML = e.innerHTML; }
      return kids[sel];
    },
    querySelectorAll() { return []; },
    appendChild(c) { (e.children = e.children || []).push(c); return c; },
    remove() {}, focus() {}, closest() { return null; },
  };
  return e;
}

const json = (status, body) => ({ ok: status >= 200 && status < 300, status, json: async () => body });
const flush = () => new Promise((r) => setTimeout(r, 0));
const PROPOSAL = {
  status: 'ok', target_agent_id: 'autoreiv', needs_tool: false, skill_id: 'cite-sources', name: 'Cite Sources',
  plain_summary: { observed_slip: 's', remedy: 'r' }, runbook_markdown: '---\nname: cite-sources\n---\n# Cite Sources', message_id: 'p1',
};
const OK = { status: 'adopted', target_agent_id: 'autoreiv', skill_id: 'cite-sources', name: 'Cite Sources', active: true, already_adopted: false, resets_on_restart: false };

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

async function adoptWith(body, status = 200, proposal = PROPOSAL) {
  const { renderSkillProposalCard } = await import('../../../src/web/static/modules/studios/chat/render.js');
  vi.stubGlobal('fetch', vi.fn(async () => json(status, body)));
  const toast = vi.fn();
  const el = renderSkillProposalCard(proposal, { container: fakeEl(), sessionId: 's1', showToastFn: toast });
  const card = el.querySelector('.skill-proposal-card');
  await card.querySelector('.btn-adopt-skill').click();
  await flush();
  return { toast, card };
}

describe('CARD-502 Adopt message', () => {
  it('REQ-502-005: active shows "<name> is on for <agent> from your next message."', async () => {
    const { toast, card } = await adoptWith(OK);
    expect(toast).toHaveBeenCalledWith('Cite Sources is on for autoreiv from your next message.', 'success');
    expect(card.querySelector('.card-actions').innerHTML).toContain('Cite Sources is on for autoreiv from your next message.');
  });

  it('REQ-502-004: keep-customizations off adds the restart warning', async () => {
    const { toast } = await adoptWith({ ...OK, resets_on_restart: true });
    const [msg, type] = toast.mock.calls[0];
    expect(msg).toBe('Cite Sources is on for autoreiv from your next message. Keep my agent customizations is off, so it will be removed on the next restart.');
    expect(type).toBe('warning');
  });

  it('REQ-502-006: re-adopt says Updated', async () => {
    const { toast } = await adoptWith({ ...OK, already_adopted: true });
    expect(toast.mock.calls[0][0]).toBe('Updated Cite Sources for autoreiv. It is used from your next message.');
  });

  it('REQ-502-005: a 200 that is not active is an error, not a success', async () => {
    const { toast } = await adoptWith({ ...OK, active: false });
    const [msg, type] = toast.mock.calls[0];
    expect(type).toBe('error');
    expect(msg).toContain('Adoption failed');
    expect(msg).not.toContain('is on for');
  });

  it('REQ-502-006: a 409 shows the server sentence', async () => {
    const { toast } = await adoptWith({ detail: 'autoreiv already has a platform skill called wiki-inbox. Rename the lesson and try again.' }, 409);
    expect(toast.mock.calls[0][0]).toContain('already has a platform skill called wiki-inbox');
  });

  it('an adopted card from history says "On for <agent>."', async () => {
    const { renderSkillProposalCard } = await import('../../../src/web/static/modules/studios/chat/render.js');
    const el = renderSkillProposalCard({ ...PROPOSAL, adoption_state: 'adopted' }, { container: fakeEl() });
    expect(el.innerHTML).toContain('On for <strong>autoreiv</strong>.');
  });

  it('the hard-coded "Active for your next message" text is gone', () => {
    expect(fs.readFileSync(RENDER, 'utf-8')).not.toContain('Active for your next message');
  });
});
