import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import { loadPageHtml } from './template_helper.js';
import * as qp from '../../../src/web/static/modules/studios/chat/quick_prompts.js';

/**
 * CARD-469 - Quick Prompts picker in Chat rewired to the real template IDs (REQ-469-008..012).
 */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

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
    this.innerHTML = '';
    this.value = '';
    this.children = [];
  }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  dispatchEvent(evt) {
    return Promise.all((this.listeners[evt.type] || []).slice().map((fn) => fn(evt)));
  }
  contains(node) { return node === this || this.children.includes(node); }
  focus() { this.focused = (this.focused || 0) + 1; }
}

const PROMPTS = [
  { id: 'p1', title: 'Deploy checklist', category: 'ops', description: 'Ship it', template_text: 'Walk me through a deploy.' },
  { id: 'p2', title: 'Code <review>', category: 'dev', description: '', template_text: 'Review this diff for bugs.' },
];

const flush = () => new Promise((r) => setTimeout(r, 0));

function env({ data = PROMPTS } = {}) {
  const els = {
    chatPromptsBtn: new FakeEl(),
    chatPromptsQuickPicker: new FakeEl(['hidden']),
    chatPromptsQuickSearch: new FakeEl(),
    chatPromptsQuickList: new FakeEl(),
    chatManagePromptsBtn: new FakeEl(),
  };
  els.chatPromptsQuickPicker.children.push(els.chatPromptsQuickSearch, els.chatPromptsQuickList, els.chatManagePromptsBtn);
  const promptInput = new FakeEl();
  const inputEvents = [];
  promptInput.addEventListener('input', () => inputEvents.push(promptInput.value));
  const doc = new FakeEl();
  const fetched = [];
  const toasts = [];
  let picked = 0;
  let managed = 0;
  qp.setupQuickPromptPicker({
    ...els,
    promptInput,
    doc,
    fetchFn: async (url) => { fetched.push(url); return { ok: true, json: async () => data }; },
    setTimeoutFn: (fn) => fn(),
    showToastFn: (m, k) => toasts.push([m, k]),
    onPicked: () => { picked += 1; },
    onManage: () => { managed += 1; },
  });
  const openPicker = async () => {
    await els.chatPromptsBtn.dispatchEvent({ type: 'click', target: els.chatPromptsBtn, stopPropagation() {} });
    await flush();
  };
  const itemTarget = (idx) => ({
    closest: (sel) => (sel === '[data-quick-idx]' ? { getAttribute: () => String(idx) } : null),
  });
  return { els, promptInput, inputEvents, doc, fetched, toasts, openPicker, itemTarget, picked: () => picked, managed: () => managed };
}

describe('CARD-469 Quick Prompts picker', () => {
  it('the Quick Prompts button opens the picker, focuses the filter and loads /api/prompts', async () => {
    const e = env();
    e.els.chatPromptsQuickSearch.value = 'stale';
    await e.openPicker();
    expect(e.els.chatPromptsQuickPicker.classList.contains('hidden')).toBe(false);
    expect(e.els.chatPromptsQuickSearch.value).toBe('');
    expect(e.els.chatPromptsQuickSearch.focused).toBe(1);
    expect(e.fetched).toEqual(['/api/prompts']);
    expect(e.els.chatPromptsQuickList.innerHTML).toContain('Deploy checklist');
    expect(e.els.chatPromptsQuickList.innerHTML).toContain('data-quick-idx="1"');
  });

  it('escapes prompt titles', async () => {
    const e = env();
    await e.openPicker();
    expect(e.els.chatPromptsQuickList.innerHTML).toContain('Code &lt;review&gt;');
    expect(e.els.chatPromptsQuickList.innerHTML).not.toContain('<review>');
  });

  it('clicking the button again closes the picker', async () => {
    const e = env();
    await e.openPicker();
    await e.openPicker();
    expect(e.els.chatPromptsQuickPicker.classList.contains('hidden')).toBe(true);
  });

  it('accepts a {prompts: [...]} response shape', async () => {
    const e = env({ data: { prompts: PROMPTS } });
    await e.openPicker();
    expect(e.els.chatPromptsQuickList.innerHTML).toContain('Deploy checklist');
  });

  it('typing in the filter narrows by title, category, description or template text', async () => {
    const e = env();
    await e.openPicker();
    e.els.chatPromptsQuickSearch.value = 'diff';
    await e.els.chatPromptsQuickSearch.dispatchEvent({ type: 'input' });
    expect(e.els.chatPromptsQuickList.innerHTML).toContain('Code &lt;review&gt;');
    expect(e.els.chatPromptsQuickList.innerHTML).not.toContain('Deploy checklist');
    e.els.chatPromptsQuickSearch.value = 'zzz-nothing';
    await e.els.chatPromptsQuickSearch.dispatchEvent({ type: 'input' });
    expect(e.els.chatPromptsQuickList.innerHTML).toContain('No matching prompts');
  });

  it('clicking a prompt puts its template_text in the box, resizes, focuses, closes the picker and toasts', async () => {
    const e = env();
    await e.openPicker();
    await e.els.chatPromptsQuickList.dispatchEvent({ type: 'click', target: e.itemTarget(0) });
    expect(e.promptInput.value).toBe('Walk me through a deploy.');
    expect(e.inputEvents).toEqual(['Walk me through a deploy.']);
    expect(e.promptInput.focused).toBe(1);
    expect(e.els.chatPromptsQuickPicker.classList.contains('hidden')).toBe(true);
    expect(e.toasts[0][0]).toBe('Loaded "Deploy checklist"');
    expect(e.picked()).toBe(1);
  });

  it('a pick after filtering inserts the filtered item, not the original index', async () => {
    const e = env();
    await e.openPicker();
    e.els.chatPromptsQuickSearch.value = 'review';
    await e.els.chatPromptsQuickSearch.dispatchEvent({ type: 'input' });
    await e.els.chatPromptsQuickList.dispatchEvent({ type: 'click', target: e.itemTarget(0) });
    expect(e.promptInput.value).toBe('Review this diff for bugs.');
  });

  it('clicking outside or pressing Escape closes the picker; clicking inside does not', async () => {
    const e = env();
    await e.openPicker();
    await e.doc.dispatchEvent({ type: 'click', target: e.els.chatPromptsQuickSearch });
    expect(e.els.chatPromptsQuickPicker.classList.contains('hidden')).toBe(false);
    await e.doc.dispatchEvent({ type: 'click', target: new FakeEl() });
    expect(e.els.chatPromptsQuickPicker.classList.contains('hidden')).toBe(true);
    await e.openPicker();
    await e.doc.dispatchEvent({ type: 'keydown', key: 'Escape' });
    expect(e.els.chatPromptsQuickPicker.classList.contains('hidden')).toBe(true);
  });

  it('Manage in Prompts Studio closes the picker and opens the Prompts studio', async () => {
    const e = env();
    await e.openPicker();
    await e.els.chatManagePromptsBtn.dispatchEvent({ type: 'click' });
    expect(e.els.chatPromptsQuickPicker.classList.contains('hidden')).toBe(true);
    expect(e.managed()).toBe(1);
  });
});

describe('CARD-469 Quick Prompts wiring contracts', () => {
  const chromeSrc = read('src/web/static/modules/studios/chat/chrome.js');

  it('chrome.js no longer looks up the ghost prompt IDs', () => {
    for (const ghost of ['chatPromptCatalogBtn', 'chatClosePromptsModalBtn', 'chatPromptsModalList']) {
      expect(chromeSrc).not.toContain(ghost);
    }
  });

  it('chrome.js wires the picker with the real template IDs, all present in index.html', () => {
    const html = loadPageHtml();
    const ids = ['chatPromptsBtn', 'chatPromptsQuickPicker', 'chatPromptsQuickSearch', 'chatPromptsQuickList', 'chatManagePromptsBtn'];
    expect(chromeSrc).toContain('setupQuickPromptPicker(');
    for (const id of ids) {
      expect(chromeSrc).toContain(`getEl('${id}')`);
      expect(html, `#${id} missing from index.html`).toContain(`id="${id}"`);
    }
  });
});
