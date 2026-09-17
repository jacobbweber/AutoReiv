/**
 * StudioRegistry: Polymorphic Studio Lifecycle Manager [REQ-ARCH-002]
 * Enables Open/Closed Principle compliance by decoupling studio activation and deactivation from switchTab branching.
 */

export class StudioRegistry {
  constructor() {
    this._studios = new Map();
    this._activeId = null;
  }

  /**
   * Register a studio instance with lifecycle hooks.
   * @param {string} id - Studio identifier (e.g. 'chat', 'routines')
   * @param {Object} studio - Studio controller or lifecycle adapter
   * @param {string} [studio.name] - Human-readable name
   * @param {Function} [studio.mount] - Invoked on initial app boot
   * @param {Function} [studio.activate] - Invoked when tab is selected
   * @param {Function} [studio.deactivate] - Invoked when leaving tab
   */
  register(id, studio) {
    if (!id || typeof id !== 'string') {
      throw new TypeError('StudioRegistry: id must be a non-empty string');
    }
    if (!studio || typeof studio !== 'object') {
      throw new TypeError('StudioRegistry: studio must be an object');
    }
    this._studios.set(id, studio);
  }

  /**
   * Check if a studio is registered.
   * @param {string} id
   * @returns {boolean}
   */
  has(id) {
    return this._studios.has(id);
  }

  /**
   * Retrieve a registered studio.
   * @param {string} id
   * @returns {Object|null}
   */
  get(id) {
    return this._studios.get(id) || null;
  }

  /**
   * Get the currently active studio id.
   * @returns {string|null}
   */
  getActiveId() {
    return this._activeId;
  }

  /**
   * Activate a studio by ID, deactivating the previously active studio.
   * @param {string} id
   * @param {any} [params] - Optional activation parameters
   */
  activate(id, params) {
    if (this._activeId && this._activeId !== id) {
      const prev = this._studios.get(this._activeId);
      if (prev && typeof prev.deactivate === 'function') {
        try {
          prev.deactivate();
        } catch (err) {
          console.error(`[StudioRegistry] Error deactivating studio '${this._activeId}':`, err);
        }
      }
    }

    this._activeId = id;
    const next = this._studios.get(id);
    if (next && typeof next.activate === 'function') {
      try {
        next.activate(params);
      } catch (err) {
        console.error(`[StudioRegistry] Error activating studio '${id}':`, err);
      }
    }
  }

  /**
   * List all registered studio ids.
   * @returns {string[]}
   */
  listIds() {
    return Array.from(this._studios.keys());
  }

  /**
   * List all registered studio descriptors.
   * @returns {Array<{ id: string, studio: Object }>}
   */
  list() {
    return Array.from(this._studios.entries()).map(([id, studio]) => ({ id, studio }));
  }
}

export const studioRegistry = new StudioRegistry();
