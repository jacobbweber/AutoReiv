import { describe, it, expect, afterEach, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

import { compactSession, setupChatChrome } from '../../../src/web/static/modules/studios/chat/chrome.js';
import { setupQuickPromptPicker } from '../../../src/web/static/modules/studios/chat/quick_prompts.js';

/**
 * CARD-471 - Chat options drawer and tools window wiring: Compact, View tools, closing the tools window,
 * outside click and Escape (REQ-471-001..006).
 */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');
const flush = () => new Promise((r) => setTimeout(r, 0));

class FakeClassList {
  constructor(initial = []) { this.set = new Set(initial); }
  add(...c) { c.forEach((x) => this.set.add(x)); }
  remove(...c) { c.forEach((x) => this.set.delete(x)); }
  contains(c) { return this.set.has(c); }
  toggle(c, force) {
    const on = force === undefined ? !this.set.has(c) : !!force;
    if (on) this.set.add(c); else this.set.delete(c);
    return on;
  }
}

class FakeEl {
  constructor(classes = []) {
    this.listeners = {};
    this.classList = new FakeClassList(classes);
    this.children = [];
    this.attrs = {};
    this.innerHTML = '';
    this.textContent = '';
    this.value = '';
    this.disabled = false;
    this.style = {};
    this.isConnected = true;
  }
  addEventListener(type, fn, capture) { (this.listeners[type] ||= []).push({ fn, capture: !!capture }); }
  async fire(type, extra = {}) {
    const evt = {
      type, target: this, defaultPrevented: false, stopped: false,
      preventDefault() { this.defaultPrevented = true; },
      stopPropagation() { this.stopped = true; },
      ...extra,
    };
    for (const { fn } of this.listeners[type] || []) await fn(evt);
    return evt;
  }
  contains(node) { return node === this || this.children.some((c) => c.contains(node)); }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  querySelector() { return this.focusEl || null; }
  focus() {}
}

const IDS = [
  'chatOptionsToggleBtn', 'chatOptionsDrawer', 'chatOptionsCloseBtn', 'chatManualCompactBtn', 'chatViewToolsBtn',
  'chatToolsModal', 'chatToolsModalCloseBtn', 'chatToolsModalDismissBtn', 'chatToolsModalList', 'chatToolsModalTitle',
  'chatToolsModalBadge', 'chatToolsSearchInput', 'chatPromptsQuickPicker', 'chatContextTokensBadge',
  'chatContextProgressBar', 'chatToolsCountBadge',
];

const CONTEXT = {
  used_tokens: 1200, max_tokens: 8192, percent_used: 15, tools_count: 2, agent_name: 'Generalist',
  tools: [
    { name: 'web_search', description: 'Search the web' },
    { name: 'wiki_read', description: 'Read a wiki note' },
  ],
};

function env({ sessionId = 's1', focus = null } = {}) {
  const els = {};
  IDS.forEach((id) => { els[id] = new FakeEl(); });
  ['chatOptionsDrawer', 'chatToolsModal', 'chatPromptsQuickPicker'].forEach((id) => els[id].classList.add('hidden'));
  els.chatOptionsDrawer.children.push(els.chatManualCompactBtn, els.chatViewToolsBtn, els.chatOptionsCloseBtn);
  els.chatToolsModal.children.push(els.chatToolsModalCloseBtn, els.chatToolsModalDismissBtn, els.chatToolsModalList, els.chatToolsSearchInput);
  const doc = new FakeEl();
  if (focus) { doc.focusEl = new FakeEl(); doc.focusEl.setAttribute('data-desktop-focus', focus); }
  const win = new FakeEl();
  const toasts = [];
  const reloaded = [];
  const fetched = [];
  vi.stubGlobal('fetch', async (url, opts = {}) => {
    fetched.push([url, opts.method || 'GET']);
    if (String(url).endsWith('/compact')) {
      return { ok: true, json: async () => ({ success: true, compaction_applied: true, turns_compacted: 4, original_tokens: 3000, compacted_tokens: 1000 }) };
    }
    return { ok: true, json: async () => CONTEXT };
  });
  const state = { activeSessionId: sessionId, selectedAgentId: 'generalist', messages: [] };
  setupChatChrome(state, { ...els, doc, win }, {
    showToastFn: (m, k) => toasts.push([m, k]),
    reloadMessages: async (sid) => reloaded.push(sid),
  });
  const openDrawer = () => els.chatOptionsToggleBtn.fire('click');
  const escape = () => win.fire('keydown', { key: 'Escape' });
  const isOpen = (id) => !els[id].classList.contains('hidden');
  return { els, doc, win, toasts, reloaded, fetched, state, openDrawer, escape, isOpen };
}

afterEach(() => vi.unstubAllGlobals());

describe('CARD-471 chrome reads the template\'s real IDs', () => {
  it('every element ID setupChatChrome looks up exists in index.html (no ghost IDs)', () => {
    const html = read('src/web/templates/index.html');
    const js = read('src/web/static/modules/studios/chat/chrome.js');
    const body = js.slice(js.indexOf('export function setupChatChrome'));
    const ids = [...body.matchAll(/getEl\('([A-Za-z0-9_-]+)'\)/g)].map((m) => m[1]);
    expect(ids.length).toBeGreaterThan(20);
    const missing = ids.filter((id) => !html.includes(`id="${id}"`));
    expect(missing).toEqual([]);
    expect(body).not.toMatch(/chatCompactBtn'|chatInspectToolsBtn'/);
  });
});

describe('CARD-471 Compact (REQ-471-001)', () => {
  it('compacts, reports turns and freed tokens, reloads messages and context, and re-enables the button', async () => {
    const button = new FakeEl();
    const toasts = [];
    const calls = [];
    let disabledDuring = null;
    const res = await compactSession({ activeSessionId: 's9' }, {
      button,
      showToastFn: (m, k) => toasts.push([m, k]),
      postCompactionFn: async (sid) => { disabledDuring = button.disabled; calls.push(['post', sid]); return { success: true, compaction_applied: true, turns_compacted: 6, original_tokens: 12000, compacted_tokens: 2000 }; },
      reloadMessagesFn: async (sid) => calls.push(['messages', sid]),
      reloadContextFn: async () => calls.push(['context']),
    });
    expect(res.compaction_applied).toBe(true);
    expect(disabledDuring).toBe(true);
    expect(button.disabled).toBe(false);
    expect(toasts).toEqual([['Compacted 6 turns (freed 10,000 tokens)', 'success']]);
    expect(calls).toEqual([['post', 's9'], ['messages', 's9'], ['context']]);
  });

  it('says the chat is already compact when nothing was compressed, without reloading messages', async () => {
    const toasts = [];
    const reloaded = [];
    await compactSession({ activeSessionId: 's1' }, {
      showToastFn: (m, k) => toasts.push([m, k]),
      postCompactionFn: async () => ({ success: true, compaction_applied: false }),
      reloadMessagesFn: async (sid) => reloaded.push(sid),
    });
    expect(toasts).toEqual([['Conversation is already compact. No earlier turns to compress.', 'info']]);
    expect(reloaded).toEqual([]);
  });

  it('shows the error and re-enables the button when compaction fails', async () => {
    const button = new FakeEl();
    const toasts = [];
    await compactSession({ activeSessionId: 's1' }, {
      button,
      showToastFn: (m, k) => toasts.push([m, k]),
      postCompactionFn: async () => ({ success: false, error: 'Session not found' }),
    });
    expect(toasts).toEqual([['Session not found', 'error']]);
    expect(button.disabled).toBe(false);
  });

  it('with no open chat says so and calls nothing', async () => {
    const toasts = [];
    let posted = false;
    await compactSession({ activeSessionId: null }, {
      showToastFn: (m, k) => toasts.push([m, k]),
      postCompactionFn: async () => { posted = true; },
    });
    expect(posted).toBe(false);
    expect(toasts).toEqual([['No active chat session to compact.', 'info']]);
  });

  it('the drawer\'s Compact button posts to the compact endpoint and reloads the open chat', async () => {
    const e = env();
    await e.els.chatManualCompactBtn.fire('click');
    await flush();
    expect(e.fetched).toContainEqual(['/api/sessions/s1/compact', 'POST']);
    expect(e.toasts).toContainEqual(['Compacted 4 turns (freed 2,000 tokens)', 'success']);
    expect(e.reloaded).toEqual(['s1']);
  });
});

describe('CARD-471 View tools and closing the tools window (REQ-471-002, REQ-471-003)', () => {
  it('View tools opens the window with the agent, count and tool list; search filters it', async () => {
    const e = env();
    await e.els.chatViewToolsBtn.fire('click');
    expect(e.isOpen('chatToolsModal')).toBe(true);
    expect(e.els.chatToolsModalTitle.textContent).toBe('Active Tools (Generalist)');
    expect(e.els.chatToolsModalBadge.textContent).toBe('2 tools');
    expect(e.els.chatToolsModalList.innerHTML).toContain('web_search');
    expect(e.els.chatToolsModalList.innerHTML).toContain('wiki_read');
    e.els.chatToolsSearchInput.value = 'wiki';
    await e.els.chatToolsSearchInput.fire('input', { target: { value: 'wiki' } });
    expect(e.els.chatToolsModalList.innerHTML).toContain('wiki_read');
    expect(e.els.chatToolsModalList.innerHTML).not.toContain('web_search');
  });

  for (const how of ['chatToolsModalCloseBtn', 'chatToolsModalDismissBtn', 'backdrop']) {
    it(`closes by ${how}`, async () => {
      const e = env();
      await e.els.chatViewToolsBtn.fire('click');
      if (how === 'backdrop') await e.els.chatToolsModal.fire('click');
      else await e.els[how].fire('click');
      expect(e.isOpen('chatToolsModal')).toBe(false);
    });
  }

  it('a click inside the tools window (not the backdrop) keeps it open', async () => {
    const e = env();
    await e.els.chatViewToolsBtn.fire('click');
    await e.els.chatToolsModal.fire('click', { target: e.els.chatToolsModalList });
    expect(e.isOpen('chatToolsModal')).toBe(true);
  });
});

describe('CARD-471 outside click closes the drawer (REQ-471-004)', () => {
  it('a click elsewhere closes it; clicks inside the drawer, on its toggle, in the tools window or on a re-rendered button do not', async () => {
    const e = env();
    await e.openDrawer();
    expect(e.isOpen('chatOptionsDrawer')).toBe(true);
    const detached = new FakeEl();
    detached.isConnected = false;
    for (const target of [e.els.chatManualCompactBtn, e.els.chatOptionsToggleBtn, e.els.chatToolsModalList, detached]) {
      await e.doc.fire('click', { target });
      expect(e.isOpen('chatOptionsDrawer')).toBe(true);
    }
    await e.doc.fire('click', { target: new FakeEl() });
    expect(e.isOpen('chatOptionsDrawer')).toBe(false);
  });
});

describe('CARD-471 Escape closes the topmost layer only (REQ-471-005, REQ-471-006)', () => {
  it('first Escape closes the tools window, second closes the drawer, and neither reaches the desktop', async () => {
    const e = env();
    await e.openDrawer();
    await e.els.chatViewToolsBtn.fire('click');
    const first = await e.escape();
    expect(e.isOpen('chatToolsModal')).toBe(false);
    expect(e.isOpen('chatOptionsDrawer')).toBe(true);
    expect(first.stopped && first.defaultPrevented).toBe(true);
    const second = await e.escape();
    expect(e.isOpen('chatOptionsDrawer')).toBe(false);
    expect(second.stopped).toBe(true);
  });

  it('listens on window in the capture phase so it runs before the desktop\'s minimize handler', () => {
    const e = env();
    expect(e.win.listeners.keydown.some((l) => l.capture)).toBe(true);
  });

  it('with nothing open, Escape passes through untouched (the desktop may minimize Chat as before)', async () => {
    const e = env();
    const evt = await e.escape();
    expect(evt.stopped).toBe(false);
    expect(evt.defaultPrevented).toBe(false);
  });

  it('leaves Escape to the Quick Prompts picker when it is open', async () => {
    const e = env();
    await e.openDrawer();
    e.els.chatPromptsQuickPicker.classList.remove('hidden');
    const evt = await e.escape();
    expect(evt.stopped).toBe(false);
    expect(e.isOpen('chatOptionsDrawer')).toBe(true);
  });

  it('does not close the drawer when another desktop window has focus', async () => {
    const e = env({ focus: 'wiki' });
    await e.openDrawer();
    const evt = await e.escape();
    expect(e.isOpen('chatOptionsDrawer')).toBe(true);
    expect(evt.stopped).toBe(false);
  });

  it('closes the drawer when Chat has desktop focus', async () => {
    const e = env({ focus: 'chat' });
    await e.openDrawer();
    await e.escape();
    expect(e.isOpen('chatOptionsDrawer')).toBe(false);
  });

  it('the picker stops its Escape so the desktop does not also minimize Chat', async () => {
    const picker = new FakeEl(['hidden']);
    const btn = new FakeEl();
    const doc = new FakeEl();
    setupQuickPromptPicker({
      chatPromptsBtn: btn, chatPromptsQuickPicker: picker, chatPromptsQuickSearch: new FakeEl(), chatPromptsQuickList: new FakeEl(),
      chatManagePromptsBtn: new FakeEl(), promptInput: new FakeEl(), doc,
      fetchFn: async () => ({ ok: true, json: async () => [] }), setTimeoutFn: (fn) => fn(),
    });
    await btn.fire('click');
    await flush();
    expect(picker.classList.contains('hidden')).toBe(false);
    const evt = await doc.fire('keydown', { key: 'Escape' });
    expect(picker.classList.contains('hidden')).toBe(true);
    expect(evt.stopped).toBe(true);
  });
});
