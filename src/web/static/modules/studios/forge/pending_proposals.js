/**
 * Agent Studio: pending capability proposals for this agent [CARD-539, ADR-0061 rule 8].
 * An agent grows only when Jacob accepts: "attach tool T to skill S". Accept ticks the skill.
 */

import { escapeHtml } from '../../utils/formatters.js';

export const ATTACH_TOOL_PROPOSAL = 'attach_tool_to_skill';

export function attachProposals(rows) {
  return (Array.isArray(rows) ? rows : []).filter((r) => r && r.tool_name === ATTACH_TOOL_PROPOSAL);
}

export function renderPendingProposalsHtml(rows) {
  const items = attachProposals(rows);
  if (!items.length) return '';
  const cards = items.map((r) => {
    const a = r.arguments || {};
    const what = a.new_skill
      ? `New skill <strong>${escapeHtml(a.skill_id)}</strong> with tool <code>${escapeHtml(a.tool)}</code>`
      : `Attach <code>${escapeHtml(a.tool)}</code> to skill <strong>${escapeHtml(a.skill_id)}</strong>`;
    const id = escapeHtml(r.id);
    return `
      <div class="p-2.5 rounded-lg bg-amber-950/20 border border-amber-800/40 space-y-1.5" data-proposal-row="${id}">
        <div class="text-[11px] text-slate-200">${what}</div>
        ${a.description ? `<div class="text-[10px] text-slate-400">${escapeHtml(a.description)}</div>` : ''}
        <div class="flex items-center gap-2">
          <button type="button" data-attach-decision="APPROVED" data-id="${id}" class="px-2 py-0.5 rounded bg-emerald-700 hover:bg-emerald-600 text-white text-[11px] font-semibold">Accept</button>
          <button type="button" data-attach-decision="REJECTED" data-id="${id}" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-rose-900 text-slate-200 text-[11px]">Reject</button>
          <span class="text-[10px] text-slate-400" data-attach-status></span>
        </div>
      </div>`;
  }).join('');
  return `<div class="text-[11px] font-semibold text-amber-200">Pending proposals (${items.length})</div>${cards}`;
}

export async function decideAttachProposal(approvalId, decision, fetchImpl = fetch) {
  const res = await fetchImpl(`/api/approvals/${encodeURIComponent(approvalId)}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `HTTP ${res.status}`);
  return body;
}

export async function loadPendingProposals(agentId, host, { fetchImpl = fetch, onChanged } = {}) {
  if (!host || !agentId) return [];
  let rows;
  try {
    const res = await fetchImpl(`/api/approvals/pending?agent_id=${encodeURIComponent(agentId)}`);
    rows = res.ok ? await res.json() : [];
  } catch {
    rows = [];
  }
  const html = renderPendingProposalsHtml(rows);
  host.innerHTML = html;
  host.classList.toggle('hidden', !html);
  host.querySelectorAll('[data-attach-decision]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const row = btn.closest('[data-proposal-row]');
      const status = row && row.querySelector('[data-attach-status]');
      row && row.querySelectorAll('button').forEach((b) => { b.disabled = true; });
      try {
        const body = await decideAttachProposal(btn.dataset.id, btn.dataset.attachDecision, fetchImpl);
        if (status) status.textContent = (body.execution && (body.execution.output || body.execution.error)) || 'Done.';
        if (onChanged) await onChanged(body);
      } catch (err) {
        if (status) status.textContent = `Failed: ${err.message}`;
        row && row.querySelectorAll('button').forEach((b) => { b.disabled = false; });
      }
    });
  });
  return attachProposals(rows);
}
