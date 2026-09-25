import { describe, it, expect, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

import { loadPageHtml } from './template_helper.js';
import * as composer from '../../../src/web/static/modules/studios/chat/composer.js';

/**
 * CARD-469 - Composer wiring lost in the CARD-397 split: Enter-to-send, paperclip.
 * Behavioural tests with small element fakes (no jsdom in this repo).
 */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

class FakeClassList {
  constructor(initial = []) {
    this.set = new Set(initial);
  }
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
    this.clicks = 0;
  }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  dispatchEvent(evt) {
    return Promise.all((this.listeners[evt.type] || []).slice().map((fn) => fn(evt)));
  }
  querySelectorAll() { return []; }
  click() { this.clicks += 1; return this.dispatchEvent({ type: 'click' }); }
  focus() { this.focused = true; }
}

function keyEvent(overrides = {}) {
  const evt = { type: 'keydown', key: 'Enter', shiftKey: false, isComposing: false, keyCode: 13, prevented: false, ...overrides };
  evt.preventDefault = () => { evt.prevented = true; };
  return evt;
}

function makeForm() {
  const form = new FakeEl();
  form.submits = 0;
  form.requestSubmit = () => { form.submits += 1; };
  return form;
}

const savedMatchMedia = globalThis.matchMedia;
afterEach(() => {
  globalThis.matchMedia = savedMatchMedia;
});

describe('CARD-469 Enter-to-send (REQ-469-001..005)', () => {
  function setup({ streaming = false, form = makeForm() } = {}) {
    const promptInput = new FakeEl();
    composer.setupComposerKeyboard({ promptInput, chatForm: form, isStreaming: () => streaming });
    return { promptInput, form };
  }

  it('Enter without Shift prevents the newline and submits exactly once', async () => {
    const { promptInput, form } = setup();
    const evt = keyEvent();
    await promptInput.dispatchEvent(evt);
    expect(evt.prevented).toBe(true);
    expect(form.submits).toBe(1);
  });

  it('Shift+Enter inserts a newline and does not submit', async () => {
    const { promptInput, form } = setup();
    const evt = keyEvent({ shiftKey: true });
    await promptInput.dispatchEvent(evt);
    expect(evt.prevented).toBe(false);
    expect(form.submits).toBe(0);
  });

  it('does not submit while an IME composition is active (isComposing or keyCode 229)', async () => {
    const { promptInput, form } = setup();
    const a = keyEvent({ isComposing: true });
    const b = keyEvent({ keyCode: 229 });
    await promptInput.dispatchEvent(a);
    await promptInput.dispatchEvent(b);
    expect(a.prevented).toBe(false);
    expect(b.prevented).toBe(false);
    expect(form.submits).toBe(0);
  });

  it('sends on touch devices too - same rule as desktop (D1)', async () => {
    globalThis.matchMedia = (q) => ({ matches: /coarse/.test(q), media: q });
    const { promptInput, form } = setup();
    await promptInput.dispatchEvent(keyEvent());
    expect(form.submits).toBe(1);
  });

  it('ignores Enter while a reply is streaming (D2): no newline, no second turn', async () => {
    const { promptInput, form } = setup({ streaming: true });
    const evt = keyEvent();
    await promptInput.dispatchEvent(evt);
    expect(evt.prevented).toBe(true);
    expect(form.submits).toBe(0);
  });

  it('falls back to dispatching submit when requestSubmit is unavailable', async () => {
    const form = new FakeEl();
    const seen = [];
    form.addEventListener('submit', (e) => seen.push(e.type));
    const { promptInput } = setup({ form });
    await promptInput.dispatchEvent(keyEvent());
    expect(seen).toEqual(['submit']);
  });

  it('the submit handler starts no turn while streaming and keeps the typed text', async () => {
    const chatForm = new FakeEl();
    const promptInput = new FakeEl();
    promptInput.value = 'second message';
    const turns = [];
    composer.setupComposerControls({
      chatForm,
      promptInput,
      state: { isStreaming: true, stagedAttachments: [] },
      onExecuteTurn: (t) => turns.push(t),
    });
    await chatForm.dispatchEvent({ type: 'submit', preventDefault() {} });
    expect(turns).toEqual([]);
    expect(promptInput.value).toBe('second message');
  });
});

describe('CARD-469 wireComposer: paperclip and keyboard wired from real IDs (REQ-469-006/007)', () => {
  function env({ uploadName = 'notes.txt' } = {}) {
    const els = {
      chatAttachBtn: new FakeEl(),
      chatFileInput: new FakeEl(),
      chatAttachmentsPreviewList: new FakeEl(['hidden']),
    };
    const chatForm = makeForm();
    const promptInput = new FakeEl();
    const state = { activeSessionId: 's-1', isStreaming: false };
    const calls = [];
    const toasts = [];
    let before = 0;
    let n = 0;
    const fetchFn = async (url, init) => {
      calls.push({ url, init });
      n += 1;
      const filename = n === 1 ? uploadName : `second-${n}.txt`;
      return { ok: true, json: async () => ({ id: `f${n}`, filename, size_bytes: 12, content_type: 'text/plain', url: '/u', path: '/p' }) };
    };
    composer.wireComposer(state, {
      getEl: (id) => els[id] || null,
      chatForm,
      promptInput,
      showToastFn: (m, k) => toasts.push([m, k]),
      onBeforeAttach: () => { before += 1; },
      fetchFn,
    });
    return { els, chatForm, promptInput, state, calls, toasts, getBefore: () => before };
  }

  it('initialises state.stagedAttachments as an array', () => {
    const { state } = env();
    expect(Array.isArray(state.stagedAttachments)).toBe(true);
  });

  it('clicking the paperclip opens the file picker', async () => {
    const { els } = env();
    await els.chatAttachBtn.dispatchEvent({ type: 'click' });
    expect(els.chatFileInput.clicks).toBe(1);
  });

  it('choosing a file uploads it, stages it on state and shows a chip', async () => {
    const e = env();
    e.els.chatFileInput.value = 'C:\\fakepath\\notes.txt';
    await e.els.chatFileInput.dispatchEvent({ type: 'change', target: { files: [{ name: 'notes.txt' }] } });
    expect(e.calls.map((c) => c.url)).toEqual(['/api/chat/upload']);
    expect(e.state.stagedAttachments.map((a) => a.filename)).toEqual(['notes.txt']);
    expect(e.els.chatAttachmentsPreviewList.innerHTML).toContain('notes.txt');
    expect(e.els.chatAttachmentsPreviewList.classList.contains('hidden')).toBe(false);
    expect(e.toasts[0][0]).toContain('Attached notes.txt');
    expect(e.getBefore()).toBe(1);
    expect(e.els.chatFileInput.value).toBe('');
  });

  it('after a send clears the staged list, a new upload still stages and shows (no stale array)', async () => {
    const e = env();
    await e.els.chatFileInput.dispatchEvent({ type: 'change', target: { files: [{ name: 'a.txt' }] } });
    const arrayRef = e.state.stagedAttachments;
    composer.clearStagedAttachments(e.state, e.els.chatAttachmentsPreviewList);
    expect(e.state.stagedAttachments).toBe(arrayRef);
    expect(e.state.stagedAttachments.length).toBe(0);
    expect(e.els.chatAttachmentsPreviewList.classList.contains('hidden')).toBe(true);
    await e.els.chatFileInput.dispatchEvent({ type: 'change', target: { files: [{ name: 'b.txt' }] } });
    expect(e.state.stagedAttachments.length).toBe(1);
    expect(e.els.chatAttachmentsPreviewList.innerHTML).toContain('second-2.txt');
  });

  it('wires Enter-to-send and respects state.isStreaming', async () => {
    const e = env();
    await e.promptInput.dispatchEvent(keyEvent());
    expect(e.chatForm.submits).toBe(1);
    e.state.isStreaming = true;
    await e.promptInput.dispatchEvent(keyEvent());
    expect(e.chatForm.submits).toBe(1);
  });
});

describe('CARD-469 wiring contracts (REQ-469-012)', () => {
  const chatSrc = read('src/web/static/modules/studios/chat.js');
  const composerSrc = read('src/web/static/modules/studios/chat/composer.js');

  it('chat.js wires the composer through wireComposer with an object, never positional helper calls', () => {
    expect(chatSrc).toMatch(/wireComposer\(state,\s*\{/);
    expect(chatSrc).not.toMatch(/setupComposerKeyboard\(\s*promptInput/);
    expect(chatSrc).not.toMatch(/setupComposerAttachments\(\s*state/);
  });

  it('chat.js clears staged attachments in place instead of replacing the array', () => {
    expect(chatSrc).not.toMatch(/state\.stagedAttachments\s*=\s*\[\]/);
    expect(chatSrc).toMatch(/clearStagedAttachments\(state/);
  });

  it('chat.js does not grow past its pre-CARD-469 size (1,045 lines; CARD-456 cap work)', () => {
    expect(chatSrc.split('\n').length).toBeLessThanOrEqual(1045);
  });

  it('every element ID the composer wiring looks up exists in index.html', () => {
    const html = loadPageHtml();
    const block = composerSrc.slice(composerSrc.indexOf('export function wireComposer'));
    const ids = [...block.matchAll(/getEl\('([\w-]+)'\)/g)].map((m) => m[1]);
    expect(ids).toEqual(expect.arrayContaining(['chatAttachBtn', 'chatFileInput', 'chatAttachmentsPreviewList']));
    for (const id of ids) {
      expect(html, `#${id} missing from index.html`).toContain(`id="${id}"`);
    }
  });

  it('the placeholder still promises Enter to send, Shift+Enter for newline', () => {
    expect(loadPageHtml()).toMatch(/id="promptInput"[^>]*Enter to send, Shift\+Enter for newline/);
  });
});
