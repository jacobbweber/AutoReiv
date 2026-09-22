/**
 * Factory studio — agent brief shell [CARD-386 / CARD-418].
 *
 * Skill pick/create, metadata, and tool scoping live in Skill Studio.
 * This window keeps the agent brief and the display-only assigned-skills list.
 */

import { $ } from '../dom.js';
import { publishAgentsLoaded } from '../state/store.js';
import { storageSet } from '../utils/storage.js';
import { PICKER_KEYS } from './agent_picker.js';
import { toSnakeCase } from '../utils/slug.js';
import { getSkillStudio } from './skill_studio.js';

export { toSnakeCase };

export function populateFactoryAgentOptions(selectEl, agents = [], selectedAgentId = '') {
  if (!selectEl) return;
  selectEl.innerHTML = '';

  const createOpt = (val, text) => {
    if (typeof document !== 'undefined' && document.createElement) {
      const opt = document.createElement('option');
      opt.value = val;
      opt.textContent = text;
      return opt;
    }
    return { value: val, textContent: text };
  };

  const defaultOpt = createOpt('', 'All Agents');
  selectEl.appendChild(defaultOpt);

  (agents || []).forEach((ag) => {
    if (ag.id === 'agent_builder' || ag.id === 'agent-builder') return;
    const opt = createOpt(ag.id, `${ag.name || ag.id} (${ag.id})`);
    selectEl.appendChild(opt);
  });

  if (selectedAgentId) {
    selectEl.value = selectedAgentId;
  }
}

export function applyBacklogGapToIntake(gap = {}) {
  if (!gap) return null;
  const seedIntent = gap.missing_capability || gap.identified_capability || gap.description || gap.intent || gap.name || '';
  const objectives = gap.objectives || (gap.suggested_steps ? gap.suggested_steps : (seedIntent ? [seedIntent] : []));
  return {
    targetAgentId: gap.agent_id || gap.target_agent_id || '',
    seedIntent,
    objectives,
    deliverableType: gap.suggested_deliverable || gap.deliverable_type || 'tool',
    referenceDocs: gap.user_intent || '',
    capabilityGapId: gap.id || null,
  };
}

export function buildForgeInitialPrompt(agentId = '') {
  if (agentId) {
    return `Let's design a new capability for agent ${agentId}. What tools or skills do we need?`;
  }
  return `Let's design a new capability. What agent, tools, or skills should we build?`;
}

export const LEGACY_GAP_TRIGGER_CLASS = 'btn-train-gap';
export const LEGACY_GAP_PAYLOAD_FIELD = 'identified_capability';

export function initFactoryStudio(_state, callbacks = {}) {
  const factoryAgentSelect = $('factoryAgentSelect');
  const factoryAgentModeBadge = $('factoryAgentModeBadge');
  const factoryAgentIdInput = $('factoryAgentIdInput');
  const factoryAgentNameInput = $('factoryAgentNameInput');
  const factoryAgentPromptInput = $('factoryAgentPromptInput');
  const factoryOpenSkillStudioBtn = $('factoryOpenSkillStudioBtn');

  let loadedAgents = [];
  let assignedSkills = [];

  if (typeof window !== 'undefined') {
    window.openFactoryStudioForAgent = (agentId) => {
      if (typeof callbacks.openFactoryStudio === 'function') {
        callbacks.openFactoryStudio(agentId);
      }
      setAgentScope(agentId);
    };
  }

  function snapshotAgent() {
    const val = factoryAgentSelect ? factoryAgentSelect.value : '';
    const creating = !val || val === '__new__';
    const agentId = creating
      ? ((factoryAgentIdInput && factoryAgentIdInput.value.trim()) || '')
      : val;
    return {
      agentId: agentId && agentId !== '__new__' ? agentId : '',
      agentName: (factoryAgentNameInput && factoryAgentNameInput.value.trim()) || '',
      rolePersona: (factoryAgentPromptInput && factoryAgentPromptInput.value.trim()) || '',
      skills: assignedSkills.slice(),
    };
  }

  function publishScope(refreshPicker = true) {
    const studio = getSkillStudio();
    if (studio && typeof studio.syncAgentScope === 'function') {
      studio.syncAgentScope(snapshotAgent(), { refreshPicker });
    }
  }

  async function loadAgents(preferredAgentId = null) {
    try {
      const resp = await fetch('/api/agents');
      if (resp.ok) {
        const data = await resp.json();
        loadedAgents = Array.isArray(data) ? data : (data.agents || []);
        if (preferredAgentId) storageSet(PICKER_KEYS.factory, preferredAgentId);
        publishAgentsLoaded(loadedAgents);
        onAgentSelectChanged();
      }
    } catch (err) {
      console.error('[FactoryStudio] Failed to load agents:', err);
    }
  }

  function setAgentScope(agentId) {
    if (factoryAgentSelect) {
      factoryAgentSelect.value = agentId || '__new__';
      onAgentSelectChanged();
    }
  }

  function onAgentSelectChanged() {
    if (!factoryAgentSelect) return;
    const val = factoryAgentSelect.value;
    const factoryIntakeAgentIdBadge = $('factoryIntakeAgentIdBadge');
    const factoryIntakeLivePackPath = $('factoryIntakeLivePackPath');
    const factoryIntakeLiveCounts = $('factoryIntakeLiveCounts');

    if (val === '__new__') {
      if (factoryAgentModeBadge) {
        factoryAgentModeBadge.textContent = 'New';
        factoryAgentModeBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-950/60 border border-brand-500/30 text-brand-400';
      }
      if (factoryIntakeAgentIdBadge) {
        factoryIntakeAgentIdBadge.textContent = 'New Agent';
        factoryIntakeAgentIdBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-950/80 text-brand-300 border border-brand-500/30';
      }
      if (factoryIntakeLivePackPath) {
        factoryIntakeLivePackPath.textContent = 'packs/<agent_id>';
      }
      if (factoryIntakeLiveCounts) {
        factoryIntakeLiveCounts.textContent = 'Skills: 0 | Tools: 0';
      }
      if (factoryAgentIdInput) {
        factoryAgentIdInput.value = toSnakeCase(factoryAgentNameInput ? factoryAgentNameInput.value : '');
        factoryAgentIdInput.readOnly = true;
      }
      if (factoryAgentNameInput) {
        factoryAgentNameInput.value = '';
        factoryAgentNameInput.focus();
      }
      if (factoryAgentPromptInput) factoryAgentPromptInput.value = '';
      assignedSkills = [];
    } else {
      const agent = loadedAgents.find((a) => a.id === val);
      if (factoryAgentModeBadge) {
        factoryAgentModeBadge.textContent = 'Existing';
        factoryAgentModeBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-400';
      }
      const agentId = agent ? agent.id : val;
      if (factoryIntakeAgentIdBadge) {
        factoryIntakeAgentIdBadge.textContent = agent ? (agent.name || agent.id) : (val || 'AutoReiv');
        factoryIntakeAgentIdBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-950/80 border border-indigo-500/30 text-indigo-300';
      }
      if (factoryIntakeLivePackPath) {
        factoryIntakeLivePackPath.textContent = `packs/${agentId || 'AutoReiv'}`;
      }
      const sCount = agent && agent.allowed_skill ? agent.allowed_skill.length : (agent && agent.skills ? agent.skills.length : 0);
      const tCount = agent && agent.tools ? agent.tools.length : 0;
      if (factoryIntakeLiveCounts) {
        factoryIntakeLiveCounts.textContent = `Skills: ${sCount} | Tools: ${tCount}`;
      }
      if (agent) {
        if (factoryAgentIdInput) {
          factoryAgentIdInput.value = agent.id || '';
          factoryAgentIdInput.readOnly = true;
        }
        if (factoryAgentNameInput) factoryAgentNameInput.value = agent.name || '';
        if (factoryAgentPromptInput) factoryAgentPromptInput.value = agent.system_prompt || agent.description || '';
        assignedSkills = agent.allowed_skill ? [...agent.allowed_skill] : (agent.skills ? [...agent.skills] : []);
      }
    }
    publishScope(true);
  }

  if (factoryAgentSelect) {
    factoryAgentSelect.addEventListener('change', onAgentSelectChanged);
  }

  if (factoryAgentNameInput) {
    factoryAgentNameInput.addEventListener('input', () => {
      if (factoryAgentSelect && factoryAgentSelect.value === '__new__') {
        const slug = toSnakeCase(factoryAgentNameInput.value);
        if (factoryAgentIdInput) factoryAgentIdInput.value = slug;
        const badge = $('factoryIntakeAgentIdBadge');
        const packPath = $('factoryIntakeLivePackPath');
        if (badge) badge.textContent = slug || 'New Agent';
        if (packPath) packPath.textContent = slug ? `packs/${slug}` : 'packs/<agent_id>';
      }
      publishScope(false);
    });
  }

  if (factoryAgentPromptInput) {
    factoryAgentPromptInput.addEventListener('input', () => publishScope(false));
  }

  if (factoryOpenSkillStudioBtn) {
    factoryOpenSkillStudioBtn.addEventListener('click', () => {
      const snap = snapshotAgent();
      if (typeof callbacks.openSkillStudio === 'function') {
        callbacks.openSkillStudio(snap.agentId || null, null);
      }
    });
  }

  const factoryIntakeTalkToForgeBtn = $('factoryIntakeTalkToForgeBtn');
  if (factoryIntakeTalkToForgeBtn) {
    factoryIntakeTalkToForgeBtn.addEventListener('click', () => {
      const agentId = (factoryAgentSelect && factoryAgentSelect.value !== '__new__') ? factoryAgentSelect.value : '';
      const prompt = buildForgeInitialPrompt(agentId);
      if (typeof callbacks.switchTab === 'function') {
        callbacks.switchTab('chat');
      }
      const chatInput = $('chatInput');
      if (chatInput) {
        chatInput.value = prompt;
        chatInput.focus();
      }
    });
  }

  return {
    loadFactoryStudio: async (preferredAgentId = null) => {
      await loadAgents(preferredAgentId);
      if (preferredAgentId) setAgentScope(preferredAgentId);
    },
    setAgentScope,
    stopPolling: () => {},
  };
}
