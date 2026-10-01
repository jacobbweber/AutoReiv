import { describe, it, expect, beforeEach } from 'vitest';

import { renderMessageItem } from '../../../src/web/static/modules/studios/chat/render.js';
import * as stream from '../../../src/web/static/modules/studios/chat/stream.js';

// CARD-482: the can't-view-images notice is a saved chat note; the thread shows it after a reload.
const TEXT = "This model can't view images, so it only saw the file name `shot.png`.";

function fakeDoc() {
  return {
    createElement: (tag) => ({
      tag, className: '', textContent: '', attrs: {},
      setAttribute(k, v) { this.attrs[k] = v; },
      getAttribute(k) { return this.attrs[k]; },
    }),
  };
}

function fakeContainer() {
  return {
    children: [],
    appendChild(el) { this.children.push(el); return el; },
    querySelectorAll(sel) {
      const cls = sel.replace(/^\./, '');
      return this.children.filter((c) => String(c.className).split(/\s+/).includes(cls));
    },
  };
}

describe('CARD-482 chat note', () => {
  let doc;
  beforeEach(() => {
    doc = fakeDoc();
    globalThis.document = doc;
  });

  it('renders a note row as a status line, not a chat bubble [REQ-482-001]', () => {
    const box = fakeContainer();
    let bubbles = 0;
    renderMessageItem({ role: 'note', name: 'attachment_notice', content: TEXT }, 0, [], {
      messagesContainer: box, appendMessageBubbleFn: () => { bubbles += 1; },
    });
    expect(bubbles).toBe(0);
    const notes = box.querySelectorAll('.chat-note');
    expect(notes.length).toBe(1);
    expect(notes[0].className).toContain('chat-attachment-notice');
    expect(notes[0].getAttribute('role')).toBe('status');
    expect(notes[0].textContent).toBe(TEXT);
  });

  it('does not draw the live notice twice when the reloaded thread already shows it', () => {
    const box = fakeContainer();
    renderMessageItem({ role: 'note', content: TEXT }, 0, [], { messagesContainer: box });
    const outcome = stream.trackStreamOutcome();
    outcome.note('attachment_notice', { message: TEXT });
    stream.reportStreamOutcome(outcome, { messagesContainer: box, doc });
    expect(box.querySelectorAll('.chat-attachment-notice').length).toBe(1);
  });

  it('still draws the live notice when nothing saved it yet', () => {
    const box = fakeContainer();
    const outcome = stream.trackStreamOutcome();
    outcome.note('attachment_notice', { message: TEXT });
    stream.reportStreamOutcome(outcome, { messagesContainer: box, doc });
    expect(box.querySelectorAll('.chat-attachment-notice').length).toBe(1);
  });
});
