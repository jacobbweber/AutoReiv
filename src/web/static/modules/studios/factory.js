/**
 * Factory Studio Controller [CARD-195, REQ-FACT-034 - REQ-FACT-039]
 *
 * Provides a dedicated, first-class workspace for the Agent Training Factory:
 * 1. Pipeline & Phase Prompts Inspector: 8-stage flowchart, context variables,
 *    and platform-wide system prompt customization.
 * 2. Training Runs & Live Monitor: Two-pane telemetry view with run filtering,
 *    live progress stepper, HITL deployment gate, and streaming packet logs.
 */

import { $, $queryAll, escapeHtml, safeCreateIcons } from '../dom.js';
import {
  collectPacketArtifacts,
  buildExpectedPackPaths,
  formatLabPacketFeedLines,
  formatLabActivityFeedText,
  populateTrainModalForRetry,
} from './forge.js';
import {
  populateTrainAgentTargetOptions,
  updateTrainAgentLiveIndicator,
} from './chat.js';

export const PHASE_METADATA = [
  {
    id: 'intent_distill',
    num: '01',
    name: 'Intent Distill',
    icon: 'message-circle-question',
    defaultDesc: 'Distills high-level operator brief into structured starter objectives, constraints, prerequisites, and Reflexion lessons.',
  },
  {
    id: 'ground',
    num: '02',
    name: 'Ground',
    icon: 'search',
    defaultDesc: 'Executes safe, read-only discovery against target host environment, filesystem, APIs, and credentials.',
  },
  {
    id: 'blueprint',
    num: '03',
    name: 'Blueprint',
    icon: 'compass',
    defaultDesc: 'Synthesizes tool schemas, capability taxonomy (tool, skill, mcp), file maps, and test plans.',
  },
  {
    id: 'author',
    num: '04',
    name: 'Author',
    icon: 'code',
    defaultDesc: 'Synthesizes complete, runnable Python tool code, PowerShell cmdlets, and SKILL.md runbooks.',
  },
  {
    id: 'scenario_verify',
    num: '05',
    name: 'Scenario Verify',
    icon: 'list-checks',
    defaultDesc: 'Executes authored tools against simulated sandbox fixtures and mock environments.',
  },
  {
    id: 'verify',
    num: '06',
    name: 'Code Verify',
    icon: 'shield-check',
    defaultDesc: 'Performs static AST validation, security guardrail allowlist checks, and idempotency tests.',
  },
  {
    id: 'optimize',
    num: '07',
    name: 'Optimize',
    icon: 'check-circle',
    defaultDesc: 'Refines code structure, handles edge cases, and removes redundant token baggage.',
  },
  {
    id: 'promote',
    num: '08',
    name: 'Promote',
    icon: 'rocket',
    defaultDesc: 'Packages verified files into the target agent pack, updates profile, and triggers fleet deployment.',
  },
];

export const PHASE_ORDER = PHASE_METADATA.map((p) => p.id);

export function calculateProgressIndex(nodeId, status) {
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

  const phase = legacyMap[nodeId] || nodeId;
  if (phase === 'done' || status === 'done') return PHASE_ORDER.length;
  if (status === 'waiting_approval') return PHASE_ORDER.indexOf('promote');
  return PHASE_ORDER.indexOf(phase);
}

export function filterJobs(jobs = [], searchQuery = '', statusFilter = 'all', agentFilter = '') {
  const query = String(searchQuery || '').trim().toLowerCase();
  const filter = String(statusFilter || 'all').trim().toLowerCase();
  const agent = String(agentFilter || '').trim().toLowerCase();

  return (jobs || []).filter((job) => {
    if (!job) return false;

    if (agent && agent !== 'all') {
      const jobAgent = String(job.target_agent_id || job.agent_id || '').trim().toLowerCase();
      if (jobAgent !== agent) return false;
    }

    const matchesSearch =
      !query ||
      (job.target_agent_id && job.target_agent_id.toLowerCase().includes(query)) ||
      (job.id && job.id.toLowerCase().includes(query));

    if (!matchesSearch) return false;

    if (filter === 'all') return true;
    const jobStatus = String(job.status || '').toLowerCase();
    if (filter === 'running') return jobStatus === 'running' || jobStatus === 'queued';
    if (filter === 'waiting_approval' || filter === 'waiting') return jobStatus === 'waiting_approval';
    if (filter === 'done') return jobStatus === 'done';
    if (filter === 'failed') return jobStatus === 'failed';
    return jobStatus === filter;
  });
}

export function populateFactoryAgentOptions(selectEl, agents = [], selectedAgentId = '') {
  if (!selectEl) return;
  selectEl.innerHTML = '<option value="">All Agents (Platform View)</option>';
  if (!selectEl.children) selectEl.children = [];
  if (selectEl.children.length === 0) {
    selectEl.children.push({ value: '', textContent: 'All Agents (Platform View)' });
  }

  (agents || []).forEach((ag) => {
    const id = ag.id || ag.agent_id || (typeof ag === 'string' ? ag : '');
    if (!id) return;
    if (id === 'agent_builder' || id === 'agent-builder') return;
    const name = ag.name || id;
    const label = name === id ? id : `${name} (${id})`;
    if (typeof document !== 'undefined') {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = label;
      if (selectedAgentId && id === selectedAgentId) {
        opt.selected = true;
      }
      selectEl.appendChild(opt);
    } else if (selectEl.appendChild) {
      const opt = { value: id, textContent: label };
      if (selectedAgentId && id === selectedAgentId) {
        opt.selected = true;
      }
      selectEl.appendChild(opt);
    }
  });
  if (selectedAgentId) {
    selectEl.value = selectedAgentId;
  }
}

export function initFactoryStudio(state, callbacks = {}) {
  // DOM Elements - Shell & Sub-Tabs
  const factoryTabPipelineBtn = $('factoryTabPipelineBtn');
  const factoryTabRunsBtn = $('factoryTabRunsBtn');
  const factoryPipelineView = $('factoryPipelineView');
  const factoryRunsView = $('factoryRunsView');
  const factoryActiveRunsBadge = $('factoryActiveRunsBadge');
  const factoryActiveStatusPill = $('factoryActiveStatusPill');
  const factoryRefreshBtn = $('factoryRefreshBtn');
  const factoryNewRunBtn = $('factoryNewRunBtn');
  const factoryNewRunBtnText = $('factoryNewRunBtnText');
  const factoryAgentSelect = $('factoryAgentSelect');

  // DOM Elements - Pipeline & Prompt Inspector
  const factoryFlowchartContainer = $('factoryFlowchartContainer');
  const factoryInspectorStageTitle = $('factoryInspectorStageTitle');
  const factoryInspectorStageDesc = $('factoryInspectorStageDesc');
  const factoryInspectorStatusBadge = $('factoryInspectorStatusBadge');
  const factoryContextVarPills = $('factoryContextVarPills');
  const factoryPhasePromptInput = $('factoryPhasePromptInput');
  const factoryPromptLastUpdated = $('factoryPromptLastUpdated');
  const factoryPromptCharCount = $('factoryPromptCharCount');
  const factorySavePromptBtn = $('factorySavePromptBtn');
  const factoryResetPromptBtn = $('factoryResetPromptBtn');

  // DOM Elements - Runs & Telemetry
  const factoryRunsListPane = $('factoryRunsListPane');
  const factoryRunDetailPane = $('factoryRunDetailPane');
  const factoryRunSearchInput = $('factoryRunSearchInput');
  const factoryRunsList = $('factoryRunsList');
  const factoryMobileBackToRunsBtn = $('factoryMobileBackToRunsBtn');
  const factoryDetailJobBadge = $('factoryDetailJobBadge');
  const factoryDetailStatusPill = $('factoryDetailStatusPill');
  const factoryDetailRetryBtn = $('factoryDetailRetryBtn');
  const factoryDetailCopyFeedBtn = $('factoryDetailCopyFeedBtn');
  const factoryDetailCopyFeedText = $('factoryDetailCopyFeedText');
  const factoryDetailStepper = $('factoryDetailStepper');
  const factoryDetailHitlCard = $('factoryDetailHitlCard');
  const factoryDetailHitlToolsList = $('factoryDetailHitlToolsList');
  const factoryDetailApproveBtn = $('factoryDetailApproveBtn');
  const factoryDetailRejectBtn = $('factoryDetailRejectBtn');
  const factoryDetailArtifactPills = $('factoryDetailArtifactPills');
  const factoryDetailPacketsFeed = $('factoryDetailPacketsFeed');
  const factoryDetailPacketCount = $('factoryDetailPacketCount');

  // State
  let activeSubView = 'pipeline'; // 'pipeline' | 'runs'
  let phasesData = [];
  let selectedPhaseId = 'intent_distill';
  let allJobs = [];
  let selectedJobId = null;
  let currentJobData = null;
  let statusFilter = 'all';
  let pollInterval = null;
  let activeAgentScope = '';
  let allAgents = [];

  function showToast(msg, type = 'info') {
    if (typeof callbacks.showToast === 'function') {
      callbacks.showToast(msg, type);
    }
  }

  // -------------------------------------------------------------
  // 1. Sub-View Switching
  // -------------------------------------------------------------
  function switchSubView(targetView) {
    activeSubView = targetView;
    if (targetView === 'pipeline') {
      if (factoryPipelineView) factoryPipelineView.classList.remove('hidden');
      if (factoryRunsView) factoryRunsView.classList.add('hidden');
      if (factoryTabPipelineBtn) {
        factoryTabPipelineBtn.className =
          'px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 bg-brand-600 text-white shadow-sm';
        factoryTabPipelineBtn.setAttribute('aria-selected', 'true');
      }
      if (factoryTabRunsBtn) {
        factoryTabRunsBtn.className =
          'px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 text-slate-400 hover:text-white hover:bg-slate-800';
        factoryTabRunsBtn.setAttribute('aria-selected', 'false');
      }
      loadPhaseInstructions();
    } else {
      if (factoryPipelineView) factoryPipelineView.classList.add('hidden');
      if (factoryRunsView) {
        factoryRunsView.classList.remove('hidden');
        factoryRunsView.classList.add('flex');
      }
      if (factoryTabPipelineBtn) {
        factoryTabPipelineBtn.className =
          'px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 text-slate-400 hover:text-white hover:bg-slate-800';
        factoryTabPipelineBtn.setAttribute('aria-selected', 'false');
      }
      if (factoryTabRunsBtn) {
        factoryTabRunsBtn.className =
          'px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center space-x-1.5 bg-brand-600 text-white shadow-sm';
        factoryTabRunsBtn.setAttribute('aria-selected', 'true');
      }
      loadTrainingRuns();
    }
    safeCreateIcons();
  }

  if (factoryTabPipelineBtn) {
    factoryTabPipelineBtn.addEventListener('click', () => switchSubView('pipeline'));
  }
  if (factoryTabRunsBtn) {
    factoryTabRunsBtn.addEventListener('click', () => switchSubView('runs'));
  }

  // -------------------------------------------------------------
  // 2. Flowchart & Phase Prompt Inspector
  // -------------------------------------------------------------
  async function loadPhaseInstructions() {
    try {
      const res = await fetch('/api/agent_training_factory/phases/instructions');
      if (!res.ok) throw new Error(`Failed to load phase instructions (${res.status})`);
      const data = await res.json();
      phasesData = data.phases || [];
      renderFlowchart();
      renderPhaseInspector(selectedPhaseId);
    } catch (err) {
      console.error('[Factory Studio] Phase instruction error:', err);
    }
  }

  function renderFlowchart() {
    if (!factoryFlowchartContainer) return;
    factoryFlowchartContainer.innerHTML = '';

    PHASE_METADATA.forEach((meta) => {
      const pData = phasesData.find((p) => p.phase_id === meta.id) || {};
      const isCustom = Boolean(pData.is_custom);
      const isSelected = meta.id === selectedPhaseId;

      const tile = document.createElement('button');
      tile.type = 'button';
      tile.id = `factoryStageTile-${meta.id}`;
      tile.dataset.phaseId = meta.id;
      tile.className = `p-3 rounded-xl border text-left transition relative flex flex-col justify-between space-y-2 group cursor-pointer ${
        isSelected
          ? 'ring-2 ring-brand-500 border-brand-500 bg-brand-950/70 shadow-lg shadow-brand-500/20'
          : 'border-slate-800 bg-slate-950/70 hover:border-slate-700 hover:bg-slate-900/90'
      }`;

      tile.innerHTML = `
        <div class="flex items-center justify-between w-full">
          <span class="text-[10px] font-mono font-bold ${isSelected ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-400'}">${meta.num}</span>
          <div class="w-6 h-6 rounded-lg ${isSelected ? 'bg-brand-900/80 text-brand-300' : 'bg-slate-900 text-slate-400 group-hover:text-white'} flex items-center justify-center">
            <i data-lucide="${meta.icon}" class="w-3.5 h-3.5"></i>
          </div>
        </div>
        <div>
          <div class="text-xs font-bold ${isSelected ? 'text-white' : 'text-slate-300 group-hover:text-white'} truncate">${meta.name}</div>
          <div class="mt-1 flex items-center space-x-1">
            <span class="w-1.5 h-1.5 rounded-full ${isCustom ? 'bg-amber-400' : 'bg-emerald-400'}"></span>
            <span class="text-[9px] font-mono ${isCustom ? 'text-amber-300' : 'text-emerald-300'}">${isCustom ? 'Custom' : 'Default'}</span>
          </div>
        </div>
      `;

      tile.addEventListener('click', () => {
        selectedPhaseId = meta.id;
        renderFlowchart();
        renderPhaseInspector(meta.id);
      });

      factoryFlowchartContainer.appendChild(tile);
    });

    safeCreateIcons();
  }

  function renderPhaseInspector(phaseId) {
    const meta = PHASE_METADATA.find((m) => m.id === phaseId) || PHASE_METADATA[0];
    const pData = phasesData.find((p) => p.phase_id === phaseId) || {};
    const isCustom = Boolean(pData.is_custom);

    if (factoryInspectorStageTitle) {
      factoryInspectorStageTitle.textContent = `Stage ${meta.num}: ${meta.name}`;
    }

    if (factoryInspectorStageDesc) {
      factoryInspectorStageDesc.textContent = pData.description || meta.defaultDesc;
    }

    if (factoryInspectorStatusBadge) {
      factoryInspectorStatusBadge.textContent = isCustom ? 'Custom Override' : 'Platform Default';
      factoryInspectorStatusBadge.className = isCustom
        ? 'px-2.5 py-0.5 rounded-full text-[10px] font-semibold border bg-amber-950/50 border-amber-700/60 text-amber-300'
        : 'px-2.5 py-0.5 rounded-full text-[10px] font-semibold border bg-emerald-950/50 border-emerald-700/60 text-emerald-300';
    }

    if (factoryPromptLastUpdated) {
      factoryPromptLastUpdated.textContent = isCustom ? 'Custom platform override' : 'Built-in platform default';
    }

    // Context Variables Pills
    if (factoryContextVarPills) {
      factoryContextVarPills.innerHTML = '';
      const vars = pData.context_variables || [
        'target_agent_id',
        'seed_intent',
        'objectives',
        'failure_lessons',
      ];
      vars.forEach((v) => {
        const pill = document.createElement('button');
        pill.type = 'button';
        pill.className =
          'px-2 py-0.5 rounded-lg bg-slate-900 hover:bg-brand-950 border border-slate-700 hover:border-brand-500/60 text-cyan-300 font-mono text-[11px] transition shadow-sm';
        pill.textContent = `{{${v}}}`;
        pill.title = `Click to insert {{${v}}} at cursor`;
        pill.addEventListener('click', () => {
          insertContextVariable(`{{${v}}}`);
        });
        factoryContextVarPills.appendChild(pill);
      });
    }

    // System Prompt Textarea
    if (factoryPhasePromptInput) {
      factoryPhasePromptInput.value = pData.active_prompt || pData.default_prompt || '';
      updateCharCount();
    }
  }

  function insertContextVariable(token) {
    if (!factoryPhasePromptInput) return;
    const start = factoryPhasePromptInput.selectionStart || 0;
    const end = factoryPhasePromptInput.selectionEnd || 0;
    const text = factoryPhasePromptInput.value;
    factoryPhasePromptInput.value = text.substring(0, start) + token + text.substring(end);
    factoryPhasePromptInput.selectionStart = factoryPhasePromptInput.selectionEnd = start + token.length;
    factoryPhasePromptInput.focus();
    updateCharCount();
    showToast(`Inserted ${token} into prompt editor`, 'info');
  }

  function updateCharCount() {
    if (!factoryPhasePromptInput || !factoryPromptCharCount) return;
    const len = factoryPhasePromptInput.value.length;
    factoryPromptCharCount.textContent = `${len.toLocaleString()} chars`;
  }

  if (factoryPhasePromptInput) {
    factoryPhasePromptInput.addEventListener('input', updateCharCount);
  }

  // Save Custom Phase Prompt
  if (factorySavePromptBtn) {
    factorySavePromptBtn.addEventListener('click', async () => {
      if (!factoryPhasePromptInput) return;
      const promptText = factoryPhasePromptInput.value.trim();
      if (!promptText) {
        showToast('System prompt instructions cannot be empty.', 'warning');
        return;
      }

      factorySavePromptBtn.disabled = true;
      factorySavePromptBtn.textContent = 'Saving...';
      try {
        const res = await fetch(`/api/agent_training_factory/phases/${encodeURIComponent(selectedPhaseId)}/instructions`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: promptText }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        showToast(`Saved custom instructions for ${selectedPhaseId}!`, 'success');
        await loadPhaseInstructions();
      } catch (err) {
        showToast(`Failed to save prompt: ${err.message}`, 'error');
      } finally {
        factorySavePromptBtn.disabled = false;
        factorySavePromptBtn.textContent = 'Save Instructions';
        safeCreateIcons();
      }
    });
  }

  // Reset to Platform Default
  if (factoryResetPromptBtn) {
    factoryResetPromptBtn.addEventListener('click', async () => {
      factoryResetPromptBtn.disabled = true;
      try {
        const res = await fetch(`/api/agent_training_factory/phases/${encodeURIComponent(selectedPhaseId)}/instructions`, {
          method: 'DELETE',
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${res.status}`);
        }
        showToast(`Restored platform default for ${selectedPhaseId}.`, 'info');
        await loadPhaseInstructions();
      } catch (err) {
        showToast(`Failed to reset prompt: ${err.message}`, 'error');
      } finally {
        factoryResetPromptBtn.disabled = false;
        safeCreateIcons();
      }
    });
  }

  // -------------------------------------------------------------
  // 3. Training Runs & Live Monitor
  // -------------------------------------------------------------
  async function loadFactoryAgents() {
    try {
      const res = await fetch('/api/agents');
      if (res.ok) {
        allAgents = await res.json();
        populateFactoryAgentOptions(factoryAgentSelect, allAgents, activeAgentScope);
        updateNewRunButtonScope();
      }
    } catch (err) {
      console.warn('[Factory Studio] Failed to load agents list:', err);
    }
  }

  function updateNewRunButtonScope() {
    if (!factoryNewRunBtnText) return;
    if (activeAgentScope) {
      const ag = allAgents.find((a) => (a.id || a.agent_id) === activeAgentScope);
      const name = ag ? (ag.name || ag.id) : activeAgentScope;
      factoryNewRunBtnText.textContent = `Train ${name}`;
      if (factoryNewRunBtn) {
        factoryNewRunBtn.title = `Train new capabilities for ${name} in the factory`;
      }
    } else {
      factoryNewRunBtnText.textContent = 'New Training Run';
      if (factoryNewRunBtn) {
        factoryNewRunBtn.title = 'Start new training run';
      }
    }
  }

  function updateRunsStatusBadges() {
    const relevantJobs = activeAgentScope
      ? allJobs.filter((j) => String(j.target_agent_id || j.agent_id || '').toLowerCase() === activeAgentScope.toLowerCase())
      : allJobs;
    const activeJobs = relevantJobs.filter((j) => ['running', 'queued', 'waiting_approval'].includes(j.status));

    if (factoryActiveRunsBadge) {
      if (activeJobs.length > 0) {
        factoryActiveRunsBadge.textContent = String(activeJobs.length);
        factoryActiveRunsBadge.classList.remove('hidden');
      } else {
        factoryActiveRunsBadge.classList.add('hidden');
      }
    }

    if (factoryActiveStatusPill) {
      if (activeJobs.some((j) => j.status === 'waiting_approval')) {
        factoryActiveStatusPill.textContent = 'WAITING APPROVAL';
        factoryActiveStatusPill.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono border bg-amber-950/60 border-amber-700/60 text-amber-300';
      } else if (activeJobs.length > 0) {
        factoryActiveStatusPill.textContent = `${activeJobs.length} RUNNING`;
        factoryActiveStatusPill.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono border bg-brand-950/60 border-brand-700/60 text-brand-300 animate-pulse';
      } else {
        factoryActiveStatusPill.textContent = 'Ready';
        factoryActiveStatusPill.className = 'px-2 py-0.5 rounded-full text-[10px] font-mono border bg-slate-800 border-slate-700 text-slate-300';
      }
    }
  }

  async function loadAgentCapabilityGaps(agentId = '') {
    const agentBacklogList = $('agentBacklogList');
    const agentBacklogCountBadge = $('agentBacklogCountBadge');
    if (!agentBacklogList) return;

    try {
      const url = agentId
        ? `/api/agents/${encodeURIComponent(agentId)}/gaps?status=pending`
        : '/api/agents/gaps?status=pending';
      const res = await fetch(url);
      const data = res.ok ? await res.json() : {};
      const items = Array.isArray(data) ? data : (data.gaps || []);
      if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = String(items.length);
      if (!items.length) {
        agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
        return;
      }
      agentBacklogList.innerHTML = items.map((gap) => {
        const targetAgent = gap.agent_id || agentId || 'agent';
        return `
        <div class="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 space-y-1.5" data-gap-id="${escapeHtml(gap.id)}" data-agent-id="${escapeHtml(targetAgent)}">
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-1.5">
              ${!agentId ? `<span class="px-1.5 py-0.2 rounded text-[9px] font-mono bg-slate-800 text-brand-300 border border-slate-700">${escapeHtml(targetAgent)}</span>` : ''}
              <span class="text-xs font-semibold text-amber-300 font-mono">${escapeHtml(gap.identified_capability || gap.missing_capability || 'Missing Capability')}</span>
            </div>
            <div class="flex items-center space-x-1.5">
              <button type="button" class="btn-train-gap px-2 py-0.5 rounded bg-amber-600 hover:bg-amber-500 text-white text-[10px] font-semibold transition" data-gap-id="${escapeHtml(gap.id)}" data-agent-id="${escapeHtml(targetAgent)}" title="Launch training directly for this capability">⚡ Train</button>
              <button type="button" class="btn-dismiss-gap px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 text-[10px] font-medium transition" data-gap-id="${escapeHtml(gap.id)}" data-agent-id="${escapeHtml(targetAgent)}" title="Dismiss gap">Dismiss</button>
            </div>
          </div>
          ${gap.suggested_tool_name ? `<div class="text-[10px] text-slate-400 font-mono">Suggested tool: <span class="text-emerald-400">${escapeHtml(gap.suggested_tool_name)}</span></div>` : ''}
          <p class="text-[11px] text-slate-400 whitespace-pre-wrap">${escapeHtml(gap.turn_text || gap.user_prompt || '')}</p>
        </div>
      `;
      }).join('');

      agentBacklogList.querySelectorAll('.btn-train-gap').forEach((btn) => {
        btn.addEventListener('click', async (e) => {
          const gapId = e.currentTarget.dataset.gapId;
          const targetAgent = e.currentTarget.dataset.agentId || agentId;
          try {
            const trainRes = await fetch(`/api/agents/${encodeURIComponent(targetAgent)}/gaps/${encodeURIComponent(gapId)}/train`, { method: 'POST' });
            if (!trainRes.ok) throw new Error('Failed to launch training');
            showToast(`Training launched for ${targetAgent}!`, 'success');
            await loadAgentCapabilityGaps(activeAgentScope);
            await loadTrainingRuns();
          } catch (err) {
            showToast(String(err.message || err), 'error');
          }
        });
      });

      agentBacklogList.querySelectorAll('.btn-dismiss-gap').forEach((btn) => {
        btn.addEventListener('click', async (e) => {
          const gapId = e.currentTarget.dataset.gapId;
          const targetAgent = e.currentTarget.dataset.agentId || agentId;
          try {
            const delRes = await fetch(`/api/agents/${encodeURIComponent(targetAgent)}/gaps/${encodeURIComponent(gapId)}`, { method: 'DELETE' });
            if (!delRes.ok) throw new Error('Failed to dismiss gap');
            showToast('Capability gap dismissed', 'info');
            await loadAgentCapabilityGaps(activeAgentScope);
          } catch (err) {
            showToast(String(err.message || err), 'error');
          }
        });
      });
    } catch (err) {
      console.warn('[AutoReiv Factory] Failed to load capability gaps:', err);
      agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
      if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = '0';
    }
  }

  function setAgentScope(agentId) {
    activeAgentScope = String(agentId || '').trim();
    if (factoryAgentSelect) {
      factoryAgentSelect.value = activeAgentScope;
    }
    updateNewRunButtonScope();
    updateRunsStatusBadges();
    renderRunsList();
    loadAgentCapabilityGaps(activeAgentScope);
  }

  if (factoryAgentSelect) {
    factoryAgentSelect.addEventListener('change', () => {
      setAgentScope(factoryAgentSelect.value);
    });
  }

  async function loadTrainingRuns() {
    try {
      const res = await fetch('/api/agent_training_factory/jobs');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      allJobs = data.jobs || [];

      updateRunsStatusBadges();
      renderRunsList();
      await loadAgentCapabilityGaps(activeAgentScope);

      const relevantJobs = activeAgentScope
        ? allJobs.filter((j) => String(j.target_agent_id || j.agent_id || '').toLowerCase() === activeAgentScope.toLowerCase())
        : allJobs;
      const activeJobs = relevantJobs.filter((j) => ['running', 'queued', 'waiting_approval'].includes(j.status));

      if (!selectedJobId || !relevantJobs.some((j) => j.id === selectedJobId)) {
        if (relevantJobs.length > 0) {
          const active = activeJobs[0] || relevantJobs[0];
          selectedJobId = active.id;
        } else {
          selectedJobId = null;
        }
      }

      if (selectedJobId) {
        await loadJobDetails(selectedJobId);
      }
    } catch (err) {
      console.error('[Factory Studio] Runs error:', err);
    }
  }

  function renderRunsList() {
    if (!factoryRunsList) return;
    const query = factoryRunSearchInput ? factoryRunSearchInput.value : '';
    const filtered = filterJobs(allJobs, query, statusFilter, activeAgentScope);

    factoryRunsList.innerHTML = '';
    if (filtered.length === 0) {
      factoryRunsList.innerHTML = `
        <div class="p-6 text-center space-y-2 text-slate-500">
          <i data-lucide="inbox" class="w-8 h-8 mx-auto text-slate-600"></i>
          <p class="text-xs">No training runs match filter.</p>
        </div>
      `;
      safeCreateIcons();
      return;
    }

    filtered.forEach((job) => {
      const isSelected = job.id === selectedJobId;
      const card = document.createElement('div');
      card.className = `p-3 rounded-xl border transition cursor-pointer space-y-1.5 ${
        isSelected
          ? 'border-brand-500 bg-brand-950/50 shadow-md ring-1 ring-brand-500/50'
          : 'border-slate-800 bg-slate-950/60 hover:border-slate-700 hover:bg-slate-900/60'
      }`;

      let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';
      if (job.status === 'running') badgeColor = 'bg-brand-950 text-brand-300 border-brand-700 animate-pulse';
      else if (job.status === 'done') badgeColor = 'bg-emerald-950 text-emerald-300 border-emerald-700';
      else if (job.status === 'waiting_approval') badgeColor = 'bg-amber-950 text-amber-300 border-amber-700';
      else if (job.status === 'failed') badgeColor = 'bg-rose-950 text-rose-300 border-rose-700';

      const timeStr = job.created_at ? new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

      card.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-mono font-bold text-xs text-white truncate max-w-[160px]">${escapeHtml(job.target_agent_id)}</span>
          <span class="px-2 py-0.5 rounded-full text-[9px] font-mono uppercase font-semibold border ${badgeColor}">
            ${escapeHtml(job.status)}
          </span>
        </div>
        <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono">
          <span>${escapeHtml(job.id ? job.id.slice(0, 10) : '')}</span>
          <span>${escapeHtml(timeStr)}</span>
        </div>
      `;

      card.addEventListener('click', () => {
        selectedJobId = job.id;
        renderRunsList();
        loadJobDetails(job.id);

        // Mobile responsiveness: on small screens switch view to details pane
        if (typeof window !== 'undefined' && window.innerWidth < 1024) {
          if (factoryRunsListPane) factoryRunsListPane.classList.add('hidden');
          if (factoryRunDetailPane) factoryRunDetailPane.classList.remove('hidden');
        }
      });

      factoryRunsList.appendChild(card);
    });

    safeCreateIcons();
  }

  async function loadJobDetails(jobId) {
    if (!jobId) return;
    try {
      const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(jobId)}`);
      if (!res.ok) return;
      const data = await res.json();
      currentJobData = data;
      const job = data.job || {};
      const packets = data.packets || [];
      const evals = data.eval_runs || [];

      // Header
      if (factoryDetailJobBadge) {
        factoryDetailJobBadge.textContent = `${job.target_agent_id} (${job.id})`;
      }

      // Status Pill
      if (factoryDetailStatusPill) {
        const dot = factoryDetailStatusPill.querySelector('span:first-child');
        const txt = factoryDetailStatusPill.querySelector('.status-text');
        if (txt) txt.textContent = String(job.status || 'UNKNOWN').toUpperCase();
        factoryDetailStatusPill.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-semibold border flex items-center space-x-1.5';

        if (job.status === 'done') {
          factoryDetailStatusPill.classList.add('border-emerald-500/50', 'bg-emerald-950/40', 'text-emerald-300');
          if (dot) dot.className = 'w-1.5 h-1.5 rounded-full bg-emerald-400';
        } else if (job.status === 'waiting_approval') {
          factoryDetailStatusPill.classList.add('border-amber-500/50', 'bg-amber-950/40', 'text-amber-300');
          if (dot) dot.className = 'w-1.5 h-1.5 rounded-full bg-amber-400';
        } else if (job.status === 'running') {
          factoryDetailStatusPill.classList.add('border-brand-500/50', 'bg-brand-950/40', 'text-brand-300');
          if (dot) dot.className = 'w-1.5 h-1.5 rounded-full bg-brand-400 animate-ping';
        } else if (job.status === 'failed') {
          factoryDetailStatusPill.classList.add('border-rose-500/50', 'bg-rose-950/40', 'text-rose-300');
          if (dot) dot.className = 'w-1.5 h-1.5 rounded-full bg-rose-400';
        } else {
          factoryDetailStatusPill.classList.add('border-slate-700', 'bg-slate-800', 'text-slate-300');
          if (dot) dot.className = 'w-1.5 h-1.5 rounded-full bg-slate-400';
        }
      }

      // Retry Button
      if (factoryDetailRetryBtn) {
        factoryDetailRetryBtn.classList.remove('hidden');
      }

      // Stepper
      renderDetailStepper(job);

      // HITL Card
      renderDetailHitl(job, packets, evals);

      // Artifact Pills
      renderDetailArtifacts(job, packets);

      // Packets Activity Feed
      renderDetailFeed(packets);

      safeCreateIcons();
    } catch (err) {
      console.error('[Factory Studio] Job detail error:', err);
    }
  }

  function renderDetailStepper(job) {
    if (!factoryDetailStepper) return;
    factoryDetailStepper.innerHTML = '';

    const activeIdx = calculateProgressIndex(job.current_node_id, job.status);

    PHASE_METADATA.forEach((meta, idx) => {
      let state = 'idle';
      if (activeIdx >= 0) {
        if (idx < activeIdx) state = 'done';
        else if (idx === activeIdx) state = 'active';
      }

      const step = document.createElement('div');
      step.className = `p-2 rounded-xl border text-center space-y-1 transition ${
        state === 'done'
          ? 'border-emerald-500/60 bg-emerald-950/40 text-emerald-300'
          : state === 'active'
          ? 'border-brand-500 bg-brand-950/40 text-brand-300 ring-1 ring-brand-500'
          : 'border-slate-800 bg-slate-950/50 text-slate-500'
      }`;

      step.innerHTML = `
        <div class="text-[9px] font-mono">${meta.num}</div>
        <div class="font-bold text-[10px] md:text-[11px] truncate">${meta.name}</div>
        <div class="text-center py-0.5"><i data-lucide="${meta.icon}" class="w-3.5 h-3.5 mx-auto"></i></div>
      `;

      factoryDetailStepper.appendChild(step);
    });
  }

  function renderDetailHitl(job, packets, evals) {
    if (!factoryDetailHitlCard) return;
    if (job.status === 'waiting_approval') {
      factoryDetailHitlCard.classList.remove('hidden');
      if (factoryDetailHitlToolsList) {
        factoryDetailHitlToolsList.innerHTML = '';
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
          chip.className =
            'px-2 py-0.5 rounded-lg bg-emerald-900/40 border border-emerald-700/50 text-emerald-300 font-mono text-[11px]';
          chip.textContent = t;
          factoryDetailHitlToolsList.appendChild(chip);
        });
      }
    } else {
      factoryDetailHitlCard.classList.add('hidden');
    }
  }

  function renderDetailArtifacts(job, packets) {
    if (!factoryDetailArtifactPills) return;
    const artifacts = collectPacketArtifacts(packets);
    factoryDetailArtifactPills.innerHTML = '';

    if (artifacts.length === 0) {
      factoryDetailArtifactPills.innerHTML = '<span class="text-slate-500 text-[11px] italic">No authored artifacts yet.</span>';
      return;
    }

    artifacts.forEach((art, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className =
        'px-2 py-0.5 rounded-lg bg-slate-800 hover:bg-brand-900/40 border border-slate-700 hover:border-brand-500/50 text-slate-200 hover:text-brand-200 font-mono text-[11px] transition shadow-sm';
      btn.dataset.testid = `factory-artifact-pill-${idx}`;
      btn.title = 'Preview artifact from job packet';
      btn.textContent = art.path;
      btn.addEventListener('click', () => openArtifactPreviewModal(art, job.target_agent_id));
      factoryDetailArtifactPills.appendChild(btn);
    });
  }

  function openArtifactPreviewModal(art, agentId) {
    const modal = $('labArtifactPreviewModal');
    const titleEl = $('labArtifactPreviewTitle');
    const bodyEl = $('labArtifactPreviewBody');
    const pathsEl = $('labArtifactPreviewPaths');
    const noteEl = $('labArtifactPreviewNote');
    if (!modal || !art) return;

    if (titleEl) titleEl.textContent = art.path || 'Artifact';
    if (bodyEl) bodyEl.textContent = art.content || '(No inline content in packet; wiki path listed for review.)';
    if (noteEl) {
      noteEl.textContent =
        art.kind === 'wiki'
          ? 'Pre-promote: Wiki path from Grounding packet (vault staged).'
          : 'Pre-promote: content is from the job packet (staged in memory).';
    }
    if (pathsEl) {
      const expected = art.kind === 'file' ? buildExpectedPackPaths(agentId, [art.path]) : [art.path];
      pathsEl.innerHTML = '';
      expected.forEach((p) => {
        const li = document.createElement('li');
        li.className = 'font-mono text-[11px] text-emerald-300 break-all';
        li.textContent = p;
        pathsEl.appendChild(li);
      });
    }

    modal.classList.remove('hidden');
    safeCreateIcons();
  }

  function renderDetailFeed(packets) {
    if (factoryDetailPacketCount) {
      factoryDetailPacketCount.textContent = `${packets.length} packet${packets.length === 1 ? '' : 's'}`;
    }

    if (!factoryDetailPacketsFeed) return;
    if (packets.length === 0) {
      factoryDetailPacketsFeed.innerHTML = '<div class="text-slate-500 italic py-2">No activity recorded for this job yet.</div>';
      return;
    }

    factoryDetailPacketsFeed.innerHTML = '';
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
        factoryDetailPacketsFeed.appendChild(row);
      });
    });

    factoryDetailPacketsFeed.scrollTop = factoryDetailPacketsFeed.scrollHeight;
  }

  // Mobile Back Button
  if (factoryMobileBackToRunsBtn) {
    factoryMobileBackToRunsBtn.addEventListener('click', () => {
      if (factoryRunsListPane) factoryRunsListPane.classList.remove('hidden');
      if (factoryRunDetailPane) factoryRunDetailPane.classList.add('hidden');
    });
  }

  // Filter Search Input
  if (factoryRunSearchInput) {
    factoryRunSearchInput.addEventListener('input', () => {
      renderRunsList();
    });
  }

  // Status Filter Pills
  const statusPills = $queryAll('.factory-status-filter');
  statusPills.forEach((btn) => {
    btn.addEventListener('click', () => {
      statusPills.forEach((b) => {
        b.className = 'factory-status-filter px-2.5 py-1 rounded-lg font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition';
      });
      btn.className = 'factory-status-filter active px-2.5 py-1 rounded-lg font-semibold bg-brand-600 text-white transition';
      statusFilter = btn.dataset.filter || 'all';
      renderRunsList();
    });
  });

  // Copy Feed Button
  if (factoryDetailCopyFeedBtn) {
    factoryDetailCopyFeedBtn.addEventListener('click', async () => {
      const packets = currentJobData ? currentJobData.packets || [] : [];
      if (packets.length === 0) {
        showToast('No activity feed logs to copy.', 'info');
        return;
      }
      const textToCopy = formatLabActivityFeedText(packets);
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(textToCopy);
        } else {
          const ta = document.createElement('textarea');
          ta.value = textToCopy;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
        }
        if (factoryDetailCopyFeedText) {
          const original = factoryDetailCopyFeedText.textContent;
          factoryDetailCopyFeedText.textContent = 'Copied!';
          setTimeout(() => {
            if (factoryDetailCopyFeedText) factoryDetailCopyFeedText.textContent = original;
          }, 2000);
        }
        showToast('Activity feed copied to clipboard!', 'success');
      } catch (err) {
        console.error('Copy feed failed:', err);
        showToast('Failed to copy feed.', 'error');
      }
    });
  }

  // Retry Button
  if (factoryDetailRetryBtn) {
    factoryDetailRetryBtn.addEventListener('click', () => {
      if (!currentJobData) {
        showToast('No training run selected to retry.', 'warning');
        return;
      }
      populateTrainModalForRetry(currentJobData);
      const retriedAgentId = currentJobData?.inputs?.target_agent_id || currentJobData?.job?.target_agent_id || '';
      const modal = $('trainAgentHandshakeModal');
      if (modal && retriedAgentId) modal.dataset.agentId = retriedAgentId;
      updateTrainAgentLiveIndicator(
        {
          nameGroup: $('trainAgentNameGroup'),
          liveInfo: $('trainAgentLiveInfo'),
          livePackPath: $('trainAgentLivePackPath'),
          liveCounts: $('trainAgentLiveCounts'),
          liveInfoText: $('trainAgentLiveInfoText'),
          modalTitle: $('trainAgentModalTitle'),
          intentInput: $('trainSeedIntentInput'),
          seedObj: $('trainSeedObjectives'),
          targetBadge: $('trainAgentTargetBadge'),
          targetName: $('trainAgentTargetName'),
          targetIdBadge: $('trainAgentTargetIdBadge'),
        },
        retriedAgentId || '__new__',
        allAgents
      );
      if (modal) modal.classList.remove('hidden');
      safeCreateIcons();
    });
  }

  // HITL Approve Deploy
  if (factoryDetailApproveBtn) {
    factoryDetailApproveBtn.addEventListener('click', async () => {
      if (!selectedJobId) return;
      factoryDetailApproveBtn.disabled = true;
      factoryDetailApproveBtn.textContent = 'Deploying...';
      try {
        const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(selectedJobId)}/promote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'approved' }),
        });
        if (!res.ok) throw new Error('Deployment failed');
        const data = await res.json();
        showToast(`Successfully deployed ${data.agent_id} pack to live fleet!`, 'success');
        if (typeof callbacks.onReloadAgents === 'function') {
          callbacks.onReloadAgents(data.agent_id);
        }
        await loadJobDetails(selectedJobId);
        await loadTrainingRuns();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        factoryDetailApproveBtn.disabled = false;
        factoryDetailApproveBtn.textContent = 'Approve & Deploy to Fleet';
        safeCreateIcons();
      }
    });
  }

  // HITL Reject
  if (factoryDetailRejectBtn) {
    factoryDetailRejectBtn.addEventListener('click', async () => {
      if (!selectedJobId) return;
      try {
        const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(selectedJobId)}/promote`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: 'rejected' }),
        });
        if (!res.ok) throw new Error('Rejection failed');
        showToast('Training run rejected and aborted.', 'info');
        await loadJobDetails(selectedJobId);
        await loadTrainingRuns();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  // Refresh Button
  if (factoryRefreshBtn) {
    factoryRefreshBtn.addEventListener('click', () => {
      if (activeSubView === 'pipeline') {
        loadPhaseInstructions();
      } else {
        loadTrainingRuns();
      }
      showToast('Refreshed factory state.', 'info');
    });
  }

  // Conversational New Agent Pack Creator [REQ-FACT-044]
  const factoryNewAgentBtn = $('factoryNewAgentBtn');
  if (factoryNewAgentBtn) {
    factoryNewAgentBtn.addEventListener('click', () => {
      if (typeof callbacks.onStartNewAgentPack === 'function') {
        callbacks.onStartNewAgentPack();
      }
    });
  }

  // New Training Run Launcher Button [REQ-FACT-041, REQ-FACT-043]
  if (factoryNewRunBtn) {
    factoryNewRunBtn.addEventListener('click', () => {
      if (!activeAgentScope) {
        showToast('Please select an agent from the dropdown above to train.', 'warning');
        return;
      }
      const modal = $('trainAgentHandshakeModal');
      if (modal) {
        // Reset modal fields for fresh run
        const intentInput = $('trainSeedIntentInput');
        const seedObj = $('trainSeedObjectives');
        const targetLoc = $('trainTargetLocation');
        if (intentInput) intentInput.value = '';
        if (seedObj) seedObj.value = '';
        if (targetLoc) targetLoc.value = '';

        const trainAgentTargetSelect = $('trainAgentTargetSelect');
        if (trainAgentTargetSelect) {
          populateTrainAgentTargetOptions(trainAgentTargetSelect, allAgents, activeAgentScope);
        }
        modal.dataset.agentId = activeAgentScope;

        updateTrainAgentLiveIndicator(
          {
            nameGroup: $('trainAgentNameGroup'),
            liveInfo: $('trainAgentLiveInfo'),
            livePackPath: $('trainAgentLivePackPath'),
            liveCounts: $('trainAgentLiveCounts'),
            liveInfoText: $('trainAgentLiveInfoText'),
            modalTitle: $('trainAgentModalTitle'),
            intentInput: $('trainSeedIntentInput'),
            seedObj: $('trainSeedObjectives'),
            targetBadge: $('trainAgentTargetBadge'),
            targetName: $('trainAgentTargetName'),
            targetIdBadge: $('trainAgentTargetIdBadge'),
          },
          activeAgentScope,
          allAgents
        );
        modal.classList.remove('hidden');
        safeCreateIcons();
      }
    });
  }

  // -------------------------------------------------------------
  // 4. Poller & Public API
  // -------------------------------------------------------------
  function startPolling() {
    stopPolling();
    pollInterval = setInterval(() => {
      if (state.activeTab === 'factory') {
        if (activeSubView === 'runs') {
          loadTrainingRuns();
        }
      }
    }, 2500);
  }

  function stopPolling() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }

  // Global helper bridge
  if (typeof window !== 'undefined') {
    window.openFactoryStudioForAgent = (agentId) => {
      switchSubView('runs');
      setAgentScope(agentId);
      loadTrainingRuns();
    };
  }

  return {
    loadFactoryStudio: async (preferredAgentId = null) => {
      await loadFactoryAgents();
      if (preferredAgentId) {
        setAgentScope(preferredAgentId);
        switchSubView('runs');
        await loadTrainingRuns();
        const matched = allJobs.find((j) => (j.target_agent_id || j.agent_id) === preferredAgentId);
        if (matched) {
          selectedJobId = matched.id;
          await loadJobDetails(matched.id);
        }
      } else {
        if (activeSubView === 'pipeline') {
          await loadPhaseInstructions();
        } else {
          await loadTrainingRuns();
        }
      }
      startPolling();
    },
    setAgentScope,
    switchSubView,
    stopPolling,
  };
}
