import { describe, it, expect, vi } from 'vitest';
import { EventBus, EVENTS, eventBus } from '../../../src/web/static/modules/events/event-bus.js';

describe('EventBus [REQ-ARCH-001]', () => {
  it('subscribes and emits events with payloads', () => {
    const bus = new EventBus();
    const handler = vi.fn();

    const unsubscribe = bus.on(EVENTS.AGENT_SAVED, handler);
    bus.emit(EVENTS.AGENT_SAVED, { agentId: 'assistant' });

    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith({ agentId: 'assistant' });

    unsubscribe();
    bus.emit(EVENTS.AGENT_SAVED, { agentId: 'assistant-2' });
    expect(handler).toHaveBeenCalledTimes(1);
  });

  it('unsubscribes via off() correctly', () => {
    const bus = new EventBus();
    const handler = vi.fn();

    bus.on(EVENTS.TAB_SWITCH, handler);
    bus.off(EVENTS.TAB_SWITCH, handler);
    bus.emit(EVENTS.TAB_SWITCH, { tab: 'wiki' });

    expect(handler).not.toHaveBeenCalled();
  });

  it('supports once() for single-execution handlers', () => {
    const bus = new EventBus();
    const handler = vi.fn();

    bus.once(EVENTS.AGENTS_RELOAD, handler);
    bus.emit(EVENTS.AGENTS_RELOAD, { count: 3 });
    bus.emit(EVENTS.AGENTS_RELOAD, { count: 4 });

    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler).toHaveBeenCalledWith({ count: 3 });
  });

  it('handles errors inside handlers gracefully without stopping other handlers', () => {
    const bus = new EventBus();
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const badHandler = vi.fn(() => {
      throw new Error('Boom');
    });
    const goodHandler = vi.fn();

    bus.on(EVENTS.TOAST_SHOW, badHandler);
    bus.on(EVENTS.TOAST_SHOW, goodHandler);

    bus.emit(EVENTS.TOAST_SHOW, { message: 'Hello' });

    expect(badHandler).toHaveBeenCalledTimes(1);
    expect(goodHandler).toHaveBeenCalledTimes(1);
    expect(errSpy).toHaveBeenCalled();
    errSpy.mockRestore();
  });

  it('clears handlers per event or entirely', () => {
    const bus = new EventBus();
    const h1 = vi.fn();
    const h2 = vi.fn();

    bus.on('eventA', h1);
    bus.on('eventB', h2);

    bus.clear('eventA');
    bus.emit('eventA', {});
    bus.emit('eventB', {});

    expect(h1).not.toHaveBeenCalled();
    expect(h2).toHaveBeenCalledTimes(1);

    bus.clear();
    bus.emit('eventB', {});
    expect(h2).toHaveBeenCalledTimes(1);
  });

  it('provides a default singleton eventBus', () => {
    expect(eventBus).toBeInstanceOf(EventBus);
    expect(typeof eventBus.on).toBe('function');
    expect(typeof eventBus.emit).toBe('function');
  });
});
