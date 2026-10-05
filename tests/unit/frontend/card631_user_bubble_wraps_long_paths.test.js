/**
 * CARD-631: user bubble can shrink (min-w-0 max-w-full); msg-body wraps long paths.
 */
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import { appendMessageBubble } from '../../../src/web/static/modules/studios/chat/render.js';

describe('CARD-631 user bubble wraps long paths', () => {
  let mockContainer;
  let originalDocument;

  beforeEach(() => {
    mockContainer = {
      nodeType: 1,
      children: [],
      appendChild(child) {
        this.children.push(child);
        return child;
      },
    };
    originalDocument = globalThis.document;
    globalThis.document = {
      createElement: (tag) => {
        const bodyEl = { nodeType: 1, className: 'msg-body', innerHTML: '' };
        const el = {
          tagName: tag.toUpperCase(),
          nodeType: 1,
          className: '',
          innerHTML: '',
          bodyEl,
          querySelectorAll: () => [],
          querySelector: (sel) => (sel === '.msg-body' ? bodyEl : null),
        };
        return el;
      },
    };
  });

  afterEach(() => {
    globalThis.document = originalDocument;
  });

  it('user bubble has min-w-0 and max-w-full so long content can shrink', () => {
    const long = 'see `D:\\Projects\\Active\\AutoReiv\\data\\attachments\\64797e5bd11e_launch-notes.txt` please';
    const bubble = appendMessageBubble('user', long, null, {
      messagesContainer: mockContainer,
      renderMarkdownFn: (el, text) => { el.innerHTML = text; },
    });
    expect(bubble).not.toBeNull();
    expect(bubble.innerHTML).toMatch(/min-w-0/);
    expect(bubble.innerHTML).toMatch(/max-w-full/);
    const inner = bubble.innerHTML;
    // The bubble shell (not the row) carries the shrink classes
    expect(inner).toContain('min-w-0 max-w-full');
    expect(inner).toContain('msg-body');
    expect(inner).toContain('break-words');
    expect(bubble.querySelector('.msg-body')).toBeTruthy();
  });

  it('msg-body CSS uses overflow-wrap anywhere (components.css)', () => {
    const css = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/css/components.css'),
      'utf-8',
    );
    expect(css).toMatch(/\.msg-body\s*\{[^}]*overflow-wrap:\s*anywhere/s);
    expect(css).toMatch(/\.msg-body code/);
  });

  it('negative: a short message still uses a max-width bubble (not forced full width on md+)', () => {
    const bubble = appendMessageBubble('user', 'hi', null, {
      messagesContainer: mockContainer,
      renderMarkdownFn: (el, text) => { el.innerHTML = text; },
    });
    expect(bubble.innerHTML).toContain('md:max-w-3xl');
    // Does not use w-full on the user bubble (that would always stretch)
    const shellMatch = bubble.innerHTML.match(/class="([^"]*min-w-0[^"]*)"/);
    expect(shellMatch).toBeTruthy();
    expect(shellMatch[1]).not.toMatch(/(^|\s)w-full(\s|$)/);
  });
});
