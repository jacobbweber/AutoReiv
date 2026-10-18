import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  state,
  publishAgentsLoaded,
  subscribeAgentsLoaded,
  registerTabSwitcher,
  requestTabSwitch,
} from '../../../src/web/static/modules/state/store.js';

describe('Shared Application State Store [CARD-716]', () => {
  beforeEach(() => {
    state.agents = [];
    registerTabSwitcher(null);
  });

  it('publishes and replays loaded agents to subscribers', () => {
    const listener = vi.fn();
    const unsub = subscribeAgentsLoaded(listener);

    publishAgentsLoaded([{ id: 'autoreiv', name: 'AutoReiv' }]);
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledWith([{ id: 'autoreiv', name: 'AutoReiv' }]);

    const lateListener = vi.fn();
    const unsubLate = subscribeAgentsLoaded(lateListener);
    expect(lateListener).toHaveBeenCalledTimes(1);

    unsub();
    unsubLate();
  });

  it('routes requestTabSwitch through the registered switcher', () => {
    const switcher = vi.fn();
    registerTabSwitcher(switcher);

    requestTabSwitch('settings');
    expect(switcher).toHaveBeenCalledWith('settings');
  });
});
