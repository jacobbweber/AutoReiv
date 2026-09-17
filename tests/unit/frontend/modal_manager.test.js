import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  openModal,
  closeModal,
  toggleModal,
  isModalOpen,
  setupModal,
  getActiveModal,
  getModalStack,
  clearModals,
  handleEscapeKey,
} from '../../../src/web/static/modules/ui/modal.js';

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
      toggle: (token) => {
        if (classes.has(token)) {
          classes.delete(token);
          return false;
        } else {
          classes.add(token);
          return true;
        }
      },
    };
    this.eventListeners = {};
  }

  getAttribute(name) {
    return this.attributes[name] !== undefined ? this.attributes[name] : null;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  addEventListener(event, handler) {
    if (!this.eventListeners[event]) this.eventListeners[event] = [];
    this.eventListeners[event].push(handler);
  }

  removeEventListener(event, handler) {
    if (!this.eventListeners[event]) return;
    this.eventListeners[event] = this.eventListeners[event].filter((h) => h !== handler);
  }

  dispatchEvent(event) {
    const handlers = this.eventListeners[event.type] || [];
    handlers.forEach((h) => h(event));
  }

  click() {
    this.dispatchEvent({ type: 'click', target: this });
  }

  querySelectorAll(selector) {
    if (this._mockChildren) {
      return this._mockChildren.filter((child) => {
        if (selector.includes('[data-modal-close]') && child.getAttribute('data-modal-close')) return true;
        return false;
      });
    }
    return [];
  }
}

describe('Modal Manager [REQ-ARCH-004]', () => {
  let modalA, modalB;

  beforeEach(() => {
    clearModals();
    modalA = new MockDOMElement('testModalA');
    modalA.classList.add('hidden');

    modalB = new MockDOMElement('testModalB');
    modalB.classList.add('hidden');
  });

  afterEach(() => {
    clearModals();
  });

  it('opens and closes modals, managing classes and aria attributes', () => {
    expect(isModalOpen(modalA)).toBe(false);

    openModal(modalA);
    expect(modalA.classList.contains('hidden')).toBe(false);
    expect(modalA.classList.contains('flex')).toBe(true);
    expect(modalA.getAttribute('aria-modal')).toBe('true');
    expect(isModalOpen(modalA)).toBe(true);
    expect(getActiveModal()).toBe(modalA);
    expect(getModalStack()).toHaveLength(1);

    closeModal(modalA);
    expect(modalA.classList.contains('hidden')).toBe(true);
    expect(modalA.classList.contains('flex')).toBe(false);
    expect(isModalOpen(modalA)).toBe(false);
    expect(getActiveModal()).toBeNull();
    expect(getModalStack()).toHaveLength(0);
  });

  it('maintains a stack for nested/sequential modals and pops in LIFO order', () => {
    openModal(modalA);
    openModal(modalB);

    expect(getActiveModal()).toBe(modalB);
    expect(getModalStack()).toEqual([modalA, modalB]);

    // Handle escape closes topmost modal (B)
    const closed = handleEscapeKey();
    expect(closed).toBe(modalB);
    expect(isModalOpen(modalB)).toBe(false);
    expect(isModalOpen(modalA)).toBe(true);
    expect(getActiveModal()).toBe(modalA);

    // Second escape closes modal A
    const secondClosed = handleEscapeKey();
    expect(secondClosed).toBe(modalA);
    expect(isModalOpen(modalA)).toBe(false);
    expect(getActiveModal()).toBeNull();
  });

  it('setupModal binds close buttons and backdrop', () => {
    const closeBtn = new MockDOMElement('closeBtn', 'button');
    closeBtn.setAttribute('data-modal-close', 'true');
    modalA._mockChildren = [closeBtn];

    setupModal(modalA);

    openModal(modalA);
    expect(isModalOpen(modalA)).toBe(true);

    closeBtn.click();
    expect(isModalOpen(modalA)).toBe(false);
  });

  it('toggleModal toggles visibility state', () => {
    toggleModal(modalA);
    expect(isModalOpen(modalA)).toBe(true);

    toggleModal(modalA);
    expect(isModalOpen(modalA)).toBe(false);
  });
});
