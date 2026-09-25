import { describe, it, expect } from 'vitest';

import * as stream from '../../../src/web/static/modules/studios/chat/stream.js';

/**
 * CARD-475 - a text-only model that gets an image still answers, and the user sees why the
 * picture was ignored. The backend sends `event: attachment_notice`; the finalize step reloads
 * the thread from the DB, so the notice is rendered after the reload, like the CARD-469 error.
 */

const D6 = "This model can't view images, so it only saw the file name `shot.png`. "
  + 'Switch to a vision model (e.g. gemma-4-26b-a4b) to include pictures.';

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
      tag, className: '', textContent: '', attrs: {},
      setAttribute(k, v) { this.attrs[k] = v; },
    }),
  };
}

function fakeContainer() {
  return { children: [], appendChild(el) { this.children.push(el); return el; } };
}

const NOTICE_STREAM =
  `event: attachment_notice\ndata: ${JSON.stringify({ type: 'attachment_notice', message: D6, files: ['shot.png'] })}\n\n`
  + 'event: token\ndata: {"text": "I cannot see pictures."}\n\n'
  + 'event: turn_done\ndata: {"content": "I cannot see pictures."}\n\n';

describe('CARD-475 attachment notice', () => {
  it('collects the notice and does not count it as a failure', async () => {
    const outcome = stream.trackStreamOutcome();
    await stream.consumeChatStream(sseResponse(NOTICE_STREAM), { onEvent: (t, ev) => outcome.note(t, ev) });
    expect(outcome.notices()).toEqual([D6]);
    expect(outcome.failureMessage()).toBe(null);
  });

  it('renders the notice under the reply after the reload, with the exact D6 wording', async () => {
    const outcome = stream.trackStreamOutcome();
    await stream.consumeChatStream(sseResponse(NOTICE_STREAM), { onEvent: (t, ev) => outcome.note(t, ev) });
    const container = fakeContainer();
    const failed = stream.reportStreamOutcome(outcome, { messagesContainer: container, doc: fakeDoc() });
    expect(failed).toBe(false);
    expect(container.children).toHaveLength(1);
    const el = container.children[0];
    expect(el.className).toContain('chat-attachment-notice');
    expect(el.attrs.role).toBe('status');
    expect(el.textContent).toBe(D6);
  });

  it('the same notice twice in one turn renders once', () => {
    const outcome = stream.trackStreamOutcome();
    outcome.note('attachment_notice', { message: D6 });
    outcome.note('attachment_notice', { message: D6 });
    expect(outcome.notices()).toEqual([D6]);
  });

  it('a notice plus a failure shows both', () => {
    const outcome = stream.trackStreamOutcome();
    outcome.note('attachment_notice', { message: D6 });
    outcome.note('error', { error: 'The model returned an empty reply.' });
    const container = fakeContainer();
    expect(stream.reportStreamOutcome(outcome, { messagesContainer: container, doc: fakeDoc() })).toBe(true);
    expect(container.children.map((c) => c.className.split(' ')[0])).toEqual([
      'chat-attachment-notice', 'chat-stream-error',
    ]);
  });
});
