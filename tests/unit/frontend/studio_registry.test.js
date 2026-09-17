import { describe, it, expect, vi } from 'vitest';
import { StudioRegistry, studioRegistry } from '../../../src/web/static/modules/studios/registry.js';

describe('StudioRegistry [REQ-ARCH-002]', () => {
  it('registers and retrieves studios', () => {
    const registry = new StudioRegistry();
    const mockStudio = {
      name: 'Routines Studio',
      mount: vi.fn(),
      activate: vi.fn(),
      deactivate: vi.fn(),
    };

    registry.register('routines', mockStudio);
    expect(registry.get('routines')).toBe(mockStudio);
    expect(registry.has('routines')).toBe(true);
    expect(registry.has('unknown')).toBe(false);
  });

  it('activates registered studios and deactivates prior studio', () => {
    const registry = new StudioRegistry();
    const chat = {
      name: 'Chat Studio',
      activate: vi.fn(),
      deactivate: vi.fn(),
    };
    const routines = {
      name: 'Routines Studio',
      activate: vi.fn(),
      deactivate: vi.fn(),
    };

    registry.register('chat', chat);
    registry.register('routines', routines);

    // Initial activation
    registry.activate('chat', { param1: 'val' });
    expect(chat.activate).toHaveBeenCalledWith({ param1: 'val' });
    expect(registry.getActiveId()).toBe('chat');

    // Switching to routines deactivates chat and activates routines
    registry.activate('routines');
    expect(chat.deactivate).toHaveBeenCalled();
    expect(routines.activate).toHaveBeenCalled();
    expect(registry.getActiveId()).toBe('routines');
  });

  it('safely handles studios without optional activate/deactivate methods', () => {
    const registry = new StudioRegistry();
    const minimalStudio = { name: 'Minimal' };

    registry.register('minimal', minimalStudio);
    expect(() => registry.activate('minimal')).not.toThrow();
    expect(registry.getActiveId()).toBe('minimal');
  });

  it('lists all registered studio ids and descriptors', () => {
    const registry = new StudioRegistry();
    registry.register('chat', { name: 'Chat' });
    registry.register('wiki', { name: 'Wiki' });

    expect(registry.listIds()).toEqual(['chat', 'wiki']);
    expect(registry.list()).toHaveLength(2);
  });

  it('provides a default singleton studioRegistry', () => {
    expect(studioRegistry).toBeInstanceOf(StudioRegistry);
  });
});
