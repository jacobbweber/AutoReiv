/**
 * Agent Studio module [REQ-FE-001, REQ-FORGE-006]. Filename forge.js kept (CARD-118).
 */

import { $, $query, $queryAll, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { showToast } from '../ui/toast.js';

export function initAgentForge(state, callbacks = {}) {
  const forgeAgentSelect = $('forgeAgentSelect');
  const newAgentBtn = $('newAgentBtn');
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
  const forgePurposeSelect = $('forgePurposeSelect');
  const forgeModelSelect = $('forgeModelSelect');
  const forgeSystemPrompt = $('forgeSystemPrompt');
  const forgeSkillsGrid = $('forgeSkillsGrid');
  const forgeRunbooksGrid = $('forgeRunbooksGrid');
  const studioWorkflowsList = $('studioWorkflowsList');
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
  let cachedPlatformSkills = [];
  let cachedArchivedSkills = [];
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

  function skillCheckboxHtml(skill, archived = false) {
    const id = skill.id || '';
    const name = skill.name || id;
    const desc = skill.description || '';
    const archivedAttr = archived ? ' data-archived="1"' : '';
    const checkbox = archived
      ? ''
      : `<input type="checkbox" value="${escapeHtml(id)}" class="forge-skill-checkbox mt-0.5 rounded border-slate-700 text-brand-500 focus:ring-brand-500">`;
    return `
      <div class="flex items-start gap-2 p-2 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition text-xs">
        <label class="flex items-start space-x-2 flex-1 min-w-0 cursor-pointer">
          ${checkbox}
          <div class="flex-1 min-w-0">
            <span class="font-mono text-slate-200 block text-[11px] font-semibold truncate">${escapeHtml(name)}</span>
            <span class="text-slate-400 block text-[10px] line-clamp-2 leading-tight">${escapeHtml(desc)}</span>
          </div>
        </label>
        <button type="button" class="studio-runbook-open-btn shrink-0 px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[10px] font-semibold text-brand-300 border border-slate-700" data-pack-id="${escapeHtml(id)}"${archivedAttr}>Edit</button>
      </div>
    `;
  }

  function applySkillChecks() {
    $queryAll('.forge-skill-checkbox').forEach((cb) => {
      cb.checked = lastAllowedSkills.has(cb.value);
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

  function renderRunbooksChecklist() {
    if (!forgeRunbooksGrid) return;
    const packOwned = [];
    const platform = cachedPlatformSkills || [];
    const archived = cachedArchivedSkills || [];
    const packOwnedHtml = packOwned.length
      ? packOwned.map((s) => skillCheckboxHtml(s, false)).join('')
      : '<p class="text-[10px] text-slate-500 px-1">No pack-owned skills yet.</p>';
    const platformHtml = platform.length
      ? platform.map((s) => skillCheckboxHtml(s, false)).join('')
      : '<p class="text-[10px] text-slate-500 px-1">No platform runbooks in the skills data dir.</p>';
    const archivedHtml = archived.length
      ? archived.map((s) => skillCheckboxHtml(s, true)).join('')
      : '<p class="text-[10px] text-slate-500 px-1">No archived runbooks.</p>';
    forgeRunbooksGrid.innerHTML = `
      <div class="space-y-2">
        <h4 class="text-[11px] font-bold text-slate-300 uppercase tracking-wider">Pack-owned</h4>
        ${packOwnedHtml}
      </div>
      <div class="space-y-2">
        <h4 class="text-[11px] font-bold text-slate-300 uppercase tracking-wider">Platform</h4>
        ${platformHtml}
      </div>
      <div class="space-y-2">
        <h4 class="text-[11px] font-bold text-slate-300 uppercase tracking-wider">Archived</h4>
        ${archivedHtml}
      </div>
    `;
    forgeRunbooksGrid.querySelectorAll('.studio-runbook-open-btn').forEach((btn) => {
      btn.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        openRunbookEditor(btn.dataset.packId, btn.dataset.archived === '1');
      });
    });
    applySkillChecks();
  }

  async function loadPlatformSkills() {
    try {
      const res = await fetch('/api/skills/user-packs');
      if (res.ok) {
        const data = await res.json();
        cachedPlatformSkills = data.packs || [];
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
    renderRunbooksChecklist();
  }

  async function loadAgentForge() {
    try {
      if (!cachedSkillsCatalog) {
        const catRes = await fetch('/api/skills/catalog');
        if (catRes.ok) {
          cachedSkillsCatalog = await catRes.json();
        }
      }
      if (cachedSkillsCatalog) {
        renderToolsChecklist(cachedSkillsCatalog, []);
      }
      await loadPlatformSkills();

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
        console.warn('[AutoReiv UI] Failed to load models for Agent Studio select:', e);
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
      console.error('[AutoReiv UI] Failed to load Agent Studio:', err);
    }
  }

  function toolCheckboxHtml(tool) {
    const name = tool.name || '';
    const desc = tool.description || '';
    return `
      <label class="flex items-start space-x-2 p-2 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition cursor-pointer text-xs">
        <input type="checkbox" value="${escapeHtml(name)}" class="forge-tool-checkbox mt-0.5 rounded border-slate-700 text-brand-500 focus:ring-brand-500">
        <div class="flex-1 min-w-0">
          <span class="font-mono text-slate-200 block text-[11px] font-semibold truncate">${escapeHtml(name)}</span>
          <span class="text-slate-400 block text-[10px] line-clamp-2 leading-tight">${escapeHtml(desc)}</span>
        </div>
      </label>
    `;
  }

  function renderToolsChecklist(catalog, packToolNames = []) {
    if (!forgeSkillsGrid || !catalog) return;
    const packSet = new Set(packToolNames || []);
    const allTools = catalog.tools || [];
    const byName = new Map(allTools.map((t) => [t.name, t]));
    const packOwned = [];
    packSet.forEach((name) => {
      packOwned.push(byName.get(name) || { name, description: 'Pack-owned tool' });
    });
    const platform = allTools.filter((t) => !packSet.has(t.name));
    const packOwnedHtml = packOwned.length
      ? packOwned.map(toolCheckboxHtml).join('')
      : '<p class="text-[10px] text-slate-500 px-1">No pack-owned tools yet.</p>';
    const platformHtml = platform.length
      ? `<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">${platform.map(toolCheckboxHtml).join('')}</div>`
      : '<p class="text-[10px] text-slate-500 px-1">No platform tools registered.</p>';
    forgeSkillsGrid.innerHTML = `
      <div class="space-y-2">
        <h4 class="text-[11px] font-bold text-slate-300 uppercase tracking-wider">Pack-owned</h4>
        ${packOwnedHtml}
      </div>
      <div class="space-y-2">
        <h4 class="text-[11px] font-bold text-slate-300 uppercase tracking-wider">Platform</h4>
        ${platformHtml}
      </div>
    `;
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
    if (forgeRetentionDaysInput) forgeRetentionDaysInput.value = (agent.history_retention_days === 0 || agent.history_retention_days) ? agent.history_retention_days : 30;
    if (forgePurposeSelect) forgePurposeSelect.value = agent.purpose || 'general';
    if (forgeAvatarSelect) forgeAvatarSelect.value = agent.avatar_icon || 'bot';
    if (forgeModelSelect) forgeModelSelect.value = agent.model || 'default';
    if (forgeShowInChat) forgeShowInChat.checked = agent.show_in_chat !== false;

    if (cachedSkillsCatalog) {
      renderToolsChecklist(cachedSkillsCatalog, agent.pack_tool_names || []);
    }

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
      if (forgeRetentionDaysInput) forgeRetentionDaysInput.value = 30;
      if (forgePurposeSelect) forgePurposeSelect.value = 'task_execution';
      if (forgeAvatarSelect) forgeAvatarSelect.value = 'terminal';
      if (forgeModelSelect) forgeModelSelect.value = 'default';
      if (forgeShowInChat) forgeShowInChat.checked = true;
      if (cachedSkillsCatalog) {
        renderToolsChecklist(cachedSkillsCatalog, []);
      }

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
        cb.checked = false;
      });
      lastAllowedSkills = new Set();
      $queryAll('.forge-skill-checkbox').forEach((cb) => {
        cb.checked = false;
      });
      hideRunbookEditor();

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
      const checkedSkills = [];
      $queryAll('.forge-skill-checkbox:checked').forEach((cb) => checkedSkills.push(cb.value));

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
        allowed_skill: checkedSkills,
        pack_tool_names: (activeForgeAgent && activeForgeAgent.pack_tool_names) || [],
        show_in_chat: forgeShowInChat ? forgeShowInChat.checked : true,
        max_turns: parseInt(forgeMaxTurnsInput ? forgeMaxTurnsInput.value : 10, 10) || 10,
        history_retention_days: (function () { const n = parseInt(forgeRetentionDaysInput ? forgeRetentionDaysInput.value : 30, 10); return Number.isFinite(n) && n >= 0 ? n : 30; })(),
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

  setRunbookActionVisibility();

  return {
    loadAgentForge,
    renderAgentToForge,
  };
}
