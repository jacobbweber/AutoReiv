/**
 * Agent Studio: Architectural Proposals Submodule [ADR-0054, CARD-365, CARD-398]
 * Manages architectural governance proposal badges, cards, proposal inbox loading,
 * remedy application/dismissal, and autonomic scans/synthesis.
 */

import { $, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { showToast } from '../../ui/toast.js';

export function renderProposalBadgeHtml(proposalType) {
  const t = String(proposalType || '').toLowerCase();
  if (t === 'promotion_routine') {
    return `<span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide uppercase bg-emerald-950/80 text-emerald-400 border border-emerald-700/60 flex items-center space-x-1">
      <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
      <span>ROUTINE PROMOTION</span>
    </span>`;
  }
  if (t === 'tool_pruning') {
    return `<span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide uppercase bg-amber-950/80 text-amber-400 border border-amber-700/60 flex items-center space-x-1">
      <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
      <span>TOOL PRUNING</span>
    </span>`;
  }
  if (t === 'contract_reinforcement') {
    return `<span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide uppercase bg-blue-950/80 text-blue-400 border border-blue-700/60 flex items-center space-x-1">
      <span class="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
      <span>CONTRACT REINFORCEMENT</span>
    </span>`;
  }
  if (t === 'security_isolation') {
    return `<span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide uppercase bg-rose-950/80 text-rose-400 border border-rose-700/60 flex items-center space-x-1">
      <span class="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse"></span>
      <span>SECURITY ISOLATION</span>
    </span>`;
  }
  return `<span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono tracking-wide uppercase bg-purple-950/80 text-purple-400 border border-purple-700/60 flex items-center space-x-1">
    <span class="w-1.5 h-1.5 rounded-full bg-purple-400"></span>
    <span>SKILL DECOMPOSITION</span>
  </span>`;
}

export function renderProposalCardHtml(p) {
  if (!p) return '';
  const id = escapeHtml(p.id || '');
  const title = escapeHtml(p.title || 'Architectural Proposal');
  const desc = escapeHtml(p.description || '');
  const agentId = escapeHtml(p.agent_id || 'fleet');
  const impact = escapeHtml(p.impact_summary || 'Reduces autonomic overhead.');
  const badgeHtml = renderProposalBadgeHtml(p.proposal_type);
  const actionPayload = p.action_payload || {};

  let remedyDetail;
  if (p.proposal_type === 'promotion_routine') {
    remedyDetail = `Promotes polling sequence to routine '${escapeHtml(actionPayload.routine_name || 'Autonomous Task')}'.`;
  } else if (p.proposal_type === 'tool_pruning') {
    const tools = (actionPayload.prunable_tools || []).map(escapeHtml).join(', ');
    remedyDetail = `Prunes unused tools: [${tools || 'none'}].`;
  } else if (p.proposal_type === 'contract_reinforcement') {
    remedyDetail = `Injects verified anti-loop boundaries into prompt.`;
  } else if (p.proposal_type === 'security_isolation') {
    remedyDetail = `Applies strict sandboxing and credential restriction.`;
  } else {
    remedyDetail = 'Execute mechanical architectural refactor.';
  }

  return `
    <div class="p-3.5 rounded-xl bg-[#08090c] border border-white/[0.08] hover:border-amber-500/30 transition-all space-y-2.5" data-proposal-id="${id}">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div class="flex flex-wrap items-center gap-2">
          ${badgeHtml}
          <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-400 border border-slate-800">Agent: ${agentId}</span>
          <span class="text-xs font-bold text-slate-100">${title}</span>
        </div>
        <div class="flex items-center space-x-1.5">
          <button type="button" data-proposal-action="apply" data-id="${id}" class="px-2.5 py-1 rounded bg-amber-600/90 hover:bg-amber-500 text-[11px] font-semibold text-white shadow-sm flex items-center space-x-1 transition">
            <i data-lucide="check" class="w-3 h-3"></i>
            <span>Apply Remedy</span>
          </button>
          <button type="button" data-proposal-action="dismiss" data-id="${id}" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-rose-950/50 text-[11px] font-medium text-slate-300 hover:text-rose-200 border border-white/[0.08] transition">
            Dismiss
          </button>
        </div>
      </div>
      <p class="text-[11px] text-slate-300 leading-relaxed">${desc}</p>
      <div class="p-2 rounded-lg bg-amber-950/20 border border-amber-500/20 text-[11px] text-amber-200/90 flex items-start space-x-2">
        <i data-lucide="zap" class="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5"></i>
        <div>
          <span class="font-semibold text-amber-300">Autonomic Impact:</span> ${impact}
        </div>
      </div>
      <div class="text-[10px] text-slate-400 font-mono flex items-center space-x-1 pt-0.5">
        <i data-lucide="wrench" class="w-3 h-3 text-slate-500"></i>
        <span>Action Remedy: ${remedyDetail}</span>
      </div>
    </div>
  `;
}

/**
 * Loads architectural proposals for the specified agent or fleet scope.
 */
export async function loadArchitecturalProposals(agentId = null) {
  const statusEl = $('forgeProposalStatusText');
  const badgeEl = $('forgeProposalCountBadge');
  const listEl = $('forgeProposalsList');
  if (!listEl) return;
  if (statusEl) statusEl.textContent = 'Loading proposals...';
  try {
    const url = `/api/observability/architectural/proposals?status=pending${agentId ? `&agent_id=${encodeURIComponent(agentId)}` : ''}`;
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to load proposals');
    const proposals = data.proposals || [];

    if (badgeEl) {
      if (proposals.length > 0) {
        badgeEl.textContent = String(proposals.length);
        badgeEl.classList.remove('hidden');
      } else {
        badgeEl.classList.add('hidden');
      }
    }

    if (statusEl) {
      statusEl.textContent = `Pending: ${proposals.length} proposal(s)`;
    }

    if (!proposals.length) {
      listEl.innerHTML = `
        <div class="p-3 text-xs text-slate-500 italic bg-white/[0.02] border border-white/[0.04] rounded-lg text-center">
          No active architectural proposals for this scope. Click "Scan &amp; Synthesize" to audit recent telemetry.
        </div>`;
    } else {
      listEl.innerHTML = proposals.map((p) => renderProposalCardHtml(p)).join('');
      safeCreateIcons();
    }
  } catch (err) {
    if (statusEl) statusEl.textContent = `Error: ${err.message || err}`;
    listEl.innerHTML = `<div class="p-3 text-xs text-rose-400 bg-rose-950/20 border border-rose-800/30 rounded-lg">${escapeHtml(String(err.message || err))}</div>`;
  }
}

/**
 * Runs an action (apply / dismiss) on an architectural proposal.
 */
export async function runArchitecturalProposalAction(action, proposalId, getActiveAgentId = null) {
  const statusEl = $('forgeProposalStatusText');
  if (!proposalId) return;
  try {
    if (statusEl) statusEl.textContent = `${action === 'apply' ? 'Applying remedy' : 'Dismissing proposal'}...`;
    const res = await fetch(`/api/observability/architectural/proposals/${encodeURIComponent(proposalId)}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `${action} failed`);

    if (action === 'apply') {
      const msg = data.routine_name
        ? `Promoted to Routine '${data.routine_name}'!`
        : 'Proposal remedy executed successfully.';
      showToast(msg, 'success');
    } else {
      showToast('Proposal dismissed.', 'info');
    }

    const activeAgentId = typeof getActiveAgentId === 'function' ? getActiveAgentId() : null;
    await loadArchitecturalProposals(activeAgentId);
  } catch (err) {
    showToast(`Action failed: ${err.message || err}`, 'error');
    if (statusEl) statusEl.textContent = `Error: ${err.message || err}`;
  }
}

/**
 * Scans telemetry and synthesizes architectural proposals.
 */
export async function scanAndSynthesizeProposals(getActiveAgentId = null) {
  const statusEl = $('forgeProposalStatusText');
  const scanBtn = $('forgeProposalScanBtn');
  try {
    if (scanBtn) scanBtn.disabled = true;
    if (statusEl) statusEl.textContent = 'Scanning telemetry & God-Agent thresholds...';

    // 1. Trigger scan
    const scanRes = await fetch('/api/observability/architectural/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lookback_hours: 72 }),
    });
    const scanData = await scanRes.json().catch(() => ({}));
    if (!scanRes.ok) throw new Error(scanData.detail || 'Scan failed');

    // 2. Synthesize proposals
    if (statusEl) statusEl.textContent = 'Synthesizing actionable proposals...';
    const genRes = await fetch('/api/observability/architectural/proposals/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const genData = await genRes.json().catch(() => ({}));
    if (!genRes.ok) throw new Error(genData.detail || 'Proposal synthesis failed');

    const count = genData.generated_count || 0;
    showToast(`Scan complete: ${count} new proposal(s) synthesized.`, count > 0 ? 'success' : 'info');

    const activeAgentId = typeof getActiveAgentId === 'function' ? getActiveAgentId() : null;
    await loadArchitecturalProposals(activeAgentId);
  } catch (err) {
    showToast(`Scan error: ${err.message || err}`, 'error');
    if (statusEl) statusEl.textContent = `Error: ${err.message || err}`;
  } finally {
    if (scanBtn) scanBtn.disabled = false;
  }
}

/**
 * Wires architectural proposals controls and event listeners.
 */
export function setupArchitecturalProposals({
  getActiveAgentId = null,
} = {}) {
  const forgeProposalRefreshBtn = $('forgeProposalRefreshBtn');
  if (forgeProposalRefreshBtn) {
    forgeProposalRefreshBtn.addEventListener('click', () => {
      const activeAgentId = typeof getActiveAgentId === 'function' ? getActiveAgentId() : null;
      loadArchitecturalProposals(activeAgentId);
    });
  }

  const forgeProposalScanBtn = $('forgeProposalScanBtn');
  if (forgeProposalScanBtn) {
    forgeProposalScanBtn.addEventListener('click', () => {
      scanAndSynthesizeProposals(getActiveAgentId);
    });
  }

  const forgeProposalsList = $('forgeProposalsList');
  if (forgeProposalsList) {
    forgeProposalsList.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-proposal-action]');
      if (!btn) return;
      const action = btn.getAttribute('data-proposal-action');
      const id = btn.getAttribute('data-id');
      if (action && id) runArchitecturalProposalAction(action, id, getActiveAgentId);
    });
  }

  return {
    loadArchitecturalProposals,
    runArchitecturalProposalAction,
    scanAndSynthesizeProposals,
  };
}
