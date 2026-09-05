/**
 * Agent Studio module [REQ-FE-001, REQ-FORGE-006]. Filename forge.js kept (CARD-118).
 */

import { $, $query, $queryAll, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { showToast } from '../ui/toast.js';
import { PRESETS_DEFAULTS } from './settings.js';

export function startNewAgentPackFromStudio(callbacks = {}) {
  if (typeof callbacks.onStartNewAgentPack === 'function') {
    callbacks.onStartNewAgentPack();
    return true;
  }
  return false;
}

export function initAgentForge(state, callbacks = {}) {
  const forgeAgentSelect = $('forgeAgentSelect');
  const newAgentBtn = $('newAgentBtn');
  const forgeTrainNewAgentBtn = $('forgeTrainNewAgentBtn');
  const forgeTrainAgentBtn = $('forgeTrainAgentBtn');
  const saveAgentBtn = $('saveAgentBtn');
  const deleteAgentBtn = $('deleteAgentBtn');
  const forgeImportPackBtn = $('forgeImportPackBtn');
  const forgeExportPackBtn = $('forgeExportPackBtn');
  const forgeImportPackInput = $('forgeImportPackInput');
  const forgeShowInChat = $('forgeShowInChat');
  const forgeStatusBanner = $('forgeStatusBanner');
  const forgeBuiltinBadge = $('forgeBuiltinBadge');
  const forgeAvatarPreview = $('forgeAvatarIcon');
  const forgeAvatarSelect = $('forgeAvatarSelect');
  const forgeNameInput = $('forgeNameInput');
  const forgeIdInput = $('forgeIdInput');
  const forgeDescInput = $('forgeDescInput');
  const forgeToneSelect = $('forgeToneSelect');
  const forgeMaxTurnsInput = $('forgeMaxTurnsInput');
  const forgeRetentionDaysInput = $('forgeRetentionDaysInput');
  const forgeProviderSelect = $('forgeProviderSelect');
  const forgeProviderConfigContainer = $('forgeProviderConfigContainer');
  const forgeApiBaseUrlInput = $('forgeApiBaseUrlInput');
  const forgeApiKeyInput = $('forgeApiKeyInput');
  const forgeContextWindowInput = $('forgeContextWindowInput');
  const forgeDiscoverModelsBtn = $('forgeDiscoverModelsBtn');
  const forgeAgentModelSelect = $('forgeAgentModelSelect');
  let cachedDiscoveredModels = [];
  const forgeStorageEnabled = $('forgeStorageEnabled');
  const forgeStorageTypeContainer = $('forgeStorageTypeContainer');
  const forgeStorageType = $('forgeStorageType');
  const forgeMemoryEnabled = $('forgeMemoryEnabled');
  const forgeMemoryRetentionDays = $('forgeMemoryRetentionDays');
  const forgeMemoryRetentionDaysLabel = $('forgeMemoryRetentionDaysLabel');
  const forgePinnedMemory = $('forgePinnedMemory');
  const btnOpenBrainDrawer = $('btnOpenBrainDrawer');
  const btnPurgeBrain = $('btnPurgeBrain');
  const agentBrainDrawer = $('agentBrainDrawer');
  const brainDrawerAgentName = $('brainDrawerAgentName');
  const brainSearchInput = $('brainSearchInput');
  const brainShelfPinnedContainer = $('brainShelfPinnedContainer');
  const brainShelfSummariesCount = $('brainShelfSummariesCount');
  const brainShelfSummariesContainer = $('brainShelfSummariesContainer');
  const brainShelfFactsCount = $('brainShelfFactsCount');
  const brainShelfFactsContainer = $('brainShelfFactsContainer');
  const closeBrainDrawerBtn = $('closeBrainDrawerBtn');
  const closeBrainDrawerFooterBtn = $('closeBrainDrawerFooterBtn');
  const forgeSystemPrompt = $('forgeSystemPrompt');
  const forgeSkillsGrid = $('forgeSkillsGrid');
  const forgePackBoxTitle = $('forgePackBoxTitle');
  const forgeRunbooksGrid = $('forgeRunbooksGrid');
  const studioWorkflowsList = $('studioWorkflowsList');
  const selectAllToolsBtn = $('selectAllToolsBtn');
  const clearAllToolsBtn = $('clearAllToolsBtn');
  const forgeStatTurns = $('forgeStatTurns');
  const forgeStatTokens = $('forgeStatTokens');
  const forgeStatCost = $('forgeStatCost');
  const forgeStatTools = $('forgeStatTools');
  const forgeStatErrors = $('forgeStatErrors');
  const forgeStatLatency = $('forgeStatLatency');

  const linkRoutineForAgentBtn = $('linkRoutineForAgentBtn');
  const forgeAssignedRoutinesList = $('forgeAssignedRoutinesList');

  const manageTonesBtn = $('manageTonesBtn');
  const manageTonesModal = $('manageTonesModal');
  const closeManageTonesModalBtn = $('closeManageTonesModalBtn');
  const openNewToneFormBtn = $('openNewToneFormBtn');
  const manageTonesList = $('manageTonesList');
  const manageToneForm = $('manageToneForm');
  const manageToneFormTitle = $('manageToneFormTitle');
  const closeToneFormBtn = $('closeToneFormBtn');
  const cancelToneFormBtn = $('cancelToneFormBtn');
  const toneFormMode = $('toneFormMode');
  const toneFormName = $('toneFormName');
  const toneFormId = $('toneFormId');
  const toneFormDescription = $('toneFormDescription');
  const toneFormDirective = $('toneFormDirective');

  let activeForgeAgent = null;
  let cachedSkillsCatalog = null;
  let cachedPlatformSkills = [];
  let cachedArchivedSkills = [];
  let cachedTones = [];
  let lastAllowedSkills = new Set();
  let activeRunbookId = '';
  let activeRunbookArchived = false;

  const studioRunbookEditor = $('studioRunbookEditor');
  const studioRunbookName = $('studioRunbookName');
  const studioRunbookBlurb = $('studioRunbookBlurb');
  const studioRunbookBody = $('studioRunbookBody');
  const studioRunbookPath = $('studioRunbookPath');
  const studioRunbookSaveBtn = $('studioRunbookSaveBtn');
  const studioRunbookArchiveBtn = $('studioRunbookArchiveBtn');
  const studioRunbookUnarchiveBtn = $('studioRunbookUnarchiveBtn');
  const studioRunbookDeleteBtn = $('studioRunbookDeleteBtn');
  const studioNewRunbookSlug = $('studioNewRunbookSlug');
  const studioNewRunbookBtn = $('studioNewRunbookBtn');

  function toolCheckboxHtml(tool, skillId = '', home = '') {
    const name = tool.name || '';
    const desc = tool.description || '';
    const skillAttr = skillId ? ` data-skill-id="${escapeHtml(skillId)}"` : '';
    const homeAttr = home ? ` data-home="${escapeHtml(home)}"` : '';
    return `
      <label class="flex items-start space-x-2 p-2 rounded-lg bg-slate-950/50 border border-slate-800 hover:border-slate-700 transition cursor-pointer text-xs">
        <input type="checkbox" value="${escapeHtml(name)}" class="forge-tool-checkbox mt-0.5 rounded border-slate-700 text-brand-500 focus:ring-brand-500"${skillAttr}${homeAttr}>
        <div class="flex-1 min-w-0">
          <span class="font-mono text-slate-200 block text-[11px] font-semibold truncate">${escapeHtml(name)}</span>
          <span class="text-slate-400 block text-[10px] line-clamp-2 leading-tight">${escapeHtml(desc)}</span>
        </div>
      </label>
    `;
  }

  function skillRowHtml(skill, home, archived = false) {
    const id = skill.id || '';
    const name = skill.name || id;
    const desc = skill.description || '';
    const tools = skill.tools || [];
    const archivedAttr = archived ? ' data-archived="1"' : '';
    const checkbox = archived
      ? ''
      : `<input type="checkbox" value="${escapeHtml(id)}" class="forge-skill-checkbox mt-0.5 rounded border-slate-700 text-brand-500 focus:ring-brand-500" data-home="${escapeHtml(home)}">`;
    const toolHtml = tools.length
      ? `<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">${tools.map((t) => toolCheckboxHtml(t, id, home)).join('')}</div>`
      : '<p class="text-[10px] text-slate-500 px-1">No tools nested under this skill.</p>';
    return `
      <div class="forge-skill-row rounded-lg bg-slate-900/60 border border-slate-800" data-skill-id="${escapeHtml(id)}" data-home="${escapeHtml(home)}">
        <div class="flex items-start gap-2 p-2">
          <label class="flex items-start space-x-2 flex-1 min-w-0 cursor-pointer">
            ${checkbox}
            <div class="flex-1 min-w-0">
              <span class="font-mono text-slate-200 block text-[11px] font-semibold truncate">${escapeHtml(name)}</span>
              <span class="text-slate-400 block text-[10px] line-clamp-2 leading-tight">${escapeHtml(desc)}</span>
            </div>
          </label>
          <button type="button" class="studio-runbook-open-btn shrink-0 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-semibold text-brand-300 border border-slate-700" data-pack-id="${escapeHtml(id)}"${archivedAttr}>Edit</button>
          <button type="button" class="forge-skill-expand shrink-0 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-semibold text-slate-300 border border-slate-700" aria-expanded="false">Tools</button>
        </div>
        <div class="forge-skill-tools hidden px-2 pb-2 space-y-2">
          ${toolHtml}
        </div>
      </div>
    `;
  }

  function applySkillChecks() {
    $queryAll('.forge-skill-checkbox').forEach((cb) => {
      cb.checked = lastAllowedSkills.has(cb.value);
    });
  }

  function bindSkillRowHandlers(root) {
    if (!root) return;
    root.querySelectorAll('.studio-runbook-open-btn').forEach((btn) => {
      btn.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        openRunbookEditor(btn.dataset.packId, btn.dataset.archived === '1');
      });
    });
    root.querySelectorAll('.forge-skill-expand').forEach((btn) => {
      btn.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        const row = btn.closest('.forge-skill-row');
        const tools = row ? row.querySelector('.forge-skill-tools') : null;
        if (!tools) return;
        const open = !tools.classList.contains('hidden');
        tools.classList.toggle('hidden', open);
        btn.setAttribute('aria-expanded', open ? 'false' : 'true');
      });
    });
  }

  function setRunbookActionVisibility() {
    const has = Boolean(activeRunbookId);
    if (studioRunbookArchiveBtn) {
      studioRunbookArchiveBtn.classList.toggle('hidden', !has || activeRunbookArchived);
    }
    if (studioRunbookUnarchiveBtn) {
      studioRunbookUnarchiveBtn.classList.toggle('hidden', !has || !activeRunbookArchived);
    }
    if (studioRunbookDeleteBtn) {
      studioRunbookDeleteBtn.classList.toggle('hidden', !has);
    }
  }

  function hideRunbookEditor() {
    activeRunbookId = '';
    activeRunbookArchived = false;
    if (studioRunbookEditor) studioRunbookEditor.classList.add('hidden');
    if (studioRunbookName) studioRunbookName.value = '';
    if (studioRunbookBlurb) studioRunbookBlurb.value = '';
    if (studioRunbookBody) studioRunbookBody.value = '';
    if (studioRunbookPath) studioRunbookPath.textContent = '';
    setRunbookActionVisibility();
  }

  function applyRunbook(data, archivedHint) {
    const manifest = data.manifest || {};
    activeRunbookId = manifest.id || activeRunbookId;
    activeRunbookArchived = Boolean(archivedHint || data.archived || manifest.origin === 'archived');
    if (studioRunbookName) studioRunbookName.value = manifest.name || data.name || '';
    if (studioRunbookBlurb) studioRunbookBlurb.value = manifest.description || data.description || '';
    if (studioRunbookBody) studioRunbookBody.value = data.instructions || '';
    if (studioRunbookPath) studioRunbookPath.textContent = manifest.path || '';
    if (studioRunbookEditor) studioRunbookEditor.classList.remove('hidden');
    setRunbookActionVisibility();
    safeCreateIcons();
  }

  async function openRunbookEditor(packId, archived) {
    if (!packId) return;
    try {
      const res = await fetch(`/api/skills/user-packs/${encodeURIComponent(packId)}`);
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      applyRunbook(data, archived);
    } catch (err) {
      showToast(String(err.message || err), 'error');
    }
  }

  function renderPlatformSkills() {
    if (!forgeSkillsGrid) return;
    const packOwnedIds = new Set((activeForgeAgent && activeForgeAgent.pack_skills ? activeForgeAgent.pack_skills : []).map((s) => s.id));
    const platform = (cachedPlatformSkills || []).filter((s) => !packOwnedIds.has(s.id));
    const archived = cachedArchivedSkills || [];
    const platformHtml = platform.length
      ? platform.map((s) => skillRowHtml(s, 'platform', false)).join('')
      : '<p class="text-[10px] text-slate-500 px-1">No platform runbooks in the skills data dir.</p>';
    const archivedHtml = archived.length
      ? `<div class="space-y-2 pt-2"><h4 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Archived</h4>${archived.map((s) => skillRowHtml(s, 'archived', true)).join('')}</div>`
      : '';
    forgeSkillsGrid.innerHTML = `${platformHtml}${archivedHtml}`;
    bindSkillRowHandlers(forgeSkillsGrid);
    applySkillChecks();
  }

  function renderPackSkills() {
    if (!forgeRunbooksGrid) return;
    const packSkills = (activeForgeAgent && activeForgeAgent.pack_skills) || [];
    const packHtml = packSkills.length
      ? packSkills.map((s) => skillRowHtml(s, 'pack', false)).join('')
      : '<p class="text-[10px] text-slate-500 px-1">No pack-owned skills yet.</p>';
    forgeRunbooksGrid.innerHTML = packHtml;
    bindSkillRowHandlers(forgeRunbooksGrid);
    applySkillChecks();
  }

  function renderNestedHomes() {
    renderPlatformSkills();
    renderPackSkills();
  }

  async function loadPlatformSkills() {
    try {
      if (cachedSkillsCatalog && Array.isArray(cachedSkillsCatalog.platform_skills)) {
        cachedPlatformSkills = cachedSkillsCatalog.platform_skills;
      } else {
        const res = await fetch('/api/skills/user-packs');
        if (res.ok) {
          const data = await res.json();
          cachedPlatformSkills = data.packs || [];
        }
      }
      const archRes = await fetch('/api/skills/archived-packs');
      if (archRes.ok) {
        const archData = await archRes.json();
        cachedArchivedSkills = archData.packs || [];
      } else {
        cachedArchivedSkills = [];
      }
    } catch (e) {
      console.warn('[AutoReiv UI] Failed to load platform skills:', e);
      cachedPlatformSkills = [];
      cachedArchivedSkills = [];
    }
    renderNestedHomes();
  }

  function populateAgentModelSelect(selectedProvider, targetModel = 'default') {
    if (!forgeAgentModelSelect) return;
    forgeAgentModelSelect.innerHTML = '<option value="default">Use Global Default</option>';
    const prov = (selectedProvider || 'default').toLowerCase();

    const filteredModels =
      prov === 'default'
        ? cachedDiscoveredModels
        : cachedDiscoveredModels.filter((m) => (m.provider || '').toLowerCase() === prov);

    filteredModels.forEach((m) => {
      const opt = document.createElement('option');
      opt.value = m.name;
      opt.textContent = prov === 'default' ? `${m.name} (${m.provider})` : m.name;
      forgeAgentModelSelect.appendChild(opt);
    });

    if (targetModel && targetModel !== 'default') {
      const exists = Array.from(forgeAgentModelSelect.options).some((o) => o.value === targetModel);
      if (!exists) {
        const customOpt = document.createElement('option');
        customOpt.value = targetModel;
        customOpt.textContent = `${targetModel} (Custom)`;
        forgeAgentModelSelect.appendChild(customOpt);
      }
      forgeAgentModelSelect.value = targetModel;
    } else {
      forgeAgentModelSelect.value = 'default';
    }
  }

  function updateProviderConfigVisibility(provider) {
    const p = (provider || 'default').toLowerCase();
    if (!forgeProviderConfigContainer) return;
    if (p === 'default') {
      forgeProviderConfigContainer.classList.add('hidden');
    } else {
      forgeProviderConfigContainer.classList.remove('hidden');
      if (PRESETS_DEFAULTS[p] && forgeApiKeyInput) {
        forgeApiKeyInput.placeholder = PRESETS_DEFAULTS[p].keyPlaceholder || 'Optional for Local';
      }
    }
  }

  async function discoverModelsForAgent() {
    const prov = forgeProviderSelect ? forgeProviderSelect.value : 'default';
    const isCustom = prov !== 'default';
    const url = isCustom && forgeApiBaseUrlInput ? forgeApiBaseUrlInput.value.trim() : '';
    const key = isCustom && forgeApiKeyInput ? forgeApiKeyInput.value.trim() : '';

    if (forgeDiscoverModelsBtn) {
      forgeDiscoverModelsBtn.disabled = true;
      forgeDiscoverModelsBtn.innerHTML = '<span>⏳ Discovering...</span>';
    }

    try {
      const params = new URLSearchParams();
      if (isCustom) {
        params.set('provider_id', prov);
        if (url) params.set('host_url', url);
        if (key) params.set('api_key', key);
      }
      const query = params.toString();
      const endpoint = query ? `/api/models/discover?${query}` : '/api/models/discover';
      const res = await fetch(endpoint);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      const discovered = data.models || [];
      if (isCustom) {
        cachedDiscoveredModels = [
          ...cachedDiscoveredModels.filter((m) => (m.provider || '').toLowerCase() !== prov.toLowerCase()),
          ...discovered,
        ];
      } else {
        cachedDiscoveredModels = discovered;
      }
      const curModel = forgeAgentModelSelect ? forgeAgentModelSelect.value : 'default';
      populateAgentModelSelect(prov, curModel);
      showToast(`Discovered ${discovered.length} model(s) for ${prov}`, 'success');
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to discover models:', err);
      showToast(`Failed to discover models: ${err.message || err}`, 'error');
    } finally {
      if (forgeDiscoverModelsBtn) {
        forgeDiscoverModelsBtn.disabled = false;
        forgeDiscoverModelsBtn.innerHTML = '<span>🔄 Refresh Models</span>';
      }
    }
  }

  async function loadAgentForge() {
    try {
      const catRes = await fetch('/api/skills/catalog');
      if (catRes.ok) {
        cachedSkillsCatalog = await catRes.json();
      }
      await loadPlatformSkills();

      try {
        const modRes = await fetch('/api/models/discover');
        if (modRes.ok) {
          const modData = await modRes.json();
          cachedDiscoveredModels = modData.models || [];
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
      state.agents = agents;
      const studioAgents = agents.filter((a) => a.id !== 'agent-builder');

      if (forgeAgentSelect) {
        const selectedId = forgeAgentSelect.value || (studioAgents[0] ? studioAgents[0].id : null);
        forgeAgentSelect.innerHTML = '';
        studioAgents.forEach((a) => {
          const opt = document.createElement('option');
          opt.value = a.id;
          opt.textContent = `${a.name} ${a.is_platform_pack ? '(Platform)' : a.is_builtin ? '(Built-in)' : '(Custom)'}`;
          forgeAgentSelect.appendChild(opt);
        });

        if (selectedId && studioAgents.some((a) => a.id === selectedId)) {
          forgeAgentSelect.value = selectedId;
        } else if (studioAgents.length > 0) {
          forgeAgentSelect.value = studioAgents[0].id;
        }

        const targetAgent = studioAgents.find((a) => a.id === forgeAgentSelect.value) || studioAgents[0];
        if (targetAgent) {
          renderAgentToForge(targetAgent);
        }
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load Agent Studio:', err);
    }
  }

  async function renderAgentToForge(agent) {
    activeForgeAgent = agent;
    if (!agent) return;

    if (forgeNameInput) forgeNameInput.value = agent.name || '';
    if (forgeIdInput) {
      forgeIdInput.value = agent.id || '';
      forgeIdInput.disabled = true;
    }
    if (forgeDescInput) forgeDescInput.value = agent.description || '';
    if (forgeSystemPrompt) forgeSystemPrompt.value = agent.system_prompt || '';
    loadTones(agent.tone || 'default');
    if (forgeMaxTurnsInput) forgeMaxTurnsInput.value = agent.max_turns || 10;
    if (forgeRetentionDaysInput) forgeRetentionDaysInput.value = (agent.history_retention_days === 0 || agent.history_retention_days) ? agent.history_retention_days : 30;
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
    if (forgePackBoxTitle) {
      forgePackBoxTitle.textContent = `${agent.name || 'Agent'} Pack Skills & Tools`;
    }

    renderNestedHomes();

    updateAvatarPreview(agent.avatar_icon || 'bot');

    if (forgeBuiltinBadge) {
      if (agent.is_platform_pack) {
        forgeBuiltinBadge.textContent = 'Platform Agent Pack';
        forgeBuiltinBadge.className =
          'text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800';
      } else if (agent.is_builtin) {
        forgeBuiltinBadge.textContent = 'Built-in Baseline';
        forgeBuiltinBadge.className =
          'text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800';
      } else {
        forgeBuiltinBadge.textContent = 'Custom Agent';
        forgeBuiltinBadge.className =
          'text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';
      }
    }

    if (deleteAgentBtn) {
      if (agent.is_builtin || agent.is_platform_pack) {
        deleteAgentBtn.disabled = true;
        deleteAgentBtn.classList.add('opacity-40', 'cursor-not-allowed');
      } else {
        deleteAgentBtn.disabled = false;
        deleteAgentBtn.classList.remove('opacity-40', 'cursor-not-allowed');
      }
    }

    const allowed = new Set(agent.allowed_tool_names || agent.allowed_tools || []);
    const checkboxes = $queryAll('.forge-tool-checkbox');
    checkboxes.forEach((cb) => {
      cb.checked = allowed.has(cb.value);
    });

    lastAllowedSkills = new Set(agent.allowed_skill || []);
    applySkillChecks();

    loadAgentTelemetry(agent.id);
    loadAgentAssignedRoutines(agent.id);
    loadAgentWorkflows(agent.id);
  }

  function updateAvatarPreview(iconName) {
    if (forgeAvatarPreview) {
      forgeAvatarPreview.innerHTML = `<i data-lucide="${iconName}" class="w-7 h-7"></i>`;
      safeCreateIcons();
    }
  }


  function chapterKindLabel(kind) {
    return kind === 'handoff' ? 'handoff' : 'skill';
  }

  async function loadAgentWorkflows(agentId) {
    if (!studioWorkflowsList) return;
    if (!agentId) {
      studioWorkflowsList.innerHTML = '<p id="studioWorkflowsEmpty" class="text-[11px] text-slate-500">No workflows yet.</p>';
      return;
    }
    try {
      const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/workflows`);
      const items = res.ok ? await res.json() : [];
      renderStudioWorkflows(agentId, Array.isArray(items) ? items : []);
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to load workflows:', err);
      studioWorkflowsList.innerHTML = '<p id="studioWorkflowsEmpty" class="text-[11px] text-slate-500">No workflows yet.</p>';
    }
  }

  function renderStudioWorkflows(agentId, workflows) {
    if (!studioWorkflowsList) return;
    if (!workflows.length) {
      studioWorkflowsList.innerHTML = '<p id="studioWorkflowsEmpty" class="text-[11px] text-slate-500">No workflows yet.</p>';
      return;
    }
    studioWorkflowsList.innerHTML = workflows.map((wf) => {
      const chapters = Array.isArray(wf.chapters) ? wf.chapters : [];
      const rows = chapters.map((ch, idx) => {
        const kind = chapterKindLabel(ch.kind);
        const who = kind === 'handoff' ? (ch.handoff_target_agent_id || ch.assigned_agent_id || '') : (ch.assigned_agent_id || agentId);
        return `<div class="flex flex-wrap items-center gap-1.5 text-[11px]" data-wf-id="${escapeHtml(wf.id)}" data-ch-idx="${idx}">
          <span class="font-mono text-slate-500 w-4">${idx + 1}.</span>
          <input data-wf-field="name" class="flex-1 min-w-[7rem] bg-slate-800 border border-slate-700 rounded px-1.5 py-0.5 text-[11px] text-slate-100" value="${escapeHtml(ch.name || '')}">
          <select data-wf-field="kind" class="bg-slate-800 border border-slate-700 rounded px-1 py-0.5 text-[11px] text-slate-200">
            <option value="skill"${kind === 'skill' ? ' selected' : ''}>skill</option>
            <option value="handoff"${kind === 'handoff' ? ' selected' : ''}>handoff</option>
          </select>
          <input data-wf-field="who" class="w-32 bg-slate-800 border border-slate-700 rounded px-1.5 py-0.5 text-[11px] text-slate-200 font-mono" value="${escapeHtml(who)}" title="Who owns this chapter">
          <input data-wf-field="done" class="flex-1 min-w-[8rem] bg-slate-800 border border-slate-700 rounded px-1.5 py-0.5 text-[11px] text-slate-300" value="${escapeHtml(ch.success_rule || '')}" placeholder="done when">
          <button type="button" data-wf-move="-1" class="px-1 text-slate-400 hover:text-white" title="Move up">Up</button>
          <button type="button" data-wf-move="1" class="px-1 text-slate-400 hover:text-white" title="Move down">Down</button>
        </div>`;
      }).join('');
      return `<div class="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800 space-y-2" data-workflow-card="${escapeHtml(wf.id)}">
        <div class="flex flex-wrap items-center gap-2">
          <input data-wf-name class="flex-1 min-w-[8rem] bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white font-medium" value="${escapeHtml(wf.name || '')}">
          <button type="button" data-wf-save class="px-2 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-[11px] font-semibold">Save</button>
          <button type="button" data-wf-delete class="px-2 py-1 bg-slate-800 hover:bg-rose-900/70 text-rose-300 rounded text-[11px] font-semibold border border-slate-700">Delete</button>
        </div>
        <div class="space-y-1" data-wf-chapters>${rows}</div>
      </div>`;
    }).join('');

    studioWorkflowsList.querySelectorAll('[data-workflow-card]').forEach((card) => {
      const wfId = card.getAttribute('data-workflow-card');
      card.querySelector('[data-wf-save]')?.addEventListener('click', () => saveStudioWorkflow(agentId, wfId, card));
      card.querySelector('[data-wf-delete]')?.addEventListener('click', () => deleteStudioWorkflow(agentId, wfId, card));
      card.querySelectorAll('[data-wf-move]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const dir = Number(btn.getAttribute('data-wf-move') || 0);
          moveStudioChapter(card, btn.closest('[data-ch-idx]'), dir);
        });
      });
    });
  }

  function collectStudioChapters(card) {
    const rows = [...card.querySelectorAll('[data-ch-idx]')];
    return rows.map((row) => {
      const kind = row.querySelector('[data-wf-field="kind"]')?.value || 'skill';
      const who = (row.querySelector('[data-wf-field="who"]')?.value || '').trim();
      const name = (row.querySelector('[data-wf-field="name"]')?.value || '').trim();
      return {
        name: name || 'Chapter',
        kind,
        assigned_agent_id: who,
        skill_id: null,
        handoff_target_agent_id: kind === 'handoff' ? who : null,
        success_rule: (row.querySelector('[data-wf-field="done"]')?.value || '').trim(),
      };
    });
  }

  function moveStudioChapter(card, row, dir) {
    if (!row) return;
    const parent = card.querySelector('[data-wf-chapters]');
    if (!parent) return;
    const rows = [...parent.children];
    const idx = rows.indexOf(row);
    const next = idx + dir;
    if (idx < 0 || next < 0 || next >= rows.length) return;
    if (dir < 0) parent.insertBefore(row, rows[next]);
    else parent.insertBefore(rows[next], row);
  }

  async function saveStudioWorkflow(agentId, workflowId, card) {
    const name = (card.querySelector('[data-wf-name]')?.value || '').trim();
    if (!name) {
      showToast('Workflow name is required.', 'error');
      return;
    }
    try {
      const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/workflows/${encodeURIComponent(workflowId)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, chapters: collectStudioChapters(card) }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showToast('Workflow saved', 'success');
      await loadAgentWorkflows(agentId);
    } catch (err) {
      showToast(String(err.message || err), 'error');
    }
  }

  async function deleteStudioWorkflow(agentId, workflowId, card) {
    const name = (card.querySelector('[data-wf-name]')?.value || workflowId);
    if (!window.confirm(`Delete workflow "${name}"? This cannot be undone.`)) return;
    try {
      const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/workflows/${encodeURIComponent(workflowId)}`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showToast('Workflow deleted', 'success');
      await loadAgentWorkflows(agentId);
    } catch (err) {
      showToast(String(err.message || err), 'error');
    }
  }

  async function loadAgentAssignedRoutines(agentId) {
    if (!forgeAssignedRoutinesList) return;
    try {
      const res = await fetch(`/api/routines?agent_id=${encodeURIComponent(agentId)}`);
      if (!res.ok) return;
      const routines = await res.json();
      forgeAssignedRoutinesList.innerHTML = '';

      if (routines.length === 0) {
        forgeAssignedRoutinesList.innerHTML = `
          <p class="text-[11px] text-slate-500 italic py-1">No scheduled background routines currently assigned to this agent.</p>
        `;
        return;
      }

      routines.forEach((r) => {
        const item = document.createElement('div');
        item.className =
          'p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/60 flex items-center justify-between text-xs space-x-2';
        item.innerHTML = `
          <div class="min-w-0 flex-1">
            <div class="flex items-center space-x-2">
              <span class="font-semibold text-slate-200 truncate">${escapeHtml(r.name)}</span>
              <span class="text-[9px] font-mono px-1.5 py-0.2 rounded ${r.enabled ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-amber-950 text-amber-400 border border-amber-800'}">${r.enabled ? 'Active' : 'Paused'}</span>
            </div>
            <div class="text-[10px] text-slate-400 flex items-center space-x-2 mt-0.5">
              <span>${escapeHtml(r.human_schedule || r.cron_expression)}</span>
              <span class="text-brand-400 font-mono">Next: ${escapeHtml(r.next_run_eta || 'scheduled')}</span>
            </div>
          </div>
          <div class="flex items-center space-x-1 flex-shrink-0">
            <button class="forge-routine-run-btn p-1.5 rounded bg-slate-700 hover:bg-brand-600 text-slate-200 hover:text-white transition" title="Run Routine Now">
              <i data-lucide="play" class="w-3 h-3"></i>
            </button>
            <button class="forge-routine-edit-btn p-1.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 transition" title="Edit Routine">
              <i data-lucide="edit-3" class="w-3 h-3"></i>
            </button>
          </div>
        `;
        forgeAssignedRoutinesList.appendChild(item);

        $query('.forge-routine-edit-btn', item)?.addEventListener('click', () => {
          const routinesTabBtn = $query('.tab-btn[data-tab="routines"]');
          if (routinesTabBtn) routinesTabBtn.click();
          if (callbacks.openRoutineModal) callbacks.openRoutineModal(r);
        });

        $query('.forge-routine-run-btn', item)?.addEventListener('click', async (e) => {
          const btn = e.currentTarget;
          btn.innerHTML = `<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i>`;
          try {
            await fetch(`/api/routines/${r.id}/run`, { method: 'POST' });
            btn.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i>`;
            setTimeout(() => {
              btn.innerHTML = `<i data-lucide="play" class="w-3 h-3"></i>`;
              safeCreateIcons();
            }, 2000);
          } catch (err) {
            console.error('[AutoReiv UI] Failed to run routine from Agent Studio:', err);
            btn.innerHTML = `<i data-lucide="play" class="w-3 h-3"></i>`;
            safeCreateIcons();
          }
        });
      });

      safeCreateIcons();
    } catch (e) {
      console.warn('[AutoReiv UI] Failed to load agent assigned routines:', e);
    }
  }

  if (linkRoutineForAgentBtn) {
    linkRoutineForAgentBtn.addEventListener('click', () => {
      const agentId = activeForgeAgent ? activeForgeAgent.id : forgeAgentSelect ? forgeAgentSelect.value : null;
      if (callbacks.openRoutineModal) callbacks.openRoutineModal(null, agentId);
    });
  }

  async function loadAgentTelemetry(agentId) {
    try {
      const res = await fetch(`/api/observability/kpi?agent_id=${encodeURIComponent(agentId)}`);
      if (!res.ok) return;
      const data = await res.json();

      // Resolve matching agent metrics (or match legacy aliases)
      const aliases = [agentId];
      if (agentId === 'assistant') aliases.push('general-assistant');
      if (agentId === 'general-assistant') aliases.push('assistant');

      const agentMetrics =
        (data.agents || []).find((a) => aliases.includes(a.agent_id)) ||
        (data.overview && data.overview.total_turns > 0 ? data.overview : null);

      if (agentMetrics) {
        const turns = agentMetrics.turn_count ?? agentMetrics.total_turns ?? 0;
        const tokens = agentMetrics.total_tokens ?? 0;
        const cost = agentMetrics.estimated_cost_usd ?? tokens * 0.000001;
        const tools = agentMetrics.tool_call_count ?? agentMetrics.total_tool_calls ?? 0;
        const errors = agentMetrics.error_count ?? 0;
        const errorPct = turns > 0 ? (errors / turns) * 100 : (agentMetrics.error_rate_pct ?? 0);
        const latency = agentMetrics.avg_duration_ms ?? agentMetrics.avg_turn_duration_ms ?? 0;

        if (forgeStatTurns) forgeStatTurns.textContent = turns.toLocaleString();
        if (forgeStatTokens) forgeStatTokens.textContent = tokens.toLocaleString();
        if (forgeStatCost) forgeStatCost.textContent = `$${cost < 0.01 && cost > 0 ? cost.toFixed(4) : cost.toFixed(2)}`;
        if (forgeStatTools) forgeStatTools.textContent = tools.toLocaleString();
        if (forgeStatErrors) forgeStatErrors.textContent = `${errorPct.toFixed(1)}%`;
        if (forgeStatLatency) forgeStatLatency.textContent = `${Math.round(latency)}ms`;
      } else {
        if (forgeStatTurns) forgeStatTurns.textContent = '0';
        if (forgeStatTokens) forgeStatTokens.textContent = '0';
        if (forgeStatCost) forgeStatCost.textContent = '$0.00';
        if (forgeStatTools) forgeStatTools.textContent = '0';
        if (forgeStatErrors) forgeStatErrors.textContent = '0.0%';
        if (forgeStatLatency) forgeStatLatency.textContent = '0ms';
      }
    } catch (e) {
      console.warn('[AutoReiv UI] Failed to load agent telemetry:', e);
    }
  }

  if (forgeAgentSelect) {
    forgeAgentSelect.addEventListener('change', () => {
      const selectedId = forgeAgentSelect.value;
      const agent = (state.agents || []).find((a) => a.id === selectedId);
      if (agent) renderAgentToForge(agent);
    });
  }

  if (forgeAvatarSelect) {
    forgeAvatarSelect.addEventListener('change', () => {
      updateAvatarPreview(forgeAvatarSelect.value);
    });
  }


  if (forgeExportPackBtn) {
    forgeExportPackBtn.addEventListener('click', async () => {
      const id = (activeForgeAgent && activeForgeAgent.id) || (forgeIdInput ? forgeIdInput.value.trim() : '');
      if (!id) {
        showToast('Select an agent to export.', 'warning');
        return;
      }
      try {
        const res = await fetch(`/api/agents/${encodeURIComponent(id)}/pack.zip`);
        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `HTTP ${res.status}`);
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${id}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
        showToast(`Exported ${id}`, 'success');
      } catch (err) {
        showToast(`Export failed: ${err.message || err}`, 'error');
      }
    });
  }

  if (forgeImportPackBtn && forgeImportPackInput) {
    forgeImportPackBtn.addEventListener('click', () => forgeImportPackInput.click());
    forgeImportPackInput.addEventListener('change', async (event) => {
      const file = event.target.files && event.target.files[0];
      event.target.value = '';
      if (!file) return;
      try {
        const body = new FormData();
        body.append('file', file);
        const res = await fetch('/api/agents/import-pack', { method: 'POST', body });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        const imported = data.agent || {};
        showToast(`Imported ${imported.name || imported.id || 'pack'}`, 'success');
        if (callbacks.onAgentSaved) {
          await callbacks.onAgentSaved(imported.id);
        }
        await loadAgentForge();
        if (forgeAgentSelect && imported.id) forgeAgentSelect.value = imported.id;
      } catch (err) {
        showToast(`Import failed: ${err.message || err}`, 'error');
      }
    });
  }

  if (forgeProviderSelect) {
    forgeProviderSelect.addEventListener('change', () => {
      const p = forgeProviderSelect.value;
      updateProviderConfigVisibility(p);
      if (p !== 'default' && PRESETS_DEFAULTS[p]) {
        const knownUrls = Object.values(PRESETS_DEFAULTS).map((preset) => preset.url);
        if (forgeApiBaseUrlInput && (!forgeApiBaseUrlInput.value || knownUrls.includes(forgeApiBaseUrlInput.value))) {
          forgeApiBaseUrlInput.value = PRESETS_DEFAULTS[p].url;
        }
      }
      const currentModel = forgeAgentModelSelect ? forgeAgentModelSelect.value : 'default';
      populateAgentModelSelect(p, currentModel);
    });
  }

  if (forgeDiscoverModelsBtn) {
    forgeDiscoverModelsBtn.addEventListener('click', () => {
      discoverModelsForAgent();
    });
  }

  if (forgeStorageEnabled && forgeStorageTypeContainer) {
    forgeStorageEnabled.addEventListener('change', () => {
      forgeStorageTypeContainer.classList.toggle('hidden', !forgeStorageEnabled.checked);
    });
  }

  if (forgeMemoryRetentionDays && forgeMemoryRetentionDaysLabel) {
    forgeMemoryRetentionDays.addEventListener('input', () => {
      forgeMemoryRetentionDaysLabel.textContent = `${forgeMemoryRetentionDays.value} days`;
    });
  }

  async function loadAndRenderBrainDrawer(agentId, query = '') {
    if (!agentBrainDrawer) return;
    if (brainDrawerAgentName) brainDrawerAgentName.textContent = `(${agentId})`;

    if (brainShelfPinnedContainer) {
      const pinned = forgePinnedMemory ? forgePinnedMemory.value.trim() : '';
      brainShelfPinnedContainer.textContent = pinned || 'No pinned directives configured.';
    }

    try {
      const url = query
        ? `/api/agents/${encodeURIComponent(agentId)}/memory?query=${encodeURIComponent(query)}`
        : `/api/agents/${encodeURIComponent(agentId)}/memory`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (data.pinned && data.pinned.content && brainShelfPinnedContainer) {
        brainShelfPinnedContainer.textContent = data.pinned.content;
      }

      // Shelf 2: Episodic Summaries
      const summaries = data.session_summaries || [];
      if (brainShelfSummariesCount) brainShelfSummariesCount.textContent = `${summaries.length} sessions`;
      if (brainShelfSummariesContainer) {
        if (summaries.length === 0) {
          brainShelfSummariesContainer.innerHTML = '<div class="text-slate-500 text-xs italic py-2">No episodic session summaries recorded yet.</div>';
        } else {
          brainShelfSummariesContainer.innerHTML = summaries.map((s) => `
            <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1.5">
              <div class="flex items-center justify-between text-[11px] text-slate-400">
                <span class="font-mono text-blue-400 font-medium">Session ${escapeHtml(s.session_id ? s.session_id.slice(0, 8) : '')}</span>
                <span>${escapeHtml(s.created_at || '')}</span>
              </div>
              <p class="text-xs text-slate-300 leading-relaxed">${escapeHtml(s.summary_text || '')}</p>
            </div>
          `).join('');
        }
      }

      // Shelf 3: Semantic Facts
      const facts = data.semantic_facts || [];
      if (brainShelfFactsCount) brainShelfFactsCount.textContent = `${facts.length} facts`;
      if (brainShelfFactsContainer) {
        if (facts.length === 0) {
          brainShelfFactsContainer.innerHTML = '<div class="text-slate-500 text-xs italic py-2">No semantic facts compiled yet.</div>';
        } else {
          brainShelfFactsContainer.innerHTML = facts.map((f) => `
            <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start justify-between space-x-3">
              <div class="space-y-1 flex-1">
                <div class="flex items-center space-x-2">
                  <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-800/60">${escapeHtml(f.category || 'fact')}</span>
                  <span class="text-[10px] font-mono text-slate-400">conf: ${Number(f.confidence || 1.0).toFixed(2)}</span>
                  <span class="text-[10px] font-mono text-slate-400">access: ${f.access_count || 0}</span>
                </div>
                <p class="text-xs text-slate-200">${escapeHtml(f.fact_text || '')}</p>
              </div>
              <button type="button" class="btn-forget-fact text-[11px] text-rose-400 hover:text-rose-300 px-2 py-1 rounded bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/50 transition flex-shrink-0" data-fact-id="${escapeHtml(f.id)}">
                Forget
              </button>
            </div>
          `).join('');

          brainShelfFactsContainer.querySelectorAll('.btn-forget-fact').forEach((btn) => {
            btn.addEventListener('click', async (e) => {
              const factId = e.currentTarget.dataset.factId;
              if (!factId) return;
              try {
                const delRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/memory/facts/${encodeURIComponent(factId)}`, {
                  method: 'DELETE',
                });
                if (!delRes.ok) throw new Error('Failed to delete fact');
                showToast('Fact forgotten', 'success');
                const curQuery = brainSearchInput ? brainSearchInput.value.trim() : '';
                await loadAndRenderBrainDrawer(agentId, curQuery);
              } catch (err) {
                showToast(String(err.message || err), 'error');
              }
            });
          });
        }
      }
    } catch (e) {
      console.error('[Agent Brain] Failed to fetch memory:', e);
      showToast('Failed to load agent brain memory', 'error');
    }
  }

  function openBrainDrawer() {
    const agentId = forgeIdInput ? forgeIdInput.value.trim() : (activeForgeAgent ? activeForgeAgent.id : '');
    if (!agentId) {
      showToast('Please select or save an agent first.', 'warning');
      return;
    }
    if (agentBrainDrawer) {
      agentBrainDrawer.classList.remove('hidden');
      if (brainSearchInput) brainSearchInput.value = '';
      loadAndRenderBrainDrawer(agentId);
      safeCreateIcons();
    }
  }

  function closeBrainDrawer() {
    if (agentBrainDrawer) {
      agentBrainDrawer.classList.add('hidden');
    }
  }

  if (btnOpenBrainDrawer) {
    btnOpenBrainDrawer.addEventListener('click', openBrainDrawer);
  }

  if (closeBrainDrawerBtn) {
    closeBrainDrawerBtn.addEventListener('click', closeBrainDrawer);
  }

  if (closeBrainDrawerFooterBtn) {
    closeBrainDrawerFooterBtn.addEventListener('click', closeBrainDrawer);
  }

  if (brainSearchInput) {
    let searchDebounce = null;
    brainSearchInput.addEventListener('input', () => {
      clearTimeout(searchDebounce);
      searchDebounce = setTimeout(() => {
        const agentId = forgeIdInput ? forgeIdInput.value.trim() : (activeForgeAgent ? activeForgeAgent.id : '');
        if (agentId) {
          loadAndRenderBrainDrawer(agentId, brainSearchInput.value.trim());
        }
      }, 250);
    });
  }

  if (btnPurgeBrain) {
    btnPurgeBrain.addEventListener('click', async () => {
      const agentId = forgeIdInput ? forgeIdInput.value.trim() : (activeForgeAgent ? activeForgeAgent.id : '');
      if (!agentId) {
        showToast('Please select an agent first.', 'warning');
        return;
      }
      if (!window.confirm(`Permanently purge all episodic summaries and semantic facts for agent "${agentId}"?`)) {
        return;
      }
      try {
        const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/memory`, {
          method: 'DELETE',
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        showToast(`Brain memory purged for agent "${agentId}"`, 'success');
        if (agentBrainDrawer && !agentBrainDrawer.classList.contains('hidden')) {
          loadAndRenderBrainDrawer(agentId);
        }
      } catch (err) {
        showToast(String(err.message || err), 'error');
      }
    });
  }

  if (newAgentBtn) {
    newAgentBtn.addEventListener('click', () => {
      startNewAgentPackFromStudio(callbacks);
      showToast('Talk to AutoReiv to build the pack.', 'info');
    });
  }

  if (forgeTrainNewAgentBtn) {
    forgeTrainNewAgentBtn.addEventListener('click', () => {
      const modal = $('trainAgentHandshakeModal');
      if (modal) {
        delete modal.dataset.agentId;
        modal.classList.remove('hidden');
        const trainTargetLocation = $('trainTargetLocation');
        const trainSeedObjectives = $('trainSeedObjectives');
        if (trainSeedObjectives) {
          trainSeedObjectives.value = '';
          trainSeedObjectives.placeholder = 'List 1 to 3 capabilities for this new agent (one per line)...';
        }
        if (trainTargetLocation) {
          trainTargetLocation.focus();
        }
      }
    });
  }

  if (forgeTrainAgentBtn) {
    forgeTrainAgentBtn.addEventListener('click', () => {
      const modal = $('trainAgentHandshakeModal');
      if (modal) {
        const currentAgentId = forgeIdInput ? forgeIdInput.value.trim() : '';
        const currentAgentName = forgeNameInput ? forgeNameInput.value.trim() : '';
        if (currentAgentId) {
          modal.dataset.agentId = currentAgentId;
        } else {
          delete modal.dataset.agentId;
        }
        modal.classList.remove('hidden');
        const trainTargetLocation = $('trainTargetLocation');
        const trainSeedObjectives = $('trainSeedObjectives');
        if (trainSeedObjectives && currentAgentName) {
          trainSeedObjectives.value = '';
          trainSeedObjectives.placeholder = `List 1 to 3 capabilities to train for ${currentAgentName} (one per line)...`;
        }
        if (trainTargetLocation) {
          trainTargetLocation.focus();
        }
      }
    });
  }

  if (selectAllToolsBtn) {
    selectAllToolsBtn.addEventListener('click', () => {
      $queryAll('.forge-tool-checkbox').forEach((cb) => (cb.checked = true));
    });
  }

  if (clearAllToolsBtn) {
    clearAllToolsBtn.addEventListener('click', () => {
      $queryAll('.forge-tool-checkbox').forEach((cb) => (cb.checked = false));
    });
  }

  if (saveAgentBtn) {
    saveAgentBtn.addEventListener('click', async () => {
      const name = forgeNameInput ? forgeNameInput.value.trim() : '';
      let id = forgeIdInput ? forgeIdInput.value.trim() : '';
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

      const checkedSkills = [];
      $queryAll('.forge-skill-checkbox:checked').forEach((cb) => checkedSkills.push(cb.value));
      const tickedSkills = new Set(checkedSkills);
      const checkedTools = [];
      const packTools = [];
      $queryAll('.forge-tool-checkbox:checked').forEach((cb) => {
        const skillId = cb.dataset.skillId || '';
        if (skillId && !tickedSkills.has(skillId)) return;
        checkedTools.push(cb.value);
        if (cb.dataset.home === 'pack') packTools.push(cb.value);
      });

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
        allowed_tool_names: checkedTools,
        allowed_skill: checkedSkills,
        pack_tool_names: packTools,
        show_in_chat: forgeShowInChat ? forgeShowInChat.checked : true,
        max_turns: parseInt(forgeMaxTurnsInput ? forgeMaxTurnsInput.value : 10, 10) || 10,
        history_retention_days: (function () { const n = parseInt(forgeRetentionDaysInput ? forgeRetentionDaysInput.value : 30, 10); return Number.isFinite(n) && n >= 0 ? n : 30; })(),
        storage_enabled: Boolean(forgeStorageEnabled && forgeStorageEnabled.checked),
        storage_type: forgeStorageType ? forgeStorageType.value : 'sqlite',
        memory_enabled: Boolean(forgeMemoryEnabled && forgeMemoryEnabled.checked),
        memory_retention_days: (function () {
          const n = parseInt(forgeMemoryRetentionDays ? forgeMemoryRetentionDays.value : 30, 10);
          return Number.isFinite(n) && n >= 1 && n <= 365 ? n : 30;
        })(),
        pinned_memory: forgePinnedMemory ? forgePinnedMemory.value.trim() : '',
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
          const errData = await res.json();
          throw new Error(errData.detail || 'Failed to save agent profile');
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

  const deleteAgentModal = $('deleteAgentModal');
  const deleteAgentModalMessage = $('deleteAgentModalMessage');
  const purgeHistoryCheckbox = $('purgeHistoryCheckbox');
  const confirmDeleteAgentBtn = $('confirmDeleteAgentBtn');
  const cancelDeleteAgentBtn = $('cancelDeleteAgentBtn');
  const closeDeleteAgentModalBtn = $('closeDeleteAgentModalBtn');

  function openDeleteModal() {
    if (!activeForgeAgent || activeForgeAgent.is_builtin) return;
    if (deleteAgentModalMessage) {
      deleteAgentModalMessage.textContent = `Are you sure you want to permanently delete custom agent "${activeForgeAgent.name}"? This will remove the agent configuration, delete its pack files, and unbind any assigned routines.`;
    }
    if (purgeHistoryCheckbox) purgeHistoryCheckbox.checked = false;
    if (deleteAgentModal) deleteAgentModal.classList.remove('hidden');
    safeCreateIcons();
  }

  function closeDeleteModal() {
    if (deleteAgentModal) deleteAgentModal.classList.add('hidden');
  }

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


  if (studioNewRunbookBtn) {
    studioNewRunbookBtn.addEventListener('click', async () => {
      const slug = ((studioNewRunbookSlug && studioNewRunbookSlug.value) || '').trim();
      if (!slug) {
        showToast('Runbook slug is required', 'error');
        return;
      }
      try {
        const res = await fetch('/api/skills/user-packs', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: slug, name: slug, description: 'User skill runbook.' }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        if (studioNewRunbookSlug) studioNewRunbookSlug.value = '';
        showToast(`Created ${slug}`, 'success');
        await loadPlatformSkills();
        applyRunbook(data, false);
      } catch (err) {
        showToast(String(err.message || err), 'error');
      }
    });
  }

  if (studioRunbookSaveBtn) {
    studioRunbookSaveBtn.addEventListener('click', async () => {
      if (!activeRunbookId) {
        showToast('Open a runbook first', 'error');
        return;
      }
      if (activeRunbookArchived) {
        showToast('Unarchive this runbook before saving', 'error');
        return;
      }
      try {
        studioRunbookSaveBtn.disabled = true;
        const res = await fetch(`/api/skills/user-packs/${encodeURIComponent(activeRunbookId)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: studioRunbookName ? studioRunbookName.value : '',
            description: studioRunbookBlurb ? studioRunbookBlurb.value : '',
            instructions: studioRunbookBody ? studioRunbookBody.value : '',
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        showToast('Runbook saved', 'success');
        await loadPlatformSkills();
        applyRunbook(data, false);
      } catch (err) {
        showToast(String(err.message || err), 'error');
      } finally {
        studioRunbookSaveBtn.disabled = false;
      }
    });
  }

  if (studioRunbookArchiveBtn) {
    studioRunbookArchiveBtn.addEventListener('click', async () => {
      if (!activeRunbookId) {
        showToast('Open a runbook first', 'error');
        return;
      }
      if (!window.confirm(`Archive runbook "${activeRunbookId}"? It leaves the live list and can be unarchived later.`)) {
        return;
      }
      try {
        studioRunbookArchiveBtn.disabled = true;
        const res = await fetch(`/api/skills/user-packs/${encodeURIComponent(activeRunbookId)}/archive`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ confirm: true }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        showToast(`Archived ${activeRunbookId}`, 'success');
        hideRunbookEditor();
        await loadPlatformSkills();
      } catch (err) {
        showToast(String(err.message || err), 'error');
      } finally {
        studioRunbookArchiveBtn.disabled = false;
      }
    });
  }

  if (studioRunbookUnarchiveBtn) {
    studioRunbookUnarchiveBtn.addEventListener('click', async () => {
      if (!activeRunbookId) {
        showToast('Open an archived runbook first', 'error');
        return;
      }
      if (!window.confirm(`Unarchive runbook "${activeRunbookId}" and restore it to the live list?`)) {
        return;
      }
      try {
        studioRunbookUnarchiveBtn.disabled = true;
        const res = await fetch(`/api/skills/user-packs/${encodeURIComponent(activeRunbookId)}/unarchive`, {
          method: 'POST',
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        showToast(`Unarchived ${activeRunbookId}`, 'success');
        await loadPlatformSkills();
        await openRunbookEditor(activeRunbookId, false);
      } catch (err) {
        showToast(String(err.message || err), 'error');
      } finally {
        studioRunbookUnarchiveBtn.disabled = false;
      }
    });
  }

  if (studioRunbookDeleteBtn) {
    studioRunbookDeleteBtn.addEventListener('click', async () => {
      if (!activeRunbookId) {
        showToast('Open a runbook first', 'error');
        return;
      }
      if (!window.confirm(`Permanently delete runbook "${activeRunbookId}"? This removes the directory under skills/ and cannot be undone.`)) {
        return;
      }
      try {
        studioRunbookDeleteBtn.disabled = true;
        const params = new URLSearchParams({ confirm: 'true' });
        const res = await fetch(
          `/api/skills/user-packs/${encodeURIComponent(activeRunbookId)}?${params.toString()}`,
          { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ confirm: true }) },
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        showToast(`Deleted ${activeRunbookId}`, 'success');
        hideRunbookEditor();
        await loadPlatformSkills();
      } catch (err) {
        showToast(String(err.message || err), 'error');
      } finally {
        studioRunbookDeleteBtn.disabled = false;
      }
    });
  }

  async function loadTones(selectedToneId = null) {
    try {
      const res = await fetch('/api/tones');
      if (!res.ok) return;
      cachedTones = await res.json();

      if (forgeToneSelect) {
        const currentVal =
          selectedToneId ||
          forgeToneSelect.value ||
          (activeForgeAgent ? activeForgeAgent.tone : 'default');
        forgeToneSelect.innerHTML = '';
        cachedTones.forEach((t) => {
          const opt = document.createElement('option');
          opt.value = t.id;
          opt.textContent = `${t.name}${t.description ? ` (${t.description})` : ''}`;
          forgeToneSelect.appendChild(opt);
        });
        forgeToneSelect.value = currentVal;
        if (!forgeToneSelect.value && cachedTones.length > 0) {
          forgeToneSelect.value = cachedTones[0].id;
        }
      }
    } catch (e) {
      console.warn('[AutoReiv UI] Failed to load tones:', e);
    }
  }

  function openManageTonesModal() {
    if (!manageTonesModal) return;
    manageTonesModal.classList.remove('hidden');
    hideToneForm();
    renderManageTonesList();
  }

  function closeManageTonesModal() {
    if (!manageTonesModal) return;
    manageTonesModal.classList.add('hidden');
    hideToneForm();
  }

  function showToneForm(mode = 'create', tone = null) {
    if (!manageToneForm) return;
    manageToneForm.classList.remove('hidden');
    if (toneFormMode) toneFormMode.value = mode;
    if (manageToneFormTitle) {
      manageToneFormTitle.textContent = mode === 'edit' && tone ? `Edit Tone: ${tone.name}` : 'Create Custom Tone';
    }
    if (toneFormId) {
      toneFormId.value = tone ? tone.id : '';
      toneFormId.disabled = mode === 'edit';
    }
    if (toneFormName) toneFormName.value = tone ? tone.name : '';
    if (toneFormDescription) toneFormDescription.value = tone ? tone.description : '';
    if (toneFormDirective) toneFormDirective.value = tone ? tone.directive : '';
    if (toneFormName) toneFormName.focus();
  }

  function hideToneForm() {
    if (!manageToneForm) return;
    manageToneForm.classList.add('hidden');
    if (manageToneForm.reset) manageToneForm.reset();
  }

  async function renderManageTonesList() {
    if (!manageTonesList) return;
    manageTonesList.innerHTML = '<div class="text-slate-500 py-3 text-center">Loading tones...</div>';
    await loadTones();

    if (cachedTones.length === 0) {
      manageTonesList.innerHTML = '<div class="text-slate-500 py-3 text-center">No tones found.</div>';
      return;
    }

    manageTonesList.innerHTML = '';
    cachedTones.forEach((t) => {
      const item = document.createElement('div');
      item.className = 'p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-1.5 transition';

      const badgeClass = t.is_builtin
        ? 'bg-indigo-950 text-indigo-300 border-indigo-800'
        : 'bg-emerald-950 text-emerald-300 border-emerald-800';
      const badgeText = t.is_builtin ? 'Built-in' : 'Custom';

      item.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="font-bold text-white text-xs">${escapeHtml(t.name)}</span>
            <span class="text-[10px] font-mono px-1.5 py-0.5 rounded border ${badgeClass}">${badgeText}</span>
            <span class="text-[10px] font-mono text-slate-500">id: ${escapeHtml(t.id)}</span>
          </div>
          ${
            !t.is_builtin
              ? `
            <div class="flex items-center space-x-1.5">
              <button type="button" class="edit-tone-btn text-[11px] text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 transition" data-id="${escapeHtml(t.id)}">Edit</button>
              <button type="button" class="del-tone-btn text-[11px] text-rose-400 hover:text-rose-300 px-2 py-0.5 rounded bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/50 transition" data-id="${escapeHtml(t.id)}">Delete</button>
            </div>
          `
              : ''
          }
        </div>
        ${t.description ? `<p class="text-[11px] text-slate-400">${escapeHtml(t.description)}</p>` : ''}
        <div class="p-2 rounded bg-slate-900/80 border border-slate-800 text-[11px] font-mono text-slate-300 whitespace-pre-wrap">${escapeHtml(t.directive)}</div>
      `;

      // Wire Edit button
      const editBtn = item.querySelector('.edit-tone-btn');
      if (editBtn) {
        editBtn.addEventListener('click', () => {
          showToneForm('edit', t);
        });
      }

      // Wire Delete button
      const delBtn = item.querySelector('.del-tone-btn');
      if (delBtn) {
        delBtn.addEventListener('click', async () => {
          if (!window.confirm(`Delete custom tone "${t.name}" (${t.id})?`)) return;
          try {
            const res = await fetch(`/api/tones/${encodeURIComponent(t.id)}`, { method: 'DELETE' });
            if (!res.ok) {
              const err = await res.json().catch(() => ({}));
              throw new Error(err.detail || `HTTP ${res.status}`);
            }
            showToast(`Deleted tone "${t.name}"`, 'success');
            await renderManageTonesList();
          } catch (e) {
            showToast(String(e.message || e), 'error');
          }
        });
      }

      manageTonesList.appendChild(item);
    });
  }

  if (manageTonesBtn) {
    manageTonesBtn.addEventListener('click', openManageTonesModal);
  }

  if (closeManageTonesModalBtn) {
    closeManageTonesModalBtn.addEventListener('click', closeManageTonesModal);
  }

  if (openNewToneFormBtn) {
    openNewToneFormBtn.addEventListener('click', () => showToneForm('create'));
  }

  if (closeToneFormBtn) {
    closeToneFormBtn.addEventListener('click', hideToneForm);
  }

  if (cancelToneFormBtn) {
    cancelToneFormBtn.addEventListener('click', hideToneForm);
  }

  if (manageToneForm) {
    manageToneForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const mode = toneFormMode ? toneFormMode.value : 'create';
      const id = toneFormId ? toneFormId.value.trim().toLowerCase() : '';
      const name = toneFormName ? toneFormName.value.trim() : '';
      const description = toneFormDescription ? toneFormDescription.value.trim() : '';
      const directive = toneFormDirective ? toneFormDirective.value.trim() : '';

      if (!id || !name || !directive) {
        showToast('Name, ID, and Directive are required.', 'warning');
        return;
      }

      try {
        if (mode === 'create') {
          const res = await fetch('/api/tones', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id, name, description, directive }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
          }
          showToast(`Created tone "${name}"`, 'success');
        } else {
          const res = await fetch(`/api/tones/${encodeURIComponent(id)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, directive }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
          }
          showToast(`Updated tone "${name}"`, 'success');
        }
        hideToneForm();
        await renderManageTonesList();
      } catch (err) {
        showToast(String(err.message || err), 'error');
      }
    });
  }

  setRunbookActionVisibility();

  // ==================== LAB TRAINING MONITOR DRAWER [CARD-164] ====================
  const forgeLabMonitorBtn = $('forgeLabMonitorBtn');
  const forgeLabRunsBadge = $('forgeLabRunsBadge');
  const labMonitorDrawer = $('labMonitorDrawer');
  const closeLabMonitorDrawerBtn = $('closeLabMonitorDrawerBtn');
  const closeLabMonitorDrawerFooterBtn = $('closeLabMonitorDrawerFooterBtn');
  const refreshLabMonitorBtn = $('refreshLabMonitorBtn');
  const labJobSelect = $('labJobSelect');
  const labJobStatusPill = $('labJobStatusPill');
  const labMonitorJobBadge = $('labMonitorJobBadge');
  const labHitlCard = $('labHitlCard');
  const labHitlToolsList = $('labHitlToolsList');
  const labApproveDeployBtn = $('labApproveDeployBtn');
  const labRejectDeployBtn = $('labRejectDeployBtn');
  const labPacketsFeed = $('labPacketsFeed');
  const labPacketsCount = $('labPacketsCount');

  let labPollTimer = null;

  async function updateLabRunsBadge() {
    try {
      const res = await fetch('/api/factory/jobs');
      if (!res.ok) return;
      const data = await res.json();
      const jobs = data.jobs || [];
      const activeJobs = jobs.filter((j) => ['queued', 'running', 'waiting_approval'].includes(j.status));
      if (forgeLabRunsBadge) {
        if (activeJobs.length > 0) {
          forgeLabRunsBadge.textContent = String(activeJobs.length);
          forgeLabRunsBadge.classList.remove('hidden');
        } else {
          forgeLabRunsBadge.classList.add('hidden');
        }
      }
    } catch {
      // quiet fail
    }
  }

  function setStepVisual(el, state) {
    if (!el) return;
    el.classList.remove('border-emerald-500', 'bg-emerald-950/40', 'border-brand-500', 'bg-brand-950/40', 'border-slate-800', 'bg-slate-950/50');
    const num = el.querySelector('.step-num');
    const name = el.querySelector('.step-name');
    const icon = el.querySelector('.step-icon');

    if (state === 'done') {
      el.classList.add('border-emerald-500', 'bg-emerald-950/40');
      if (num) num.className = 'step-num text-[10px] font-mono text-emerald-400';
      if (name) name.className = 'step-name font-semibold text-emerald-300';
      if (icon) icon.className = 'step-icon text-emerald-400';
    } else if (state === 'active') {
      el.classList.add('border-brand-500', 'bg-brand-950/40');
      if (num) num.className = 'step-num text-[10px] font-mono text-brand-400';
      if (name) name.className = 'step-name font-semibold text-brand-300';
      if (icon) icon.className = 'step-icon text-brand-400';
    } else {
      el.classList.add('border-slate-800', 'bg-slate-950/50');
      if (num) num.className = 'step-num text-[10px] font-mono text-slate-500';
      if (name) name.className = 'step-name font-semibold text-slate-400';
      if (icon) icon.className = 'step-icon text-slate-500';
    }
  }

  async function loadLabJobDetails(jobId) {
    if (!jobId) return;
    try {
      const res = await fetch(`/api/factory/jobs/${encodeURIComponent(jobId)}`);
      if (!res.ok) return;
      const data = await res.json();
      const job = data.job;
      const packets = data.packets || [];
      const evals = data.eval_runs || [];

      if (labMonitorJobBadge) {
        labMonitorJobBadge.textContent = `${job.target_agent_id} (${job.id})`;
      }

      // Status Pill
      if (labJobStatusPill) {
        const dot = labJobStatusPill.querySelector('span:first-child');
        const txt = labJobStatusPill.querySelector('.status-text');
        if (txt) txt.textContent = job.status.toUpperCase();
        labJobStatusPill.className = 'px-2.5 py-1 rounded-full text-xs font-semibold border flex items-center space-x-1.5';
        if (dot) dot.className = 'w-2 h-2 rounded-full';

        if (job.status === 'done') {
          labJobStatusPill.classList.add('border-emerald-500/50', 'bg-emerald-950/40', 'text-emerald-300');
          if (dot) dot.classList.add('bg-emerald-400');
        } else if (job.status === 'waiting_approval') {
          labJobStatusPill.classList.add('border-amber-500/50', 'bg-amber-950/40', 'text-amber-300');
          if (dot) dot.classList.add('bg-amber-400');
        } else if (job.status === 'running') {
          labJobStatusPill.classList.add('border-brand-500/50', 'bg-brand-950/40', 'text-brand-300');
          if (dot) dot.classList.add('bg-brand-400');
        } else if (job.status === 'failed') {
          labJobStatusPill.classList.add('border-rose-500/50', 'bg-rose-950/40', 'text-rose-300');
          if (dot) dot.classList.add('bg-rose-400');
        } else {
          labJobStatusPill.classList.add('border-slate-700', 'bg-slate-800', 'text-slate-300');
          if (dot) dot.classList.add('bg-slate-400');
        }
      }

      // Stepper logic
      const node = job.current_node_id;
      const status = job.status;

      // 1. Discovery
      if (node === 'discovery_probe') {
        setStepVisual($('labStep1'), 'active');
      } else {
        setStepVisual($('labStep1'), 'done');
      }

      // 2. Blueprint
      if (node === 'architecture_blueprint') {
        setStepVisual($('labStep2'), 'active');
      } else if (['discovery_probe'].includes(node)) {
        setStepVisual($('labStep2'), 'idle');
      } else {
        setStepVisual($('labStep2'), 'done');
      }

      // 3. Toolmaker
      if (['conduct_node', 'coder_node'].includes(node)) {
        setStepVisual($('labStep3'), 'active');
      } else if (['discovery_probe', 'architecture_blueprint'].includes(node)) {
        setStepVisual($('labStep3'), 'idle');
      } else {
        setStepVisual($('labStep3'), 'done');
      }

      // 4. Sandbox Battery
      if (node === 'sandbox_battery_node') {
        setStepVisual($('labStep4'), 'active');
      } else if (['discovery_probe', 'architecture_blueprint', 'conduct_node', 'coder_node'].includes(node)) {
        setStepVisual($('labStep4'), 'idle');
      } else {
        setStepVisual($('labStep4'), 'done');
      }

      // 5. Deploy Gate
      if (['critic_signoff_node', 'hitl_deploy_gate_node'].includes(node) || status === 'waiting_approval') {
        setStepVisual($('labStep5'), status === 'done' ? 'done' : 'active');
      } else if (status === 'done') {
        setStepVisual($('labStep5'), 'done');
      } else {
        setStepVisual($('labStep5'), 'idle');
      }

      // HITL Card
      if (labHitlCard) {
        if (status === 'waiting_approval') {
          labHitlCard.classList.remove('hidden');
          if (labHitlToolsList) {
            labHitlToolsList.innerHTML = '';
            const toolNames = new Set();
            packets.forEach((p) => {
              if (p.payload && p.payload.tool_name) toolNames.add(p.payload.tool_name);
              if (p.payload && p.payload.authored_files) {
                p.payload.authored_files.forEach((f) => toolNames.add(f));
              }
            });
            evals.forEach((e) => toolNames.add(e.tool_name));
            if (toolNames.size === 0) toolNames.add(`manage_${job.target_agent_id.replace(/-/g, '_')}`);

            toolNames.forEach((t) => {
              const chip = document.createElement('span');
              chip.className = 'px-2 py-0.5 rounded-lg bg-emerald-900/40 border border-emerald-700/50 text-emerald-300 font-mono text-[11px]';
              chip.textContent = t;
              labHitlToolsList.appendChild(chip);
            });
          }
        } else {
          labHitlCard.classList.add('hidden');
        }
      }

      // Live Activity Feed
      if (labPacketsCount) {
        labPacketsCount.textContent = `${packets.length} packet${packets.length === 1 ? '' : 's'}`;
      }
      if (labPacketsFeed) {
        if (packets.length === 0) {
          labPacketsFeed.innerHTML = '<div class="text-slate-500 italic py-2">No activity recorded for this job yet.</div>';
        } else {
          labPacketsFeed.innerHTML = '';
          packets.forEach((p) => {
            const timeStr = p.created_at ? new Date(p.created_at).toLocaleTimeString() : '';
            const role = p.sender_role || 'system';
            let msg = '';
            if (p.payload) {
              msg = p.payload.message || p.payload.goal || JSON.stringify(p.payload);
            }
            const row = document.createElement('div');
            row.className = 'flex items-start space-x-2 py-0.5';

            let roleColor = 'text-slate-400';
            if (role === 'inspector') roleColor = 'text-cyan-400';
            else if (role === 'conductor') roleColor = 'text-brand-400';
            else if (role === 'coder') roleColor = 'text-amber-400';
            else if (role === 'sandbox_runner') roleColor = 'text-purple-400';
            else if (role === 'critic') roleColor = 'text-emerald-400';

            row.innerHTML = `
              <span class="text-slate-500 text-[10px] flex-shrink-0">[${escapeHtml(timeStr)}]</span>
              <span class="${roleColor} font-semibold flex-shrink-0">[${escapeHtml(role.toUpperCase())}]</span>
              <span class="text-slate-200">${escapeHtml(msg)}</span>
            `;
            labPacketsFeed.appendChild(row);
          });
          labPacketsFeed.scrollTop = labPacketsFeed.scrollHeight;
        }
      }

      safeCreateIcons();
    } catch (e) {
      console.error('Failed to load lab job details:', e);
    }
  }

  async function openLabMonitorDrawer(preferredJobId = null) {
    if (!labMonitorDrawer) return;
    labMonitorDrawer.classList.remove('hidden');

    try {
      const res = await fetch('/api/factory/jobs');
      if (!res.ok) throw new Error('Failed to list factory jobs');
      const data = await res.json();
      const jobs = data.jobs || [];

      if (labJobSelect) {
        labJobSelect.innerHTML = '';
        if (jobs.length === 0) {
          const opt = document.createElement('option');
          opt.value = '';
          opt.textContent = 'No training runs found';
          labJobSelect.appendChild(opt);
        } else {
          jobs.forEach((j) => {
            const opt = document.createElement('option');
            opt.value = j.id;
            opt.textContent = `[${j.status.toUpperCase()}] ${j.target_agent_id} (${j.id.slice(0, 10)})`;
            labJobSelect.appendChild(opt);
          });

          const activeJob = jobs.find((j) => j.status === 'running' || j.status === 'waiting_approval');
          const targetJobId = preferredJobId || (activeJob ? activeJob.id : jobs[0].id);
          labJobSelect.value = targetJobId;
          await loadLabJobDetails(targetJobId);
        }
      }

      if (labPollTimer) clearInterval(labPollTimer);
      labPollTimer = setInterval(() => {
        if (labJobSelect && labJobSelect.value) {
          loadLabJobDetails(labJobSelect.value);
          updateLabRunsBadge();
        }
      }, 2500);

      safeCreateIcons();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  function closeLabMonitorDrawer() {
    if (labMonitorDrawer) labMonitorDrawer.classList.add('hidden');
    if (labPollTimer) {
      clearInterval(labPollTimer);
      labPollTimer = null;
    }
  }

  if (forgeLabMonitorBtn) {
    forgeLabMonitorBtn.addEventListener('click', () => {
      openLabMonitorDrawer();
    });
  }

  if (closeLabMonitorDrawerBtn) {
    closeLabMonitorDrawerBtn.addEventListener('click', closeLabMonitorDrawer);
  }

  if (closeLabMonitorDrawerFooterBtn) {
    closeLabMonitorDrawerFooterBtn.addEventListener('click', closeLabMonitorDrawer);
  }

  if (refreshLabMonitorBtn) {
    refreshLabMonitorBtn.addEventListener('click', () => {
      if (labJobSelect && labJobSelect.value) {
        loadLabJobDetails(labJobSelect.value);
        updateLabRunsBadge();
      }
    });
  }

  if (labJobSelect) {
    labJobSelect.addEventListener('change', () => {
      if (labJobSelect.value) {
        loadLabJobDetails(labJobSelect.value);
      }
    });
  }

  if (labApproveDeployBtn) {
    labApproveDeployBtn.addEventListener('click', async () => {
      const jobId = labJobSelect ? labJobSelect.value : null;
      if (!jobId) return;
      labApproveDeployBtn.disabled = true;
      labApproveDeployBtn.textContent = 'Deploying...';
      try {
        const res = await fetch(`/api/factory/jobs/${encodeURIComponent(jobId)}/promote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'approved' }),
        });
        if (!res.ok) throw new Error('Promotion deployment failed');
        const data = await res.json();
        showToast(`Successfully deployed ${data.agent_id} pack to live fleet!`, 'success');
        if (typeof callbacks.onReloadAgents === 'function') {
          callbacks.onReloadAgents();
        }
        await loadLabJobDetails(jobId);
        await updateLabRunsBadge();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        labApproveDeployBtn.disabled = false;
        labApproveDeployBtn.textContent = 'Approve & Deploy to Fleet';
      }
    });
  }

  if (labRejectDeployBtn) {
    labRejectDeployBtn.addEventListener('click', async () => {
      const jobId = labJobSelect ? labJobSelect.value : null;
      if (!jobId) return;
      try {
        const res = await fetch(`/api/factory/jobs/${encodeURIComponent(jobId)}/promote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'rejected' }),
        });
        if (!res.ok) throw new Error('Rejection failed');
        showToast('Training run rejected and aborted.', 'info');
        await loadLabJobDetails(jobId);
        await updateLabRunsBadge();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // Initial badge check
  updateLabRunsBadge();

  return {
    loadAgentForge,
    renderAgentToForge,
    openLabMonitorDrawer,
    updateLabRunsBadge,
  };
}
