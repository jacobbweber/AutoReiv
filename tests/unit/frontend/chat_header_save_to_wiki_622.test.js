import { describe, it, expect, afterEach, vi } from 'vitest';

import { setupChatChrome } from '../../../src/web/static/modules/studios/chat/chrome.js';

/**
 * CARD-622 - Header Save to Wiki must call exportSessionToWiki even when app
 * callbacks are nested under callbacks.callbacks (the setupChatChrome call site
 * pattern since CARD-397; same class of bug CARD-471 fixed for Compact).
 */

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
  constructor() {
    this.listeners = {};
    this.classList = new FakeClassList();
    this.children = [];
    this.attrs = {};
    this.innerHTML = '';
    this.textContent = '';
    this.value = '';
    this.disabled = false;
    this.style = {};
    this.isConnected = true;
  }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  async fire(type, extra = {}) {
    const evt = { type, target: this, ...extra };
    for (const fn of this.listeners[type] || []) await fn(evt);
    return evt;
  }
  contains(node) { return node === this || this.children.some((c) => c.contains(node)); }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  querySelector() { return null; }
  focus() {}
}

const IDS = [
  'chatOptionsToggleBtn', 'chatOptionsDrawer', 'chatOptionsCloseBtn', 'chatOptionsToggleIcon',
  'chatManualCompactBtn', 'chatViewToolsBtn', 'chatToolsModal', 'chatToolsModalCloseBtn',
  'chatToolsModalDismissBtn', 'chatToolsModalList', 'chatToolsModalTitle', 'chatToolsModalBadge',
  'chatToolsSearchInput', 'chatPromptsQuickPicker', 'chatContextTokensBadge',
  'chatContextProgressBar', 'chatToolsCountBadge', 'promptInput', 'chatShowJourneyBtn',
  'chatJourneyDrawer', 'chatJourneyCloseBtn', 'chatJourneyContent', 'chatDebugToggleBtn',
  'chatDebugPane', 'chatDebugCloseBtn', 'chatDebugContent', 'chatDebugCopyBtn',
  'chatDebugTabMessages', 'chatDebugTabTools', 'chatDebugTabMetrics', 'chatDebugTabSystem',
  'copyThreadBtn', 'exportThreadWikiBtn',
];

function env(extraCallbacks = {}) {
  const els = {};
  IDS.forEach((id) => { els[id] = new FakeEl(); });
  ['chatOptionsDrawer', 'chatToolsModal', 'chatPromptsQuickPicker'].forEach((id) => els[id].classList.add('hidden'));
  const doc = new FakeEl();
  const win = new FakeEl();
  const toasts = [];
  const exported = [];
  const state = {
    activeSessionId: 'sess-622',
    selectedAgentId: 'autoreiv',
    messages: [
      { role: 'user', content: 'Hello' },
      { role: 'assistant', content: 'Hi there' },
    ],
  };
  const appCallbacks = {
    exportSessionToWiki: (sid) => { exported.push(sid); },
  };
  setupChatChrome(state, { ...els, doc, win }, {
    showToastFn: (m, k) => toasts.push([m, k]),
    ...extraCallbacks,
    // Mirror chat.js: nest the app bag under callbacks (CARD-397 split).
    callbacks: appCallbacks,
  });
  return { els, toasts, exported, state, appCallbacks };
}

afterEach(() => vi.restoreAllMocks());

describe('CARD-622 header Save to Wiki wiring', () => {
  it('calls exportSessionToWiki with the active session id when nested under callbacks.callbacks', async () => {
    const { els, toasts, exported } = env();
    await els.exportThreadWikiBtn.fire('click');
    expect(exported).toEqual(['sess-622']);
    expect(toasts.some((t) => String(t[0]).includes('not available'))).toBe(false);
  });

  it('also works when exportSessionToWiki is passed at the top level (chat.js CARD-622 pass-through)', async () => {
    const exported = [];
    const { els, toasts } = env({
      exportSessionToWiki: (sid) => { exported.push('top:' + sid); },
    });
    await els.exportThreadWikiBtn.fire('click');
    expect(exported).toEqual(['top:sess-622']);
    expect(toasts.some((t) => String(t[0]).includes('not available'))).toBe(false);
  });

  it('warns when there are no messages', async () => {
    const { els, toasts, exported, state } = env();
    state.messages = [];
    await els.exportThreadWikiBtn.fire('click');
    expect(exported).toEqual([]);
    expect(toasts).toEqual([['No messages to export', 'warning']]);
  });

  it('errors when neither top-level nor nested exportSessionToWiki exists', async () => {
    const els = {};
    IDS.forEach((id) => { els[id] = new FakeEl(); });
    ['chatOptionsDrawer', 'chatToolsModal', 'chatPromptsQuickPicker'].forEach((id) => els[id].classList.add('hidden'));
    const toasts = [];
    setupChatChrome(
      { activeSessionId: 's', messages: [{ role: 'user', content: 'x' }] },
      { ...els, doc: new FakeEl(), win: new FakeEl() },
      { showToastFn: (m, k) => toasts.push([m, k]) },
    );
    await els.exportThreadWikiBtn.fire('click');
    expect(toasts).toEqual([['Save to Wiki is not available (session export unwired)', 'error']]);
  });
});
