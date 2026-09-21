import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';
import { appendMessageBubble } from '../../../src/web/static/modules/studios/chat/render.js';

describe('CARD-406: Chat Input Render Bubble Integrity', () => {
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
        const bodyEl = {
          nodeType: 1,
          className: 'msg-body',
          innerHTML: '',
        };
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

  it('renders user message bubble when messagesContainer is passed in options object (4th parameter)', () => {
    const bubble = appendMessageBubble('user', 'Hello Agent', null, {
      messagesContainer: mockContainer,
      activeAgentTitle: { textContent: 'AutoReiv' },
      renderMarkdownFn: (targetEl, text) => {
        targetEl.innerHTML = text;
      },
    });

    expect(bubble).not.toBeNull();
    expect(mockContainer.children.length).toBe(1);
    expect(mockContainer.children[0]).toBe(bubble);
    expect(bubble.className).toContain('justify-end');
    expect(bubble.innerHTML).toContain('You');
    expect(bubble.bodyEl.innerHTML).toBe('Hello Agent');
  });

  it('renders user message bubble when container is passed as 3rd parameter (polymorphic compatibility)', () => {
    const bubble = appendMessageBubble('user', 'Polymorphic test', mockContainer, {
      activeAgentId: 'autoreiv',
      renderMarkdownFn: (targetEl, text) => {
        targetEl.innerHTML = text;
      },
    });

    expect(bubble).not.toBeNull();
    expect(mockContainer.children.length).toBe(1);
    expect(mockContainer.children[0]).toBe(bubble);
    expect(bubble.className).toContain('justify-end');
    expect(bubble.innerHTML).toContain('You');
    expect(bubble.bodyEl.innerHTML).toBe('Polymorphic test');
  });

  it('returns null and does not throw if no container is provided anywhere', () => {
    const bubble = appendMessageBubble('user', 'Orphan message', null, {});
    expect(bubble).toBeNull();
  });

  it('verifies chat.js executeChatTurn passes messagesContainer into appendMessageBubbleDirect options', () => {
    const chatJs = fs.readFileSync(
      path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'),
      'utf-8',
    );
    expect(chatJs).toMatch(
      /appendMessageBubbleDirect\(\s*['"]user['"]\s*,\s*userPrompt\s*,\s*null\s*,\s*\{[\s\S]*?messagesContainer/,
    );
  });
});
