/**
 * Unit & Regression Tests for Chat Studio SSE Stream Event Parsing and Message Load Rendering (CARD-401)
 * [REQ-401-001, REQ-401-002, REQ-401-003, REQ-401-004]
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { consumeChatStream } from '../../../src/web/static/modules/studios/chat/stream.js';
import { renderMessages } from '../../../src/web/static/modules/studios/chat/render.js';

class MockDOMElement {
  constructor(id = '', tagName = 'div') {
    this.id = id;
    this.tagName = tagName.toUpperCase();
    this.attributes = {};
    const classes = new Set();
    this.classList = {
      add: (...tokens) => tokens.forEach((t) => classes.add(t)),
      remove: (...tokens) => tokens.forEach((t) => classes.delete(t)),
      contains: (token) => classes.has(token),
    };
    this.children = [];
    this.innerHTML = '';
    this.textContent = '';
  }

  getAttribute(name) {
    return this.attributes[name] !== undefined ? this.attributes[name] : null;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  appendChild(child) {
    this.children.push(child);
  }

  querySelectorAll() {
    return [];
  }
}

function createMockStreamResponse(chunks) {
  let index = 0;
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]));
        index++;
      } else {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

describe('CARD-401: SSE Stream Event Parsing & Token Dispatch', () => {
  it('[REQ-401-001] correctly dispatches onReasoning and onToken for standard multi-line SSE', async () => {
    const ssePayload = [
      'event: reasoning\ndata: {"text": "Let me think..."}\n\n',
      'event: reasoning\ndata: {"text": " Analyzing prompt."}\n\n',
      'event: token\ndata: {"text": "Hello"}\n\n',
      'event: token\ndata: {"text": " world!"}\n\n',
      'event: turn_done\ndata: {"content": "Hello world!"}\n\n',
    ];

    const response = createMockStreamResponse(ssePayload);
    const reasoningTokens = [];
    const contentTokens = [];
    const eventsReceived = [];

    await consumeChatStream(response, {
      onReasoning: (text) => {
        reasoningTokens.push(text);
      },
      onToken: (text) => {
        contentTokens.push(text);
      },
      onEvent: (eventType, ev) => {
        eventsReceived.push({ eventType, ev });
      },
    });

    expect(reasoningTokens.join('')).toBe('Let me think... Analyzing prompt.');
    expect(contentTokens.join('')).toBe('Hello world!');
    expect(eventsReceived.map((e) => e.eventType)).toEqual([
      'reasoning',
      'reasoning',
      'token',
      'token',
      'turn_done',
    ]);
  });

  it('[REQ-401-004] Negative Assertion: SSE chunks lacking type in JSON body still fire onToken and onReasoning via event header', async () => {
    // Before CARD-401, this exact payload resulted in 0 onToken/onReasoning calls because eventType was undefined
    const ssePayloadWithoutJsonType = [
      'event: reasoning\ndata: {"text": "Thinking deeply"}\n\n',
      'event: token\ndata: {"text": "Real response"}\n\n',
    ];

    const response = createMockStreamResponse(ssePayloadWithoutJsonType);
    let capturedReasoning = '';
    let capturedContent = '';

    await consumeChatStream(response, {
      onReasoning: (text) => { capturedReasoning += text; },
      onToken: (text) => { capturedContent += text; },
    });

    expect(capturedReasoning).not.toBe('');
    expect(capturedReasoning).toBe('Thinking deeply');
    expect(capturedContent).not.toBe('');
    expect(capturedContent).toBe('Real response');
  });

  it('supports payload with embedded type property as defense-in-depth', async () => {
    const ssePayloadWithJsonType = [
      'data: {"type": "reasoning", "text": "Thought A"}\n\n',
      'data: {"type": "token", "text": "Answer B"}\n\n',
    ];

    const response = createMockStreamResponse(ssePayloadWithJsonType);
    let reasoning = '';
    let tokens = '';

    await consumeChatStream(response, {
      onReasoning: (t) => { reasoning += t; },
      onToken: (t) => { tokens += t; },
    });

    expect(reasoning).toBe('Thought A');
    expect(tokens).toBe('Answer B');
  });
});

describe('CARD-401: Conversation History & renderMessages Compatibility', () => {
  let prevDoc;

  beforeEach(() => {
    prevDoc = globalThis.document;
    globalThis.document = {
      createElement: (tag) => new MockDOMElement('', tag),
    };
  });

  afterEach(() => {
    globalThis.document = prevDoc;
  });

  it('[REQ-401-003] renderMessages safely renders when passed an options object', () => {
    const container = new MockDOMElement('messagesContainer', 'div');
    const messages = [
      { id: '1', role: 'user', content: 'Hi there' },
      { id: '2', role: 'assistant', content: 'Hello user' },
    ];

    const mockRenderItem = vi.fn();

    renderMessages({
      messagesContainer: container,
      messages,
      isStreaming: false,
      renderMessageItemFn: mockRenderItem,
    });

    expect(mockRenderItem).toHaveBeenCalledTimes(2);
    expect(mockRenderItem).toHaveBeenCalledWith(messages[0], 0, messages, expect.any(Object));
    expect(mockRenderItem).toHaveBeenCalledWith(messages[1], 1, messages, expect.any(Object));
  });

  it('[REQ-401-003] renderMessages is backward-compatible with legacy positional arguments (messages, container, opts)', () => {
    const container = new MockDOMElement('messagesContainer', 'div');
    const messages = [
      { id: 'm1', role: 'user', content: 'Legacy test' },
    ];

    const mockRenderItem = vi.fn();

    renderMessages(messages, container, {
      renderMessageItemFn: mockRenderItem,
    });

    expect(mockRenderItem).toHaveBeenCalledTimes(1);
    expect(mockRenderItem).toHaveBeenCalledWith(messages[0], 0, messages, expect.any(Object));
  });

  it('renderMessages displays friendly empty state when messages array is empty', () => {
    const container = new MockDOMElement('messagesContainer', 'div');
    const activeAgentTitle = new MockDOMElement('activeAgentTitle', 'span');
    activeAgentTitle.textContent = 'Direct Agent';

    renderMessages({
      messagesContainer: container,
      messages: [],
      activeAgentTitle,
    });

    expect(container.innerHTML).toContain('Start a new conversation with Direct Agent');
  });
});
