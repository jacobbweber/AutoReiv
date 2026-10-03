import { describe, it, expect, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

import { setupComposerControls, setComposerText } from '../../../src/web/static/modules/studios/chat/composer.js';
import { restoreFailedSend, shouldRestoreFailedSend, showFailedTurn } from '../../../src/web/static/modules/studios/chat/failed_send.js';

/**
 * CARD-484: a failed Chat send must not throw away the typed message.
 * Element fakes, no jsdom (repo convention).
 */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

class FakeEl {
  constructor() { this.listeners = {}; this.value = ''; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  dispatchEvent(evt) { return Promise.all((this.listeners[evt.type] || []).slice().map((fn) => fn(evt))); }
  focus() {}
}

const abortError = () => Object.assign(new Error('The operation was aborted.'), { name: 'AbortError' });
const savedFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = savedFetch; });

/** The executeChatTurn failure path in small: fetch, throw on !ok, restore in the catch. */
function wireComposer({ status = 500, throwErr = null, streamFirst = '' } = {}) {
  const toasts = [];
  const bubble = { innerHTML: '' };
  globalThis.fetch = async () => {
    if (throwErr) throw throwErr;
    return { ok: status >= 200 && status < 300, status };
  };
  const chatForm = new FakeEl();
  const promptInput = new FakeEl();
  const state = { activeSessionId: 's1', isStreaming: false, stagedAttachments: [], messages: [] };
  const seen = { sentText: null, boxDuringTurn: null };
  const onExecuteTurn = async (userPrompt) => {
    seen.sentText = userPrompt;
    seen.boxDuringTurn = promptInput.value;
    let accumulated = '';
    try {
      const response = await fetch('/api/chat/stream', { method: 'POST' });
      if (!response.ok) throw new Error(`Stream error: HTTP ${response.status}`);
      accumulated += streamFirst;
      if (streamFirst) throw new Error('stream dropped');
    } catch (err) {
      if (err.name === 'AbortError') return;
      showFailedTurn({ err, showToast: (m, kind) => toasts.push([m, kind]), streamContentEl: bubble, isResume: false, userPrompt, replyStarted: accumulated.length > 0, promptInput, setText: setComposerText });
    }
  };
  setupComposerControls({ chatForm, promptInput, state, onExecuteTurn });
  const send = async (text) => {
    promptInput.value = text;
    await chatForm.dispatchEvent({ type: 'submit', preventDefault() {} });
  };
  return { promptInput, send, seen, toasts, bubble };
}

describe('REQ-484-001: a failed send restores the typed text', () => {
  it('HTTP 500: the box is cleared during the turn, then "hello" is back', async () => {
    const { promptInput, send, seen, toasts, bubble } = wireComposer({ status: 500 });
    await send('hello');
    expect(toasts).toEqual([['Chat turn failed: Stream error: HTTP 500', 'error']]);
    expect(bubble.innerHTML).toContain('Error: Stream error: HTTP 500');
    expect(seen.sentText).toBe('hello');
    expect(seen.boxDuringTurn).toBe('');
    expect(promptInput.value).toBe('hello');
  });

  it('HTTP 422 and a network drop restore too', async () => {
    const a = wireComposer({ status: 422 });
    await a.send('validate me');
    expect(a.promptInput.value).toBe('validate me');
    const b = wireComposer({ throwErr: new TypeError('Failed to fetch') });
    await b.send('offline');
    expect(b.promptInput.value).toBe('offline');
  });

  it('a successful send leaves the box empty', async () => {
    const { promptInput, send } = wireComposer({ status: 200 });
    await send('hello');
    expect(promptInput.value).toBe('');
  });

  it('a failure after the reply started streaming does not restore', async () => {
    const { promptInput, send } = wireComposer({ status: 200, streamFirst: 'Partial answer' });
    await send('hello');
    expect(promptInput.value).toBe('');
  });

  it('never overwrites text typed since the send', () => {
    const promptInput = { value: 'new draft' };
    const done = restoreFailedSend({ err: new Error('HTTP 500'), userPrompt: 'hello', promptInput, setText: (el, t) => { el.value = t; } });
    expect(done).toBe(false);
    expect(promptInput.value).toBe('new draft');
  });
});

describe('REQ-484-002: Stop never restores', () => {
  it('AbortError leaves the box empty', async () => {
    const { promptInput, send } = wireComposer({ throwErr: abortError() });
    await send('hello');
    expect(promptInput.value).toBe('');
  });

  it('rules: resume, empty prompt and no error do not restore', () => {
    expect(shouldRestoreFailedSend({ err: new Error('x'), userPrompt: 'hi' })).toBe(true);
    expect(shouldRestoreFailedSend({ err: abortError(), userPrompt: 'hi' })).toBe(false);
    expect(shouldRestoreFailedSend({ err: new Error('x'), userPrompt: '', isResume: false })).toBe(false);
    expect(shouldRestoreFailedSend({ err: new Error('x'), userPrompt: 'hi', isResume: true })).toBe(false);
    expect(shouldRestoreFailedSend({ err: null, userPrompt: 'hi' })).toBe(false);
  });
});

describe('wiring: executeChatTurn restores in its catch', () => {
  it('chat.js routes its non-Stop catch through showFailedTurn with the sent text', () => {
    const src = read('src/web/static/modules/studios/chat.js');
    expect(src).toContain("from './chat/failed_send.js'");
    const guardAt = src.indexOf("if (err.name !== 'AbortError' && ownStream.isCurrent(turn)) {");
    const callAt = src.indexOf('showFailedTurn({', guardAt);
    expect(guardAt).toBeGreaterThan(0);
    expect(callAt - guardAt).toBeLessThan(120);
    const call = src.slice(callAt, src.indexOf('\n', callAt));
    for (const part of ['userPrompt', 'isResume: options.isResume', 'replyStarted: accumulatedContent.length > 0', 'promptInput', 'setText: setComposerText']) {
      expect(call).toContain(part);
    }
  });
});
