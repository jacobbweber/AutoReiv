import { describe, it, expect, beforeEach, vi } from 'vitest';

class MockElement {
  constructor(id = '', tagName = 'div') {
    this.id = id;
    this.tagName = tagName.toUpperCase();
    this.attributes = {};
    this.classList = new Set();
    this.children = [];
    this.innerHTML = '';
    this.textContent = '';
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  getAttribute(name) {
    return this.attributes[name] || null;
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  addEventListener(_event, _fn) {}

  remove() {}
}

describe('Dynamic Studio Module [CARD-133]', () => {
  let mockSidebarNav;
  let mockDynView;

  beforeEach(() => {
    mockSidebarNav = new MockElement('sidebarNav');
    mockDynView = new MockElement('view-dynamic');
    global.document = {
      getElementById: vi.fn((id) => {
        if (id === 'sidebarNav') return mockSidebarNav;
        if (id === 'view-dynamic') return mockDynView;
        return null;
      }),
      createElement: vi.fn((tag) => new MockElement('', tag)),
      querySelectorAll: vi.fn(() => []),
      querySelector: vi.fn(() => null),
    };
    global.fetch = vi.fn();
  });

  it('fetches dashboards from /api/agent-packs/dashboards and mounts nav tabs', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          pack_id: 'gardening',
          tab_title: 'Garden Studio',
          icon: 'sprout',
          description: 'Hydroponics & soil sensors',
          cards: [],
        },
      ],
    });

    const { refreshDynamicStudioTabs } = await import('../../../src/web/static/modules/studios/dynamic_studio.js');
    await refreshDynamicStudioTabs();

    expect(global.fetch).toHaveBeenCalledWith('/api/agent-packs/dashboards');
    expect(mockSidebarNav.children.length).toBe(1);
    const tab = mockSidebarNav.children[0];
    expect(tab.id).toBe('tab-dynamic-gardening');
    expect(tab.getAttribute('data-pack-id')).toBe('gardening');
  });
});
