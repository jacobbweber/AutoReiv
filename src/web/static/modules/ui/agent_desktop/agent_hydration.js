/**
 * Hydrate a restored desktop studio's agent picker [CARD-410].
 * If the roster is already in memory, bind immediately. Otherwise wait for one agents:loaded broadcast.
 */

/**
 * @param {string} tab
 * @param {{ state?: object, eventBus?: { once?: Function, on?: Function }, eventName?: string, bind?: Function }} deps
 * @returns {'immediate'|'pending'|'unavailable'}
 */
export function hydrateRestoredStudioPicker(tab, {
  state,
  eventBus,
  eventName = 'agents:loaded',
  bind,
} = {}) {
  const run = (agents) => {
    if (typeof bind === 'function') bind(tab, Array.isArray(agents) ? agents : []);
  };
  const ready = Array.isArray(state?.agents) && state.agents.length > 0;
  if (ready) {
    run(state.agents);
    return 'immediate';
  }
  if (eventBus && typeof eventBus.once === 'function') {
    eventBus.once(eventName, (agents) => run(agents));
    return 'pending';
  }
  return 'unavailable';
}
