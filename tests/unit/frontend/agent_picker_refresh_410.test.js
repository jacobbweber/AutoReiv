/**
 * CARD-410: restored studio windows must fill agent pickers after browser refresh.
 * REQ-410-001 roster populates without a second open.
 * REQ-410-002 prior selection is kept when it is still valid.
 * REQ-410-003 close/reopen is not required.
 */

import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { EVENTS, eventBus } from '../../../src/web/static/modules/events/event-bus.js';
import { bindStudioAgentPickers, PICKER_KEYS } from '../../../src/web/static/modules/studios/agent_picker.js';
import { hydrateRestoredStudioPicker } from '../../../src/web/static/modules/ui/agent_desktop/agent_hydration.js';
import { state, publishAgentsLoaded, subscribeAgentsLoaded } from '../../../src/web/static/modules/state/store.js';

const AGENTS = [
  { id: 'wiki', name: 'Wiki', show_in_chat: true },
  { id: 'assistant', name: 'Assistant', is_builtin: true, show_in_chat: true },
  { id: 'developer', name: 'Developer', show_in_chat: true },
  { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
  { id: 'agent-builder', name: 'Agent Builder', show_in_chat: false },
];

function createSelect(id, initialValue = '') {
  const options = [];
  const el = {
    id,
    dataset: {},
    options,
    _value: initialValue,
    appendChild(opt) {
      options.push(opt);
    },
    addEventListener(type, fn) {
      el._listeners = el._listeners || {};
      el._listeners[type] = el._listeners[type] || [];
      el._listeners[type].push(fn);
    },
    get value() {
      return this._value;
    },
    set value(v) {
      this._value = v == null ? '' : String(v);
    },
  };
  let html = '';
  Object.defineProperty(el, 'innerHTML', {
    configurable: true,
    get() {
      return html;
    },
    set(v) {
      html = String(v);
      options.length = 0;
    },
  });
  return el;
}

function optionValues(select) {
  return select.options.map((opt) => opt.value);
}

function installMemoryLocalStorage() {
  const store = new Map();
  globalThis.localStorage = {
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    setItem(key, value) {
      store.set(String(key), String(value));
    },
    removeItem(key) {
      store.delete(key);
    },
    clear() {
      store.clear();
    },
  };
}

describe('CARD-410 restored studio agent pickers', () => {
  let prevDocument;
  let prevAgents;
  let prevSelected;
  let selects;

  beforeEach(() => {
    prevDocument = globalThis.document;
    prevAgents = state.agents;
    prevSelected = state.selectedAgentId;
    state.agents = [];
    state.selectedAgentId = 'autoreiv';
    eventBus.clear(EVENTS.AGENTS_LOADED);
    installMemoryLocalStorage();
    localStorage.setItem(PICKER_KEYS.chat, 'developer');
    localStorage.setItem(PICKER_KEYS.agents, 'developer');
    localStorage.setItem(PICKER_KEYS.factory, 'developer');
    localStorage.setItem(PICKER_KEYS.routines, 'developer');
    localStorage.setItem(PICKER_KEYS.observability, 'developer');

    selects = {
      agentSelect: createSelect('agentSelect'),
      forgeAgentSelect: createSelect('forgeAgentSelect'),
      factoryAgentSelect: createSelect('factoryAgentSelect', '__new__'),
      routinesFilterAgent: createSelect('routinesFilterAgent', ''),
      observeAgentKpiSelect: createSelect('observeAgentKpiSelect', ''),
    };
    globalThis.document = {
      getElementById(id) {
        return selects[id] || null;
      },
      createElement() {
        return { value: '', textContent: '' };
      },
    };
  });

  afterEach(() => {
    eventBus.clear(EVENTS.AGENTS_LOADED);
    state.agents = prevAgents;
    state.selectedAgentId = prevSelected;
    globalThis.document = prevDocument;
  });

  it('keeps pickers empty until agents:loaded, then fills them without a second window open [REQ-410-001, REQ-410-003]', () => {
    const mode = hydrateRestoredStudioPicker('agents', {
      state,
      eventBus,
      eventName: EVENTS.AGENTS_LOADED,
      bind: (_tab, agents) => bindStudioAgentPickers(agents, { state }),
    });

    expect(mode).toBe('pending');
    expect(optionValues(selects.forgeAgentSelect)).toEqual([]);
    expect(optionValues(selects.agentSelect)).toEqual([]);

    publishAgentsLoaded(AGENTS);

    expect(optionValues(selects.forgeAgentSelect)).toEqual(['autoreiv', 'developer']);
    expect(optionValues(selects.agentSelect)).toEqual(['developer', 'autoreiv']);
    expect(optionValues(selects.forgeAgentSelect)).not.toContain('assistant');
    expect(optionValues(selects.forgeAgentSelect)).not.toContain('wiki');
    expect(optionValues(selects.forgeAgentSelect)).not.toContain('agent-builder');
    expect(optionValues(selects.agentSelect)).not.toContain('assistant');
    expect(optionValues(selects.agentSelect)).not.toContain('wiki');
  });

  it('restores the prior agent selection on each studio picker [REQ-410-002]', () => {
    hydrateRestoredStudioPicker('agents', {
      state,
      eventBus,
      eventName: EVENTS.AGENTS_LOADED,
      bind: (_tab, agents) => bindStudioAgentPickers(agents, { state }),
    });
    publishAgentsLoaded(AGENTS);

    expect(selects.agentSelect.value).toBe('developer');
    expect(selects.forgeAgentSelect.value).toBe('developer');
    expect(selects.factoryAgentSelect.value).toBe('developer');
    expect(selects.routinesFilterAgent.value).toBe('developer');
    expect(selects.observeAgentKpiSelect.value).toBe('developer');
    expect(state.selectedAgentId).toBe('developer');
    expect(optionValues(selects.factoryAgentSelect)[0]).toBe('__new__');
    expect(optionValues(selects.routinesFilterAgent)[0]).toBe('');
    expect(optionValues(selects.observeAgentKpiSelect)[0]).toBe('');
  });

  it('replays a roster that arrived before the picker subscribed [REQ-410-001]', () => {
    publishAgentsLoaded(AGENTS);
    expect(optionValues(selects.forgeAgentSelect)).toEqual([]);

    const unsubscribe = subscribeAgentsLoaded((agents) => bindStudioAgentPickers(agents, { state }));

    expect(optionValues(selects.forgeAgentSelect)).toEqual(['autoreiv', 'developer']);
    expect(selects.forgeAgentSelect.value).toBe('developer');
    expect(optionValues(selects.agentSelect)).toEqual(['developer', 'autoreiv']);
    unsubscribe();
  });

  it('binds immediately when the roster is already in memory [REQ-410-001]', () => {
    state.agents = AGENTS;
    const mode = hydrateRestoredStudioPicker('chat', {
      state,
      eventBus,
      eventName: EVENTS.AGENTS_LOADED,
      bind: (_tab, agents) => bindStudioAgentPickers(agents, { state }),
    });
    expect(mode).toBe('immediate');
    expect(optionValues(selects.agentSelect)).toEqual(['developer', 'autoreiv']);
    expect(selects.agentSelect.value).toBe('developer');
  });
});
