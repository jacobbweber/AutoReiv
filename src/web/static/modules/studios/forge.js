/**
 * Agent Studio Coordinator Module [REQ-FE-001, CARD-119, CARD-127, CARD-148, CARD-153, CARD-162, CARD-202, CARD-350, CARD-389, CARD-398]
 * Orchestrates agent inspection, editing, saving, deletion, and coordinates focused Agent Studio submodules:
 * - proposals.js: Architectural governance proposals inbox, category badges, remedy execution, synthesis
 * - scaffold.js: Quick presets and the New Agent modal
 * - tools.js: OS baseline tools, capability gaps backlog, remote MCP server management, credential grants
 * - runbook.js: Skill toggle rows and Open in Skill Studio [CARD-411, CARD-418, CARD-419]
 * - skill_pills.js: Agent↔skill toggle pills; on/off writes allowed_skill only [CARD-419]
 * - config.js: Per-agent LLM providers, model discovery, avatar preview, routines, telemetry, brain drawer, tones
 * - agent_file_status.js: Edited / shipped version changed / Use shipped version [CARD-570]
 */

import { $, $queryAll, safeCreateIcons } from '../dom.js';
import { formatAgentSelectOption } from '../utils/formatters.js';
import { showToast } from '../ui/toast.js';
import { publishAgentsLoaded } from '../state/store.js';
import { storageGet, storageSet } from '../utils/storage.js';
import { PRESETS_DEFAULTS } from './settings.js';
import {
  PICKER_KEYS,
  bindStudioAgentPickers,
  fillAgentSelect,
  isStudioAgentVisible,
  sortStudioAgentsAlphabetically,
} from './agent_picker.js';

export { isStudioAgentVisible, sortStudioAgentsAlphabetically };

// Re-export all decomposed submodules for complete backward compatibility [CARD-398]
export * from './forge/proposals.js';
export * from './forge/scaffold.js';
export * from './forge/tools.js';
export * from './forge/runbook.js';
export * from './forge/config.js';

import {
  setupArchitecturalProposals,
  loadArchitecturalProposals,
} from './forge/proposals.js';
import { loadPendingProposals } from './forge/pending_proposals.js';

import {
  setupScaffold,
  openQuickScaffoldModal,
} from './forge/scaffold.js';

import {
  setupAgentMcpControls,
  loadAgentCapabilityGaps,
  loadAgentMcpServers,
  loadAgentCredentialGrants,
} from './forge/tools.js';

import {
  setupRunbookEditor,
  loadPlatformSkills,
  renderNestedHomes,
  applySkillChecks,
} from './forge/runbook.js';
import {
  allowlistForSave,
  pillsFromPersistedAgent,
  skillsForSave,
} from './forge/skill_pills.js';

import {
  setupAgentModelConfig,
  setupBrainDrawer,
  setupToneManager,
  populateAgentModelSelect,
  updateProviderConfigVisibility,
  updateAvatarPreview,
  loadAgentAssignedRoutines,
  loadAgentTelemetry,
  loadTones,
  setCachedDiscoveredModels,
} from './forge/config.js';
import { setupAgentFileStatus } from './forge/agent_file_status.js';

/** Default turn budget for an agent with no stored value; keep equal to DEFAULT_AGENT_MAX_TURNS in src/domain/kernel/models.py [CARD-445]. */
export const DEFAULT_AGENT_MAX_TURNS = 50;

export { formatAgentSelectOption };

/**
 * Populates agent select element with alphabetical sorted options [CARD-202].
 */
/**
 * CARD-573: an Agent Studio load or render that finished late must not overwrite the form the user is editing.
 * beginRender() returns isCurrent(); a newer render makes older ones stale. userPicked() marks a user agent pick,
 * pickedSince(mark) tells a background load that the user already picked (and may be editing) since it started.
 */
export function createForgeLoadGuard() {
  let render = 0;
  let pick = 0;
  return {
    beginRender() { render += 1; const seq = render; return () => seq === render; },
    userPicked() { pick += 1; },
    pickMark: () => pick,
    pickedSince: (mark) => pick !== mark,
  };
}

/** CARD-573: until an agent is shown / while one is filled in, its editable sections are inert (they start inert in index.html) and Save waits. */
export const FORGE_AGENT_SECTIONS = 'details.forge-section[data-card="299"]';
export function setForgeFormBusy(on, doc = typeof document !== 'undefined' ? document : null) {
  if (!doc || typeof doc.querySelectorAll !== 'function') return;
  doc.querySelectorAll(FORGE_AGENT_SECTIONS).forEach((el) => {
    if (on) { el.setAttribute('inert', ''); el.setAttribute('aria-busy', 'true'); } else { el.removeAttribute('inert'); el.removeAttribute('aria-busy'); }
  });
}

export function populateForgeAgentSelectOptions(selectEl, agents = [], selectedId = null) {
  if (!selectEl) return null;
  return fillAgentSelect(selectEl, sortStudioAgentsAlphabetically(agents), {
    selectedId,
    label: formatAgentSelectOption,
  });
}

/**
 * Main Controller Entry Point for Agent Studio [CARD-398].
 */
export function initAgentForge(state, callbacks = {}) {
  // DOM Cache
  const forgeAgentSelect = $('forgeAgentSelect');
  const newAgentBtn = $('newAgentBtn');
  const forgeBuiltinBadge = $('forgeBuiltinBadge');
  const forgeAvatarSelect = $('forgeAvatarSelect');
  const forgeNameInput = $('forgeNameInput');
  const forgeIdInput = $('forgeIdInput');
  const forgeDescInput = $('forgeDescInput');
  const forgeToneSelect = $('forgeToneSelect');
  const forgeMaxTurnsInput = $('forgeMaxTurnsInput');
  const forgeRetentionDaysInput = $('forgeRetentionDaysInput');
  const forgeAlwaysAutoRunInput = $('forgeAlwaysAutoRunInput'); // CARD-573
  const forgeProviderSelect = $('forgeProviderSelect');
  const forgeApiBaseUrlInput = $('forgeApiBaseUrlInput');
  const forgeApiKeyInput = $('forgeApiKeyInput');
  const forgeContextWindowInput = $('forgeContextWindowInput');
  const forgeAgentModelSelect = $('forgeAgentModelSelect');
  const forgeStorageEnabled = $('forgeStorageEnabled');
  const forgeStorageTypeContainer = $('forgeStorageTypeContainer');
  const forgeStorageType = $('forgeStorageType');
  const forgeMemoryEnabled = $('forgeMemoryEnabled');
  const forgeMemoryRetentionDays = $('forgeMemoryRetentionDays');
  const forgeMemoryRetentionDaysLabel = $('forgeMemoryRetentionDaysLabel');
  const forgePinnedMemory = $('forgePinnedMemory');
  const forgeSystemPrompt = $('forgeSystemPrompt');
  const forgeCredentialGrantsList = $('forgeCredentialGrantsList');
  const saveAgentBtn = $('saveAgentBtn');
  const deleteAgentBtn = $('deleteAgentBtn');
  const forgeShowInChat = $('forgeShowInChat');
  const forgeStatusBanner = $('forgeStatusBanner');
  const linkRoutineForAgentBtn = $('linkRoutineForAgentBtn');
  const forgeOpenObserveBtn = $('forgeOpenObserveBtn');

  // Delete modal elements
  const deleteAgentModal = $('deleteAgentModal');
  const deleteAgentModalMessage = $('deleteAgentModalMessage');
  const purgeHistoryCheckbox = $('purgeHistoryCheckbox');
  const confirmDeleteAgentBtn = $('confirmDeleteAgentBtn');
  const cancelDeleteAgentBtn = $('cancelDeleteAgentBtn');
  const closeDeleteAgentModalBtn = $('closeDeleteAgentModalBtn');

  // Internal coordinator state
  let activeForgeAgent = null;
  const loadGuard = createForgeLoadGuard(); // CARD-573
  let forgeBusy = true; // CARD-573: nothing shown until the first load renders an agent
  let loadsInFlight = 0;
  let cachedSkillsCatalog = null;
  let cachedPlatformSkills = [];
  let cachedOperatorSkills = [];
  let cachedArchivedSkills = [];
  let lastAllowedSkills = new Set();
  let currentAgentMcpServers = [];

  const agentFileStatus = setupAgentFileStatus({
    onAgentRefreshed: (fresh) => renderAgentToForge(fresh),
  });

  function getActiveAgentId() {
    return (activeForgeAgent && activeForgeAgent.id) || (forgeAgentSelect ? forgeAgentSelect.value : null);
  }

  function getActiveAgent() {
    return activeForgeAgent;
  }

  function onToggleSkill(skillId, pressed) {
    if (!skillId) return;
    if (pressed) lastAllowedSkills.add(skillId);
    else lastAllowedSkills.delete(skillId);
  }

  function onOpenSkillStudio(skillId) {
    const agentId = getActiveAgentId();
    if (typeof callbacks.openSkillStudio === 'function') {
      callbacks.openSkillStudio(agentId, skillId || null);
    }
  }

  function skillScopeHandlers() {
    return {
      onToggleSkill,
      onOpenSkillStudio,
    };
  }

  function renderNestedHomesWrapper() {
    renderNestedHomes({
      cachedPlatformSkills,
      cachedOperatorSkills,
      cachedArchivedSkills,
      activeForgeAgent,
      lastAllowedSkills,
      ...skillScopeHandlers(),
    });
  }

  async function loadPlatformSkillsWrapper() {
    const result = await loadPlatformSkills({
      cachedSkillsCatalog,
      activeForgeAgent,
      lastAllowedSkills,
      ...skillScopeHandlers(),
      onLoaded: ({ platformSkills, operatorSkills, archivedSkills, catalog }) => {
        cachedPlatformSkills = platformSkills;
        cachedOperatorSkills = operatorSkills || [];
        cachedArchivedSkills = archivedSkills;
        cachedSkillsCatalog = catalog;
      },
    });
    return result;
  }

  async function loadAgentForge(targetAgentId) {
    const pickMark = loadGuard.pickMark(); // CARD-573
    if (!activeForgeAgent) { forgeBusy = true; setForgeFormBusy(true); } // nothing shown yet: no edits on an empty form
    loadsInFlight += 1;
    try {
      const catRes = await fetch('/api/skills/catalog');
      if (catRes.ok) {
        cachedSkillsCatalog = await catRes.json();
      }
      await loadPlatformSkillsWrapper();

      try {
        const modRes = await fetch('/api/models/discover');
        if (modRes.ok) {
          const modData = await modRes.json();
          setCachedDiscoveredModels(modData.models || []);
          const curProv = forgeProviderSelect ? forgeProviderSelect.value : 'default';
          const curMod = forgeAgentModelSelect ? forgeAgentModelSelect.value : 'default';
          populateAgentModelSelect(curProv, curMod);
        }
      } catch (e) {
        console.warn('[AutoReiv UI] Failed to load models for Agent Studio select:', e);
      }

      const res = await fetch('/api/agents');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const agents = await res.json();
      if (targetAgentId) {
        storageSet(PICKER_KEYS.agents, targetAgentId);
        if (forgeAgentSelect) forgeAgentSelect.value = '';
      }
      publishAgentsLoaded(agents);
      bindStudioAgentPickers(agents, { state });
      const studioAgents = agents.filter(isStudioAgentVisible);
      const selectedId = (forgeAgentSelect && forgeAgentSelect.value)
        || targetAgentId
        || storageGet(PICKER_KEYS.agents)
        || (studioAgents[0] ? studioAgents[0].id : null);
      const targetAgent = studioAgents.find((a) => a.id === selectedId) || studioAgents[0];
      // CARD-573: if the user picked this agent while the load ran, keep the form they may be editing.
      const userHasIt = loadGuard.pickedSince(pickMark) && activeForgeAgent && activeForgeAgent.id === (targetAgent && targetAgent.id);
      if (targetAgent && !userHasIt) {
        await renderAgentToForge(targetAgent);
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load Agent Studio:', err);
    } finally {
      loadsInFlight -= 1;
      if (!activeForgeAgent && !loadsInFlight) { forgeBusy = false; setForgeFormBusy(false); }
    }
  }

  async function renderAgentToForge(agent) {
    const isCurrent = loadGuard.beginRender(); // CARD-573: a newer render wins; this one stops after its awaits
    activeForgeAgent = agent;
    if (!agent) return;
    forgeBusy = true;
    setForgeFormBusy(true);
    try {
      await fillForgeForm(agent, isCurrent);
    } finally {
      if (isCurrent()) { forgeBusy = false; setForgeFormBusy(false); }
    }
  }

  async function fillForgeForm(agent, isCurrent) {

    if (forgeNameInput) forgeNameInput.value = agent.name || '';
    if (forgeIdInput) {
      forgeIdInput.value = agent.id || '';
      forgeIdInput.disabled = true;
    }
    if (forgeDescInput) forgeDescInput.value = agent.description || '';
    if (forgeSystemPrompt) forgeSystemPrompt.value = agent.system_prompt || '';
    await loadTones(agent.tone || 'default');
    if (!isCurrent()) return;
    if (forgeMaxTurnsInput) forgeMaxTurnsInput.value = agent.max_turns || DEFAULT_AGENT_MAX_TURNS;
    if (forgeRetentionDaysInput) forgeRetentionDaysInput.value = (agent.history_retention_days === 0 || agent.history_retention_days) ? agent.history_retention_days : 30;
    if (forgeAlwaysAutoRunInput) forgeAlwaysAutoRunInput.checked = agent.always_auto_run === true;
    const agentProv = agent.provider || 'default';
    if (forgeProviderSelect) forgeProviderSelect.value = agentProv;
    if (forgeApiBaseUrlInput) {
      forgeApiBaseUrlInput.value = agent.api_base_url || (PRESETS_DEFAULTS[agentProv] ? PRESETS_DEFAULTS[agentProv].url : '');
    }
    if (forgeApiKeyInput) {
      forgeApiKeyInput.value = agent.api_key || '';
    }
    if (forgeContextWindowInput) {
      forgeContextWindowInput.value = (agent.context_window && agent.context_window > 0) ? agent.context_window : '';
    }
    updateProviderConfigVisibility(agentProv);
    populateAgentModelSelect(agentProv, agent.model || 'default');
    if (forgeAvatarSelect) forgeAvatarSelect.value = agent.avatar_icon || 'bot';
    if (forgeShowInChat) forgeShowInChat.checked = agent.show_in_chat !== false;
    if (forgeStorageEnabled) forgeStorageEnabled.checked = Boolean(agent.storage_enabled);
    if (forgeStorageType) forgeStorageType.value = agent.storage_type || 'sqlite';
    if (forgeStorageTypeContainer) forgeStorageTypeContainer.classList.toggle('hidden', !agent.storage_enabled);
    if (forgeMemoryEnabled) forgeMemoryEnabled.checked = agent.memory_enabled !== false;
    const retentionDays = agent.memory_retention_days !== undefined ? agent.memory_retention_days : 30;
    if (forgeMemoryRetentionDays) forgeMemoryRetentionDays.value = retentionDays;
    if (forgeMemoryRetentionDaysLabel) forgeMemoryRetentionDaysLabel.textContent = `${retentionDays} days`;
    if (forgePinnedMemory) forgePinnedMemory.value = agent.pinned_memory || '';

    renderNestedHomesWrapper();
    updateAvatarPreview(agent.avatar_icon || 'bot');

    if (forgeBuiltinBadge) {
      if (agent.id === 'agent-builder' || agent.is_builtin) {
        forgeBuiltinBadge.textContent = 'System Baseline';
        forgeBuiltinBadge.className =
          'text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800';
      } else {
        forgeBuiltinBadge.textContent = 'Agent Skill';
        forgeBuiltinBadge.className =
          'text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800';
      }
    }

    if (deleteAgentBtn) {
      const isProtected = agent.id === 'autoreiv' || agent.id === 'agent-builder' || Boolean(agent.is_builtin);
      if (isProtected) {
        deleteAgentBtn.disabled = true;
        deleteAgentBtn.classList.add('opacity-40', 'cursor-not-allowed');
      } else {
        deleteAgentBtn.disabled = false;
        deleteAgentBtn.classList.remove('opacity-40', 'cursor-not-allowed');
      }
    }

    lastAllowedSkills = new Set(pillsFromPersistedAgent(agent));
    applySkillChecks(lastAllowedSkills);

    loadAgentTelemetry(agent.id);
    loadAgentAssignedRoutines(agent.id, callbacks);
    loadAgentCapabilityGaps(agent.id, callbacks);
    const mcpServers = await loadAgentMcpServers(agent.id, {
      getActiveAgent,
      onServersChanged: (servers) => { currentAgentMcpServers = servers; },
    });
    if (!isCurrent()) return;
    currentAgentMcpServers = mcpServers;
    loadAgentCredentialGrants(agent);
    loadArchitecturalProposals(agent.id);
    agentFileStatus.render(agent);
    // CARD-539: accept/reject attach-tool-to-skill proposals; accepting reloads so the tick shows.
    loadPendingProposals(agent.id, typeof document !== 'undefined' ? document.getElementById('forgePendingProposals') : null, {
      onChanged: async () => {
        cachedSkillsCatalog = null;
        await loadPlatformSkillsWrapper(); // a new skill from the proposal must be in the list to show ticked
        const res = await fetch(`/api/agents/${encodeURIComponent(agent.id)}`);
        if (res.ok) await renderAgentToForge(await res.json());
      },
    });
  }

  function openDeleteModal() {
    if (!activeForgeAgent || activeForgeAgent.is_builtin) return;
    if (deleteAgentModalMessage) {
      deleteAgentModalMessage.textContent = `Are you sure you want to permanently delete custom agent "${activeForgeAgent.name}"? This will remove the agent configuration, delete its skill files, and unbind any assigned routines.`;
    }
    if (purgeHistoryCheckbox) purgeHistoryCheckbox.checked = false;
    if (deleteAgentModal) deleteAgentModal.classList.remove('hidden');
    safeCreateIcons();
  }

  function closeDeleteModal() {
    if (deleteAgentModal) deleteAgentModal.classList.add('hidden');
  }

  // Delete modal listeners
  if (deleteAgentBtn) {
    deleteAgentBtn.addEventListener('click', openDeleteModal);
  }
  if (cancelDeleteAgentBtn) cancelDeleteAgentBtn.addEventListener('click', closeDeleteModal);
  if (closeDeleteAgentModalBtn) closeDeleteAgentModalBtn.addEventListener('click', closeDeleteModal);

  if (confirmDeleteAgentBtn) {
    confirmDeleteAgentBtn.addEventListener('click', async () => {
      if (!activeForgeAgent || activeForgeAgent.is_builtin) return;
      const purge = purgeHistoryCheckbox ? purgeHistoryCheckbox.checked : false;
      closeDeleteModal();

      try {
        const res = await fetch(`/api/agents/${encodeURIComponent(activeForgeAgent.id)}?purge_history=${purge}`, { method: 'DELETE' });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Failed to delete agent');
        }

        showToast(`Agent "${activeForgeAgent.name}" deleted.`, 'info');

        if (forgeStatusBanner) {
          forgeStatusBanner.textContent = `Agent "${activeForgeAgent.name}" deleted.`;
          forgeStatusBanner.className =
            'px-4 py-2 text-xs font-medium text-center border-b border-rose-800 bg-rose-950/60 text-rose-300 block';
          setTimeout(() => forgeStatusBanner.classList.add('hidden'), 3500);
        }

        if (callbacks.onAgentDeleted) {
          await callbacks.onAgentDeleted();
        }
        await loadAgentForge();
      } catch (err) {
        console.error('[AutoReiv UI] Delete agent error:', err);
        showToast(`Error deleting agent: ${err.message}`, 'error');
      }
    });
  }

  // Save Agent handler
  if (saveAgentBtn) {
    saveAgentBtn.addEventListener('click', async () => {
      if (forgeBusy) { showToast('Agent is still loading; try Save again in a moment.', 'warning'); return; } // CARD-573
      const name = forgeNameInput ? forgeNameInput.value.trim() : '';
      let id = (activeForgeAgent && activeForgeAgent.id) || (forgeIdInput ? forgeIdInput.value.trim() : '');
      if (!name) {
        showToast('Agent name is required.', 'warning');
        return;
      }
      if (!id) {
        id = name
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/^-|-$/g, '');
      }

      const isStorage = Boolean(forgeStorageEnabled && forgeStorageEnabled.checked);
      const pillNodes = typeof document !== 'undefined'
        ? document.querySelectorAll('.forge-skill-pill[data-skill-id]')
        : [];
      const fromPills = skillsForSave([...lastAllowedSkills], pillNodes); // CARD-509: keep pill-less skills
      const checkedSkills = allowlistForSave(fromPills, { storageEnabled: isStorage });

      // CARD-539: Save sends skill ticks only; the server derives tools from skills (ADR-0061).

      const payload = {
        id: id,
        name: name,
        description: forgeDescInput ? forgeDescInput.value.trim() : '',
        system_prompt: forgeSystemPrompt ? forgeSystemPrompt.value.trim() : '',
        purpose: (activeForgeAgent && activeForgeAgent.purpose) ? activeForgeAgent.purpose : 'general',
        tone: forgeToneSelect ? forgeToneSelect.value : 'default',
        avatar_icon: forgeAvatarSelect ? forgeAvatarSelect.value : 'bot',
        provider: forgeProviderSelect ? forgeProviderSelect.value : 'default',
        api_base_url:
          forgeProviderSelect && forgeProviderSelect.value !== 'default' && forgeApiBaseUrlInput
            ? forgeApiBaseUrlInput.value.trim() || null
            : null,
        api_key:
          forgeProviderSelect && forgeProviderSelect.value !== 'default' && forgeApiKeyInput
            ? forgeApiKeyInput.value.trim() || null
            : null,
        context_window: (function () {
          if (!forgeContextWindowInput) return null;
          const val = parseInt(forgeContextWindowInput.value, 10);
          return Number.isFinite(val) && val > 0 ? val : null;
        })(),
        model: forgeAgentModelSelect ? forgeAgentModelSelect.value : 'default',
        allowed_skill: checkedSkills,
        // D10: a stale tab gets 409 instead of dropping a tick accepted elsewhere
        expected_skills_version: (activeForgeAgent && activeForgeAgent.skills_version) || null,
        show_in_chat: forgeShowInChat ? forgeShowInChat.checked : true,
        max_turns: parseInt(forgeMaxTurnsInput ? forgeMaxTurnsInput.value : DEFAULT_AGENT_MAX_TURNS, 10) || DEFAULT_AGENT_MAX_TURNS,
        history_retention_days: (function () { const n = parseInt(forgeRetentionDaysInput ? forgeRetentionDaysInput.value : 30, 10); return Number.isFinite(n) && n >= 0 ? n : 30; })(),
        always_auto_run: Boolean(forgeAlwaysAutoRunInput && forgeAlwaysAutoRunInput.checked), // CARD-573
        storage_enabled: Boolean(forgeStorageEnabled && forgeStorageEnabled.checked),
        storage_type: forgeStorageType ? forgeStorageType.value : 'sqlite',
        memory_enabled: Boolean(forgeMemoryEnabled && forgeMemoryEnabled.checked),
        memory_retention_days: (function () {
          const n = parseInt(forgeMemoryRetentionDays ? forgeMemoryRetentionDays.value : 30, 10);
          return Number.isFinite(n) && n >= 1 && n <= 365 ? n : 30;
        })(),
        pinned_memory: forgePinnedMemory ? forgePinnedMemory.value.trim() : '',
        mcp_servers: currentAgentMcpServers.length > 0
          ? currentAgentMcpServers
          : (activeForgeAgent && activeForgeAgent.mcp_servers ? activeForgeAgent.mcp_servers : []),
        allowed_credentials: (function () {
          const creds = [];
          $queryAll('.forge-credential-checkbox:checked', forgeCredentialGrantsList).forEach((cb) => {
            if (cb.value) creds.push(cb.value);
          });
          return creds;
        })(),
      };

      const isExisting = Boolean(activeForgeAgent && activeForgeAgent.id === id);
      const url = isExisting ? `/api/agents/${encodeURIComponent(id)}` : '/api/agents';
      const method = isExisting ? 'PUT' : 'POST';

      try {
        saveAgentBtn.disabled = true;
        saveAgentBtn.innerHTML =
          '<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Saving...</span>';
        safeCreateIcons();

        const res = await fetch(url, {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          let errMsg = 'Failed to save agent profile';
          const errData = await res.json().catch(() => ({}));
          if (Array.isArray(errData.detail)) {
            errMsg = errData.detail
              .map((d) => {
                const loc = Array.isArray(d.loc) ? d.loc.filter((x) => x !== 'body').join('.') : '';
                return loc ? `${loc}: ${d.msg}` : d.msg;
              })
              .join('; ');
          } else if (typeof errData.detail === 'string') {
            errMsg = errData.detail;
          }
          throw new Error(errMsg);
        }

        saveAgentBtn.innerHTML = '<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400"></i><span>Saved!</span>';
        setTimeout(() => {
          saveAgentBtn.innerHTML = '<i data-lucide="save" class="w-3.5 h-3.5"></i><span>Save Profile</span>';
          saveAgentBtn.disabled = false;
          safeCreateIcons();
        }, 2000);

        showToast(`Agent "${name}" saved successfully!`, 'success');

        if (forgeStatusBanner) {
          forgeStatusBanner.textContent = `Agent "${name}" saved successfully!`;
          forgeStatusBanner.className =
            'px-4 py-2 text-xs font-medium text-center border-b border-emerald-800 bg-emerald-950/60 text-emerald-300 block';
          setTimeout(() => forgeStatusBanner.classList.add('hidden'), 3500);
        }

        if (callbacks.onAgentSaved) {
          await callbacks.onAgentSaved(id);
        }
        await loadAgentForge();
        if (forgeAgentSelect) forgeAgentSelect.value = id;
      } catch (err) {
        console.error('[AutoReiv UI] Save agent error:', err);
        showToast(`Error saving agent: ${err.message}`, 'error');
        saveAgentBtn.innerHTML = '<i data-lucide="save" class="w-3.5 h-3.5"></i><span>Save Profile</span>';
        saveAgentBtn.disabled = false;
        safeCreateIcons();
      }
    });
  }

  // Storage toggle sync
  if (forgeStorageEnabled && forgeStorageTypeContainer) {
    forgeStorageEnabled.addEventListener('change', () => {
      forgeStorageTypeContainer.classList.toggle('hidden', !forgeStorageEnabled.checked);
      const storageSkillPill = document.querySelector('.forge-skill-pill[data-skill-id="sqlite-storage"]');
      if (storageSkillPill) {
        storageSkillPill.setAttribute('aria-pressed', forgeStorageEnabled.checked ? 'true' : 'false');
      }
      onToggleSkill('sqlite-storage', forgeStorageEnabled.checked);
    });
  }

  // Agent selector change
  if (forgeAgentSelect) {
    forgeAgentSelect.addEventListener('change', () => {
      const selectedId = forgeAgentSelect.value;
      loadGuard.userPicked(); // CARD-573
      if (selectedId) storageSet(PICKER_KEYS.agents, selectedId);
      const agent = (state.agents || []).find((a) => a.id === selectedId);
      if (agent) renderAgentToForge(agent);
      else if (selectedId) { // CARD-573: roster not loaded yet; the running load (or a new one) shows the pick
        activeForgeAgent = null; forgeBusy = true; setForgeFormBusy(true);
        if (!loadsInFlight) loadAgentForge(selectedId);
      }
    });
  }

  // Avatar select change
  if (forgeAvatarSelect) {
    forgeAvatarSelect.addEventListener('change', () => {
      updateAvatarPreview(forgeAvatarSelect.value);
    });
  }

  // New Agent button -> blank new-agent form in Agent Studio (CARD-569)
  if (newAgentBtn) {
    newAgentBtn.addEventListener('click', () => {
      openQuickScaffoldModal();
    });
  }

  // Observability cross link
  if (forgeOpenObserveBtn) {
    forgeOpenObserveBtn.addEventListener('click', () => {
      if (typeof callbacks.switchTab === 'function') callbacks.switchTab('observability');
    });
  }

  // Link routine for agent
  if (linkRoutineForAgentBtn) {
    linkRoutineForAgentBtn.addEventListener('click', () => {
      const agentId = getActiveAgentId();
      if (callbacks.openRoutineModal) callbacks.openRoutineModal(null, agentId);
    });
  }

  // Wire Submodules
  setupArchitecturalProposals({
    getActiveAgentId,
  });

  setupScaffold({
    callbacks,
    onLoadAgent: loadAgentForge,
  });

  setupAgentMcpControls({
    openToolsStudio: (agentId) => {
      if (typeof callbacks.openToolsStudio === 'function') {
        callbacks.openToolsStudio(agentId, 'agent');
      }
    },
  });

  setupRunbookEditor({
    getActiveAgentId,
    openSkillStudio: (agentId, skillId) => {
      if (typeof callbacks.openSkillStudio === 'function') {
        callbacks.openSkillStudio(agentId, skillId);
      }
    },
  });

  setupAgentModelConfig();

  setupBrainDrawer({
    getActiveAgentId,
  });

  setupToneManager();

  return {
    loadAgentForge,
    renderAgentToForge,
    loadAgentCredentialGrants,
    loadArchitecturalProposals,
  };
}
