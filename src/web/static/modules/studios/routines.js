/**
 * Routines Studio Module [REQ-FE-001, REQ-ROUT-001 - REQ-ROUT-005]
 */

import { $, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { showToast } from '../ui/toast.js';


export function getHumanCronPreview(cronStr) {
  const s = (cronStr || '').trim();
  if (!s) return 'Invalid cron expression';
  if (s === '* * * * *') return 'Every minute';
  if (s.startsWith('*/') && s.endsWith('* * * *')) return `Every ${s.slice(2, s.indexOf(' '))} minutes`;
  if (s === '0 * * * *') return 'Every hour at minute 0';
  if (s === '0 */2 * * *') return 'Every 2 hours';
  if (s === '0 8 * * *') return 'Daily at 08:00 UTC';
  if (s === '0 0 * * 0') return 'Weekly on Sunday at 00:00 UTC';
  return `Cron schedule: ${s}`;
}

export function initRoutinesStudio(state, callbacks = {}) {
  const routinesGrid = $('routinesGrid');
  const refreshRoutinesBtn = $('refreshRoutinesBtn');
  const newRoutineBtn = $('newRoutineBtn');
  const routineStatusBanner = $('routineStatusBanner');
  const routineModal = $('routineModal');
  const routineModalTitle = $('routineModalTitle');
  const routineModalForm = $('routineModalForm');
  const closeRoutineModalBtn = $('closeRoutineModalBtn');
  const cancelRoutineModalBtn = $('cancelRoutineModalBtn');
  const routineNameInput = $('routineNameInput');
  const routineIdInput = $('routineIdInput');
  const routineAgentSelect = $('routineAgentSelect');
  const routinePresetSelect = $('routinePresetSelect');
  const routineCronInput = $('routineCronInput');
  const routineHumanPreview = $('routineHumanPreview');
  const routinePromptInput = $('routinePromptInput');
  const routineEnabledInput = $('routineEnabledInput');
  const saveRoutineBtn = $('saveRoutineBtn');

  function showRoutineBanner(msg, isError = false) {
    if (!routineStatusBanner) return;
    routineStatusBanner.textContent = msg;
    routineStatusBanner.className = `px-4 py-2 rounded-lg text-xs font-medium text-center border ${
      isError ? 'bg-rose-950/70 text-rose-300 border-rose-800' : 'bg-emerald-950/70 text-emerald-300 border-emerald-800'
    }`;
    routineStatusBanner.classList.remove('hidden');
    setTimeout(() => routineStatusBanner.classList.add('hidden'), 4000);
  }

  async function populateRoutineAgentSelect(selectedAgentId = null) {
    if (!routineAgentSelect) return;

    if (!state.agents || state.agents.length === 0) {
      try {
        const res = await fetch('/api/agents');
        if (res.ok) {
          state.agents = await res.json();
        }
      } catch (err) {
        console.error('[AutoReiv Routines] Failed to fetch agents for select:', err);
      }
    }

    const agentsList = (state.agents && state.agents.length > 0)
      ? state.agents
      : [
          { id: 'assistant', name: 'General Assistant' },
          { id: 'librarian', name: 'Librarian (Wiki)' },
          { id: 'sre-diagnostics', name: 'AutoReiv Platform SRE' },
        ];

    routineAgentSelect.innerHTML = '';
    agentsList.forEach((a) => {
      const opt = document.createElement('option');
      opt.value = a.id;
      opt.textContent = `${a.avatar_icon ? '' : '🤖 '}${a.name || a.id} (${a.id})`;
      if (selectedAgentId && a.id === selectedAgentId) opt.selected = true;
      routineAgentSelect.appendChild(opt);
    });

    if (selectedAgentId) {
      routineAgentSelect.value = selectedAgentId;
    }
  }

  async function openRoutineModal(routine = null, preselectedAgentId = null) {
    if (!routineModal) return;
    const targetAgentId = routine ? routine.agent_id : (preselectedAgentId || 'assistant');
    await populateRoutineAgentSelect(targetAgentId);

    if (routine) {
      if (routineModalTitle) {
        routineModalTitle.innerHTML = `<i data-lucide="edit-3" class="w-4 h-4 text-brand-400"></i><span>Edit Routine: ${escapeHtml(routine.name)}</span>`;
      }
      if (routineNameInput) routineNameInput.value = routine.name || '';
      if (routineIdInput) {
        routineIdInput.value = routine.id || '';
        routineIdInput.disabled = true;
      }
      if (routineAgentSelect) routineAgentSelect.value = routine.agent_id;
      if (routineCronInput) routineCronInput.value = routine.cron_expression || '0 * * * *';
      if (routinePresetSelect) {
        const matchingOpt = Array.from(routinePresetSelect.options).find((o) => o.value === routine.cron_expression);
        routinePresetSelect.value = matchingOpt ? routine.cron_expression : 'custom';
      }
      if (routinePromptInput) routinePromptInput.value = routine.prompt || '';
      if (routineEnabledInput) routineEnabledInput.checked = routine.enabled !== false;
      if (routineHumanPreview) {
        routineHumanPreview.textContent = `Schedule: ${routine.human_schedule || getHumanCronPreview(routine.cron_expression)}`;
      }
    } else {
      if (routineModalTitle) {
        routineModalTitle.innerHTML = `<i data-lucide="plus-circle" class="w-4 h-4 text-brand-400"></i><span>Create Autonomous Routine</span>`;
      }
      if (routineNameInput) routineNameInput.value = '';
      if (routineIdInput) {
        routineIdInput.value = '';
        routineIdInput.disabled = false;
      }
      if (routinePresetSelect) routinePresetSelect.value = '0 * * * *';
      if (routineCronInput) routineCronInput.value = '0 * * * *';
      if (routinePromptInput) routinePromptInput.value = '';
      if (routineEnabledInput) routineEnabledInput.checked = true;
      if (routineHumanPreview) {
        routineHumanPreview.textContent = 'Schedule: Every hour at minute 0';
      }
    }

    routineModal.classList.remove('hidden');
    safeCreateIcons();
  }

  function closeRoutineModal() {
    if (routineModal) routineModal.classList.add('hidden');
  }

  async function loadRoutines() {
    try {
      const res = await fetch('/api/routines');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const routines = await res.json();
      if (!routinesGrid) return;
      routinesGrid.innerHTML = '';

      if (routines.length === 0) {
        routinesGrid.innerHTML = `
          <div class="col-span-full p-8 text-center bg-slate-900/40 rounded-xl border border-slate-800 text-slate-400 text-xs">
            No routines configured. Click <strong>+ New Routine</strong> to create one!
          </div>
        `;
        return;
      }

      routines.forEach((r) => {
        const isBuiltin = [
          'routine-sre-health',
          'morning-briefing',
          'routine-daily-brief',
          'routine-wiki-prune',
        ].includes(r.id);
        const card = document.createElement('div');
        card.className = `p-5 rounded-2xl bg-slate-900 border ${
          r.enabled ? 'border-slate-800' : 'border-slate-800/50 opacity-75'
        } flex flex-col justify-between space-y-4 hover:border-slate-700 transition shadow-sm`;

        const lastRunText = r.last_run_at ? new Date(r.last_run_at).toLocaleString() : 'Never executed';
        const statusBadge = r.enabled
          ? `<span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center space-x-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span><span>Active</span></span>`
          : `<span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 flex items-center space-x-1"><span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span><span>Paused</span></span>`;

        card.innerHTML = `
          <div class="space-y-3">
            <div class="flex items-start justify-between gap-2">
              <div>
                <div class="flex items-center space-x-2 mb-1">
                  <span class="text-xs font-semibold px-2 py-0.5 rounded bg-brand-950 text-brand-400 border border-brand-800 font-mono">${escapeHtml(r.agent_id)}</span>
                  ${statusBadge}
                </div>
                <h3 class="font-bold text-base text-white tracking-tight">${escapeHtml(r.name)}</h3>
                <span class="text-[10px] font-mono text-slate-500">${escapeHtml(r.id)}</span>
              </div>
            </div>

            <!-- Schedule & Frequency Details -->
            <div class="p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-1">
              <div class="flex items-center justify-between text-xs">
                <span class="text-slate-300 font-medium">${escapeHtml(r.human_schedule || r.cron_expression)}</span>
                <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-700">${escapeHtml(r.cron_expression || `${r.interval_seconds}s`)}</span>
              </div>
              <div class="text-[11px] text-brand-400 font-mono flex items-center space-x-1">
                <i data-lucide="clock" class="w-3 h-3"></i>
                <span>Next run ${escapeHtml(r.next_run_eta || 'scheduled')}</span>
              </div>
            </div>

            <!-- Directive Preview -->
            <div class="text-xs text-slate-300 line-clamp-2 bg-slate-950/40 p-2 rounded-lg border border-slate-800/80 font-mono text-[11px] leading-relaxed">
              "${escapeHtml(r.prompt || r.description || '')}"
            </div>

            <!-- Last Run Telemetry -->
            <div class="flex items-center justify-between text-[11px] text-slate-400 pt-1">
              <span>Last Run: <span class="text-slate-300">${lastRunText}</span></span>
              <span>Status: <strong class="${r.last_status === 'success' ? 'text-emerald-400' : 'text-slate-400'}">${escapeHtml(r.last_status)}</strong></span>
            </div>
          </div>

          <!-- Card Actions Footer -->
          <div class="pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
            <div class="flex items-center space-x-1.5">
              <button class="edit-routine-btn px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 rounded-lg transition" title="Edit Schedule & Prompt">
                Edit
              </button>
              <button class="toggle-routine-btn px-2.5 py-1 ${r.enabled ? 'bg-amber-950/40 hover:bg-amber-900/60 text-amber-300 border-amber-800/60' : 'bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 border-emerald-800/60'} border text-xs font-medium rounded-lg transition" title="${r.enabled ? 'Pause Routine' : 'Resume Routine'}">
                ${r.enabled ? 'Pause' : 'Resume'}
              </button>
              ${
                !isBuiltin
                  ? `<button class="delete-routine-btn px-2 py-1 bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 border border-rose-800/60 text-xs font-medium rounded-lg transition" title="Delete Routine">Delete</button>`
                  : ''
              }
            </div>
            <button class="trigger-routine-btn px-3 py-1 bg-brand-600 hover:bg-brand-500 text-xs font-semibold text-white rounded-lg shadow-sm transition flex items-center space-x-1" data-id="${r.id}">
              <i data-lucide="play" class="w-3 h-3"></i>
              <span>Run Now</span>
            </button>
          </div>
        `;
        routinesGrid.appendChild(card);

        // Edit listener
        card.querySelector('.edit-routine-btn')?.addEventListener('click', () => openRoutineModal(r));

        // Toggle listener
        card.querySelector('.toggle-routine-btn')?.addEventListener('click', async () => {
          try {
            await fetch(`/api/routines/${r.id}/toggle`, { method: 'POST' });
            showRoutineBanner(`Routine '${r.name}' ${r.enabled ? 'paused' : 'resumed'}.`);
            await loadRoutines();
          } catch (err) {
            showRoutineBanner(`Failed to toggle routine: ${err.message}`, true);
          }
        });

        // Delete listener
        card.querySelector('.delete-routine-btn')?.addEventListener('click', async () => {
          if (!confirm(`Are you sure you want to delete routine '${r.name}'?`)) return;
          try {
            const delRes = await fetch(`/api/routines/${r.id}`, { method: 'DELETE' });
            if (!delRes.ok) {
              const err = await delRes.json();
              throw new Error(err.detail || 'Delete failed');
            }
            showRoutineBanner(`Routine '${r.name}' deleted.`);
            await loadRoutines();
          } catch (err) {
            showRoutineBanner(`Failed to delete: ${err.message}`, true);
          }
        });

        // Trigger listener
        card.querySelector('.trigger-routine-btn')?.addEventListener('click', async (e) => {
          const btn = e.currentTarget;
          const origHtml = btn.innerHTML;
          btn.innerHTML = `<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i><span>Running...</span>`;
          btn.disabled = true;
          try {
            const runRes = await fetch(`/api/routines/${r.id}/run`, { method: 'POST' });
            const runData = await runRes.json();
            btn.innerHTML = `<span>Completed!</span>`;
            showRoutineBanner(
              `Routine '${r.name}' finished with status: ${runData.status} (${runData.duration_ms || 0}ms)`
            );
            setTimeout(() => {
              btn.innerHTML = origHtml;
              btn.disabled = false;
              loadRoutines();
            }, 2500);
          } catch (err) {
            btn.innerHTML = `<span>Failed</span>`;
            showRoutineBanner(`Routine execution error: ${err.message}`, true);
            setTimeout(() => {
              btn.innerHTML = origHtml;
              btn.disabled = false;
            }, 2500);
          }
        });
      });

      safeCreateIcons();
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load routines:', err);
    }
  }

  // Routine Modal Listeners
  if (newRoutineBtn) newRoutineBtn.addEventListener('click', () => openRoutineModal(null));
  if (closeRoutineModalBtn) closeRoutineModalBtn.addEventListener('click', closeRoutineModal);
  if (cancelRoutineModalBtn) cancelRoutineModalBtn.addEventListener('click', closeRoutineModal);

  if (routinePresetSelect) {
    routinePresetSelect.addEventListener('change', () => {
      if (routinePresetSelect.value !== 'custom') {
        if (routineCronInput) routineCronInput.value = routinePresetSelect.value;
        if (routineHumanPreview) {
          routineHumanPreview.textContent = `Schedule: ${getHumanCronPreview(routinePresetSelect.value)}`;
        }
      }
    });
  }

  if (routineCronInput) {
    routineCronInput.addEventListener('input', () => {
      if (routineHumanPreview) {
        routineHumanPreview.textContent = `Schedule: ${getHumanCronPreview(routineCronInput.value)}`;
      }
    });
  }

  if (routineModalForm) {
    routineModalForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = (routineNameInput?.value || '').trim();
      const id = (routineIdInput?.value || '').trim();
      const agent_id = routineAgentSelect?.value || 'system-agent';
      const cron_expr = (routineCronInput?.value || '0 * * * *').trim();
      const prompt_template = (routinePromptInput?.value || '').trim();
      const enabled = routineEnabledInput ? routineEnabledInput.checked : true;

      if (!name || !prompt_template) {
        showToast('Please provide a Routine Name and Mission Prompt.', 'warning');
        return;
      }

      const payload = {
        name,
        agent_id,
        cron_expr,
        prompt_template,
        enabled,
      };
      if (id) payload.id = id;

      try {
        if (saveRoutineBtn) saveRoutineBtn.disabled = true;
        let res;
        if (id && routineIdInput?.disabled) {
          res = await fetch(`/api/routines/${encodeURIComponent(id)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
        } else {
          res = await fetch('/api/routines', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
        }

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Save failed');
        }

        closeRoutineModal();
        showToast(`Routine '${name}' saved successfully!`, 'success');
        showRoutineBanner(`Routine '${name}' saved successfully!`);
        await loadRoutines();
        if (callbacks.onRoutineSaved) {
          callbacks.onRoutineSaved();
        }
      } catch (err) {
        showToast(`Failed to save routine: ${err.message}`, 'error');
      } finally {
        if (saveRoutineBtn) saveRoutineBtn.disabled = false;
      }

    });
  }

  if (refreshRoutinesBtn) refreshRoutinesBtn.addEventListener('click', loadRoutines);
  populateRoutineAgentSelect();

  return {
    loadRoutines,
    openRoutineModal,
    closeRoutineModal,
    showRoutineBanner,
  };
}
