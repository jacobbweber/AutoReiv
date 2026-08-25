/**
 * Unit Tests for Toast Notification Subsystem [REQ-TOAST-001, REQ-TOAST-003, REQ-TOAST-004].
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  showToast,
  getOrCreateToastContainer,
  initConnectivityMonitor,
} from '../../../src/web/static/modules/ui/toast.js';

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
    this.children = [];

    this.parentNode = null;
    this.innerHTML = '';
    this.textContent = '';
    this.eventListeners = {};
  }

  getAttribute(name) {
    return this.attributes[name] !== undefined ? this.attributes[name] : null;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  addEventListener(event, fn) {
    if (!this.eventListeners[event]) this.eventListeners[event] = [];
    this.eventListeners[event].push(fn);
  }

  click() {
    if (this.eventListeners['click']) {
      this.eventListeners['click'].forEach((fn) => fn({ target: this }));
    }
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  removeChild(child) {
    const idx = this.children.indexOf(child);
    if (idx !== -1) {
      this.children.splice(idx, 1);
      child.parentNode = null;
    }
    return child;
  }

  contains(child) {
    if (child === this) return true;
    return this.children.some((c) => (c.contains ? c.contains(child) : c === child));
  }

  querySelector(selector) {
    if (selector.includes('button')) {
      const btn = this.children.find((c) => c.tagName === 'BUTTON');
      if (btn) return btn;
      const b = new MockDOMElement('', 'button');
      b.setAttribute('aria-label', 'Close notification');
      return b;
    }
    return null;
  }
}

describe('Toast Notification Subsystem', () => {
  let mockDoc;
  let mockBody;
  let offlineBanner;
  let retryBtn;

  beforeEach(() => {
    mockBody = new MockDOMElement('body', 'body');
    offlineBanner = new MockDOMElement('offlineBanner', 'div');
    offlineBanner.classList.add('hidden');
    retryBtn = new MockDOMElement('offlineBannerRetryBtn', 'button');
    offlineBanner.appendChild(retryBtn);
    mockBody.appendChild(offlineBanner);

    mockDoc = {
      body: mockBody,
      getElementById: (id) => {
        if (id === 'offlineBanner') return offlineBanner;
        if (id === 'offlineBannerRetryBtn') return retryBtn;
        return mockBody.children.find((c) => c.id === id) || null;
      },
      createElement: (tag) => new MockDOMElement('', tag),
    };

    globalThis.document = mockDoc;
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe('getOrCreateToastContainer', () => {
    it('creates #toastContainer element in DOM if not present', () => {
      const container = getOrCreateToastContainer();
      expect(container).not.toBeNull();
      expect(container.id).toBe('toastContainer');
      expect(container.getAttribute('aria-live')).toBe('polite');
    });

    it('reuses existing #toastContainer element', () => {
      const first = getOrCreateToastContainer();
      const second = getOrCreateToastContainer();
      expect(first).toBe(second);
    });
  });

  describe('showToast', () => {
    it('renders a success toast with status role and polite aria-live', () => {
      const toast = showToast('Operation succeeded', 'success');
      expect(toast).not.toBeNull();
      expect(toast.getAttribute('role')).toBe('status');
      expect(toast.getAttribute('aria-live')).toBe('polite');
      expect(toast.innerHTML).toContain('Operation succeeded');
    });

    it('renders an error toast with alert role and assertive aria-live', () => {
      const toast = showToast('Failed to load note', 'error');
      expect(toast).not.toBeNull();
      expect(toast.getAttribute('role')).toBe('alert');
      expect(toast.getAttribute('aria-live')).toBe('assertive');
      expect(toast.innerHTML).toContain('Failed to load note');
    });

    it('auto-dismisses toast after duration timeout', () => {
      const toast = showToast('Auto dismissing', 'info', 1000);
      const container = getOrCreateToastContainer();
      expect(container.contains(toast)).toBe(true);

      // Fast-forward duration + fadeout
      vi.advanceTimersByTime(1000);
      vi.advanceTimersByTime(250);

      expect(container.contains(toast)).toBe(false);
    });
  });

  describe('initConnectivityMonitor', () => {
    it('shows offline banner and warning toast on connection failure', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));
      const onStatusChange = vi.fn();

      const monitor = initConnectivityMonitor({
        healthUrl: '/api/health',
        intervalMs: 0,
        onStatusChange,
      });

      await monitor.check();

      expect(offlineBanner.classList.contains('hidden')).toBe(false);
      expect(onStatusChange).toHaveBeenCalledWith(false);

      // Reconnect
      global.fetch = vi.fn().mockResolvedValue({ ok: true });
      await monitor.check();

      expect(offlineBanner.classList.contains('hidden')).toBe(true);
      expect(onStatusChange).toHaveBeenCalledWith(true);

      monitor.stop();
    });
  });
});

