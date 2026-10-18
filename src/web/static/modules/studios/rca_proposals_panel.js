/**
 * Staged RCA Self-Healing Proposals Panel [CARD-704].
 * Renders recurring tool and routine failure RCA cards in Capabilities Studio
 * with one-click "Repair in Chat" and "Dismiss" actions.
 */

import { $, escapeHtml, safeCreateIcons } from '../dom.js';
import { api } from '../services/api.js';
import { requestTabSwitch } from '../state/store.js';
import { setComposerText } from './chat/composer.js';
import { showToast } from '../ui/toast.js';

function severityBadgeClasses(severity) {
  const sev = String(severity || 'warning').toLowerCase();
  if (sev === 'critical') {
    return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
  }
  if (sev === 'high') {
    return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
  }
  return 'bg-yellow-500/15 text-yellow-200 border-yellow-500/30';
}

/**
 * Pure HTML renderer for staged RCA proposal cards [CARD-704].
 * @param {Array<Object>} proposals
 * @returns {string}
 */
export function renderRcaProposalsHtml(proposals = []) {
  const list = Array.isArray(proposals) ? proposals : [];
  if (list.length === 0) {
    return '';
  }
  return list
    .map((p) => {
      const id = String(p.id || '').trim();
      const kind = String(p.kind || 'tool').trim();
      const target = String(p.target_name || id).trim();
      const skillId = p.skill_id ? String(p.skill_id).trim() : '';
      const filePath = p.file_path ? String(p.file_path).trim() : '';
      const severity = String(p.severity || 'warning').toLowerCase();
      const failCount = Number(p.failure_count) || 1;
      const latestError = String(p.latest_error || 'Execution error').trim();
      const remediation = String(p.suggested_remediation || '').trim();
      const traces = Array.isArray(p.trace_ids) ? p.trace_ids.filter(Boolean) : [];
      const primaryTrace = traces[0] || 'n/a';
      const badgeCls = severityBadgeClasses(severity);
      const locationBadge =
        skillId && filePath
          ? `<span class="px-2 py-0.5 rounded bg-[#141721] border border-white/[0.08] text-[10px] font-mono text-emerald-300">${escapeHtml(skillId)}/${escapeHtml(filePath)}</span>`
          : `<span class="px-2 py-0.5 rounded bg-[#141721] border border-white/[0.08] text-[10px] font-mono text-slate-300">${escapeHtml(kind)}</span>`;

      return `<div class="p-3 rounded-xl bg-[#0e1015]/95 border border-amber-500/30 space-y-2 shadow-sm" data-testid="rca-proposal-card" data-proposal-id="${escapeHtml(id)}" data-target-name="${escapeHtml(target)}">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex flex-wrap items-center gap-2 min-w-0">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase border ${badgeCls}">${escapeHtml(severity)}</span>
            <span class="font-mono text-xs font-bold text-white truncate">${escapeHtml(target)}</span>
            ${locationBadge}
            <span class="text-[11px] font-mono text-amber-300" data-testid="rca-failure-count">${failCount} ${failCount === 1 ? 'failure' : 'failures'}</span>
            <span class="text-[10px] font-mono text-slate-400" data-testid="rca-trace-ref">trace: ${escapeHtml(primaryTrace)}</span>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button type="button" data-rca-repair="${escapeHtml(id)}" data-testid="rca-repair-btn" class="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold transition flex items-center gap-1.5 shadow-sm">
              <i data-lucide="wrench" class="w-3.5 h-3.5"></i>
              <span>Repair in Chat</span>
            </button>
            <button type="button" data-rca-dismiss="${escapeHtml(id)}" data-testid="rca-dismiss-btn" class="px-2.5 py-1.5 rounded-lg bg-[#141721] hover:bg-slate-800 text-slate-300 text-xs border border-white/[0.08] transition">
              Dismiss
            </button>
          </div>
        </div>
        <div class="text-xs font-mono text-rose-300 bg-[#08090c] border border-rose-500/20 rounded-lg px-2.5 py-1.5 break-words" data-testid="rca-error-detail">${escapeHtml(latestError)}</div>
        ${remediation ? `<p class="text-[11px] text-slate-300">${escapeHtml(remediation)}</p>` : ''}
      </div>`;
    })
    .join('');
}

/**
 * Bind and manage the staged RCA proposals banner in Capabilities Studio [CARD-704].
 */
export function setupRcaProposalsPanel({ callbacks = {}, onInspectTool = null } = {}) {
  const panelEl = $('capabilitiesRcaProposalsPanel');
  const listEl = $('capabilitiesRcaProposalsList');
  const countBadgeEl = $('capabilitiesRcaCountBadge');
  const refreshBtnEl = $('capabilitiesRcaRefreshBtn');

  const proposalsById = new Map();

  async function refreshRcaProposals() {
    if (!panelEl || !listEl) return [];
    try {
      const data = await api.capabilities.listRcaProposals();
      const proposals = Array.isArray(data?.proposals) ? data.proposals : [];
      proposalsById.clear();
      proposals.forEach((p) => {
        if (p && p.id) proposalsById.set(String(p.id), p);
      });

      if (countBadgeEl) {
        countBadgeEl.textContent = String(proposals.length);
      }

      if (proposals.length === 0) {
        panelEl.classList.add('hidden');
        listEl.innerHTML = '';
        return [];
      }

      panelEl.classList.remove('hidden');
      listEl.innerHTML = renderRcaProposalsHtml(proposals);
      safeCreateIcons();
      return proposals;
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to load RCA proposals:', err);
      return [];
    }
  }

  async function handleRepairInChat(proposalId) {
    const proposal = proposalsById.get(String(proposalId || '').trim());
    if (!proposal) return;

    if (panelEl) {
      panelEl.dataset.lastRepairPrompt = proposal.repair_prompt || '';
    }
    if (typeof onInspectTool === 'function' && proposal.skill_id && proposal.file_path) {
      try {
        await onInspectTool(proposal.skill_id, proposal.file_path);
      } catch (err) {
        console.warn('[AutoReiv UI] Could not pre-select skill file before repair:', err);
      }
    }

    const switchFn =
      (callbacks && typeof callbacks.switchTab === 'function' && callbacks.switchTab) ||
      requestTabSwitch;
    switchFn('chat');

    const chatCtrl =
      callbacks && typeof callbacks.getChatCtrl === 'function' ? callbacks.getChatCtrl() : null;
    if (chatCtrl && typeof chatCtrl.switchSelectedAgent === 'function') {
      await chatCtrl.switchSelectedAgent('autoreiv');
    }
    if (chatCtrl && typeof chatCtrl.createNewSession === 'function') {
      await chatCtrl.createNewSession();
    }

    const promptInput = $('promptInput');
    if (promptInput && proposal.repair_prompt) {
      setComposerText(promptInput, proposal.repair_prompt, { focus: true });
      const sendBtn = $('sendBtn');
      if (sendBtn && !sendBtn.disabled) {
        sendBtn.click();
      }
    }
  }

  async function handleDismissProposal(proposalId) {
    const cleanId = String(proposalId || '').trim();
    if (!cleanId) return;
    try {
      await api.capabilities.dismissRcaProposal(cleanId);
      showToast('Dismissed RCA proposal.', 'info');
      await refreshRcaProposals();
    } catch (err) {
      showToast(`Could not dismiss RCA proposal: ${err.message}`, 'error');
    }
  }

  if (listEl) {
    listEl.addEventListener('click', (event) => {
      const repairBtn = event.target.closest('[data-rca-repair]');
      if (repairBtn) {
        const pid = repairBtn.getAttribute('data-rca-repair');
        if (pid) handleRepairInChat(pid);
        return;
      }
      const dismissBtn = event.target.closest('[data-rca-dismiss]');
      if (dismissBtn) {
        const pid = dismissBtn.getAttribute('data-rca-dismiss');
        if (pid) handleDismissProposal(pid);
      }
    });
  }

  if (refreshBtnEl) {
    refreshBtnEl.addEventListener('click', () => {
      refreshRcaProposals();
    });
  }

  return {
    refreshRcaProposals,
  };
}
