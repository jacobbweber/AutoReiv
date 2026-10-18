/**
 * Shared Application State Store [REQ-FE-001, REQ-ARCH-001]
 */

import { eventBus, EVENTS } from '../events/event-bus.js';

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

let activeTabSwitcher = null;

/**
 * Register the canonical tab switcher function from app.js [CARD-716].
 * @param {Function} switcher
 */
export function registerTabSwitcher(switcher) {
  activeTabSwitcher = typeof switcher === 'function' ? switcher : null;
}

/**
 * Switch to the requested studio tab using the registered switcher, falling back to DOM tab button click.
 * @param {string} tabName
 */
export function requestTabSwitch(tabName) {
  if (typeof activeTabSwitcher === 'function') {
    activeTabSwitcher(tabName);
    return;
  }
  if (typeof document !== 'undefined') {
    const normalized = tabName === 'skill-studio' || tabName === 'tools-studio' ? 'capabilities' : tabName;
    const btn = document.getElementById(`tab-${normalized}`);
    if (btn && typeof btn.click === 'function') {
      btn.click();
    }
  }
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
