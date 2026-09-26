/**
 * Studio agent dropdown binding [CARD-410].
 * One roster broadcast fills every restored studio picker and keeps the prior selection.
 */

import { agentsVisibleInChat } from './chat.js';
import { formatAgentSelectOption } from '../utils/formatters.js';
import { storageGet, storageSet } from '../utils/storage.js';

export const PICKER_KEYS = Object.freeze({
  chat: 'autoreiv_active_agent_id',
  agents: 'autoreiv_forge_selected_agent_id',
  routines: 'autoreiv_routines_filter_agent',
  observability: 'autoreiv_observe_selected_agent_id',
  tools: 'autoreiv_tools_studio_agent_id',
});

/** Picker keys whose studio is retired (CARD-496: the Factory, ADR-0060). */
export const RETIRED_PICKER_STORAGE_KEYS = Object.freeze(['autoreiv_factory_selected_agent_id']);

/**
 * Remove stored selections for retired studio pickers [CARD-496 D8].
 * @param {{ removeItem: (key: string) => void }|null} [store]
 */
export function clearRetiredPickerKeys(store = typeof localStorage !== 'undefined' ? localStorage : null) {
  if (!store || typeof store.removeItem !== 'function') return;
  RETIRED_PICKER_STORAGE_KEYS.forEach((key) => {
    try {
      store.removeItem(key);
    } catch {
      /* private mode */
    }
  });
}

/**
 * Agent Studio picker visibility [CARD-202, CARD-339].
 * @param {object} a
 * @returns {boolean}
 */
export function isStudioAgentVisible(a) {
  if (!a) return false;
  const id = a.id || '';
  if (a.id !== 'agent-builder' && !['assistant', 'wiki'].includes(id)) {
    return true;
  }
  return false;
}

/**
 * Sorts agents alphabetically by display name (A to Z) [CARD-202].
 * @param {Array<object>} agents
 * @returns {Array<object>}
 */
export function sortStudioAgentsAlphabetically(agents = []) {
  return [...(agents || [])].sort((a, b) => {
    const nameA = formatAgentSelectOption(a).toLowerCase();
    const nameB = formatAgentSelectOption(b).toLowerCase();
    return nameA.localeCompare(nameB);
  });
}

/**
 * Choose which option stays selected across a roster refresh.
 * A placeholder currently sitting in the control (fresh HTML default) loses to a stored id.
 * @param {{ currentValue?: string, storedValue?: string|null, stateValue?: string|null, validIds?: string[], placeholders?: string[], fallback?: string }} spec
 * @returns {string}
 */
export function resolvePickerSelection({
  currentValue = '',
  storedValue = '',
  stateValue = '',
  validIds = [],
  placeholders = [],
  fallback = '',
} = {}) {
  const valid = new Set(validIds);
  const placeholder = new Set(placeholders);
  const real = (id) => Boolean(id) && valid.has(id) && !placeholder.has(id);
  const current = currentValue == null ? '' : String(currentValue);
  const stored = storedValue == null ? '' : String(storedValue);
  const fromState = stateValue == null ? '' : String(stateValue);
  if (real(current)) return current;
  if (stored && (valid.has(stored) || placeholder.has(stored))) return stored;
  if (real(fromState)) return fromState;
  if (fallback && (valid.has(fallback) || placeholder.has(fallback))) return fallback;
  const firstReal = validIds.find((id) => id && !placeholder.has(id));
  return firstReal || '';
}

function appendOption(selectEl, value, text) {
  const doc = selectEl.ownerDocument && typeof selectEl.ownerDocument.createElement === 'function'
    ? selectEl.ownerDocument
    : document;
  const opt = doc.createElement('option');
  opt.value = value;
  opt.textContent = text;
  selectEl.appendChild(opt);
}

/**
 * Rebuild a select's options and restore a selection. Returns the applied value.
 * @param {HTMLSelectElement|null} selectEl
 * @param {Array<object>} agents
 * @param {{ selectedId?: string|null, label?: Function, leading?: {value: string, text: string}|null }} [opts]
 * @returns {string}
 */
export function fillAgentSelect(selectEl, agents = [], {
  selectedId = null,
  label = (a) => (a && (a.name || a.id || a.agent_id)) || '',
  leading = null,
} = {}) {
  if (!selectEl) return '';
  selectEl.innerHTML = '';
  const built = [];
  if (leading && leading.value !== undefined) {
    const lead = String(leading.value);
    appendOption(selectEl, lead, leading.text || '');
    built.push(lead);
  }
  (agents || []).forEach((agent) => {
    const id = agent && (agent.id || agent.agent_id);
    if (!id) return;
    appendOption(selectEl, id, label(agent));
    built.push(id);
  });
  const wanted = selectedId == null ? '' : String(selectedId);
  let next = '';
  if (wanted && built.includes(wanted)) next = wanted;
  else if (built.length) next = built[0];
  selectEl.value = next;
  return next;
}

function remember(selectEl, key) {
  if (!selectEl || typeof selectEl.addEventListener !== 'function') return;
  if (selectEl.dataset && selectEl.dataset.card410Persist === '1') return;
  if (selectEl.dataset) selectEl.dataset.card410Persist = '1';
  selectEl.addEventListener('change', () => {
    storageSet(key, selectEl.value || '');
  });
}

function byName(agents) {
  return [...(agents || [])].sort((a, b) => {
    const an = String(a.name || a.id || '');
    const bn = String(b.name || b.id || '');
    return an.localeCompare(bn) || String(a.id || '').localeCompare(String(b.id || ''));
  });
}

/**
 * Fill every studio agent picker from one roster. Safe to call more than once.
 * @param {Array<object>} agents
 * @param {{ state?: object, root?: ParentNode }} [ctx]
 * @returns {Record<string, string>}
 */
export function bindStudioAgentPickers(agents, { state, root } = {}) {
  const doc = root || (typeof document !== 'undefined' ? document : null);
  if (!doc || typeof doc.getElementById !== 'function') return {};
  const list = Array.isArray(agents) ? agents : [];
  const bound = {};

  const chatEl = doc.getElementById('agentSelect');
  const chatAgents = agentsVisibleInChat(list);
  const chatIds = chatAgents.map((a) => a.id);
  const chatSelected = resolvePickerSelection({
    currentValue: chatEl ? chatEl.value : '',
    storedValue: storageGet(PICKER_KEYS.chat),
    stateValue: state ? state.selectedAgentId : '',
    validIds: chatIds,
    fallback: chatIds.includes('autoreiv') ? 'autoreiv' : (chatIds[0] || ''),
  });
  if (state) state.selectedAgentId = chatSelected || state.selectedAgentId;
  if (chatEl) {
    bound.chat = fillAgentSelect(chatEl, chatAgents, {
      selectedId: chatSelected,
      label: formatAgentSelectOption,
    });
    if (bound.chat) storageSet(PICKER_KEYS.chat, bound.chat);
    remember(chatEl, PICKER_KEYS.chat);
  }

  const forgeEl = doc.getElementById('forgeAgentSelect');
  if (forgeEl) {
    const studioAgents = sortStudioAgentsAlphabetically(list.filter(isStudioAgentVisible));
    const forgeIds = studioAgents.map((a) => a.id);
    const forgeSelected = resolvePickerSelection({
      currentValue: forgeEl.value,
      storedValue: storageGet(PICKER_KEYS.agents),
      validIds: forgeIds,
      fallback: forgeIds[0] || '',
    });
    bound.agents = fillAgentSelect(forgeEl, studioAgents, {
      selectedId: forgeSelected,
      label: formatAgentSelectOption,
    });
    if (bound.agents) storageSet(PICKER_KEYS.agents, bound.agents);
    remember(forgeEl, PICKER_KEYS.agents);
  }

  const routinesEl = doc.getElementById('routinesFilterAgent');
  if (routinesEl) {
    const routineAgents = byName(list.filter((a) => a && (a.id || a.agent_id)));
    const routineIds = ['', ...routineAgents.map((a) => a.id || a.agent_id)];
    const routineSelected = resolvePickerSelection({
      currentValue: routinesEl.value,
      storedValue: storageGet(PICKER_KEYS.routines),
      validIds: routineIds,
      placeholders: [''],
      fallback: '',
    });
    bound.routines = fillAgentSelect(routinesEl, routineAgents, {
      selectedId: routineSelected,
      label: (a) => `${a.name || a.id} (${a.id || a.agent_id})`,
      leading: { value: '', text: 'All agents' },
    });
    storageSet(PICKER_KEYS.routines, bound.routines || '');
    remember(routinesEl, PICKER_KEYS.routines);
  }

  const observeEl = doc.getElementById('observeAgentKpiSelect');
  if (observeEl) {
    const observeAgents = list.filter((a) => a && (a.id || a.agent_id));
    const observeIds = ['', ...observeAgents.map((a) => a.id || a.agent_id)];
    const observeSelected = resolvePickerSelection({
      currentValue: observeEl.value,
      storedValue: storageGet(PICKER_KEYS.observability),
      validIds: observeIds,
      placeholders: [''],
      fallback: '',
    });
    bound.observability = fillAgentSelect(observeEl, observeAgents, {
      selectedId: observeSelected,
      label: (a) => a.name || a.id || a.agent_id,
      leading: { value: '', text: 'All agents' },
    });
    storageSet(PICKER_KEYS.observability, bound.observability || '');
    remember(observeEl, PICKER_KEYS.observability);
  }

  const toolsEl = doc.getElementById('toolsStudioAgentSelect');
  if (toolsEl) {
    const toolsAgents = sortStudioAgentsAlphabetically(list.filter(isStudioAgentVisible));
    const toolsIds = ['', ...toolsAgents.map((a) => a.id)];
    const toolsSelected = resolvePickerSelection({
      currentValue: toolsEl.value,
      storedValue: storageGet(PICKER_KEYS.tools),
      validIds: toolsIds,
      placeholders: [''],
      fallback: '',
    });
    bound.tools = fillAgentSelect(toolsEl, toolsAgents, {
      selectedId: toolsSelected,
      label: formatAgentSelectOption,
      leading: { value: '', text: 'Select an agent' },
    });
    storageSet(PICKER_KEYS.tools, bound.tools || '');
    remember(toolsEl, PICKER_KEYS.tools);
  }

  return bound;
}
