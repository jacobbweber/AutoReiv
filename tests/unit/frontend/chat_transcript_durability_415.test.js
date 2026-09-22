import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  appendMessageBubble,
  renderMessageItem,
  renderMessages,
  buildReasoningDrawerHtml,
} from '../../../src/web/static/modules/studios/chat/render.js';

function makeContainer() {
  const children = [];
  return {
    nodeType: 1,
    children,
    innerHTML: '',
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    querySelector() {
      return null;
    },
  };
}

function makeElement() {
  const kids = [];
  const el = {
    tagName: 'DIV',
    nodeType: 1,
    className: '',
    innerHTML: '',
    dataset: {},
    bodyEl: { nodeType: 1, className: 'msg-body', innerHTML: '' },
    listeners: {},
    appendChild(c) {
      kids.push(c);
      return c;
    },
    querySelector(sel) {
      if (sel === '.msg-body') return el.bodyEl;
      if (sel === '.reasoning-drawer') {
        return {
          querySelector(s) {
            if (s === '.reasoning-content') return { textContent: '', classList: { toggle: () => true, add() {}, remove() {} } };
            if (s === '.reasoning-toggle') return { addEventListener() {} };
            if (s === '.reasoning-indicator') return { textContent: 'Show' };
            return null;
          },
        };
      }
      if (sel === '.reasoning-content') return { textContent: '', classList: { toggle: () => true } };
      if (sel === '.reasoning-toggle') return { addEventListener() {} };
      if (sel === '.reasoning-indicator') return { textContent: 'Show' };
      return null;
    },
    querySelectorAll(sel) {
      if (String(sel).includes('btn')) {
        return [{
          addEventListener(evt, fn) {
            el.listeners[sel + ':' + evt] = fn;
          },
          dataset: { content: 'hello' },
          getAttribute: () => null,
        }];
      }
      return [];
    },
  };
  return el;
}

describe('CARD-415: Chat transcript durability (hydrate parity)', () => {
  let originalDocument;

  beforeEach(() => {
    originalDocument = globalThis.document;
    globalThis.document = {
      createElement: () => makeElement(),
    };
  });

  afterEach(() => {
    globalThis.document = originalDocument;
  });

  it('buildReasoningDrawerHtml emits Thinking Process chrome when reasoning present', () => {
    const html = buildReasoningDrawerHtml('chain of thought');
    expect(html).toContain('Thinking Process');
    expect(html).toContain('reasoning-drawer');
    expect(buildReasoningDrawerHtml('')).toBe('');
    expect(buildReasoningDrawerHtml('   ')).toBe('');
  });

  it('appendMessageBubble includes action row for assistant', () => {
    const container = makeContainer();
    const bubble = appendMessageBubble('assistant', 'Final answer', { reasoning: 'think hard' }, {
      messagesContainer: container,
      activeAgentTitle: { textContent: 'AutoReiv' },
      renderMarkdownFn: (el, text) => { el.innerHTML = text; },
    });
    expect(bubble).not.toBeNull();
    expect(bubble.innerHTML).toContain('Copy');
    expect(bubble.innerHTML).toContain('Save to Wiki');
    expect(bubble.innerHTML).toContain('Teach Agent');
    expect(bubble.innerHTML).toContain('Workbench');
    expect(bubble.innerHTML).toContain('Thinking Process');
  });

  it('renderMessageItem hydrates assistant with reasoning + actions and tool rows', () => {
    const container = makeContainer();
    const exportFn = vi.fn();
    renderMessageItem(
      { role: 'tool', name: 'wiki_note_create', content: '{"ok":true}' },
      0,
      [],
      { messagesContainer: container },
    );
    expect(container.children.length).toBe(1);
    expect(container.children[0].innerHTML).toContain('wiki_note_create');
    expect(container.children[0].innerHTML).toContain('Complete');

    renderMessageItem(
      { role: 'assistant', content: 'Done.', reasoning: 'used tool', id: 'm1' },
      1,
      [],
      {
        messagesContainer: container,
        activeAgentTitle: { textContent: 'AutoReiv' },
        renderMarkdownFn: (el, text) => { el.innerHTML = text; },
        exportMessageToWikiFn: exportFn,
      },
    );
    expect(container.children.length).toBe(2);
    const asst = container.children[1];
    expect(asst.innerHTML).toContain('Save to Wiki');
    expect(asst.innerHTML).toContain('Thinking Process');
  });

  it('renderMessages wires exportMessageToWikiFn into hydrate path', () => {
    const container = makeContainer();
    const exportFn = vi.fn();
    renderMessages({
      messagesContainer: container,
      messages: [
        { role: 'user', content: 'Hi' },
        { role: 'assistant', content: 'Hello', reasoning: 'greet' },
      ],
      isStreaming: false,
      activeAgentTitle: { textContent: 'AutoReiv' },
      renderMarkdownFn: (el, text) => { el.innerHTML = text; },
      exportMessageToWikiFn: exportFn,
    });
    // user + assistant
    expect(container.children.length).toBe(2);
    expect(container.children[1].innerHTML).toContain('Save to Wiki');
    expect(container.children[1].innerHTML).toContain('Thinking Process');
  });
});
