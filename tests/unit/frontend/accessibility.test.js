/**
 * Unit Tests for Frontend Accessibility Utilities [REQ-A11Y-001, REQ-A11Y-002, REQ-A11Y-003, REQ-A11Y-004].
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  getFocusableElements,
  handleFocusTrapKeydown,
  handleTablistKeydown,
  syncTabAria,
} from '../../../src/web/static/modules/utils/accessibility.js';

class MockElement {
  constructor(id = '', tagName = 'div', attributes = {}) {
    this.id = id;
    this.tagName = tagName.toUpperCase();
    this.attributes = { ...attributes };
    this.dataset = {};
    this.children = [];
    this.offsetWidth = 100;
    this.offsetHeight = 30;
    this.disabled = false;
  }

  getAttribute(name) {
    return this.attributes[name] !== undefined ? this.attributes[name] : null;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  hasAttribute(name) {
    return this.attributes[name] !== undefined;
  }

  focus() {
    globalThis.document.activeElement = this;
  }

  contains(el) {
    if (el === this) return true;
    return this.children.some((child) => child.contains(el));
  }

  querySelectorAll(selector) {
    const results = [];
    const walk = (node) => {
      for (const child of node.children) {
        if (child.matches(selector)) {
          results.push(child);
        }
        walk(child);
      }
    };
    walk(this);
    return results;
  }

  matches(selector) {
    if (this.disabled) return false;
    if (this.getAttribute('tabindex') === '-1') return false;

    if (selector.includes('button') && this.tagName === 'BUTTON') return true;
    if (selector.includes('a[href]') && this.tagName === 'A' && this.hasAttribute('href')) return true;
    if (selector.includes('input') && this.tagName === 'INPUT' && this.getAttribute('type') !== 'hidden') return true;
    if (selector.includes('select') && this.tagName === 'SELECT') return true;
    if (selector.includes('textarea') && this.tagName === 'TEXTAREA') return true;
    if (this.hasAttribute('tabindex') && this.getAttribute('tabindex') !== '-1') return true;
    return false;
  }
}

describe('Accessibility & Keyboard Navigation Utilities', () => {
  let container;

  beforeEach(() => {
    globalThis.document = {
      activeElement: null,
    };
    container = new MockElement('container', 'div');
  });

  describe('getFocusableElements', () => {
    it('returns empty array when container is invalid or has no focusable elements', () => {
      expect(getFocusableElements(null)).toEqual([]);
      expect(getFocusableElements({})).toEqual([]);
      expect(getFocusableElements(container)).toEqual([]);
    });

    it('identifies focusable elements and excludes disabled or hidden ones', () => {
      const btn1 = new MockElement('btn1', 'button');
      const btnDisabled = new MockElement('btnDisabled', 'button');
      btnDisabled.disabled = true;

      const link1 = new MockElement('link1', 'a', { href: '#home' });
      const inputHidden = new MockElement('inputHidden', 'input', { type: 'hidden' });
      const select1 = new MockElement('select1', 'select');
      const divFocusable = new MockElement('divFocusable', 'div', { tabindex: '0' });

      container.children = [btn1, btnDisabled, link1, inputHidden, select1, divFocusable];

      const focusable = getFocusableElements(container);
      const ids = focusable.map((el) => el.id);

      expect(ids).toContain('btn1');
      expect(ids).toContain('link1');
      expect(ids).toContain('select1');
      expect(ids).toContain('divFocusable');
      expect(ids).not.toContain('btnDisabled');
      expect(ids).not.toContain('inputHidden');
    });
  });

  describe('handleFocusTrapKeydown', () => {
    let btn1, btn2, btn3;

    beforeEach(() => {
      btn1 = new MockElement('firstBtn', 'button');
      btn2 = new MockElement('middleBtn', 'button');
      btn3 = new MockElement('lastBtn', 'button');
      container.children = [btn1, btn2, btn3];
    });

    it('ignores non-Tab keydown events', () => {
      const event = { key: 'Escape', preventDefault: vi.fn() };
      const handled = handleFocusTrapKeydown(event, container);
      expect(handled).toBe(false);
      expect(event.preventDefault).not.toHaveBeenCalled();
    });

    it('wraps focus from last element to first on forward Tab', () => {
      btn3.focus();
      expect(globalThis.document.activeElement).toBe(btn3);

      const event = { key: 'Tab', shiftKey: false, preventDefault: vi.fn() };
      const handled = handleFocusTrapKeydown(event, container);

      expect(handled).toBe(true);
      expect(event.preventDefault).toHaveBeenCalled();
      expect(globalThis.document.activeElement).toBe(btn1);
    });

    it('wraps focus from first element to last on Shift+Tab', () => {
      btn1.focus();
      expect(globalThis.document.activeElement).toBe(btn1);

      const event = { key: 'Tab', shiftKey: true, preventDefault: vi.fn() };
      const handled = handleFocusTrapKeydown(event, container);

      expect(handled).toBe(true);
      expect(event.preventDefault).toHaveBeenCalled();
      expect(globalThis.document.activeElement).toBe(btn3);
    });

    it('allows normal tab progression when focus is on a middle element', () => {
      btn2.focus();
      expect(globalThis.document.activeElement).toBe(btn2);

      const event = { key: 'Tab', shiftKey: false, preventDefault: vi.fn() };
      const handled = handleFocusTrapKeydown(event, container);

      expect(handled).toBe(false);
      expect(event.preventDefault).not.toHaveBeenCalled();
    });
  });

  describe('handleTablistKeydown', () => {
    let tab1, tab2, tab3, tabButtons, onSelectTab;

    beforeEach(() => {
      tab1 = new MockElement('tab-chat', 'button', { 'data-tab': 'chat', 'aria-selected': 'true' });
      tab1.dataset.tab = 'chat';
      tab2 = new MockElement('tab-routines', 'button', { 'data-tab': 'routines', 'aria-selected': 'false' });
      tab2.dataset.tab = 'routines';
      tab3 = new MockElement('tab-wiki', 'button', { 'data-tab': 'wiki', 'aria-selected': 'false' });
      tab3.dataset.tab = 'wiki';

      tabButtons = [tab1, tab2, tab3];
      onSelectTab = vi.fn();
    });

    it('navigates to next tab on ArrowRight / ArrowDown with wrap-around', () => {
      tab1.focus();
      const eventRight = { key: 'ArrowRight', preventDefault: vi.fn() };
      const handled = handleTablistKeydown(eventRight, tabButtons, onSelectTab);

      expect(handled).toBe(true);
      expect(eventRight.preventDefault).toHaveBeenCalled();
      expect(globalThis.document.activeElement).toBe(tab2);
      expect(onSelectTab).toHaveBeenCalledWith('routines');

      // Forward again
      const eventDown = { key: 'ArrowDown', preventDefault: vi.fn() };
      handleTablistKeydown(eventDown, tabButtons, onSelectTab);
      expect(globalThis.document.activeElement).toBe(tab3);
      expect(onSelectTab).toHaveBeenCalledWith('wiki');

      // Wrap around to start
      handleTablistKeydown(eventRight, tabButtons, onSelectTab);
      expect(globalThis.document.activeElement).toBe(tab1);
      expect(onSelectTab).toHaveBeenCalledWith('chat');
    });

    it('navigates to previous tab on ArrowLeft / ArrowUp', () => {
      tab1.focus();
      const eventLeft = { key: 'ArrowLeft', preventDefault: vi.fn() };
      const handled = handleTablistKeydown(eventLeft, tabButtons, onSelectTab);

      expect(handled).toBe(true);
      expect(eventLeft.preventDefault).toHaveBeenCalled();
      expect(globalThis.document.activeElement).toBe(tab3);
      expect(onSelectTab).toHaveBeenCalledWith('wiki');
    });

    it('navigates directly to Home or End tabs', () => {
      tab2.focus();
      const eventEnd = { key: 'End', preventDefault: vi.fn() };
      handleTablistKeydown(eventEnd, tabButtons, onSelectTab);
      expect(globalThis.document.activeElement).toBe(tab3);

      const eventHome = { key: 'Home', preventDefault: vi.fn() };
      handleTablistKeydown(eventHome, tabButtons, onSelectTab);
      expect(globalThis.document.activeElement).toBe(tab1);
    });
  });

  describe('syncTabAria', () => {
    it('sets aria-selected, tabindex, and aria-hidden appropriately', () => {
      const tabChat = new MockElement('tab-chat', 'button', { 'data-tab': 'chat' });
      tabChat.dataset.tab = 'chat';
      const tabRoutines = new MockElement('tab-routines', 'button', { 'data-tab': 'routines' });
      tabRoutines.dataset.tab = 'routines';

      const panelChat = new MockElement('chatView', 'div', { 'data-tab': 'chat' });
      panelChat.dataset.tab = 'chat';
      const panelRoutines = new MockElement('routinesView', 'div', { 'data-tab': 'routines' });
      panelRoutines.dataset.tab = 'routines';

      syncTabAria('routines', [tabChat, tabRoutines], [panelChat, panelRoutines]);

      expect(tabChat.getAttribute('aria-selected')).toBe('false');
      expect(tabChat.getAttribute('tabindex')).toBe('-1');

      expect(tabRoutines.getAttribute('aria-selected')).toBe('true');
      expect(tabRoutines.getAttribute('tabindex')).toBe('0');

      expect(panelChat.getAttribute('aria-hidden')).toBe('true');
      expect(panelRoutines.getAttribute('aria-hidden')).toBe('false');
    });
  });
});
