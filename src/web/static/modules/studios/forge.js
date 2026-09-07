/**
 * Agent Studio module [REQ-FE-001, REQ-FORGE-006]. Filename forge.js kept (CARD-118).
 */

import { $, $query, $queryAll, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { showToast } from '../ui/toast.js';
import { PRESETS_DEFAULTS } from './settings.js';


/** Build expected on-disk pack paths after promote (CARD-171). */
export function buildExpectedPackPaths(agentId, relativeFiles = []) {
  const root = `%LOCALAPPDATA%\\AutoReiv\\packs\\${agentId || 'agent'}`;
  return (relativeFiles || []).map((rel) => {
    const clean = String(rel || '').replace(/\//g, '\\').replace(/^\\+/, '');
    return `${root}\\${clean}`;
  });
}

/** Collect unique artifacts from factory packets (files_map + wiki_paths). */
export function collectPacketArtifacts(packets = []) {
  const out = [];
  const seen = new Set();
  for (const p of packets || []) {
    const payload = (p && p.payload) || {};
    const filesMap = payload.files_map || {};
    for (const [rel, content] of Object.entries(filesMap)) {
      const key = `file:${rel}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({
        kind: 'file',
        path: rel,
        content: content == null ? '' : String(content),
        source: p.sender_role || 'packet',
      });
    }
    const wikiPaths = payload.wiki_paths || [];
    for (const wp of wikiPaths) {
      const key = `wiki:${wp}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({
        kind: 'wiki',
        path: wp,
        content: '',
        source: p.sender_role || 'packet',
      });
    }
  }
  return out;
}


export function formatLabPacketFeedLines(packet) {
  const payload = (packet && packet.payload) || {};
  const msg = payload.message || payload.goal || '';
  const notes = (payload.critic_notes || '').trim();
  const passed = payload.passed;
  const lines = [];
  if (msg) lines.push(String(msg));
  const looksFailed =
    passed === false ||
    /FAILED/i.test(String(msg)) ||
    payload.terminal_fail === true;
  if (looksFailed) {
    const rinseKind = payload.rinse_kind || '';
    const fclass = payload.failure_class || '';
    if (rinseKind || fclass) {
      const bits = [];
      if (rinseKind) bits.push(`${rinseKind} rinse`);
      if (fclass) bits.push(fclass);
      lines.push(`Rinse: ${bits.join(' / ')}`);
    }
    if (notes) {
      const short = notes.length > 160 ? `${notes.slice(0, 157)}...` : notes;
      lines.push(`Reason: ${short}`);
    }
  }
  if (!lines.length && payload && typeof payload === 'object') {
    lines.push(JSON.stringify(payload));
  }
  return lines;
}

export function formatLabActivityFeedText(packets) {
  if (!packets || !Array.isArray(packets) || packets.length === 0) return '';
  const lines = [];
  packets.forEach((p) => {
    const timeStr = p.created_at ? new Date(p.created_at).toLocaleTimeString() : '';
    const role = (p.sender_role || 'system').toUpperCase();
    const feedLines = formatLabPacketFeedLines(p);
    feedLines.forEach((line) => {
      lines.push(`[${timeStr}] [${role}] ${line}`);
    });
  });
  return lines.join('\n');
}

export function populateTrainModalForRetry(jobData, elements = {}) {
  if (!jobData) return false;
  const job = jobData.job || jobData;
  const inputs = jobData.inputs || {};

  const agentId = inputs.target_agent_id || job.target_agent_id || '';
  const seedIntent = inputs.seed_intent || job.seed_intent || '';
  const objectives = inputs.objectives || job.objectives || [];
  const deliverableType = inputs.deliverable_type || 'auto';
  const constraints = inputs.constraints || '';
  const prerequisites = inputs.prerequisites || '';
  const referenceDocs = inputs.reference_docs || '';
  const targetLocation = inputs.target_directory || '';

  const modal = elements.modal || $('trainAgentHandshakeModal');
  if (modal) {
    modal.dataset.agentId = agentId;
  }

  const nameInput = elements.nameInput || $('trainAgentNameInput');
  const nameGroup = elements.nameGroup || $('trainAgentNameGroup');
  if (nameGroup) nameGroup.classList.remove('hidden');
  if (nameInput) nameInput.value = agentId;

  const targetLoc = elements.targetLocation || $('trainTargetLocation');
  if (targetLoc) targetLoc.value = targetLocation;

  const seedObj = elements.seedObjectives || $('trainSeedObjectives');
  if (seedObj) {
    if (objectives && objectives.length > 0) {
      seedObj.value = objectives.join('\n');
    } else {
      seedObj.value = seedIntent;
    }
  }

  const intentInput = elements.seedIntentInput || $('trainSeedIntentInput');
  if (intentInput) {
    intentInput.value = seedIntent || '';
  }

  const promptInput = elements.promptInput || $('promptInput');
  if (promptInput && seedIntent) {
    promptInput.value = seedIntent;
  }

  const deliverableSelect = elements.deliverableType || $('trainDeliverableType');
  if (deliverableSelect) deliverableSelect.value = deliverableType;

  const constraintsInput = elements.constraints || $('trainConstraintsInput');
  if (constraintsInput) constraintsInput.value = constraints;

  const prereqsInput = elements.prerequisites || $('trainPrerequisitesInput');
  if (prereqsInput) prereqsInput.value = prerequisites;

  const refDocsInput = elements.referenceDocs || $('trainReferenceDocsInput');
  if (refDocsInput) refDocsInput.value = referenceDocs;

  const advContent = elements.advancedContent || $('trainAdvancedReqsContent');
  const advChevron = elements.advancedChevron || $('trainAdvancedChevron');
  const hasAdvanced = Boolean(constraints || prerequisites || referenceDocs);
  if (advContent) {
    advContent.classList.toggle('hidden', !hasAdvanced);
    if (advChevron) advChevron.classList.toggle('rotate-180', hasAdvanced);
  }

  return true;
}

export function startNewAgentPackFromStudio(callbacks = {}) {
  if (typeof callbacks.onStartNewAgentPack === 'function') {
    callbacks.onStartNewAgentPack();
    return true;
  }
  return false;
}

export function renderToolBadgeHtml(tool, activeAgent = null) {
  const tObj = typeof tool === 'string' ? { name: tool } : (tool || {});
  const name = tObj.name || '';
  const isMcp = Boolean(
    tObj.is_mcp ||
    tObj.deliverable_type === 'mcp' ||
    tObj.type === 'mcp' ||
    name.startsWith('mcp_') ||
    (activeAgent && activeAgent.mcp_server && activeAgent.mcp_server.enabled)
  );
  return isMcp
    ? '<span class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-indigo-950/80 text-indigo-300 border border-indigo-800/80 uppercase tracking-wide">MCP Server</span>'
    : '<span class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-slate-800/80 text-slate-400 border border-slate-700/80 uppercase tracking-wide">Native Tool</span>';
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
  const forgeAllowWikiAccessCheckbox = $('forgeAllowWikiAccessCheckbox');
  const forgeAutoTrainCheckbox = $('forgeAutoTrainCheckbox');
  const forgeMaxTrainRetriesInput = $('forgeMaxTrainRetriesInput');
  const _agentTrainingBacklogCard = $('agentTrainingBacklogCard');
  const agentBacklogCountBadge = $('agentBacklogCountBadge');
  const agentBacklogList = $('agentBacklogList');
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
  const _forgeMcpServersCard = $('forgeMcpServersCard');
  const forgeMcpServerCountBadge = $('forgeMcpServerCountBadge');
  const forgeAddMcpServerBtn = $('forgeAddMcpServerBtn');
  const forgeMcpServerForm = $('forgeMcpServerForm');
  const _forgeMcpServerFormTitle = $('forgeMcpServerFormTitle');
  const forgeMcpServerFormCloseBtn = $('forgeMcpServerFormCloseBtn');
  const forgeMcpNameInput = $('forgeMcpNameInput');
  const forgeMcpTransportSelect = $('forgeMcpTransportSelect');
  const forgeMcpUrlGroup = $('forgeMcpUrlGroup');
  const forgeMcpUrlInput = $('forgeMcpUrlInput');
  const forgeMcpCommandGroup = $('forgeMcpCommandGroup');
  const forgeMcpCommandInput = $('forgeMcpCommandInput');
  const forgeMcpHeadersInput = $('forgeMcpHeadersInput');
  const forgeMcpEnabledCheckbox = $('forgeMcpEnabledCheckbox');
  const forgeMcpTestBtn = $('forgeMcpTestBtn');
  const forgeMcpSaveBtn = $('forgeMcpSaveBtn');
  const forgeMcpTestResult = $('forgeMcpTestResult');
  const forgeMcpServerList = $('forgeMcpServerList');
  let currentAgentMcpServers = [];
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
  const studioRunbookCloseBtn = $('studioRunbookCloseBtn');
  const studioRunbookCancelBtn = $('studioRunbookCancelBtn');
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
    const tObj = typeof tool === 'string' ? { name: tool, description: '' } : (tool || {});
    const name = tObj.name || '';
    const desc = tObj.description || '';
    const skillAttr = skillId ? ` data-skill-id="${escapeHtml(skillId)}"` : '';
    const homeAttr = home ? ` data-home="${escapeHtml(home)}"` : '';
    const badgeHtml = renderToolBadgeHtml(tObj, activeForgeAgent);
    return `
      <label class="flex items-start space-x-2 p-2 rounded-lg bg-slate-950/50 border border-slate-800 hover:border-slate-700 transition cursor-pointer text-xs">
        <input type="checkbox" value="${escapeHtml(name)}" class="forge-tool-checkbox mt-0.5 rounded border-slate-700 text-brand-500 focus:ring-brand-500"${skillAttr}${homeAttr}>
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between gap-1 mb-0.5">
            <span class="font-mono text-slate-200 block text-[11px] font-semibold truncate">${escapeHtml(name)}</span>
            ${badgeHtml}
          </div>
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

  async function loadAgentForge(targetAgentId) {
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
        const selectedId = targetAgentId || forgeAgentSelect.value || (studioAgents[0] ? studioAgents[0].id : null);
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
    if (forgeAllowWikiAccessCheckbox) forgeAllowWikiAccessCheckbox.checked = agent.allow_wiki_access !== false;
    if (forgeAutoTrainCheckbox) forgeAutoTrainCheckbox.checked = Boolean(agent.allow_autonomous_training);
    if (forgeMaxTrainRetriesInput) forgeMaxTrainRetriesInput.value = agent.max_training_retries !== undefined ? agent.max_training_retries : 2;
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
    loadAgentCapabilityGaps(agent.id);
    loadAgentMcpServers(agent.id);
  }

  function updateAvatarPreview(iconName) {
    if (forgeAvatarPreview) {
      forgeAvatarPreview.innerHTML = `<i data-lucide="${iconName}" class="w-7 h-7"></i>`;
      safeCreateIcons();
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

  async function loadAgentCapabilityGaps(agentId) {
    if (!agentBacklogList) return;
    if (!agentId) {
      agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
      if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = '0';
      return;
    }
    try {
      const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/gaps?status=pending`);
      const data = res.ok ? await res.json() : {};
      const items = Array.isArray(data) ? data : (data.gaps || []);
      if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = String(items.length);
      if (!items.length) {
        agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
        return;
      }
      agentBacklogList.innerHTML = items.map((gap) => `
        <div class="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800 space-y-1.5" data-gap-id="${escapeHtml(gap.id)}">
          <div class="flex items-center justify-between">
            <span class="text-xs font-semibold text-amber-300 font-mono">${escapeHtml(gap.identified_capability || gap.missing_capability || 'Missing Capability')}</span>
            <div class="flex items-center space-x-1.5">
              <button type="button" class="btn-train-gap px-2 py-0.5 rounded bg-amber-600 hover:bg-amber-500 text-white text-[10px] font-semibold transition" data-gap-id="${escapeHtml(gap.id)}">⚡ Train in Lab</button>
              <button type="button" class="btn-dismiss-gap px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 text-[10px] font-medium transition" data-gap-id="${escapeHtml(gap.id)}">Dismiss</button>
            </div>
          </div>
          ${gap.suggested_tool_name ? `<div class="text-[10px] text-slate-400 font-mono">Suggested tool: <span class="text-emerald-400">${escapeHtml(gap.suggested_tool_name)}</span></div>` : ''}
          <p class="text-[11px] text-slate-400 whitespace-pre-wrap">${escapeHtml(gap.turn_text || gap.user_prompt || '')}</p>
        </div>
      `).join('');

      agentBacklogList.querySelectorAll('.btn-train-gap').forEach((btn) => {
        btn.addEventListener('click', async (e) => {
          const gapId = e.currentTarget.dataset.gapId;
          try {
            const trainRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/gaps/${encodeURIComponent(gapId)}/train`, { method: 'POST' });
            if (!trainRes.ok) throw new Error('Failed to launch training');
            showToast('Training launched from capability gap!', 'success');
            await loadAgentCapabilityGaps(agentId);
          } catch (err) {
            showToast(String(err.message || err), 'error');
          }
        });
      });

      agentBacklogList.querySelectorAll('.btn-dismiss-gap').forEach((btn) => {
        btn.addEventListener('click', async (e) => {
          const gapId = e.currentTarget.dataset.gapId;
          try {
            const delRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/gaps/${encodeURIComponent(gapId)}`, { method: 'DELETE' });
            if (!delRes.ok) throw new Error('Failed to dismiss gap');
            showToast('Capability gap dismissed', 'info');
            await loadAgentCapabilityGaps(agentId);
          } catch (err) {
            showToast(String(err.message || err), 'error');
          }
        });
      });
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to load capability gaps:', err);
      agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
      if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = '0';
    }
  }

  async function loadAgentMcpServers(agentId) {
    if (!forgeMcpServerList) return;
    if (!agentId) {
      forgeMcpServerList.innerHTML = '<p id="forgeMcpServerEmpty" class="text-[11px] text-slate-500">No remote MCP servers configured for this agent.</p>';
      if (forgeMcpServerCountBadge) forgeMcpServerCountBadge.textContent = '0';
      return;
    }
    try {
      const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp`);
      const servers = res.ok ? await res.json() : [];
      currentAgentMcpServers = Array.isArray(servers) ? servers : [];
      if (activeForgeAgent) {
        activeForgeAgent.mcp_servers = currentAgentMcpServers;
      }
      renderAgentMcpServers(agentId, currentAgentMcpServers);
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to load agent MCP servers:', err);
      forgeMcpServerList.innerHTML = '<p id="forgeMcpServerEmpty" class="text-[11px] text-slate-500">Failed to load MCP servers.</p>';
    }
  }

  function renderAgentMcpServers(agentId, servers) {
    if (!forgeMcpServerList) return;
    if (forgeMcpServerCountBadge) {
      forgeMcpServerCountBadge.textContent = String(servers.length);
    }
    if (!servers.length) {
      forgeMcpServerList.innerHTML = '<p id="forgeMcpServerEmpty" class="text-[11px] text-slate-500">No remote MCP servers configured for this agent.</p>';
      return;
    }

    forgeMcpServerList.innerHTML = servers.map((s) => {
      const isMounted = Boolean(s.is_mounted);
      const isEnabled = s.enabled !== false;
      const toolCount = s.tool_count || (s.tools ? s.tools.length : 0);
      const target = s.url || s.command || 'N/A';
      return `
        <div class="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-2" data-server-name="${escapeHtml(s.name)}">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <span class="text-xs font-bold text-slate-200 font-mono">${escapeHtml(s.name)}</span>
              <span class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-cyan-950/70 text-cyan-400 border border-cyan-800/60">${escapeHtml(s.transport || 'sse')}</span>
              ${isEnabled 
                ? (isMounted 
                    ? `<span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-950/70 text-emerald-400 border border-emerald-800/60 flex items-center space-x-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span>Mounted (${toolCount} tools)</span>
                       </span>`
                    : '<span class="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700">Enabled</span>')
                : '<span class="px-1.5 py-0.5 rounded text-[10px] bg-slate-900 text-slate-500 border border-slate-800">Disabled</span>'
              }
            </div>
            <div class="flex items-center space-x-1.5">
              ${!isMounted && isEnabled ? `
                <button type="button" class="btn-mount-server px-2 py-1 bg-emerald-950/60 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 rounded text-[11px] font-medium flex items-center space-x-1 transition" data-server-name="${escapeHtml(s.name)}" title="Connect/Mount this MCP server">
                  <i data-lucide="play" class="w-3 h-3"></i>
                  <span>Connect</span>
                </button>
              ` : ''}
              <button type="button" class="btn-probe-server px-2 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-800/60 rounded text-[11px] font-medium flex items-center space-x-1 transition" data-server-name="${escapeHtml(s.name)}" title="Test connection probe">
                <i data-lucide="activity" class="w-3 h-3"></i>
                <span>Probe</span>
              </button>
              <button type="button" class="btn-delete-server px-2 py-1 bg-slate-800 hover:bg-rose-900/60 text-slate-400 hover:text-rose-300 border border-slate-700 rounded text-[11px] font-medium flex items-center space-x-1 transition" data-server-name="${escapeHtml(s.name)}" title="Remove this MCP server">
                <i data-lucide="trash-2" class="w-3 h-3"></i>
                <span>Delete</span>
              </button>
            </div>
          </div>
          <div class="text-[11px] font-mono text-slate-400 truncate">
            <span class="text-slate-500">Endpoint:</span> ${escapeHtml(target)}
          </div>
          <div class="server-probe-result hidden p-2 rounded text-[11px] font-mono border"></div>
        </div>
      `;
    }).join('');

    safeCreateIcons();

    forgeMcpServerList.querySelectorAll('.btn-mount-server').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const sName = e.currentTarget.dataset.serverName;
        const card = btn.closest('[data-server-name]');
        const resultEl = card ? card.querySelector('.server-probe-result') : null;
        if (resultEl) {
          resultEl.classList.remove('hidden');
          resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-slate-900 border-slate-700 text-slate-300';
          resultEl.textContent = 'Connecting to MCP server...';
        }
        try {
          const mountRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp/${encodeURIComponent(sName)}/mount`, {
            method: 'POST',
          });
          const data = await mountRes.json();
          if (data.status === 'mounted') {
            await loadAgentMcpServers(agentId);
          } else {
            if (resultEl) {
              resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
              resultEl.textContent = `✗ Mount failed: ${data.error || 'Unknown error'}`;
            }
          }
        } catch (err) {
          if (resultEl) {
            resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
            resultEl.textContent = `✗ Mount error: ${err.message || err}`;
          }
        }
      });
    });

    forgeMcpServerList.querySelectorAll('.btn-probe-server').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const sName = e.currentTarget.dataset.serverName;
        const sObj = servers.find((s) => s.name === sName);
        if (!sObj) return;
        const card = btn.closest('[data-server-name]');
        const resultEl = card ? card.querySelector('.server-probe-result') : null;
        if (resultEl) {
          resultEl.classList.remove('hidden');
          resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-slate-900 border-slate-700 text-slate-300';
          resultEl.textContent = 'Probing server endpoint...';
        }
        try {
          const probeRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sObj),
          });
          const data = await probeRes.json();
          if (resultEl) {
            if (data.status === 'ok') {
              resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-emerald-950/60 border-emerald-800 text-emerald-300';
              resultEl.textContent = `✓ OK (${data.latency_ms}ms) - ${data.tools_count} tool(s): ${(data.tools || []).join(', ')}`;
            } else {
              resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
              resultEl.textContent = `✗ Probe failed (${data.latency_ms}ms): ${data.error || 'Unknown error'}`;
            }
          }
        } catch (err) {
          if (resultEl) {
            resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
            resultEl.textContent = `✗ Probe error: ${err.message || err}`;
          }
        }
      });
    });

    forgeMcpServerList.querySelectorAll('.btn-delete-server').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const sName = e.currentTarget.dataset.serverName;
        if (!confirm(`Delete MCP server '${sName}' from this agent?`)) return;
        try {
          const delRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp/${encodeURIComponent(sName)}`, {
            method: 'DELETE',
          });
          if (!delRes.ok) throw new Error(`HTTP ${delRes.status}`);
          showToast(`MCP server '${sName}' removed`, 'info');
          await loadAgentMcpServers(agentId);
        } catch (err) {
          showToast(`Failed to delete server: ${err.message || err}`, 'error');
        }
      });
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
        const modalTitle = $('trainAgentModalTitle');
        if (modalTitle) {
          modalTitle.innerHTML = `
            <i data-lucide="cpu" class="w-4 h-4 text-emerald-400"></i>
            <span>Train New Specialist Agent (Lab Loop)</span>
          `;
        }
        const nameGroup = $('trainAgentNameGroup');
        const nameInput = $('trainAgentNameInput');
        if (nameGroup) nameGroup.classList.remove('hidden');
        if (nameInput) {
          nameInput.value = '';
          nameInput.focus();
        }
        const trainTargetLocation = $('trainTargetLocation');
        if (trainTargetLocation) {
          trainTargetLocation.value = '';
        }
        const trainSeedObjectives = $('trainSeedObjectives');
        if (trainSeedObjectives) {
          trainSeedObjectives.value = '';
          trainSeedObjectives.placeholder = 'List 1 to 3 capabilities for this new agent (one per line)...';
        }
        const trainSeedIntent = $('trainSeedIntentInput');
        if (trainSeedIntent) {
          trainSeedIntent.value = '';
          trainSeedIntent.placeholder = 'e.g. Master system administration tasks';
        }
        safeCreateIcons();
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
        const modalTitle = $('trainAgentModalTitle');
        if (modalTitle) {
          modalTitle.innerHTML = `
            <i data-lucide="flask-conical" class="w-4 h-4 text-emerald-400"></i>
            <span>Train ${escapeHtml(currentAgentName || currentAgentId || 'Agent')} (Lab Loop)</span>
          `;
        }
        const nameGroup = $('trainAgentNameGroup');
        if (nameGroup) nameGroup.classList.add('hidden');
        const nameInput = $('trainAgentNameInput');
        if (nameInput) nameInput.value = '';
        const trainTargetLocation = $('trainTargetLocation');
        if (trainTargetLocation) {
          trainTargetLocation.value = '';
        }
        const trainSeedIntent = $('trainSeedIntentInput');
        if (trainSeedIntent) {
          const desc = forgeDescInput ? forgeDescInput.value.trim() : '';
          trainSeedIntent.value = '';
          trainSeedIntent.placeholder = desc || `e.g. Expand ${currentAgentName || currentAgentId} capabilities`;
        }
        const trainSeedObjectives = $('trainSeedObjectives');
        if (trainSeedObjectives) {
          trainSeedObjectives.value = '';
          trainSeedObjectives.placeholder = `List 1 to 3 capabilities to train for ${currentAgentName || currentAgentId} (one per line)...`;
          trainSeedObjectives.focus();
        }
        safeCreateIcons();
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
        allow_wiki_access: Boolean(forgeAllowWikiAccessCheckbox && forgeAllowWikiAccessCheckbox.checked),
        allow_autonomous_training: Boolean(forgeAutoTrainCheckbox && forgeAutoTrainCheckbox.checked),
        max_training_retries: (function () {
          const n = parseInt(forgeMaxTrainRetriesInput ? forgeMaxTrainRetriesInput.value : 2, 10);
          return Number.isFinite(n) && n >= 1 && n <= 5 ? n : 2;
        })(),
        mcp_servers: currentAgentMcpServers.length > 0
          ? currentAgentMcpServers
          : (activeForgeAgent && activeForgeAgent.mcp_servers ? activeForgeAgent.mcp_servers : []),
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

  // --- Remote MCP Server Management Event Listeners [CARD-183] ---
  if (forgeAddMcpServerBtn && forgeMcpServerForm) {
    forgeAddMcpServerBtn.addEventListener('click', () => {
      forgeMcpServerForm.classList.remove('hidden');
      if (forgeMcpNameInput) forgeMcpNameInput.value = '';
      if (forgeMcpUrlInput) forgeMcpUrlInput.value = '';
      if (forgeMcpCommandInput) forgeMcpCommandInput.value = '';
      if (forgeMcpHeadersInput) forgeMcpHeadersInput.value = '';
      if (forgeMcpEnabledCheckbox) forgeMcpEnabledCheckbox.checked = true;
      if (forgeMcpTestResult) forgeMcpTestResult.classList.add('hidden');
    });
  }

  if (forgeMcpServerFormCloseBtn && forgeMcpServerForm) {
    forgeMcpServerFormCloseBtn.addEventListener('click', () => {
      forgeMcpServerForm.classList.add('hidden');
    });
  }

  if (forgeMcpTransportSelect) {
    forgeMcpTransportSelect.addEventListener('change', () => {
      const isStdio = forgeMcpTransportSelect.value === 'stdio';
      if (forgeMcpUrlGroup) forgeMcpUrlGroup.classList.toggle('hidden', isStdio);
      if (forgeMcpCommandGroup) forgeMcpCommandGroup.classList.toggle('hidden', !isStdio);
    });
  }

  if (forgeMcpTestBtn) {
    forgeMcpTestBtn.addEventListener('click', async () => {
      const name = forgeMcpNameInput ? forgeMcpNameInput.value.trim() : 'test-server';
      const transport = forgeMcpTransportSelect ? forgeMcpTransportSelect.value : 'sse';
      const url = forgeMcpUrlInput ? forgeMcpUrlInput.value.trim() : '';
      const command = forgeMcpCommandInput ? forgeMcpCommandInput.value.trim() : '';
      let headers = null;
      if (forgeMcpHeadersInput && forgeMcpHeadersInput.value.trim()) {
        try {
          headers = JSON.parse(forgeMcpHeadersInput.value.trim());
        } catch (e) {
          showToast('Invalid JSON in custom headers', 'warning');
          return;
        }
      }
      const agentId = activeForgeAgent ? activeForgeAgent.id : 'hyperv';
      if (forgeMcpTestResult) {
        forgeMcpTestResult.classList.remove('hidden');
        forgeMcpTestResult.className = 'p-2.5 rounded text-xs font-mono border bg-slate-900 border-slate-700 text-slate-300';
        forgeMcpTestResult.textContent = 'Probing server...';
      }
      try {
        const testRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp/test`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, transport, url: url || null, command: command || null, headers, enabled: true }),
        });
        const data = await testRes.json();
        if (forgeMcpTestResult) {
          if (data.status === 'ok') {
            forgeMcpTestResult.className = 'p-2.5 rounded text-xs font-mono border bg-emerald-950/60 border-emerald-800 text-emerald-300';
            forgeMcpTestResult.textContent = `✓ OK (${data.latency_ms}ms) - ${data.tools_count} tool(s) found: ${(data.tools || []).join(', ')}`;
          } else {
            forgeMcpTestResult.className = 'p-2.5 rounded text-xs font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
            forgeMcpTestResult.textContent = `✗ Probe failed (${data.latency_ms}ms): ${data.error || 'Unknown error'}`;
          }
        }
      } catch (err) {
        if (forgeMcpTestResult) {
          forgeMcpTestResult.className = 'p-2.5 rounded text-xs font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
          forgeMcpTestResult.textContent = `✗ Connection error: ${err.message || err}`;
        }
      }
    });
  }

  if (forgeMcpSaveBtn) {
    forgeMcpSaveBtn.addEventListener('click', async () => {
      const name = forgeMcpNameInput ? forgeMcpNameInput.value.trim() : '';
      if (!name) {
        showToast('Server name is required', 'warning');
        return;
      }
      const transport = forgeMcpTransportSelect ? forgeMcpTransportSelect.value : 'sse';
      const url = forgeMcpUrlInput ? forgeMcpUrlInput.value.trim() : '';
      const command = forgeMcpCommandInput ? forgeMcpCommandInput.value.trim() : '';
      if (transport === 'sse' && !url) {
        showToast('Remote URL is required for HTTP/SSE transport', 'warning');
        return;
      }
      let headers = null;
      if (forgeMcpHeadersInput && forgeMcpHeadersInput.value.trim()) {
        try {
          headers = JSON.parse(forgeMcpHeadersInput.value.trim());
        } catch (e) {
          showToast('Invalid JSON in custom headers', 'warning');
          return;
        }
      }
      const enabled = forgeMcpEnabledCheckbox ? forgeMcpEnabledCheckbox.checked : true;
      const agentId = activeForgeAgent ? activeForgeAgent.id : null;
      if (!agentId) {
        showToast('No active agent selected', 'error');
        return;
      }
      try {
        const saveRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, transport, url: url || null, command: command || null, headers, enabled }),
        });
        if (!saveRes.ok) throw new Error(`HTTP ${saveRes.status}`);
        showToast(`MCP server '${name}' saved`, 'success');
        if (forgeMcpServerForm) forgeMcpServerForm.classList.add('hidden');
        await loadAgentMcpServers(agentId);
      } catch (err) {
        showToast(`Failed to save server: ${err.message || err}`, 'error');
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

  if (studioRunbookCloseBtn) {
    studioRunbookCloseBtn.addEventListener('click', () => hideRunbookEditor());
  }

  if (studioRunbookCancelBtn) {
    studioRunbookCancelBtn.addEventListener('click', () => hideRunbookEditor());
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
  const labRetryJobBtn = $('labRetryJobBtn');
  const labCopyFeedBtn = $('labCopyFeedBtn');
  const labCopyFeedText = $('labCopyFeedText');

  let labPollTimer = null;
  let currentLabJobData = null;

  async function updateLabRunsBadge() {
    try {
      const res = await fetch('/api/agent_training_factory/jobs');
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
      const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(jobId)}`);
      if (!res.ok) return;
      const data = await res.json();
      currentLabJobData = data;
      if (labRetryJobBtn) {
        labRetryJobBtn.classList.remove('hidden');
      }
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

      // Stepper logic — Agent Training Factory phases (CARD-171)
      const node = job.current_node_id;
      const status = job.status;
      const phaseOrder = [
        'intent_distill',
        'ground',
        'blueprint',
        'author',
        'scenario_verify',
        'verify',
        'optimize',
        'promote',
      ];
      // Legacy costume nodes map into phaseOrder indices
      const legacyMap = {
        socratic_handshake: 'intent_distill',
        discovery_probe: 'ground',
        architecture_blueprint: 'blueprint',
        attempt_node: 'author',
        conduct_node: 'author',
        coder_node: 'author',
        sandbox_battery_node: 'verify',
        critic_signoff_node: 'optimize',
        hitl_deploy_gate_node: 'promote',
        pack_finalized_node: 'done',
      };
      const phase = legacyMap[node] || node;
      let activeIdx = phaseOrder.indexOf(phase);
      if (phase === 'done' || status === 'done') activeIdx = phaseOrder.length;
      if (status === 'waiting_approval') activeIdx = phaseOrder.indexOf('promote');

      const stepEls = [
        'labStep1',
        'labStep2',
        'labStep3',
        'labStep4',
        'labStep5',
        'labStep6',
        'labStep7',
        'labStep8',
      ];
      stepEls.forEach((id, idx) => {
        const el = $(id);
        if (!el) return;
        if (activeIdx < 0) {
          setStepVisual(el, 'idle');
        } else if (idx < activeIdx) {
          setStepVisual(el, 'done');
        } else if (idx === activeIdx) {
          setStepVisual(el, 'active');
        } else {
          setStepVisual(el, 'idle');
        }
      });

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
            const feedLines = formatLabPacketFeedLines(p);
            let roleColor = 'text-slate-400';
            if (role === 'intent_distill') roleColor = 'text-sky-400';
            else if (role === 'ground' || role === 'inspector') roleColor = 'text-cyan-400';
            else if (role === 'blueprint' || role === 'conductor') roleColor = 'text-brand-400';
            else if (role === 'author' || role === 'coder') roleColor = 'text-amber-400';
            else if (role === 'scenario_verify') roleColor = 'text-fuchsia-400';
            else if (role === 'verify' || role === 'sandbox_runner') roleColor = 'text-purple-400';
            else if (role === 'optimize' || role === 'critic') roleColor = 'text-emerald-400';
            else if (role === 'promote') roleColor = 'text-rose-400';

            feedLines.forEach((line, lineIdx) => {
              const row = document.createElement('div');
              row.className = 'flex items-start space-x-2 py-0.5';
              const bodyClass = lineIdx === 0 ? 'text-slate-200' : 'text-rose-300 text-[11px]';
              row.innerHTML = `
              <span class="text-slate-500 text-[10px] flex-shrink-0">[${escapeHtml(lineIdx === 0 ? timeStr : '')}]</span>
              <span class="${roleColor} font-semibold flex-shrink-0">[${escapeHtml(lineIdx === 0 ? role.toUpperCase() : '')}]</span>
              <span class="${bodyClass}">${escapeHtml(line)}</span>
            `;
              labPacketsFeed.appendChild(row);
            });
          });
          labPacketsFeed.scrollTop = labPacketsFeed.scrollHeight;
        }
      }


      // Artifact review pills (CARD-171)
      const labArtifactPills = $('labArtifactPills');
      const artifacts = collectPacketArtifacts(packets);
      if (labArtifactPills) {
        labArtifactPills.innerHTML = '';
        if (artifacts.length === 0) {
          labArtifactPills.innerHTML = '<span class="text-slate-500 text-[11px] italic">No authored artifacts yet.</span>';
        } else {
          artifacts.forEach((art, idx) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'lab-artifact-pill px-2 py-0.5 rounded-lg bg-slate-800 hover:bg-brand-900/40 border border-slate-700 hover:border-brand-500/50 text-slate-200 hover:text-brand-200 font-mono text-[11px] transition';
            btn.setAttribute('data-testid', `lab-artifact-pill-${idx}`);
            btn.setAttribute('data-artifact-path', art.path);
            btn.title = 'Preview artifact from job packet';
            btn.textContent = art.path;
            btn.addEventListener('click', () => openLabArtifactPreview(art, job.target_agent_id));
            labArtifactPills.appendChild(btn);
          });
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
      const res = await fetch('/api/agent_training_factory/jobs');
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
          if (labRetryJobBtn) {
            labRetryJobBtn.classList.add('hidden');
          }
          currentLabJobData = null;
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


  function openLabArtifactPreview(art, agentId) {
    const modal = $('labArtifactPreviewModal');
    const titleEl = $('labArtifactPreviewTitle');
    const bodyEl = $('labArtifactPreviewBody');
    const pathsEl = $('labArtifactPreviewPaths');
    const noteEl = $('labArtifactPreviewNote');
    if (!modal || !art) return;
    if (titleEl) titleEl.textContent = art.path || 'Artifact';
    if (bodyEl) {
      const content = art.content || '(No inline content in packet; wiki path listed for human review.)';
      bodyEl.textContent = content;
    }
    if (noteEl) {
      noteEl.textContent = art.kind === 'wiki'
        ? 'Pre-promote: Wiki path from Grounding packet (may already exist under the Wiki vault).'
        : 'Pre-promote: content is from the job packet (not yet written under packs/).';
    }
    if (pathsEl) {
      const expected = art.kind === 'file'
        ? buildExpectedPackPaths(agentId, [art.path])
        : [art.path];
      pathsEl.innerHTML = '';
      expected.forEach((p) => {
        const li = document.createElement('li');
        li.className = 'font-mono text-[11px] text-emerald-300 break-all';
        li.setAttribute('data-testid', 'lab-artifact-expected-path');
        li.textContent = p;
        pathsEl.appendChild(li);
      });
    }
    modal.classList.remove('hidden');
    safeCreateIcons();
  }

  function closeLabArtifactPreview() {
    const modal = $('labArtifactPreviewModal');
    if (modal) modal.classList.add('hidden');
  }

  function closeLabMonitorDrawer() {
    if (labMonitorDrawer) labMonitorDrawer.classList.add('hidden');
    if (labPollTimer) {
      clearInterval(labPollTimer);
      labPollTimer = null;
    }
  }

  window.openLabMonitorDrawer = openLabMonitorDrawer;
  window.closeLabMonitorDrawer = closeLabMonitorDrawer;

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
        const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(jobId)}/promote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'approved' }),
        });
        if (!res.ok) throw new Error('Promotion deployment failed');
        const data = await res.json();
        showToast(`Successfully deployed ${data.agent_id} pack to live fleet!`, 'success');
        if (data.agent_id) {
          await loadAgentForge(data.agent_id);
        }
        if (typeof callbacks.onReloadAgents === 'function') {
          callbacks.onReloadAgents(data.agent_id);
        }
        if (typeof callbacks.onAgentSaved === 'function') {
          callbacks.onAgentSaved();
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
        const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(jobId)}/promote`, {
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

  if (labCopyFeedBtn) {
    labCopyFeedBtn.addEventListener('click', async () => {
      const packets = currentLabJobData ? (currentLabJobData.packets || []) : [];
      if (packets.length === 0) {
        showToast('No activity feed logs to copy.', 'info');
        return;
      }
      const textToCopy = formatLabActivityFeedText(packets);
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(textToCopy);
        } else {
          const textArea = document.createElement('textarea');
          textArea.value = textToCopy;
          document.body.appendChild(textArea);
          textArea.select();
          document.execCommand('copy');
          document.body.removeChild(textArea);
        }
        if (labCopyFeedText) {
          const originalText = labCopyFeedText.textContent;
          labCopyFeedText.textContent = 'Copied!';
          setTimeout(() => {
            if (labCopyFeedText) labCopyFeedText.textContent = originalText;
          }, 2000);
        }
        showToast('Activity feed copied to clipboard!', 'success');
      } catch (err) {
        console.error('Failed to copy feed:', err);
        showToast('Failed to copy feed to clipboard.', 'error');
      }
    });
  }

  if (labRetryJobBtn) {
    labRetryJobBtn.addEventListener('click', () => {
      if (!currentLabJobData) {
        showToast('No training run selected to retry.', 'warning');
        return;
      }
      closeLabMonitorDrawer();
      populateTrainModalForRetry(currentLabJobData);
      const modal = $('trainAgentHandshakeModal');
      if (modal) {
        modal.classList.remove('hidden');
        const modalTitle = $('trainAgentModalTitle');
        if (modalTitle) {
          const agentId = currentLabJobData?.job?.target_agent_id || currentLabJobData?.inputs?.target_agent_id || '';
          modalTitle.innerHTML = `
            <i data-lucide="rotate-ccw" class="w-4 h-4 text-emerald-400"></i>
            <span>Retry Training: ${escapeHtml(agentId || 'Specialist')}</span>
          `;
        }
        safeCreateIcons();
      }
    });
  }


  const closeLabArtifactPreviewBtn = $('closeLabArtifactPreviewBtn');
  const closeLabArtifactPreviewFooterBtn = $('closeLabArtifactPreviewFooterBtn');
  if (closeLabArtifactPreviewBtn) {
    closeLabArtifactPreviewBtn.addEventListener('click', closeLabArtifactPreview);
  }
  if (closeLabArtifactPreviewFooterBtn) {
    closeLabArtifactPreviewFooterBtn.addEventListener('click', closeLabArtifactPreview);
  }
  const labArtifactPreviewModal = $('labArtifactPreviewModal');
  if (labArtifactPreviewModal) {
    labArtifactPreviewModal.addEventListener('click', (e) => {
      if (e.target === labArtifactPreviewModal) closeLabArtifactPreview();
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
