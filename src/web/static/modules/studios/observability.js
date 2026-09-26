/**
 * Observability Studio Module [REQ-FE-001, REQ-WEB-005, REQ-OBS-006]
 */

import { $, $query } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { publishAgentsLoaded } from '../state/store.js';
import { debounce } from '../utils/debounce.js';
import { showToast } from '../ui/toast.js';
import { initJourneyCanvas } from '../observability/journey_canvas.js';
import { askDeveloperWithDraft } from './tools_studio_authoring.js';
import { isToolEscalationRemedy } from './tool_escalation.js';

// CARD-520: callbacks from init (switchTab, getChatCtrl) and the rendered friction records by id.
let obsCallbacks = {};
const frictionRecsById = new Map();
const askDeveloperInFlight = new Set();

/** Standing external verifier outcomes [CARD-216]: verified | skipped_no_checker | failed */
export const VERIFY_OUTCOME_STATUSES = Object.freeze(['verified', 'skipped_no_checker', 'failed']);

export function formatVerifyStatus(status) {
  const s = String(status || '').trim();
  if (VERIFY_OUTCOME_STATUSES.includes(s)) return s;
  if (s === 'skipped') return 'skipped_no_checker';
  return s || 'skipped_no_checker';
}

/** Crash-resume operator surface [CARD-219 / REQ-RESUME-003] */
export function formatResumedFromCheckpoint(payload) {
  const data = payload || {};
  if (!data.resumed_from_checkpoint && data.resumedFromCheckpoint !== true) return '';
  const idx = data.phase_index != null ? data.phase_index : data.phaseIndex;
  const phaseBit = idx != null && idx !== '' ? ` phase ${Number(idx) + 1}` : '';
  return `Resumed (resumed_from_checkpoint${phaseBit})`;
}


/** CARD-311: omitted/nullish KPI fields stay em-dash, never fake zeros. */
export function formatKpiField(value, kind = 'number') {
  if (value == null || value === '') return '—';
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  if (kind === 'cost') {
    return `$${n < 0.01 && n > 0 ? n.toFixed(4) : n.toFixed(2)}`;
  }
  if (kind === 'ms') return `${Math.round(n)} ms`;
  if (kind === 'pct') return `${n}%`;
  return n.toLocaleString();
}

/** Unique job_ids from /api/observability/traces spans (top-level or metadata). */
export function collectUniqueJobIdsFromTraces(spans, limit = 12) {
  const ids = [];
  const seen = new Set();
  for (const s of spans || []) {
    const meta = (s && s.metadata) || {};
    const raw = (s && s.job_id) || meta.job_id || meta.jobId || '';
    const id = String(raw || '').trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    ids.push(id);
    if (ids.length >= limit) break;
  }
  return ids;
}

export function expandObsSection(name) {
  const det = $query(`#view-observability details.obs-section[data-obs-section="${name}"]`);
  if (det) det.open = true;
  return det;
}

/** Desktop tab id for Observe Studio. Operator label is "observe". [CARD-408] */
export const OBSERVE_STUDIO_TAB = 'observability';


export function initObservability(state, _callbacks = {}) {
  obsCallbacks = _callbacks || {};
  const refreshKpiBtn = $('refreshKpiBtn');
  const kpiTotalTurns = $('kpiTotalTurns');
  const kpiTotalTokens = $('kpiTotalTokens');
  const kpiTotalCost = $('kpiTotalCost');
  const kpiAvgDuration = $('kpiAvgDuration');
  const kpiAvgTtft = $('kpiAvgTtft');
  const kpiErrorRate = $('kpiErrorRate');
  const agentKpiTableBody = $('agentKpiTableBody');
  const toolKpiTableBody = $('toolKpiTableBody');

  const systemLogsTerminal = $('systemLogsTerminal');
  const logLevelSelect = $('logLevelSelect');
  const logSearchInput = $('logSearchInput');
  const logStreamToggleBtn = $('logStreamToggleBtn');
  const logStreamToggleText = $('logStreamToggleText');
  const clearLogsBtn = $('clearLogsBtn');

  const capCatResolveBtn = $('capCatResolveBtn');
  const capCatRegistryBtn = $('capCatRegistryBtn');
  if (capCatResolveBtn) capCatResolveBtn.addEventListener('click', () => { resolveCapabilityMatch(); });
  if (capCatRegistryBtn) capCatRegistryBtn.addEventListener('click', () => { loadCapabilityRegistryCapped(); });

  const standingJourneyLoadBtn = $('standingJourneyLoadBtn');
  const standingJourneyJobIdInput = $('standingJourneyJobIdInput');
  if (standingJourneyLoadBtn) {
    standingJourneyLoadBtn.addEventListener('click', () => { loadStandingJourney(); });
  }
  if (standingJourneyJobIdInput) {
    standingJourneyJobIdInput.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter') loadStandingJourney();
    });
  }

  let isLogStreamPaused = false;

  const observeAgentKpiSelect = $('observeAgentKpiSelect');
  const observeSessionSelect = $('observeSessionSelect');
  const observeGenerateReportBtn = $('observeGenerateReportBtn');
  const observeAuditContainer = $('observeAuditContainer');
  const auditTargetBadge = $('auditTargetBadge');
  const auditScaffoldBadge = $('auditScaffoldBadge');
  const auditScaffoldRatio = $('auditScaffoldRatio');
  const auditTokensBreakdown = $('auditTokensBreakdown');
  const auditTotalTokensSub = $('auditTotalTokensSub');
  const auditCost = $('auditCost');
  const auditTurnsCount = $('auditTurnsCount');
  const auditTtftSpeed = $('auditTtftSpeed');
  const auditWallClock = $('auditWallClock');
  const auditWarningsBox = $('auditWarningsBox');
  const auditBreakdownTableBody = $('auditBreakdownTableBody');

  const obsArchitecturalInboxBtn = $('obsArchitecturalInboxBtn');
  const obsArchitecturalInboxText = $('obsArchitecturalInboxText');

  async function checkArchitecturalProposalsCount() {
    if (!obsArchitecturalInboxBtn) return;
    try {
      const res = await fetch('/api/observability/architectural/proposals?status=pending&limit=100');
      if (!res.ok) return;
      const data = await res.json();
      const count = (data.proposals || []).length;
      if (count > 0) {
        obsArchitecturalInboxBtn.classList.remove('hidden');
        if (obsArchitecturalInboxText) obsArchitecturalInboxText.textContent = `Proposals (${count})`;
      } else {
        obsArchitecturalInboxBtn.classList.add('hidden');
      }
    } catch {
      // quiet fallback
    }
  }

  if (obsArchitecturalInboxBtn) {
    obsArchitecturalInboxBtn.addEventListener('click', () => {
      const tabAgents = $('tab-agents');
      if (tabAgents) tabAgents.click();
      const section = $('forgeArchitecturalSection');
      if (section) {
        section.open = true;
        section.scrollIntoView({ behavior: 'smooth' });
      }
    });
  }

  async function populateAgentKpiSelect() {
    if (!observeAgentKpiSelect) return;
    try {
      const res = await fetch('/api/agents');
      if (!res.ok) return;
      const agents = await res.json();
      publishAgentsLoaded(Array.isArray(agents) ? agents : []);
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to list agents for KPI filter:', err);
    }
  }

  function renderOverviewKpis(overview) {
    const ov = overview || {};
    if (kpiTotalTurns) kpiTotalTurns.textContent = formatKpiField(ov.total_turns);
    if (kpiTotalTokens) kpiTotalTokens.textContent = formatKpiField(ov.total_tokens);
    if (kpiTotalCost) kpiTotalCost.textContent = formatKpiField(ov.estimated_cost_usd, 'cost');
    if (kpiAvgDuration) kpiAvgDuration.textContent = formatKpiField(ov.avg_turn_duration_ms, 'ms');
    if (kpiAvgTtft) kpiAvgTtft.textContent = formatKpiField(ov.avg_ttft_ms, 'ms');
    if (kpiErrorRate) kpiErrorRate.textContent = formatKpiField(ov.error_rate_pct, 'pct');
  }

  function renderJourneyChips(ids) {
    const host = $('standingJourneyChips');
    if (!host) return;
    if (!ids.length) {
      host.innerHTML = '<span class="text-[11px] text-slate-500">No recent job_id on traces.</span>';
      return;
    }
    host.innerHTML = ids
      .map(
        (id) =>
          `<button type="button" class="standing-journey-chip px-2 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.08] text-[10px] font-mono text-indigo-300 hover:border-emerald-500/50" data-job-id="${escapeHtml(id)}">${escapeHtml(id)}</button>`,
      )
      .join('');
    host.querySelectorAll('.standing-journey-chip').forEach((btn) => {
      btn.addEventListener('click', () => {
        loadStandingJourney(btn.getAttribute('data-job-id') || '');
      });
    });
  }

  async function loadJourneyChips() {
    try {
      const res = await fetch('/api/observability/traces?limit=30');
      if (!res.ok) {
        renderJourneyChips([]);
        return;
      }
      const spans = await res.json();
      renderJourneyChips(collectUniqueJobIdsFromTraces(Array.isArray(spans) ? spans : []));
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to load journey chips:', err);
      renderJourneyChips([]);
    }
  }

  async function loadObservability() {
    try {
      await populateAgentKpiSelect();
      const agentId = observeAgentKpiSelect ? observeAgentKpiSelect.value.trim() : '';
      const url = agentId
        ? `/api/observability/kpi?agent_id=${encodeURIComponent(agentId)}`
        : '/api/observability/kpi';
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const overview = data.overview || {};
      renderOverviewKpis(overview);

      if (agentKpiTableBody) {
        agentKpiTableBody.innerHTML = '';
        let rows = Array.isArray(data.agents) ? data.agents : [];
        if (agentId) {
          rows = rows.filter((a) => String(a.agent_id || '') === agentId);
        }
        rows.forEach((a) => {
          const row = document.createElement('tr');
          row.innerHTML = `
            <td class="p-2.5 font-medium text-white">${escapeHtml(a.agent_id)}</td>
            <td class="p-2.5">${formatKpiField(a.turn_count)}</td>
            <td class="p-2.5 font-mono text-indigo-400">${formatKpiField(a.total_tokens)}</td>
            <td class="p-2.5 font-mono text-amber-400">${formatKpiField(a.estimated_cost_usd, 'cost')}</td>
            <td class="p-2.5">${formatKpiField(a.tool_call_count)}</td>
            <td class="p-2.5 text-rose-400">${formatKpiField(a.error_count)}</td>
            <td class="p-2.5">${formatKpiField(a.avg_duration_ms, 'ms')}</td>
          `;
          agentKpiTableBody.appendChild(row);
        });
        if (!rows.length) {
          const empty = document.createElement('tr');
          empty.innerHTML = '<td colspan="7" class="p-2.5 text-slate-500 italic">No agent KPI rows for this filter.</td>';
          agentKpiTableBody.appendChild(empty);
        }
      }

      if (toolKpiTableBody) {
        toolKpiTableBody.innerHTML = '';
        (data.tools || []).forEach((t) => {
          const row = document.createElement('tr');
          row.innerHTML = `
            <td class="p-2.5 font-medium text-white">${escapeHtml(t.tool_name)}</td>
            <td class="p-2.5">${formatKpiField(t.total_invocations)}</td>
            <td class="p-2.5 text-emerald-400">${formatKpiField(t.success_count)}</td>
            <td class="p-2.5 text-rose-400">${formatKpiField(t.failure_count)}</td>
            <td class="p-2.5 font-bold text-cyan-400">${formatKpiField(t.success_rate_pct, 'pct')}</td>
            <td class="p-2.5">${formatKpiField(t.avg_duration_ms, 'ms')}</td>
          `;
          toolKpiTableBody.appendChild(row);
        });
      }

      await loadSystemLogs();
      await loadJourneyChips();
      await checkArchitecturalProposalsCount();
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load observability data:', err);
    }
  }

  async function loadSystemLogs() {
    if (!systemLogsTerminal || isLogStreamPaused) return;
    try {
      const level = logLevelSelect ? logLevelSelect.value : 'ALL';
      const query = logSearchInput ? logSearchInput.value.trim() : '';
      const url = `/api/observability/logs?limit=150&level=${encodeURIComponent(level)}&query=${encodeURIComponent(query)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const logs = await res.json();

      if (!logs || logs.length === 0) {
        systemLogsTerminal.innerHTML = '<div class="text-slate-500 italic py-2">No matching logs in buffer.</div>';
        return;
      }

      const isAtBottom =
        systemLogsTerminal.scrollHeight - systemLogsTerminal.scrollTop <= systemLogsTerminal.clientHeight + 40;

      systemLogsTerminal.innerHTML = logs
        .map((l) => {
          let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';
          if (l.level === 'ERROR') badgeColor = 'bg-rose-950 text-rose-300 border-rose-800';
          else if (l.level === 'WARN' || l.level === 'WARNING')
            badgeColor = 'bg-amber-950 text-amber-300 border-amber-800';
          else if (l.level === 'INFO') badgeColor = 'bg-indigo-950 text-indigo-300 border-indigo-800';

          const timeStr = l.timestamp ? l.timestamp.split(' ')[1] || l.timestamp : '';
          return `
          <div class="flex items-start space-x-2 py-0.5 leading-relaxed hover:bg-slate-900/50 px-1 rounded transition">
            <span class="text-slate-500 text-[10px] select-none flex-shrink-0 font-mono">${escapeHtml(timeStr)}</span>
            <span class="px-1.5 py-0.2 rounded text-[10px] font-bold uppercase border flex-shrink-0 ${badgeColor}">${escapeHtml(l.level)}</span>
            <span class="text-slate-400 font-mono text-[11px] flex-shrink-0">[${escapeHtml(l.logger)}]</span>
            <span class="text-slate-200 break-all">${escapeHtml(l.message)}</span>
          </div>
        `;
        })
        .join('');

      if (isAtBottom) {
        systemLogsTerminal.scrollTop = systemLogsTerminal.scrollHeight;
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to fetch system logs:', err);
    }
  }

  if (logLevelSelect) logLevelSelect.addEventListener('change', loadSystemLogs);
  if (logSearchInput) logSearchInput.addEventListener('input', debounce(loadSystemLogs, 300));

  if (logStreamToggleBtn) {
    logStreamToggleBtn.addEventListener('click', () => {
      isLogStreamPaused = !isLogStreamPaused;
      if (logStreamToggleText) logStreamToggleText.textContent = isLogStreamPaused ? 'Resume' : 'Pause';
      logStreamToggleBtn.classList.toggle('text-emerald-400', isLogStreamPaused);
      if (!isLogStreamPaused) loadSystemLogs();
    });
  }

  if (clearLogsBtn) {
    clearLogsBtn.addEventListener('click', async () => {
      try {
        await fetch('/api/observability/logs/clear', { method: 'POST' });
        if (systemLogsTerminal)
          systemLogsTerminal.innerHTML = '<div class="text-slate-500 italic py-2">Buffer cleared.</div>';
      } catch (err) {
        console.error('[AutoReiv UI] Failed to clear logs:', err);
      }
    });
  }

  async function populateSessionSelect(agentId) {
    if (!observeSessionSelect) return;
    observeSessionSelect.innerHTML = '<option value="">Loading sessions…</option>';
    if (!agentId) {
      observeSessionSelect.innerHTML = '<option value="">Select an agent first</option>';
      if (observeAuditContainer) observeAuditContainer.classList.add('hidden');
      if (observeGenerateReportBtn) observeGenerateReportBtn.classList.add('hidden');
      return;
    }
    try {
      const res = await fetch(`/api/observability/sessions?agent_id=${encodeURIComponent(agentId)}&limit=25`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const sessions = await res.json();
      if (!Array.isArray(sessions) || !sessions.length) {
        observeSessionSelect.innerHTML = '<option value="">No recent sessions found</option>';
        if (observeAuditContainer) observeAuditContainer.classList.add('hidden');
        if (observeGenerateReportBtn) observeGenerateReportBtn.classList.add('hidden');
        return;
      }
      const opts = ['<option value="">Select a session to audit…</option>'];
      sessions.forEach((s) => {
        const title = s.title || `Session ${String(s.id).slice(0, 8)}`;
        const dateStr = s.created_at ? new Date(s.created_at).toLocaleDateString() : '';
        opts.push(`<option value="${escapeHtml(s.id)}">${escapeHtml(title)} (${escapeHtml(dateStr)})</option>`);
      });
      observeSessionSelect.innerHTML = opts.join('');
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to load agent sessions:', err);
      observeSessionSelect.innerHTML = '<option value="">Failed to load sessions</option>';
    }
  }

  async function loadSessionAudit(sessionId) {
    if (!sessionId) {
      if (observeAuditContainer) observeAuditContainer.classList.add('hidden');
      if (observeGenerateReportBtn) observeGenerateReportBtn.classList.add('hidden');
      return;
    }
    try {
      const res = await fetch(`/api/observability/audit?session_id=${encodeURIComponent(sessionId)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const report = data.report || {};
      renderAuditReport(report);
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load session audit:', err);
      showToast(err.message || 'Failed to audit session', 'error');
    }
  }

  function renderAuditReport(report) {
    if (!observeAuditContainer) return;
    observeAuditContainer.classList.remove('hidden');
    if (observeGenerateReportBtn) observeGenerateReportBtn.classList.remove('hidden');

    if (auditTargetBadge) {
      auditTargetBadge.textContent = `Session ${String(report.target_id || '').slice(0, 8)}`;
    }

    const ratio = Number(report.scaffold_ratio || 0);
    if (auditScaffoldBadge) {
      if (ratio > 10.0 || (report.warnings && report.warnings.length)) {
        auditScaffoldBadge.className = 'px-2.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20';
        auditScaffoldBadge.textContent = 'High Harness Tax';
      } else {
        auditScaffoldBadge.className = 'px-2.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
        auditScaffoldBadge.textContent = 'Normal Overhead';
      }
    }

    if (auditScaffoldRatio) auditScaffoldRatio.textContent = `${ratio.toFixed(1)}x`;
    if (auditTokensBreakdown) {
      auditTokensBreakdown.textContent = `${(report.total_prompt_tokens || 0).toLocaleString()} / ${(report.total_completion_tokens || 0).toLocaleString()}`;
    }
    if (auditTotalTokensSub) {
      auditTotalTokensSub.textContent = `Total: ${(report.total_tokens || 0).toLocaleString()} tok`;
    }
    if (auditCost) auditCost.textContent = formatKpiField(report.estimated_cost_usd, 'cost');
    if (auditTurnsCount) auditTurnsCount.textContent = `Turns: ${report.total_turns || 0}`;
    if (auditTtftSpeed) {
      const ttft = report.avg_ttft_ms != null ? `${Math.round(report.avg_ttft_ms)}ms` : '—';
      const tps = report.avg_tps != null ? `${Number(report.avg_tps).toFixed(1)} tok/s` : '—';
      auditTtftSpeed.textContent = `${ttft} | ${tps}`;
    }
    if (auditWallClock) {
      auditWallClock.textContent = `Wall-Clock: ${((report.total_wall_clock_ms || 0) / 1000).toFixed(2)}s`;
    }

    if (auditWarningsBox) {
      const warnings = report.warnings || [];
      if (warnings.length) {
        auditWarningsBox.classList.remove('hidden');
        auditWarningsBox.innerHTML = warnings.map((w) => `<div>⚠️ ${escapeHtml(w)}</div>`).join('');
      } else {
        auditWarningsBox.classList.add('hidden');
        auditWarningsBox.innerHTML = '';
      }
    }

    if (auditBreakdownTableBody) {
      auditBreakdownTableBody.innerHTML = '';
      const breakdown = report.token_breakdown || {};
      const percentages = report.token_percentages || {};
      const componentLabels = [
        { key: 'user_prompt', label: 'User Prompt', cat: 'User Input', class: 'text-indigo-300' },
        { key: 'agent_persona', label: 'Agent Persona & Constitution', cat: 'Harness', class: 'text-slate-300' },
        { key: 'tool_schemas', label: 'Tool Function JSON Schemas', cat: 'Harness Bloat', class: 'text-rose-400 font-semibold' },
        { key: 'progressive_skills', label: 'Progressive Skills Injected', cat: 'Harness', class: 'text-cyan-300' },
        { key: 'episodic_memory', label: 'Episodic Memory Recalled', cat: 'Context', class: 'text-amber-300' },
        { key: 'compacted_history', label: 'Prior Conversation History', cat: 'Context', class: 'text-slate-400' },
        { key: 'tool_results_injected', label: 'Tool Output Dumps', cat: 'Working Data', class: 'text-blue-300' },
        { key: 'completion', label: 'Model Completion Output', cat: 'Completion', class: 'text-emerald-300' },
        { key: 'reasoning', label: 'Reasoning (<think>) Tokens', cat: 'Completion', class: 'text-purple-300' },
      ];

      componentLabels.forEach((c) => {
        const val = breakdown[c.key];
        if (val == null || val === 0) return;
        const pct = percentages[c.key] != null ? `${Number(percentages[c.key]).toFixed(1)}%` : '—';
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="p-2 ${c.class}">${escapeHtml(c.label)}</td>
          <td class="p-2 text-right font-mono">${formatKpiField(val)}</td>
          <td class="p-2 text-right font-mono text-slate-400">${pct}</td>
          <td class="p-2 text-slate-500 font-mono text-[10px]">${escapeHtml(c.cat)}</td>
        `;
        auditBreakdownTableBody.appendChild(tr);
      });
    }
  }

  async function exportAuditReportToInbox() {
    const sessionId = observeSessionSelect ? observeSessionSelect.value.trim() : '';
    if (!sessionId) {
      showToast('Select a session before generating a report', 'warning');
      return;
    }
    try {
      if (observeGenerateReportBtn) {
        observeGenerateReportBtn.disabled = true;
        observeGenerateReportBtn.innerHTML = '<i data-lucide="loader" class="w-3.5 h-3.5 animate-spin"></i><span>Exporting…</span>';
      }
      const res = await fetch('/api/observability/audit/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success) {
        showToast(`Audit report saved to 00_Inbox: ${data.filename || ''}`, 'success');
      } else {
        showToast(data.error || 'Failed to export report', 'error');
      }
    } catch (err) {
      console.error('[AutoReiv UI] Export audit failed:', err);
      showToast(err.message || 'Export failed', 'error');
    } finally {
      if (observeGenerateReportBtn) {
        observeGenerateReportBtn.disabled = false;
        observeGenerateReportBtn.innerHTML = '<i data-lucide="file-text" class="w-3.5 h-3.5"></i><span>Generate Report to Inbox</span>';
        if (window.lucide) window.lucide.createIcons();
      }
    }
  }

  if (refreshKpiBtn) refreshKpiBtn.addEventListener('click', loadObservability);
  if (observeAgentKpiSelect) {
    observeAgentKpiSelect.addEventListener('change', () => {
      loadObservability();
      populateSessionSelect(observeAgentKpiSelect.value.trim());
    });
  }
  if (observeSessionSelect) {
    observeSessionSelect.addEventListener('change', () => {
      loadSessionAudit(observeSessionSelect.value.trim());
    });
  }
  if (observeGenerateReportBtn) {
    observeGenerateReportBtn.addEventListener('click', exportAuditReportToInbox);
  }

  const runFrictionAuditBtn = $('runFrictionAuditBtn');
  if (runFrictionAuditBtn) {
    runFrictionAuditBtn.addEventListener('click', runFrictionAudit);
  }
  const frictionList = $('frictionRecommendationsList');
  if (frictionList) {
    frictionList.addEventListener('click', (e) => handleFrictionAction(e));
  }
  loadFrictionRecommendations();
  checkArchitecturalProposalsCount();
  const journeyCanvas = initJourneyCanvas(state, _callbacks);

  setInterval(() => {
    const activeTab = $query('.tab-view:not(.hidden)');
    if (activeTab && activeTab.id === 'view-observability' && !isLogStreamPaused) {
      loadSystemLogs();
    }
  }, 2500);

  return {
    loadObservability,
    loadSystemLogs,
    loadStandingJourney,
    loadFrictionRecommendations,
    runFrictionAudit,
    journeyCanvas,
  };
}



/** Capability Catalog C [CARD-217] — Observability match panel (subset only). */
function renderCapabilityRows(tbody, entries) {
  if (!tbody) return;
  tbody.innerHTML = '';
  const rows = Array.isArray(entries) ? entries : [];
  if (!rows.length) {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td colspan="6" class="p-2.5 text-slate-500 italic">No matches.</td>';
    tbody.appendChild(tr);
    return;
  }
  rows.forEach((e) => {
    const tr = document.createElement('tr');
    const kws = Array.isArray(e.keywords) ? e.keywords.join(', ') : '';
    tr.innerHTML = `
      <td class="p-2.5 font-mono text-indigo-300">${escapeHtml(e.kind || '')}</td>
      <td class="p-2.5 font-medium text-white">${escapeHtml(e.name || e.id || '')}</td>
      <td class="p-2.5">${escapeHtml(e.trust_tier || '')}</td>
      <td class="p-2.5">${escapeHtml(e.risk_level || '')}</td>
      <td class="p-2.5">${e.requires_hitl ? 'yes' : 'no'}</td>
      <td class="p-2.5 text-slate-400">${escapeHtml(kws)}</td>
    `;
    tbody.appendChild(tr);
  });
}

async function resolveCapabilityMatch() {
  const intentEl = $('capCatIntentInput');
  const roleEl = $('capCatRoleInput');
  const statusEl = $('capCatStatus');
  const body = $('capCatResultsBody');
  const intent = intentEl ? intentEl.value.trim() : '';
  const role = roleEl ? roleEl.value.trim() : '';
  if (statusEl) statusEl.textContent = 'Resolving subset…';
  try {
    const res = await fetch('/api/capabilities/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intent, role: role || null, limit: 12 }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderCapabilityRows(body, data.matched || []);
    if (statusEl) {
      statusEl.textContent = `Matched ${data.count || 0} of ${data.total_indexed || 0} (subset_only=${data.subset_only !== false}` +
        (data.miss ? '; miss/fail-closed' : '') + ')';
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = `Resolve failed: ${err.message || err}`;
  }
}

async function loadCapabilityRegistryCapped() {
  const statusEl = $('capCatStatus');
  const body = $('capCatResultsBody');
  if (statusEl) statusEl.textContent = 'Loading capped operator registry…';
  try {
    const res = await fetch('/api/capabilities/registry?limit=25');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderCapabilityRows(body, data.entries || []);
    if (statusEl) {
      statusEl.textContent = `Registry view ${data.count || 0}/${data.total_indexed || 0} (operator_view; prompt_dump_forbidden=${data.prompt_dump_forbidden !== false})`;
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = `Registry failed: ${err.message || err}`;
  }
}



/** Standing journey timeline by job_id [CARD-227 / REQ-SJURN-*]. */
export function formatStandingJourneyEvent(ev) {
  const e = ev || {};
  const kind = String(e.kind || 'event');
  if (kind === 'resumed_from_checkpoint') return 'Resumed (resumed_from_checkpoint)';
  if (kind === 'a2a_child') return `A2A child_job_id=${e.child_job_id || ''}`;
  if (kind === 'policy_decision') {
    const mcp = (e.mcp || String(e.tool_name || '').startsWith('mcp_')) ? ' MCP' : '';
    return `Policy ${e.verdict || ''}${mcp}: ${e.tool_name || ''}`;
  }
  if (kind === 'catalog_match') {
    const ids = Array.isArray(e.matched_capability_ids) ? e.matched_capability_ids.join(', ') : '';
    return `Catalog matches: ${ids}`;
  }
  if (kind === 'verifier_status') return `Verifier: ${e.verifier_status || ''} (phase ${e.phase_index})`;
  if (kind === 'phase') return `Phase ${e.phase_index}: ${e.name || ''} [${e.status || ''}]`;
  if (kind === 'job' || kind === 'job_created') return `Job ${e.job_id || ''}: ${e.goal || ''}`;
  if (kind === 'skill_studio_authoring_packet') {
    const payload = e.payload || {};
    const blockers = payload.blocker_count != null ? payload.blocker_count : 0;
    return `Skill Studio ${payload.intent || 'build'} packet for ${payload.skill_id || 'skill'} (${blockers} lint blockers)`;
  }
  if (kind === 'skill_studio_authoring_proposal') {
    const count = e.payload && e.payload.patch_count != null ? e.payload.patch_count : 0;
    return `Developer proposed ${count} field patch(es)`;
  }
  if (kind === 'skill_studio_authoring_decision') {
    const decision = (e.payload && e.payload.decision) || 'decision';
    return `Operator ${decision} (draft only; Save still writes the skill)`;
  }
  return kind;
}

function observeJobViewer(opts = {}) {
  const has = (key) => Object.prototype.hasOwnProperty.call(opts, key);
  return {
    input: has('inputEl') ? opts.inputEl : $('standingJourneyJobIdInput'),
    statusEl: has('statusEl') ? opts.statusEl : $('standingJourneyStatus'),
    box: has('timelineEl') ? opts.timelineEl : $('standingJourneyTimeline'),
  };
}

/**
 * Fill the Observe job search and load the standing journey.
 * Missing or failed jobs stay in the viewer; this does not throw.
 * [CARD-408 / REQ-408-003 / REQ-408-004]
 * @param {string} [jobId]
 * @param {{ inputEl?: HTMLInputElement|null, statusEl?: HTMLElement|null, timelineEl?: HTMLElement|null, fetchFn?: Function, expand?: boolean }} [opts]
 */
export async function inspectObserveJob(jobId, opts = {}) {
  const { input, statusEl, box } = observeJobViewer(opts);
  const fetchFn = typeof opts.fetchFn === 'function' ? opts.fetchFn : (...args) => fetch(...args);
  const explicit = jobId == null ? '' : String(jobId).trim();
  if (explicit && input) input.value = explicit;
  const id = explicit || (input && input.value ? String(input.value).trim() : '');
  if (!id) {
    if (statusEl) statusEl.textContent = 'Enter a job_id to load the standing journey.';
    return { ok: false, reason: 'missing_job_id', jobId: '' };
  }
  if (opts.expand !== false) {
    try {
      const section = expandObsSection('journey');
      if (section && typeof section.scrollIntoView === 'function') {
        section.scrollIntoView({ block: 'nearest' });
      }
    } catch (err) {
      console.warn('[AutoReiv UI] Observe journey section expand failed:', err);
    }
  }
  if (statusEl) statusEl.textContent = `Loading standing journey for ${id}…`;
  if (box) box.innerHTML = '<div class="text-slate-400 italic animate-pulse">Loading journey…</div>';
  try {
    const res = await fetchFn(`/api/observability/standing-journey?job_id=${encodeURIComponent(id)}`);
    if (!res || !res.ok) {
      const status = res && res.status != null ? res.status : 'error';
      let detail = '';
      if (res && typeof res.json === 'function') {
        try {
          const body = await res.json();
          const msg = body && (body.detail || body.message);
          if (msg) detail = `: ${typeof msg === 'string' ? msg : JSON.stringify(msg)}`;
        } catch {
          /* non-JSON error body */
        }
      }
      throw new Error(`HTTP ${status}${detail}`);
    }
    const data = await res.json();
    renderStandingJourneyTimeline(data, box);
    const resumeBit = data && data.resumed_from_checkpoint ? '; resumed_from_checkpoint' : '';
    const events = (data && data.timeline) || [];
    const spans = (data && data.spans) || [];
    if (statusEl) {
      statusEl.textContent = `Loaded ${events.length} events / ${spans.length} spans${resumeBit}`;
    }
    return { ok: true, jobId: id, eventCount: events.length };
  } catch (err) {
    const message = err && err.message ? err.message : String(err);
    if (statusEl) statusEl.textContent = `Load failed: ${message}`;
    if (box) {
      box.innerHTML = `<div class="text-rose-300">Failed to load standing journey: ${escapeHtml(message)}</div>`;
    }
    return { ok: false, jobId: id, error: message };
  }
}

/** Load standing journey from the search input, or from an explicit job id. */
export function loadStandingJourney(jobIdOverride) {
  return inspectObserveJob(jobIdOverride);
}

/**
 * Open or focus Observe Studio and inspect `jobId`.
 * Blank ids do not switch studios. [CARD-408]
 * @param {string} jobId
 * @param {{ switchTab?: Function, fetchFn?: Function, inputEl?: HTMLInputElement|null, statusEl?: HTMLElement|null, timelineEl?: HTMLElement|null }} [opts]
 */
export function openObserveJob(jobId, opts = {}) {
  const id = String(jobId || '').trim();
  if (!id) {
    return Promise.resolve({
      ok: false,
      reason: 'missing_job_id',
      studio: 'observe',
      tab: OBSERVE_STUDIO_TAB,
      jobId: '',
    });
  }
  if (typeof opts.switchTab === 'function') {
    opts.switchTab(OBSERVE_STUDIO_TAB);
  }
  return inspectObserveJob(id, opts).then((result) => ({
    studio: 'observe',
    tab: OBSERVE_STUDIO_TAB,
    ...result,
    jobId: id,
  }));
}

export function renderStandingJourneyTimeline(data, boxOverride) {
  const box = boxOverride !== undefined ? boxOverride : $('standingJourneyTimeline');
  if (!box) return;
  const timeline = (data && data.timeline) || [];
  if (!timeline.length) {
    box.innerHTML = '<div class="text-slate-500 italic">No standing journey events for this job_id.</div>';
    return;
  }
  const resumeBadge = data.resumed_from_checkpoint
    ? '<span class="px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 text-[10px] font-bold uppercase">resumed_from_checkpoint</span>'
    : '';
  const childBit = (data.child_job_ids || []).length
    ? `<div class="text-[10px] text-indigo-300 mb-2">child_job_ids: ${escapeHtml((data.child_job_ids || []).join(', '))}</div>`
    : '';
  const rows = timeline
    .map((e) => {
      let color = 'border-slate-700 text-slate-300';
      const kind = String(e.kind || '');
      if (kind === 'resumed_from_checkpoint') color = 'border-amber-700 text-amber-300';
      else if (kind === 'policy_decision' && e.verdict === 'BLOCK') color = 'border-rose-700 text-rose-300';
      else if (kind === 'a2a_child') color = 'border-indigo-700 text-indigo-300';
      else if (kind === 'catalog_match') color = 'border-cyan-700 text-cyan-300';
      else if (kind === 'verifier_status') color = 'border-emerald-700 text-emerald-300';
      const label = formatStandingJourneyEvent(e);
      const ts = e.ts ? String(e.ts).replace('T', ' ').slice(0, 19) : '';
      return `<div class="flex items-start gap-2 px-1.5 py-1 rounded border ${color} bg-slate-900/40">
        <span class="text-slate-500 text-[10px] font-mono flex-shrink-0 w-28">${escapeHtml(ts)}</span>
        <span class="text-[10px] uppercase font-bold flex-shrink-0 w-28">${escapeHtml(kind)}</span>
        <span class="break-all">${escapeHtml(label)}</span>
      </div>`;
    })
    .join('');
  box.innerHTML = `<div class="flex items-center gap-2 mb-2">${resumeBadge}<span class="text-[10px] text-slate-400 font-mono">trace_id=${escapeHtml(data.job_id || '')}</span></div>${childBit}${rows}`;
}

export async function loadFrictionRecommendations() {
  const listEl = $('frictionRecommendationsList');
  if (!listEl) return;
  try {
    const res = await fetch('/api/observability/friction/recommendations');
    if (!res.ok) return;
    const recs = await res.json();
    renderFrictionRecommendations(recs);
  } catch (err) {
    console.warn('[AutoReiv UI] Failed to load friction recommendations:', err);
  }
}

export function renderFrictionRecommendations(recs) {
  const listEl = $('frictionRecommendationsList');
  if (!listEl) return;
  if (!Array.isArray(recs) || recs.length === 0) {
    listEl.innerHTML = '<div class="text-xs text-slate-500 italic p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">No active runbook recommendations. Run an audit to inspect telemetry.</div>';
    return;
  }

  frictionRecsById.clear();
  const items = recs.map((r) => {
    frictionRecsById.set(String(r.id), r);
    const isApplied = r.status === 'applied';
    const isDismissed = r.status === 'dismissed';
    const isEscalated = r.status === 'escalated';
    const isToolFix = isToolEscalationRemedy(r.remedy_kind);
    let badgeColor = 'bg-amber-950/80 text-amber-300 border-amber-800';
    if (isApplied || isEscalated) {
      badgeColor = 'bg-emerald-950/80 text-emerald-300 border-emerald-800';
    } else if (isDismissed) {
      badgeColor = 'bg-slate-800 text-slate-400 border-slate-700';
    }

    const remedyBadge = isToolFix
      ? '<span class="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold bg-purple-950/80 text-purple-300 border border-purple-800">Needs a tool</span>'
      : '<span class="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-800">Runbook SOP Patch</span>';

    const dismissBtn = `
        <button type="button" class="dismiss-friction-btn px-2 py-1 rounded bg-white/[0.04] hover:bg-white/[0.08] text-xs font-medium text-slate-400 transition" data-rec-id="${escapeHtml(r.id)}">
          <span>Dismiss</span>
        </button>`;
    let actions;
    if (isEscalated) {
      actions = '<span class="text-xs font-mono text-emerald-300">Asked Developer</span>';
    } else if (isApplied || isDismissed) {
      actions = `<span class="text-xs font-mono text-slate-400 capitalize">${escapeHtml(r.status)}</span>`;
    } else if (isToolFix) {
      actions = `
        <button type="button" class="ask-developer-friction-btn px-2.5 py-1 rounded bg-purple-600 hover:bg-purple-500 text-xs font-medium text-white transition flex items-center space-x-1" data-rec-id="${escapeHtml(r.id)}">
          <span>Ask Developer</span>
        </button>${dismissBtn}
      `;
    } else {
      actions = `
        <button type="button" class="apply-friction-btn px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-xs font-medium text-white transition flex items-center space-x-1" data-rec-id="${escapeHtml(r.id)}">
          <span>Apply Patch</span>
        </button>${dismissBtn}
      `;
    }
    const target = isToolFix
      ? `Tool: ${escapeHtml(r.tool_name || 'unknown')} (Agent: ${escapeHtml(r.agent_id || 'autoreiv')})`
      : `Target: ${escapeHtml(r.skill_path || 'unknown')} (Agent: ${escapeHtml(r.agent_id || 'autoreiv')})`;

    return `
      <div class="p-3.5 rounded-xl bg-[#12151e]/90 border border-white/[0.08] space-y-2 shadow-sm" data-rec-id="${escapeHtml(r.id)}">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center space-x-2">
            <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${badgeColor}">${escapeHtml(r.friction_type)}</span>
            ${remedyBadge}
            <span class="text-xs font-bold text-white">${escapeHtml(r.summary)}</span>
          </div>
          <div class="flex items-center space-x-2">
            ${actions}
          </div>
        </div>
        <div class="text-xs text-slate-300 font-mono bg-black/40 p-2.5 rounded-lg border border-white/[0.04] whitespace-pre-wrap">${escapeHtml(r.proposed_patch)}</div>
        <div class="flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <span>${target}</span>
          <span>${escapeHtml(r.created_at || '')}</span>
        </div>
      </div>
    `;
  }).join('');

  listEl.innerHTML = items;
}

export async function runFrictionAudit() {
  const statusEl = $('frictionAuditStatus');
  const lookbackSelect = $('frictionLookbackSelect');
  const hours = lookbackSelect ? parseInt(lookbackSelect.value, 10) || 24 : 24;

  if (statusEl) statusEl.textContent = `Auditing telemetry for trailing ${hours}h…`;
  try {
    const res = await fetch('/api/observability/friction/audit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lookback_hours: hours }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (statusEl) {
      statusEl.textContent = `Audit completed: ${data.incidents_count || 0} friction incidents, ${data.recommendations_count || 0} recommendations staged.`;
    }
    renderFrictionRecommendations(data.recommendations || []);
    showToast(`Friction audit complete: ${data.recommendations_count || 0} recommendations staged.`, 'success');
  } catch (err) {
    if (statusEl) statusEl.textContent = `Audit failed: ${err.message || err}`;
    showToast(`Audit failed: ${err.message || err}`, 'error');
  }
}

/** Developer draft for a tool escalation: the tool, its payload and where it came from [CARD-520 REQ-520-008]. */
export function buildFrictionDeveloperDraft(rec = {}) {
  const tool = String(rec.tool_name || '').trim();
  const size = rec.payload_bytes ? `${rec.payload_bytes} bytes` : 'too many bytes';
  const where = [rec.session_id ? `in session ${rec.session_id}` : '', rec.agent_id ? `(agent ${rec.agent_id})` : '']
    .filter(Boolean).join(' ');
  return {
    intent: 'modify',
    tool_name: tool,
    behavior: `Add pagination or a filter (limit/offset or a query) so ${tool} stays under 8 KB; it returned ${size}${where ? ` ${where}` : ''}.`,
    target_agent_id: rec.agent_id || 'autoreiv',
  };
}

async function askDeveloperAboutFriction(btn, recId, callbacks) {
  if (askDeveloperInFlight.has(recId)) return;
  askDeveloperInFlight.add(recId);
  btn.disabled = true;
  try {
    const rec = frictionRecsById.get(String(recId)) || { id: recId };
    const plan = await askDeveloperWithDraft(buildFrictionDeveloperDraft(rec), {
      intent: 'modify',
      fetchFn: (...args) => fetch(...args),
      switchTab: callbacks.switchTab,
      getChatCtrl: typeof callbacks.getChatCtrl === 'function' ? callbacks.getChatCtrl : () => null,
    });
    const res = await fetch(`/api/observability/friction/recommendations/${encodeURIComponent(recId)}/escalate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ developer_session_id: plan.sessionId }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      showToast(`Developer chat opened, but the card was not marked: ${body.detail || `HTTP ${res.status}`}`, 'warning');
    }
    loadFrictionRecommendations();
  } catch (err) {
    showToast(`Could not open a Developer chat: ${err.message || err}`, 'error');
    btn.disabled = false;
  } finally {
    askDeveloperInFlight.delete(recId);
  }
}

export async function handleFrictionAction(e, callbacks = obsCallbacks) {
  const askBtn = e.target.closest('.ask-developer-friction-btn');
  if (askBtn) {
    const recId = askBtn.dataset.recId;
    if (recId) await askDeveloperAboutFriction(askBtn, recId, callbacks || {});
    return;
  }

  const applyBtn = e.target.closest('.apply-friction-btn');
  if (applyBtn) {
    const recId = applyBtn.dataset.recId;
    if (!recId) return;
    applyBtn.disabled = true;
    try {
      const res = await fetch(`/api/observability/friction/recommendations/${encodeURIComponent(recId)}/apply`, {
        method: 'POST',
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === 'string' && body.detail ? body.detail : `HTTP ${res.status}`);
      }
      showToast('Runbook patch applied to SKILL.md.', 'success');
      loadFrictionRecommendations();
    } catch (err) {
      showToast(err.message || String(err), 'error');
      applyBtn.disabled = false;
    }
    return;
  }

  const dismissBtn = e.target.closest('.dismiss-friction-btn');
  if (dismissBtn) {
    const recId = dismissBtn.dataset.recId;
    if (!recId) return;
    dismissBtn.disabled = true;
    try {
      const res = await fetch(`/api/observability/friction/recommendations/${encodeURIComponent(recId)}/dismiss`, {
        method: 'POST',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showToast('Recommendation dismissed.', 'info');
      loadFrictionRecommendations();
    } catch (err) {
      showToast(`Failed to dismiss: ${err.message || err}`, 'error');
      dismissBtn.disabled = false;
    }
  }
}

