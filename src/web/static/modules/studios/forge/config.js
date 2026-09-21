/**
 * Agent Studio: Agent Configuration, Provider Discovery, Tone Management & Brain Drawer Submodule
 * [CARD-153, CARD-156, CARD-162, CARD-398]
 * Manages per-agent LLM providers, model discovery, avatar previews, telemetry stats,
 * background routine assignments, tone curation modal, and semantic brain memory shelf.
 */

import { $, $query, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { showToast } from '../../ui/toast.js';
import { PRESETS_DEFAULTS } from '../settings.js';

let cachedDiscoveredModels = [];
let cachedTones = [];

export function getCachedDiscoveredModels() {
  return cachedDiscoveredModels;
}

export function setCachedDiscoveredModels(models) {
  cachedDiscoveredModels = models || [];
}

export function populateAgentModelSelect(selectedProvider, targetModel = 'default') {
  const forgeAgentModelSelect = $('forgeAgentModelSelect');
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

export function updateProviderConfigVisibility(provider) {
  const forgeProviderConfigContainer = $('forgeProviderConfigContainer');
  const forgeApiKeyInput = $('forgeApiKeyInput');
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

export async function discoverModelsForAgent() {
  const forgeProviderSelect = $('forgeProviderSelect');
  const forgeApiBaseUrlInput = $('forgeApiBaseUrlInput');
  const forgeApiKeyInput = $('forgeApiKeyInput');
  const forgeDiscoverModelsBtn = $('forgeDiscoverModelsBtn');
  const forgeAgentModelSelect = $('forgeAgentModelSelect');

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

export function updateAvatarPreview(iconName) {
  const forgeAvatarPreview = $('forgeAvatarIcon');
  if (forgeAvatarPreview) {
    forgeAvatarPreview.innerHTML = `<i data-lucide="${iconName}" class="w-7 h-7"></i>`;
    safeCreateIcons();
  }
}

export async function loadAgentAssignedRoutines(agentId, callbacks = {}) {
  const forgeAssignedRoutinesList = $('forgeAssignedRoutinesList');
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

export async function loadAgentTelemetry(agentId) {
  const forgeStatTurns = $('forgeStatTurns');
  const forgeStatTokens = $('forgeStatTokens');
  const forgeStatCost = $('forgeStatCost');
  const forgeStatTools = $('forgeStatTools');
  const forgeStatErrors = $('forgeStatErrors');
  const forgeStatLatency = $('forgeStatLatency');

  try {
    const res = await fetch(`/api/observability/kpi?agent_id=${encodeURIComponent(agentId)}`);
    if (!res.ok) return;
    const data = await res.json();

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

export async function loadAndRenderBrainDrawer(agentId, query = '') {
  const agentBrainDrawer = $('agentBrainDrawer');
  const brainDrawerAgentName = $('brainDrawerAgentName');
  const brainShelfPinnedContainer = $('brainShelfPinnedContainer');
  const brainShelfSummariesCount = $('brainShelfSummariesCount');
  const brainShelfSummariesContainer = $('brainShelfSummariesContainer');
  const brainShelfFactsCount = $('brainShelfFactsCount');
  const brainShelfFactsContainer = $('brainShelfFactsContainer');
  const brainSearchInput = $('brainSearchInput');
  const forgePinnedMemory = $('forgePinnedMemory');

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

export function openBrainDrawer(getActiveAgentId = null) {
  const forgeIdInput = $('forgeIdInput');
  const agentBrainDrawer = $('agentBrainDrawer');
  const brainSearchInput = $('brainSearchInput');
  const idFromInput = forgeIdInput ? forgeIdInput.value.trim() : '';
  const agentId = idFromInput || (typeof getActiveAgentId === 'function' ? getActiveAgentId() : '');
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

export function closeBrainDrawer() {
  const agentBrainDrawer = $('agentBrainDrawer');
  if (agentBrainDrawer) {
    agentBrainDrawer.classList.add('hidden');
  }
}

export async function loadTones(selectedToneId = null) {
  const forgeToneSelect = $('forgeToneSelect');
  try {
    const res = await fetch('/api/tones');
    if (!res.ok) return;
    cachedTones = await res.json();

    if (forgeToneSelect) {
      const currentVal = selectedToneId || forgeToneSelect.value || 'default';
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

export function openManageTonesModal() {
  const manageTonesModal = $('manageTonesModal');
  if (!manageTonesModal) return;
  manageTonesModal.classList.remove('hidden');
  hideToneForm();
  renderManageTonesList();
}

export function closeManageTonesModal() {
  const manageTonesModal = $('manageTonesModal');
  if (!manageTonesModal) return;
  manageTonesModal.classList.add('hidden');
  hideToneForm();
}

export function showToneForm(mode = 'create', tone = null) {
  const manageToneForm = $('manageToneForm');
  const toneFormMode = $('toneFormMode');
  const manageToneFormTitle = $('manageToneFormTitle');
  const toneFormId = $('toneFormId');
  const toneFormName = $('toneFormName');
  const toneFormDescription = $('toneFormDescription');
  const toneFormDirective = $('toneFormDirective');

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

export function hideToneForm() {
  const manageToneForm = $('manageToneForm');
  if (!manageToneForm) return;
  manageToneForm.classList.add('hidden');
  if (manageToneForm.reset) manageToneForm.reset();
}

export async function renderManageTonesList() {
  const manageTonesList = $('manageTonesList');
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

    const editBtn = item.querySelector('.edit-tone-btn');
    if (editBtn) {
      editBtn.addEventListener('click', () => {
        showToneForm('edit', t);
      });
    }

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

/**
 * Wires LLM provider dropdown, discovery, and memory retention controls.
 */
export function setupAgentModelConfig() {
  const forgeProviderSelect = $('forgeProviderSelect');
  const forgeDiscoverModelsBtn = $('forgeDiscoverModelsBtn');
  const forgeAgentModelSelect = $('forgeAgentModelSelect');
  const forgeApiBaseUrlInput = $('forgeApiBaseUrlInput');
  const forgeMemoryRetentionDays = $('forgeMemoryRetentionDays');
  const forgeMemoryRetentionDaysLabel = $('forgeMemoryRetentionDaysLabel');

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

  if (forgeMemoryRetentionDays && forgeMemoryRetentionDaysLabel) {
    forgeMemoryRetentionDays.addEventListener('input', () => {
      forgeMemoryRetentionDaysLabel.textContent = `${forgeMemoryRetentionDays.value} days`;
    });
  }
}

/**
 * Wires Brain Drawer open/close/search/purge controls.
 */
export function setupBrainDrawer({ getActiveAgentId = null } = {}) {
  const btnOpenBrainDrawer = $('btnOpenBrainDrawer');
  const closeBrainDrawerBtn = $('closeBrainDrawerBtn');
  const closeBrainDrawerFooterBtn = $('closeBrainDrawerFooterBtn');
  const brainSearchInput = $('brainSearchInput');
  const btnPurgeBrain = $('btnPurgeBrain');

  if (btnOpenBrainDrawer) {
    btnOpenBrainDrawer.addEventListener('click', () => openBrainDrawer(getActiveAgentId));
  }

  if (closeBrainDrawerBtn) {
    closeBrainDrawerBtn.addEventListener('click', closeBrainDrawer);
  }

  if (closeBrainDrawerFooterBtn) {
    closeBrainDrawerFooterBtn.addEventListener('click', closeBrainDrawer);
  }

  if (brainSearchInput) {
    brainSearchInput.addEventListener('input', () => {
      const id = typeof getActiveAgentId === 'function' ? getActiveAgentId() : null;
      if (id) loadAndRenderBrainDrawer(id, brainSearchInput.value.trim());
    });
  }

  if (btnPurgeBrain) {
    btnPurgeBrain.addEventListener('click', async () => {
      const id = typeof getActiveAgentId === 'function' ? getActiveAgentId() : null;
      if (!id) return;
      if (!window.confirm(`Purge episodic memory for ${id}? Pinned memory is preserved.`)) return;
      try {
        const res = await fetch(`/api/agents/${encodeURIComponent(id)}/memory/purge`, { method: 'POST' });
        if (!res.ok) throw new Error('Purge failed');
        showToast('Memory purged', 'info');
        loadAndRenderBrainDrawer(id);
      } catch (err) {
        showToast(String(err.message || err), 'error');
      }
    });
  }
}

/**
 * Wires Tone Manager modal controls.
 */
export function setupToneManager() {
  const manageTonesBtn = $('manageTonesBtn');
  const closeManageTonesModalBtn = $('closeManageTonesModalBtn');
  const openNewToneFormBtn = $('openNewToneFormBtn');
  const closeToneFormBtn = $('closeToneFormBtn');
  const cancelToneFormBtn = $('cancelToneFormBtn');
  const manageToneForm = $('manageToneForm');
  const toneFormMode = $('toneFormMode');
  const toneFormId = $('toneFormId');
  const toneFormName = $('toneFormName');
  const toneFormDescription = $('toneFormDescription');
  const toneFormDirective = $('toneFormDirective');

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
}
