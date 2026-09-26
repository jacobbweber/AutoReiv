/**
 * EventBus: Decoupled Publish/Subscribe Mediator [REQ-ARCH-001]
 * Provides asynchronous/synchronous event dispatching across studios without direct controller references.
 */

export const EVENTS = Object.freeze({
  AGENT_SAVED: 'agent:saved',
  AGENT_DELETED: 'agent:deleted',
  AGENTS_RELOAD: 'agents:reload',
  AGENTS_LOADED: 'agents:loaded',
  TAB_SWITCH: 'tab:switch',
  ROUTINE_OPEN_MODAL: 'routine:open_modal',
  WIKI_EXPORT: 'wiki:export',
  TOAST_SHOW: 'toast:show',
  STATE_CHANGE: 'state:change',
  SESSION_CHANGE: 'session:change',
});

export class EventBus {
  constructor() {
    this._listeners = new Map();
  }

  /**
   * Subscribe a listener function to an event.
   * @param {string} event - Event name
   * @param {Function} callback - Event handler function
   * @returns {Function} Unsubscribe function
   */
  on(event, callback) {
    if (typeof callback !== 'function') {
      throw new TypeError('EventBus callback must be a function');
    }
    if (!this._listeners.has(event)) {
      this._listeners.set(event, new Set());
    }
    this._listeners.get(event).add(callback);
    return () => this.off(event, callback);
  }

  /**
   * Unsubscribe a listener function from an event.
   * @param {string} event
   * @param {Function} callback
   */
  off(event, callback) {
    const set = this._listeners.get(event);
    if (set) {
      set.delete(callback);
      if (set.size === 0) {
        this._listeners.delete(event);
      }
    }
  }

  /**
   * Subscribe a listener function that executes only once.
   * @param {string} event
   * @param {Function} callback
   * @returns {Function} Unsubscribe function
   */
  once(event, callback) {
    const wrapper = (payload) => {
      this.off(event, wrapper);
      callback(payload);
    };
    return this.on(event, wrapper);
  }

  /**
   * Emit an event to all subscribed listeners.
   * @param {string} event - Event name
   * @param {any} [payload] - Optional data payload
   */
  emit(event, payload) {
    const set = this._listeners.get(event);
    if (!set || set.size === 0) return;

    // Snapshot set to prevent mutation bugs during handler execution
    const handlers = Array.from(set);
    for (const handler of handlers) {
      try {
        handler(payload);
      } catch (err) {
        console.error(`[EventBus] Error in handler for event '${event}':`, err);
      }
    }
  }

  /**
   * Clear listeners for an event or all events.
   * @param {string} [event] - Specific event name to clear, or omit to clear all
   */
  clear(event) {
    if (event) {
      this._listeners.delete(event);
    } else {
      this._listeners.clear();
    }
  }
}

export const eventBus = new EventBus();
