/**
 * Shared Application State Store & Reactive Store Factory [REQ-FE-001, REQ-UNIT-002]
 */

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
  selectedAgentId: 'assistant',
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
