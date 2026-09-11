/**
 * Observability Studio Module [REQ-FE-001, REQ-WEB-005, REQ-OBS-006]
 */

import { $, $query } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { debounce } from '../utils/debounce.js';

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


export function initObservability(state, _callbacks = {}) {
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

  async function loadObservability() {
    try {
      const res = await fetch('/api/observability/kpi');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      if (kpiTotalTurns) kpiTotalTurns.textContent = data.overview.total_turns || 0;
      if (kpiTotalTokens) kpiTotalTokens.textContent = (data.overview.total_tokens || 0).toLocaleString();
      if (kpiTotalCost) {
        const cost = data.overview.estimated_cost_usd || 0;
        kpiTotalCost.textContent = `$${cost < 0.01 && cost > 0 ? cost.toFixed(4) : cost.toFixed(2)}`;
      }
      if (kpiAvgDuration) kpiAvgDuration.textContent = `${data.overview.avg_turn_duration_ms || 0} ms`;
      if (kpiAvgTtft) kpiAvgTtft.textContent = `${data.overview.avg_ttft_ms || 0} ms`;
      if (kpiErrorRate) kpiErrorRate.textContent = `${data.overview.error_rate_pct || 0}%`;

      // Render Agents table
      if (agentKpiTableBody) {
        agentKpiTableBody.innerHTML = '';
        (data.agents || []).forEach((a) => {
          const row = document.createElement('tr');
          const cost = a.estimated_cost_usd || 0;
          row.innerHTML = `
            <td class="p-2.5 font-medium text-white">${escapeHtml(a.agent_id)}</td>
            <td class="p-2.5">${a.turn_count}</td>
            <td class="p-2.5 font-mono text-indigo-400">${(a.total_tokens || 0).toLocaleString()}</td>
            <td class="p-2.5 font-mono text-amber-400">$${cost < 0.01 && cost > 0 ? cost.toFixed(4) : cost.toFixed(2)}</td>
            <td class="p-2.5">${a.tool_call_count}</td>
            <td class="p-2.5 text-rose-400">${a.error_count}</td>
            <td class="p-2.5">${a.avg_duration_ms} ms</td>
          `;
          agentKpiTableBody.appendChild(row);
        });
      }

      // Render Tools table
      if (toolKpiTableBody) {
        toolKpiTableBody.innerHTML = '';
        (data.tools || []).forEach((t) => {
          const row = document.createElement('tr');
          row.innerHTML = `
            <td class="p-2.5 font-medium text-white">${escapeHtml(t.tool_name)}</td>
            <td class="p-2.5">${t.total_invocations}</td>
            <td class="p-2.5 text-emerald-400">${t.success_count}</td>
            <td class="p-2.5 text-rose-400">${t.failure_count}</td>
            <td class="p-2.5 font-bold text-cyan-400">${t.success_rate_pct}%</td>
            <td class="p-2.5">${t.avg_duration_ms} ms</td>
          `;
          toolKpiTableBody.appendChild(row);
        });
      }

      // Also refresh logs
      await loadSystemLogs();
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

  if (refreshKpiBtn) refreshKpiBtn.addEventListener('click', loadObservability);

  // Poll logs periodically when in Observability view
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
  return kind;
}

export async function loadStandingJourney() {
  const input = $('standingJourneyJobIdInput');
  const statusEl = $('standingJourneyStatus');
  const box = $('standingJourneyTimeline');
  const jobId = input ? input.value.trim() : '';
  if (!jobId) {
    if (statusEl) statusEl.textContent = 'Enter a job_id to load the standing journey.';
    return;
  }
  if (statusEl) statusEl.textContent = `Loading standing journey for ${jobId}…`;
  if (box) box.innerHTML = '<div class="text-slate-400 italic animate-pulse">Loading journey…</div>';
  try {
    const res = await fetch(`/api/observability/standing-journey?job_id=${encodeURIComponent(jobId)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderStandingJourneyTimeline(data);
    const resumeBit = data.resumed_from_checkpoint ? '; resumed_from_checkpoint' : '';
    if (statusEl) {
      statusEl.textContent = `Loaded ${ (data.timeline || []).length } events / ${(data.spans || []).length} spans${resumeBit}`;
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = `Load failed: ${err.message || err}`;
    if (box) {
      box.innerHTML = `<div class="text-rose-300">Failed to load standing journey: ${escapeHtml(String(err.message || err))}</div>`;
    }
  }
}

export function renderStandingJourneyTimeline(data) {
  const box = $('standingJourneyTimeline');
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
