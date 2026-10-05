/**
 * CARD-637: "All agents" (the '' placeholder) is a real choice in the Routines and Observe filters.
 * It is the fresh-browser default and survives every agents:loaded refresh instead of snapping to
 * the first agent. Tools Studio's "Select an agent" placeholder follows the same rule.
 */
import { beforeEach, describe, expect, it } from 'vitest';
import { bindStudioAgentPickers, PICKER_KEYS, resolvePickerSelection } from '../../../src/web/static/modules/studios/agent_picker.js';

const IDS = ['', 'architect', 'autoreiv', 'tutor'];

describe('CARD-637 resolvePickerSelection with a placeholder', () => {
  it('fresh browser (nothing stored) uses the placeholder fallback, not the first agent', () => {
    expect(resolvePickerSelection({ currentValue: '', storedValue: null, validIds: IDS, placeholders: [''], fallback: '' })).toBe('');
  });

  it('a stored "All agents" stays "All agents"', () => {
    expect(resolvePickerSelection({ currentValue: '', storedValue: '', validIds: IDS, placeholders: [''], fallback: '' })).toBe('');
  });

  it('a stored real agent still wins', () => {
    expect(resolvePickerSelection({ currentValue: '', storedValue: 'tutor', validIds: IDS, placeholders: [''], fallback: '' })).toBe('tutor');
  });

  it('the current real selection still wins over storage', () => {
    expect(resolvePickerSelection({ currentValue: 'autoreiv', storedValue: '', validIds: IDS, placeholders: [''], fallback: '' })).toBe('autoreiv');
  });

  it('a stored agent that no longer exists falls back to "All agents"', () => {
    expect(resolvePickerSelection({ currentValue: '', storedValue: 'retired-agent', validIds: IDS, placeholders: [''], fallback: '' })).toBe('');
  });

  it('negative: pickers without a placeholder still fall back to a real agent', () => {
    expect(resolvePickerSelection({ currentValue: '', storedValue: null, validIds: ['developer', 'autoreiv'], fallback: '' })).toBe('developer');
    expect(resolvePickerSelection({ currentValue: '', storedValue: '', validIds: ['developer', 'autoreiv'], fallback: 'autoreiv' })).toBe('autoreiv');
  });
});

function createSelect(id, initialValue = '') {
  const options = [];
  const el = {
    id,
    dataset: {},
    options,
    _value: initialValue,
    appendChild(opt) { options.push(opt); },
    addEventListener(type, fn) {
      el._listeners = el._listeners || {};
      (el._listeners[type] = el._listeners[type] || []).push(fn);
    },
    get value() { return this._value; },
    set value(v) { this._value = v == null ? '' : String(v); },
  };
  Object.defineProperty(el, 'innerHTML', { configurable: true, get: () => '', set: () => { options.length = 0; } });
  return el;
}

const AGENTS = [
  { id: 'architect', name: 'Architect', show_in_chat: true },
  { id: 'autoreiv', name: 'AutoReiv', show_in_chat: true },
  { id: 'tutor', name: 'Tutor', show_in_chat: true },
];

describe('CARD-637 Routines / Observe / Tools pickers across agents:loaded refreshes', () => {
  let selects;
  let store;

  beforeEach(() => {
    store = new Map();
    globalThis.localStorage = {
      getItem: (k) => (store.has(k) ? store.get(k) : null),
      setItem: (k, v) => store.set(String(k), String(v)),
      removeItem: (k) => store.delete(k),
      clear: () => store.clear(),
    };
    selects = {
      routinesFilterAgent: createSelect('routinesFilterAgent', ''),
      observeAgentKpiSelect: createSelect('observeAgentKpiSelect', ''),
      toolsStudioAgentSelect: createSelect('toolsStudioAgentSelect', ''),
    };
    globalThis.document = {
      getElementById: (id) => selects[id] || null,
      createElement: () => ({ value: '', textContent: '' }),
    };
  });

  it('a fresh browser starts on the placeholder and keeps it over repeated refreshes', () => {
    for (let i = 0; i < 3; i += 1) {
      const bound = bindStudioAgentPickers(AGENTS, {});
      expect(bound.routines).toBe('');
      expect(bound.observability).toBe('');
      expect(bound.tools).toBe('');
    }
    expect(selects.routinesFilterAgent.value).toBe('');
    expect(selects.routinesFilterAgent.options[0].textContent).toBe('All agents');
    expect(localStorage.getItem(PICKER_KEYS.routines)).toBe('');
  });

  it('picking an agent, then All agents, survives the next refresh', () => {
    bindStudioAgentPickers(AGENTS, {});
    const el = selects.routinesFilterAgent;
    const change = () => el._listeners.change.forEach((fn) => fn());
    el.value = 'autoreiv';
    change();
    expect(bindStudioAgentPickers(AGENTS, {}).routines).toBe('autoreiv');
    el.value = '';
    change();
    expect(bindStudioAgentPickers(AGENTS, {}).routines).toBe('');
    expect(el.value).toBe('');
    expect(localStorage.getItem(PICKER_KEYS.routines)).toBe('');
  });
});
