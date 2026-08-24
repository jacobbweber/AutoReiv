import { describe, it, expect, vi } from 'vitest';
import { createStore } from '../../../src/web/static/modules/state/store.js';

describe('Reactive State Store [REQ-UNIT-002]', () => {
  it('initializes with default state', () => {
    const store = createStore({ count: 0, user: 'jacob' });
    expect(store.getState()).toEqual({ count: 0, user: 'jacob' });
  });

  it('updates state with partial object merging', () => {
    const store = createStore({ activeTab: 'chat', verify: false });
    store.setState({ verify: true });

    expect(store.getState()).toEqual({ activeTab: 'chat', verify: true });
  });

  it('updates state with updater function receiving current state', () => {
    const store = createStore({ count: 5 });
    store.setState((prev) => ({ count: prev.count + 3 }));

    expect(store.getState().count).toBe(8);
  });

  it('notifies subscribers on state change', () => {
    const store = createStore({ count: 1 });
    const listener = vi.fn();

    store.subscribe(listener);
    store.setState({ count: 2 });

    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledWith({ count: 2 });
  });

  it('stops notifying listener after unsubscription', () => {
    const store = createStore({ val: 'a' });
    const listener = vi.fn();

    const unsubscribe = store.subscribe(listener);
    store.setState({ val: 'b' });
    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
    store.setState({ val: 'c' });
    expect(listener).toHaveBeenCalledTimes(1); // Not called again
  });
});
