/**
 * Observability Session Harness Audit & Capability Catalog Panels [CARD-716].
 */

import { $, escapeHtml } from '../dom.js';
import { showToast } from '../ui/toast.js';

/** CARD-311: omitted/nullish KPI fields stay em-dash, never fake zeros. */
export function formatKpiField(value, kind = 'number') {
  if (value == null || value === '') return '—';
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  if (kind === 'cost') {
    return `$${n < 0.01 && n > 0 ? n.toFixed(4) : n.toFixed(2)}`;
  }
  if (kind === 'ms') return `${Math.round(n)} ms`;
  if (kind === 'pct' || kind === 'percent') return `${n}%`;
  return n.toLocaleString();
}

export async function populateSessionSelectEl(agentId, { observeSessionSelect, observeAuditContainer, observeGenerateReportBtn }) {
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

export async function loadSessionAuditData(sessionId, els) {
  const { observeAuditContainer, observeGenerateReportBtn } = els;
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
    renderAuditReportDom(report, els);
  } catch (err) {
    console.error('[AutoReiv UI] Failed to load session audit:', err);
    showToast(err.message || 'Failed to audit session', 'error');
  }
}

export function renderAuditReportDom(report, els) {
  const {
    observeAuditContainer,
    observeGenerateReportBtn,
    auditTargetBadge,
    auditScaffoldBadge,
    auditScaffoldRatio,
    auditTokensBreakdown,
    auditTotalTokensSub,
    auditCost,
    auditTurnsCount,
    auditTtftSpeed,
    auditWallClock,
    auditWarningsBox,
    auditBreakdownTableBody,
  } = els;
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

export async function exportAuditReportToInboxEl({ observeSessionSelect, observeGenerateReportBtn }) {
  const sessionId = observeSessionSelect ? observeSessionSelect.value.trim() : '';
  if (!sessionId) {
    showToast('Select a session before generating a report', 'warning');
    return;
  }
  try {
    if (observeGenerateReportBtn) {
      observeGenerateReportBtn.disabled = true;
      observeGenerateReportBtn.innerHTML = '<i data-lucide="loader" class="w-3.5 h-3.5 animate-spin"></i><span>Exporting…</span>';
      if (typeof window !== 'undefined' && window.lucide) window.lucide.createIcons();
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
      if (typeof window !== 'undefined' && window.lucide) window.lucide.createIcons();
    }
  }
}

/** Capability Catalog C [CARD-217] — Observability match panel (subset only). */
export function renderCapabilityRows(tbody, entries) {
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

export async function resolveCapabilityMatch() {
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
      statusEl.textContent =
        `Matched ${data.count || 0} of ${data.total_indexed || 0} (subset_only=${data.subset_only !== false}` +
        (data.miss ? '; miss/fail-closed' : '') +
        ')';
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = `Resolve failed: ${err.message || err}`;
  }
}

export async function loadCapabilityRegistryCapped() {
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
