import { describe, it, expect, vi } from 'vitest';
import fs from 'fs';
import path from 'path';

import { loadPageHtml } from './template_helper.js';
import {
  COMPOSER_MAX_LINES,
  COMPOSER_MAX_COLUMN_FRACTION,
  computeComposerHeight,
  getVisibleColumnHeight,
  setupComposerSizing,
  setComposerText,
} from '../../../src/web/static/modules/studios/chat/composer.js';

/**
 * CARD-465 - Chat composer grows on focus, adaptive cap, shared setter, scroll pinning.
 * Node environment: DOM elements are small fakes (no jsdom in this repo).
 */

const LINE = 20;

class FakeTarget {
  constructor() {
    this.listeners = {};
  }
  addEventListener(type, fn) {
    (this.listeners[type] ||= []).push(fn);
  }
  removeEventListener(type, fn) {
    this.listeners[type] = (this.listeners[type] || []).filter((f) => f !== fn);
  }
  dispatchEvent(evt) {
    (this.listeners[evt.type] || []).slice().forEach((fn) => fn(evt));
    return true;
  }
  fire(type) {
    return this.dispatchEvent({ type });
  }
}

function makeTextarea(doc) {
  const el = new FakeTarget();
  el.value = '';
  el.style = {};
  el._lines = () => (el.value ? el.value.split('\n').length : 1);
  Object.defineProperty(el, 'scrollHeight', { get: () => el._lines() * LINE });
  el.focus = () => {
    doc.activeElement = el;
    el.fire('focus');
  };
  el.blur = () => {
    if (doc.activeElement === el) doc.activeElement = null;
    el.fire('blur');
  };
  return el;
}

function makeEnv({ columnHeight = 800, viewportHeight = null, messages = {} } = {}) {
  const doc = new FakeTarget();
  doc.activeElement = null;
  const win = new FakeTarget();
  win.getComputedStyle = () => ({ lineHeight: `${LINE}px`, fontSize: '14px', paddingTop: '0px', paddingBottom: '0px' });
  win.setTimeout = (fn) => fn();
  if (viewportHeight != null) {
    win.visualViewport = new FakeTarget();
    win.visualViewport.height = viewportHeight;
  }
  const promptInput = makeTextarea(doc);
  const columnEl = { clientHeight: columnHeight };
  const messagesContainer = { scrollTop: 0, scrollHeight: 2000, clientHeight: 400, ...messages };
  const composerRegion = new FakeTarget();
  return { doc, win, promptInput, columnEl, messagesContainer, composerRegion };
}

function px(el) {
  return parseFloat(el.style.height);
}

describe('computeComposerHeight [CARD-465 REQ-465-001/002/004/008]', () => {
  it('uses 8 lines and 40% of the visible column', () => {
    expect(COMPOSER_MAX_LINES).toBe(8);
    expect(COMPOSER_MAX_COLUMN_FRACTION).toBeCloseTo(0.4);
  });

  it('focused -> cap (8 lines on a tall column)', () => {
    const r = computeComposerHeight({ contentHeight: LINE, lineHeight: LINE, focused: true, hasText: false, columnHeight: 900 });
    expect(r.height).toBe(8 * LINE);
    expect(r.cap).toBe(8 * LINE);
  });

  it('blur empty -> 1 line; blur with 3 lines -> 3 lines', () => {
    expect(computeComposerHeight({ contentHeight: LINE, lineHeight: LINE, focused: false, hasText: false, columnHeight: 900 }).height).toBe(LINE);
    expect(computeComposerHeight({ contentHeight: 3 * LINE, lineHeight: LINE, focused: false, hasText: true, columnHeight: 900 }).height).toBe(3 * LINE);
  });

  it('20 lines focused -> capped with inside scroll', () => {
    const r = computeComposerHeight({ contentHeight: 20 * LINE, lineHeight: LINE, focused: true, hasText: true, columnHeight: 900 });
    expect(r.height).toBe(8 * LINE);
    expect(r.overflow).toBe(true);
  });

  it('short column (phone with keyboard) -> cap is 40% of visible height', () => {
    const r = computeComposerHeight({ contentHeight: LINE, lineHeight: LINE, focused: true, hasText: false, columnHeight: 300 });
    expect(r.cap).toBe(120);
    expect(r.height).toBe(120);
  });

  it('never below one line, and unknown column height falls back to 8 lines', () => {
    expect(computeComposerHeight({ contentHeight: LINE, lineHeight: LINE, focused: true, hasText: false, columnHeight: 20 }).height).toBe(LINE);
    expect(computeComposerHeight({ contentHeight: LINE, lineHeight: LINE, focused: true, hasText: false, columnHeight: 0 }).height).toBe(8 * LINE);
  });
});

describe('getVisibleColumnHeight [REQ-465-008]', () => {
  it('visualViewport smaller than the column wins (iOS keyboard)', () => {
    expect(getVisibleColumnHeight({ clientHeight: 700 }, { visualViewport: { height: 350 } })).toBe(350);
    expect(getVisibleColumnHeight({ clientHeight: 500 }, { visualViewport: { height: 800 } })).toBe(500);
    expect(getVisibleColumnHeight({ clientHeight: 500 }, {})).toBe(500);
    expect(getVisibleColumnHeight(null, {})).toBe(0);
  });
});

describe('setupComposerSizing [REQ-465-001..006]', () => {
  it('starts at 1 line, focus -> cap, blur empty -> 1 line', () => {
    const env = makeEnv();
    setupComposerSizing({ ...env, isStickToBottom: () => false });
    expect(px(env.promptInput)).toBe(LINE);
    env.promptInput.focus();
    expect(px(env.promptInput)).toBe(8 * LINE);
    env.promptInput.blur();
    expect(px(env.promptInput)).toBe(LINE);
  });

  it('blur with 3 lines fits content; 20 lines focused caps and scrolls inside', () => {
    const env = makeEnv();
    setupComposerSizing({ ...env, isStickToBottom: () => false });
    env.promptInput.focus();
    env.promptInput.value = Array.from({ length: 20 }, (_, i) => `line ${i}`).join('\n');
    env.promptInput.fire('input');
    expect(px(env.promptInput)).toBe(8 * LINE);
    expect(env.promptInput.style.overflowY).toBe('auto');
    env.promptInput.value = 'a\nb\nc';
    env.promptInput.fire('input');
    env.promptInput.blur();
    expect(px(env.promptInput)).toBe(3 * LINE);
    expect(env.promptInput.style.overflowY).toBe('hidden');
  });

  it('phone: visualViewport resize recomputes the cap', () => {
    const env = makeEnv({ columnHeight: 800, viewportHeight: 800 });
    setupComposerSizing({ ...env, isStickToBottom: () => false });
    env.promptInput.focus();
    expect(px(env.promptInput)).toBe(8 * LINE);
    env.win.visualViewport.height = 250; // keyboard opened
    env.win.visualViewport.fire('resize');
    expect(px(env.promptInput)).toBe(100);
  });

  it('keeps a pinned list at the bottom when the composer grows [REQ-465-006]', () => {
    const env = makeEnv({ messages: { scrollTop: 1600, scrollHeight: 2000, clientHeight: 400 } });
    setupComposerSizing({ ...env, isStickToBottom: () => true });
    env.messagesContainer.scrollHeight = 2100;
    env.promptInput.focus();
    expect(env.messagesContainer.scrollTop).toBe(2100);
  });

  it('leaves a scrolled-up list where the user was reading', () => {
    const env = makeEnv({ messages: { scrollTop: 300, scrollHeight: 2000, clientHeight: 400 } });
    setupComposerSizing({ ...env, isStickToBottom: () => false });
    env.promptInput.focus();
    expect(env.messagesContainer.scrollTop).toBe(300);
  });

  it('re-pins on window / viewport resize when stuck to bottom', () => {
    const env = makeEnv({ viewportHeight: 800, messages: { scrollTop: 1600, scrollHeight: 2000, clientHeight: 400 } });
    setupComposerSizing({ ...env, isStickToBottom: () => true });
    env.messagesContainer.scrollHeight = 2500;
    env.win.visualViewport.fire('resize');
    expect(env.messagesContainer.scrollTop).toBe(2500);
  });

  it('does not shrink mid-click inside the composer; resizes after pointer release', () => {
    const env = makeEnv();
    const timers = [];
    env.win.setTimeout = (fn) => timers.push(fn);
    setupComposerSizing({ ...env, isStickToBottom: () => false });
    env.promptInput.focus();
    expect(px(env.promptInput)).toBe(8 * LINE);
    env.composerRegion.fire('pointerdown');
    env.promptInput.blur();
    expect(px(env.promptInput)).toBe(8 * LINE);
    env.doc.fire('pointerup');
    timers.splice(0).forEach((fn) => fn());
    expect(px(env.promptInput)).toBe(LINE);
  });

  it('is null-safe', () => {
    expect(() => setupComposerSizing({})).not.toThrow();
    expect(setComposerText(null, 'x')).toBe(false);
  });
});

describe('setComposerText shared setter [REQ-465-005/009]', () => {
  it('writes the value and resizes through the input listener', () => {
    const env = makeEnv();
    setupComposerSizing({ ...env, isStickToBottom: () => false });
    expect(setComposerText(env.promptInput, 'one\ntwo\nthree\nfour')).toBe(true);
    expect(env.promptInput.value).toBe('one\ntwo\nthree\nfour');
    expect(px(env.promptInput)).toBe(4 * LINE);
    setComposerText(env.promptInput, '');
    expect(px(env.promptInput)).toBe(LINE);
  });

  it('focus option focuses the composer (then it is at the cap)', () => {
    const env = makeEnv();
    setupComposerSizing({ ...env, isStickToBottom: () => false });
    setComposerText(env.promptInput, 'hello', { focus: true });
    expect(env.doc.activeElement).toBe(env.promptInput);
    expect(px(env.promptInput)).toBe(8 * LINE);
  });

  const root = path.resolve(__dirname, '../../../src/web/static');
  const writeSites = [
    'app.js',
    'modules/studios/chat.js',
    'modules/studios/chat/stream.js',
    'modules/studios/chat/composer.js',
    'modules/studios/tools_studio.js',
    'modules/studios/forge/lab_monitor.js',
    'modules/studios/prompts.js',
    'modules/studios/projects.js',
  ];

  it.each(writeSites)('%s writes the composer only through setComposerText', (rel) => {
    const src = fs.readFileSync(path.join(root, rel), 'utf-8');
    expect(src).not.toMatch(/promptInput\.value\s*=[^=]/);
    expect(src).not.toMatch(/promptInput\.dispatchEvent\(new Event\('input'\)\)/);
    expect(src).not.toMatch(/promptInput\.style\.height/);
    if (rel !== 'modules/studios/chat/composer.js') {
      expect(src).toMatch(/setComposerText/);
    }
  });
});

describe('template contracts [REQ-465-003/007]', () => {
  const html = loadPageHtml();

  it('composer has no fixed max-h-36 cap', () => {
    const tag = html.match(/<textarea id="promptInput"[^>]*>/)[0];
    expect(tag).not.toContain('max-h-36');
  });

  it('Jump to latest sits inside the message viewport, not at a fixed bottom-28', () => {
    const start = html.indexOf('id="chatMessagesViewport"');
    expect(start).toBeGreaterThan(-1);
    const end = html.indexOf('id="chatInputWrapper"', start);
    const slice = html.slice(start, end);
    expect(slice).toContain('id="messagesContainer"');
    expect(slice).toContain('id="chatJumpToLatestBtn"');
    expect(html).not.toMatch(/bottom-28[^"]*"[^>]*>\s*<button type="button" id="chatJumpToLatestBtn"/);
    expect(html).not.toContain('bottom-28 z-20 flex justify-center');
  });

  it('chat.js wires setupComposerSizing with the scroll stick-to-bottom state', () => {
    const chatJs = fs.readFileSync(path.resolve(__dirname, '../../../src/web/static/modules/studios/chat.js'), 'utf-8');
    expect(chatJs).toMatch(/setupComposerSizing\(/);
    expect(chatJs).toMatch(/isStickToBottom/);
  });
});
