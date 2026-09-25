import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

import * as stream from '../../../src/web/static/modules/studios/chat/stream.js';

/**
 * CARD-469 follow-up - a failed reply must show an error, never silence.
 * Before the CARD-397 split, chat.js rendered `error` SSE events ("Error: ...") in the reply bubble.
 * The split dropped that branch, and the finalize step reloads messages from the DB, so a failed
 * turn (e.g. an image sent to a text-only model) just vanished.
 */

const ROOT = path.resolve(__dirname, '../../..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf-8');

function sseResponse(text) {
  const bytes = new TextEncoder().encode(text);
  let done = false;
  return {
    body: {
      getReader: () => ({
        read: async () => {
          if (done) return { done: true };
          done = true;
          return { value: bytes, done: false };
        },
      }),
    },
  };
}

function fakeDoc() {
  return {
    createElement: (tag) => ({
      tag,
      className: '',
      textContent: '',
      attrs: {},
      setAttribute(k, v) { this.attrs[k] = v; },
    }),
  };
}

function fakeContainer() {
  return { children: [], appendChild(el) { this.children.push(el); return el; } };
}

describe('CARD-469 stream outcome: failed replies are reported', () => {
  it('an `event: error` from the backend is captured with its message', async () => {
    const outcome = stream.trackStreamOutcome();
    const res = sseResponse('event: error\ndata: {"error": "[vllm] Provider HTTP error 400: text-only-model is not a multimodal model"}\n\n');
    await stream.consumeChatStream(res, { onEvent: (t, ev) => outcome.note(t, ev) });
    expect(outcome.failureMessage()).toContain('not a multimodal model');
  });

  it('a normal reply reports no failure', async () => {
    const outcome = stream.trackStreamOutcome();
    const res = sseResponse('event: token\ndata: {"text": "Hello"}\n\nevent: turn_done\ndata: {"content": "Hello"}\n\n');
    await stream.consumeChatStream(res, { onEvent: (t, ev) => outcome.note(t, ev) });
    expect(outcome.failureMessage()).toBe(null);
  });

  it('a stream that ends with no events at all is reported, not silent', async () => {
    const outcome = stream.trackStreamOutcome();
    await stream.consumeChatStream(sseResponse(''), { onEvent: (t, ev) => outcome.note(t, ev) });
    expect(outcome.failureMessage()).toMatch(/ended without a response/i);
  });

  it('an error inside turn_done (worker exception path) is also reported', () => {
    const outcome = stream.trackStreamOutcome();
    outcome.note('turn_done', { content: 'x', error: 'boom' });
    expect(outcome.failureMessage()).toBe('boom');
  });

  it('reportStreamOutcome appends a visible alert and toasts on failure', () => {
    const outcome = stream.trackStreamOutcome();
    outcome.note('error', { error: 'model rejected the image' });
    const container = fakeContainer();
    const toasts = [];
    const shown = stream.reportStreamOutcome(outcome, {
      messagesContainer: container,
      showToastFn: (m, k) => toasts.push([m, k]),
      doc: fakeDoc(),
    });
    expect(shown).toBe(true);
    expect(container.children.length).toBe(1);
    const el = container.children[0];
    expect(el.className).toContain('chat-stream-error');
    expect(el.attrs.role).toBe('alert');
    expect(el.textContent).toContain('model rejected the image');
    expect(toasts).toEqual([[expect.stringContaining('model rejected the image'), 'error']]);
  });

  it('reportStreamOutcome does nothing on success', () => {
    const outcome = stream.trackStreamOutcome();
    outcome.note('token', { text: 'hi' });
    const container = fakeContainer();
    const toasts = [];
    expect(stream.reportStreamOutcome(outcome, { messagesContainer: container, showToastFn: (m) => toasts.push(m), doc: fakeDoc() })).toBe(false);
    expect(container.children).toEqual([]);
    expect(toasts).toEqual([]);
  });
});

describe('CARD-469 stream error wiring contract', () => {
  const chatSrc = read('src/web/static/modules/studios/chat.js');

  it('chat.js notes every stream event and reports the outcome after the finalize reload', () => {
    expect(chatSrc).toMatch(/trackStreamOutcome\(\)/);
    expect(chatSrc).toMatch(/outcome\.note\(eventType, ev\)/);
    const finalize = chatSrc.indexOf('await loadMessages(state.activeSessionId);\n      } else if (streamContentEl && accumulatedContent)'.replace(/\n/g, chatSrc.includes('\r\n') ? '\r\n' : '\n'));
    const report = chatSrc.indexOf('reportStreamOutcome(outcome');
    expect(finalize).toBeGreaterThan(-1);
    expect(report).toBeGreaterThan(finalize);
  });
});
