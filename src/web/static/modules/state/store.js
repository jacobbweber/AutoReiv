/**
 * Shared Application State Store & Reactive Store Factory [REQ-FE-001, REQ-UNIT-002, REQ-ARCH-001]
 */

import { eventBus, EVENTS } from '../events/event-bus.js';

/**
 * Creates an isolated reactive state store with subscription support.
 * @param {Object} [initialState={}]
 */
export function createStore(initialState = {}) {
  let currentState = { ...initialState };
  const listeners = new Set();

  return {
    getState() {
      return currentState;
    },
    setState(updater) {
      const nextState = typeof updater === 'function' ? updater(currentState) : { ...currentState, ...updater };
      currentState = nextState;
      listeners.forEach((fn) => {
        try {
          fn(currentState);
        } catch (err) {
          console.warn('[AutoReiv Store] Listener error:', err);
        }
      });
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

export const state = {
  activeTab: 'chat',
  agents: [],
  selectedAgentId: 'autoreiv',
  sessions: [],
  activeSessionId: null,
  messages: [],
  isStreaming: false,
  verifyEnabled: false,
  approvalAutoRun: false,
  goalEnabled: false,
  currentVault: null,
  activeDoc: null,
};

const globalSubscribers = new Set();

/**
 * Update the global singleton application state reactively.
 * Mutates `state`, notifies subscribers, and emits `EVENTS.STATE_CHANGE` on EventBus.
 * @param {Object|Function} updater
 */
export function updateState(updater) {
  const next = typeof updater === 'function' ? updater(state) : updater;
  if (next && typeof next === 'object') {
    Object.assign(state, next);
  }
  globalSubscribers.forEach((fn) => {
    try {
      fn(state);
    } catch (err) {
      console.warn('[AutoReiv Store] Global state listener error:', err);
    }
  });
  eventBus.emit(EVENTS.STATE_CHANGE, state);
  return state;
}

/**
 * Publish a freshly fetched agent roster and notify studio pickers.
 * Listeners run synchronously before this returns. [CARD-410]
 * @param {Array<object>} agents
 * @returns {Array<object>}
 */
export function publishAgentsLoaded(agents) {
  const list = Array.isArray(agents) ? agents : [];
  state.agents = list;
  eventBus.emit(EVENTS.AGENTS_LOADED, list);
  return list;
}

/**
 * Subscribe to roster broadcasts. If a roster is already in memory, the handler
 * runs immediately so a studio that mounts after the fetch still fills its picker.
 * @param {Function} handler
 * @returns {Function} Unsubscribe
 */
export function subscribeAgentsLoaded(handler) {
  if (typeof handler !== 'function') return () => {};
  const unsubscribe = eventBus.on(EVENTS.AGENTS_LOADED, handler);
  if (Array.isArray(state.agents) && state.agents.length) {
    try {
      handler(state.agents);
    } catch (err) {
      console.warn('[AutoReiv Store] agents:loaded replay failed:', err);
    }
  }
  return unsubscribe;
}

/**
 * Subscribe to changes in global application state.
 * @param {Function} listener
 * @returns {Function} Unsubscribe callback
 */
export function subscribeState(listener) {
  if (typeof listener !== 'function') return () => {};
  globalSubscribers.add(listener);
  return () => globalSubscribers.delete(listener);
}
