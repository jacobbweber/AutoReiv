/**
 * Agent Forge Studio Module & Co-Pilot [REQ-FE-001, REQ-FORGE-006]
 */

import { $, $query, $queryAll, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { showToast } from '../ui/toast.js';


export function initAgentForge(state, callbacks = {}) {
  const forgeAgentSelect = $('forgeAgentSelect');
  const newAgentBtn = $('newAgentBtn');
  const saveAgentBtn = $('saveAgentBtn');
  const deleteAgentBtn = $('deleteAgentBtn');
  const forgeStatusBanner = $('forgeStatusBanner');
  const forgeBuiltinBadge = $('forgeBuiltinBadge');
  const forgeAvatarPreview = $('forgeAvatarIcon');
  const forgeAvatarSelect = $('forgeAvatarSelect');
  const forgeNameInput = $('forgeNameInput');
  const forgeIdInput = $('forgeIdInput');
  const forgeDescInput = $('forgeDescInput');
  const forgeToneSelect = $('forgeToneSelect');
  const forgeMaxTurnsInput = $('forgeMaxTurnsInput');
  const forgePurposeSelect = $('forgePurposeSelect');
  const forgeModelSelect = $('forgeModelSelect');
  const forgeSystemPrompt = $('forgeSystemPrompt');
  const forgeSkillsGrid = $('forgeSkillsGrid');
  const selectAllToolsBtn = $('selectAllToolsBtn');
  const clearAllToolsBtn = $('clearAllToolsBtn');
  const forgeStatTurns = $('forgeStatTurns');
  const forgeStatTokens = $('forgeStatTokens');
  const forgeStatTools = $('forgeStatTools');
  const forgeStatErrors = $('forgeStatErrors');
  const forgeStatLatency = $('forgeStatLatency');

  const linkRoutineForAgentBtn = $('linkRoutineForAgentBtn');
  const forgeAssignedRoutinesList = $('forgeAssignedRoutinesList');

  let activeForgeAgent = null;
  let cachedSkillsCatalog = null;

  async function loadAgentForge() {
    try {
      if (!cachedSkillsCatalog) {
        const catRes = await fetch('/api/skills/catalog');
        if (catRes.ok) {
          cachedSkillsCatalog = await catRes.json();
        }
      }
      if (cachedSkillsCatalog) {
        renderSkillsCatalog(cachedSkillsCatalog);
      }

      try {
        const modRes = await fetch('/api/models/discover');
        if (modRes.ok) {
          const modData = await modRes.json();
          if (forgeModelSelect) {
            const curVal = forgeModelSelect.value;
            forgeModelSelect.innerHTML = '<option value="default">Inherit from Purpose Slot / Global Default</option>';
            (modData.models || []).forEach((m) => {
              const opt = document.createElement('option');
              opt.value = m.name;
              opt.textContent = `${m.name} (${m.provider})`;
              forgeModelSelect.appendChild(opt);
            });
            if (curVal) forgeModelSelect.value = curVal;
          }
        }
      } catch (e) {
        console.warn('[AutoReiv UI] Failed to load models for forge select:', e);
      }

      const res = await fetch('/api/agents');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const agents = await res.json();
      state.agents = agents;

      if (forgeAgentSelect) {
        const selectedId = forgeAgentSelect.value || (agents[0] ? agents[0].id : null);
        forgeAgentSelect.innerHTML = '';
        agents.forEach((a) => {
          const opt = document.createElement('option');
          opt.value = a.id;
          opt.textContent = `${a.name} ${a.is_builtin ? '(Built-in)' : '(Custom)'}`;
          forgeAgentSelect.appendChild(opt);
        });

        if (selectedId && agents.some((a) => a.id === selectedId)) {
          forgeAgentSelect.value = selectedId;
        } else if (agents.length > 0) {
          forgeAgentSelect.value = agents[0].id;
        }

        const targetAgent = agents.find((a) => a.id === forgeAgentSelect.value) || agents[0];
        if (targetAgent) {
          renderAgentToForge(targetAgent);
        }
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load Agent Forge:', err);
    }
  }

  function renderSkillsCatalog(catalog) {
    if (!forgeSkillsGrid || !catalog) return;
    forgeSkillsGrid.innerHTML = '';

    const packs = catalog.skill_packs || [
      {
        id: 'standard-tools',
        name: 'Standard Tools',
        description: 'Available platform tools',
        icon: 'cpu',
        tools: catalog.tools || [],
      },
    ];

    packs.forEach((pack) => {
      const packCard = document.createElement('div');
      packCard.className =
        'p-3 rounded-xl bg-slate-800/70 border border-slate-700/80 space-y-2 col-span-full shadow-sm';

      const toolsHtml = (pack.tools || [])
        .map(
          (t) => `
        <label class="flex items-start space-x-2 p-2 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition cursor-pointer text-xs">
          <input type="checkbox" value="${t.name}" class="forge-tool-checkbox mt-0.5 rounded border-slate-700 text-brand-500 focus:ring-brand-500" data-pack="${pack.id}">
          <div class="flex-1 min-w-0">
            <span class="font-mono text-slate-200 block text-[11px] font-semibold truncate">${escapeHtml(t.name)}</span>
            <span class="text-slate-400 block text-[10px] line-clamp-2 leading-tight">${escapeHtml(t.description || '')}</span>
          </div>
        </label>
      `
        )
        .join('');

      packCard.innerHTML = `
        <div class="flex items-center justify-between pb-2 border-b border-slate-700/60">
          <div class="flex items-center space-x-2.5">
            <input type="checkbox" class="pack-master-checkbox rounded border-slate-700 text-brand-500 focus:ring-brand-500 cursor-pointer" data-pack="${pack.id}">
            <div class="w-6 h-6 rounded-lg bg-brand-600/30 border border-brand-500/50 flex items-center justify-center text-brand-400">
              <i data-lucide="${pack.icon || 'cpu'}" class="w-3.5 h-3.5"></i>
            </div>
            <div>
              <span class="font-bold text-xs text-white block">${escapeHtml(pack.name)}</span>
              <span class="text-[10px] text-slate-400 block">${escapeHtml(pack.description || '')}</span>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-700">${(pack.tools || []).length} tools</span>
            <button type="button" class="pack-collapse-btn text-slate-400 hover:text-white p-1 rounded" title="Toggle tools">
              <i data-lucide="chevron-down" class="w-4 h-4 transition-transform duration-200" style="transform: rotate(-90deg)"></i>
            </button>
          </div>
        </div>
        <div class="pack-tools-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 pt-1 hidden">
          ${toolsHtml}
        </div>
      `;

      forgeSkillsGrid.appendChild(packCard);

      const masterCb = packCard.querySelector('.pack-master-checkbox');
      const toolCbs = packCard.querySelectorAll(`.forge-tool-checkbox[data-pack="${pack.id}"]`);

      masterCb?.addEventListener('change', () => {
        toolCbs.forEach((cb) => (cb.checked = masterCb.checked));
      });

      toolCbs.forEach((cb) => {
        cb.addEventListener('change', () => {
          const allChecked = Array.from(toolCbs).every((c) => c.checked);
          const someChecked = Array.from(toolCbs).some((c) => c.checked);
          if (masterCb) {
            masterCb.checked = allChecked;
            masterCb.indeterminate = someChecked && !allChecked;
          }
        });
      });

      const collapseBtn = packCard.querySelector('.pack-collapse-btn');
      const toolsGrid = packCard.querySelector('.pack-tools-grid');

      collapseBtn?.addEventListener('click', () => {
        const isHidden = toolsGrid.classList.toggle('hidden');
        const iconElem = collapseBtn.querySelector('svg, i');
        if (iconElem) {
          iconElem.style.transform = isHidden ? 'rotate(-90deg)' : 'rotate(0deg)';
        }
      });
    });

    safeCreateIcons();
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
    if (forgeToneSelect) forgeToneSelect.value = agent.tone || 'default';
    if (forgeMaxTurnsInput) forgeMaxTurnsInput.value = agent.max_turns || 10;
    if (forgePurposeSelect) forgePurposeSelect.value = agent.purpose || 'general';
    if (forgeAvatarSelect) forgeAvatarSelect.value = agent.avatar_icon || 'bot';
    if (forgeModelSelect) forgeModelSelect.value = agent.model || 'default';

    updateAvatarPreview(agent.avatar_icon || 'bot');

    if (forgeBuiltinBadge) {
      if (agent.is_builtin) {
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
      if (agent.is_builtin) {
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

    const masterCheckboxes = $queryAll('.pack-master-checkbox');
    masterCheckboxes.forEach((masterCb) => {
      const packId = masterCb.dataset.pack;
      const packToolCbs = $queryAll(`.forge-tool-checkbox[data-pack="${packId}"]`);
      if (packToolCbs.length > 0) {
        const allChecked = Array.from(packToolCbs).every((c) => c.checked);
        const someChecked = Array.from(packToolCbs).some((c) => c.checked);
        masterCb.checked = allChecked;
        masterCb.indeterminate = someChecked && !allChecked;
      }
    });

    loadAgentTelemetry(agent.id);
    loadAgentAssignedRoutines(agent.id);
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
            console.error('[AutoReiv UI] Failed to run routine from forge:', err);
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
      if (forgeStatTurns) forgeStatTurns.textContent = data.total_turns || 0;
      if (forgeStatTokens) forgeStatTokens.textContent = (data.total_tokens || 0).toLocaleString();
      if (forgeStatTools) forgeStatTools.textContent = data.total_tool_calls || 0;
      if (forgeStatErrors) forgeStatErrors.textContent = `${(data.error_rate_pct || 0).toFixed(1)}%`;
      if (forgeStatLatency) forgeStatLatency.textContent = `${(data.avg_duration_ms || 0).toFixed(0)}ms`;
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

  if (newAgentBtn) {
    newAgentBtn.addEventListener('click', () => {
      activeForgeAgent = null;
      if (forgeNameInput) forgeNameInput.value = '';
      if (forgeIdInput) {
        forgeIdInput.value = '';
        forgeIdInput.disabled = false;
        forgeIdInput.focus();
      }
      if (forgeDescInput) forgeDescInput.value = '';
      if (forgeSystemPrompt)
        forgeSystemPrompt.value = "You are AutoReiv's custom agent. Execute your assigned tasks safely and concisely.";
      if (forgeToneSelect) forgeToneSelect.value = 'technical';
      if (forgeMaxTurnsInput) forgeMaxTurnsInput.value = 10;
      if (forgePurposeSelect) forgePurposeSelect.value = 'task_execution';
      if (forgeAvatarSelect) forgeAvatarSelect.value = 'terminal';
      if (forgeModelSelect) forgeModelSelect.value = 'default';

      updateAvatarPreview('terminal');

      if (forgeBuiltinBadge) {
        forgeBuiltinBadge.textContent = 'New Custom';
        forgeBuiltinBadge.className =
          'text-[10px] font-mono px-2 py-0.5 rounded bg-brand-950 text-brand-400 border border-brand-800';
      }
      if (deleteAgentBtn) {
        deleteAgentBtn.disabled = true;
        deleteAgentBtn.classList.add('opacity-40', 'cursor-not-allowed');
      }

      const checkboxes = $queryAll('.forge-tool-checkbox');
      checkboxes.forEach((cb) => {
        cb.checked = cb.value === 'system_info';
      });

      if (forgeStatusBanner) {
        forgeStatusBanner.textContent =
          'Creating new custom agent. Fill in identity, prompt, and skills, then click Save Profile.';
        forgeStatusBanner.className =
          'px-4 py-2 text-xs font-medium text-center border-b border-brand-800 bg-brand-950/60 text-brand-300 block';
        setTimeout(() => forgeStatusBanner.classList.add('hidden'), 4000);
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

      const checkedTools = [];
      $queryAll('.forge-tool-checkbox:checked').forEach((cb) => checkedTools.push(cb.value));

      const payload = {
        id: id,
        name: name,
        description: forgeDescInput ? forgeDescInput.value.trim() : '',
        system_prompt: forgeSystemPrompt ? forgeSystemPrompt.value.trim() : '',
        purpose: forgePurposeSelect ? forgePurposeSelect.value : 'general',
        tone: forgeToneSelect ? forgeToneSelect.value : 'default',
        avatar_icon: forgeAvatarSelect ? forgeAvatarSelect.value : 'bot',
        model: forgeModelSelect ? forgeModelSelect.value : 'default',
        allowed_tool_names: checkedTools,
        max_turns: parseInt(forgeMaxTurnsInput ? forgeMaxTurnsInput.value : 10, 10) || 10,
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

  if (deleteAgentBtn) {
    deleteAgentBtn.addEventListener('click', async () => {
      if (!activeForgeAgent || activeForgeAgent.is_builtin) return;
      if (!confirm(`Are you sure you want to permanently delete custom agent "${activeForgeAgent.name}"?`)) return;

      try {
        const res = await fetch(`/api/agents/${encodeURIComponent(activeForgeAgent.id)}`, { method: 'DELETE' });
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


  return {
    loadAgentForge,
    renderAgentToForge,
  };
}
