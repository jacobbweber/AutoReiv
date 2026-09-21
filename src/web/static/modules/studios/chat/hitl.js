/**
 * Chat Studio: Human-In-The-Loop (HITL) Submodule [REQ-ARCH-003]
 * Handles approval decision formatting, payload construction, and card rendering.
 */

import { escapeHtml } from '../../utils/formatters.js';
import { storageGet, storageSet } from '../../utils/storage.js';
import { safeCreateIcons } from '../../dom.js';

export const CODE_KEYS = [
  'code',
  'command',
  'commandline',
  'script',
  'content',
  'codecontent',
  'query',
  'sql',
  'prompt',
  'instructions',
];

export function formatHitlArgs(args) {
  if (args == null) return '';
  let obj = args;

  if (typeof args === 'string') {
    const trimmed = args.trim();
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        obj = JSON.parse(trimmed);
      } catch {
        return args;
      }
    } else {
      return args;
    }
  }

  if (typeof obj !== 'object' || obj === null) {
    return String(obj);
  }

  // Check if obj contains a primary code or command key
  const keys = Object.keys(obj);
  const primaryKey = keys.find((k) => CODE_KEYS.includes(k.toLowerCase()));

  if (primaryKey && typeof obj[primaryKey] === 'string') {
    const primaryText = obj[primaryKey];
    const otherKeys = keys.filter((k) => k !== primaryKey);
    const metaLines = otherKeys.map((k) => {
      const v = obj[k];
      if (typeof v === 'object' && v !== null) {
        return `${k}: ${JSON.stringify(v)}`;
      }
      return `${k}: ${v}`;
    });

    const header = metaLines.length > 0 ? `${metaLines.join('\n')}\n\n` : '';
    const cleanPrimary = String(primaryText).replace(/\r\n/g, '\n');
    const fullText = `${header}${cleanPrimary}`;
    return fullText.length > 4000 ? `${fullText.slice(0, 4000)}…` : fullText;
  }

  // If there are multi-line string properties without a primary key, format each key cleanly
  const hasMultiline = keys.some((k) => typeof obj[k] === 'string' && obj[k].includes('\n'));
  if (hasMultiline) {
    const lines = keys.map((k) => {
      const v = obj[k];
      if (typeof v === 'string') {
        const cleanV = v.replace(/\r\n/g, '\n');
        if (cleanV.includes('\n')) {
          return `${k}:\n${cleanV}`;
        }
        return `${k}: ${cleanV}`;
      }
      if (typeof v === 'object' && v !== null) {
        return `${k}: ${JSON.stringify(v, null, 2)}`;
      }
      return `${k}: ${v}`;
    });
    const fullText = lines.join('\n\n');
    return fullText.length > 4000 ? `${fullText.slice(0, 4000)}…` : fullText;
  }

  // Fallback to pretty printed JSON
  try {
    const text = JSON.stringify(obj, null, 2);
    return text.length > 4000 ? `${text.slice(0, 4000)}…` : text;
  } catch {
    return String(obj);
  }
}

export function formatHitlOutput(output) {
  if (output == null) return '';

  if (typeof output === 'object' && output !== null) {
    if (output.error && !output.stdout && !output.stderr && !output.output) {
      return `Error: ${output.error}`;
    }

    let text = '';
    if (output.stdout !== undefined && output.stdout !== null) {
      text = String(output.stdout);
    } else if (output.output !== undefined && output.output !== null) {
      text = typeof output.output === 'string' ? output.output : JSON.stringify(output.output, null, 2);
    }

    if (output.stderr) {
      const errText = String(output.stderr).trim();
      if (errText) {
        text = text ? `${text}\n[stderr]\n${errText}` : `[stderr]\n${errText}`;
      }
    }

    if (!text && Object.keys(output).length > 0) {
      try {
        return JSON.stringify(output, null, 2);
      } catch {
        return String(output);
      }
    }

    text = text.replace(/\r\n/g, '\n');
    const trimmed = text.trim();
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        const parsed = JSON.parse(trimmed);
        return JSON.stringify(parsed, null, 2);
      } catch {
        // Not valid JSON, return clean text
      }
    }
    return text;
  }

  if (typeof output === 'string') {
    const clean = output.replace(/\r\n/g, '\n');
    const trimmed = clean.trim();
    if ((trimmed.startsWith('{') && trimmed.endsWith('}')) || (trimmed.startsWith('[') && trimmed.endsWith(']'))) {
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed && typeof parsed === 'object' && (parsed.stdout !== undefined || parsed.stderr !== undefined)) {
          return formatHitlOutput(parsed);
        }
        return JSON.stringify(parsed, null, 2);
      } catch {
        // Not JSON
      }
    }
    return clean;
  }

  try {
    return JSON.stringify(output, null, 2);
  } catch {
    return String(output);
  }
}

export const APPROVAL_AUTORUN_STORAGE_KEY = 'autoreiv_approval_autorun';

export function readLastApprovalAutoRun(reader = storageGet) {
  try {
    const raw = reader(APPROVAL_AUTORUN_STORAGE_KEY, '');
    return String(raw || '').trim().toLowerCase() === 'run';
  } catch {
    return false;
  }
}

export function writeLastApprovalAutoRun(enabled, writer = storageSet) {
  try {
    writer(APPROVAL_AUTORUN_STORAGE_KEY, enabled ? 'run' : 'ask');
  } catch {
    // Fail closed: next load without memory stays ask.
  }
}

export function hasVisibleHitlCard(root) {
  if (!root || typeof root.querySelector !== 'function') {
    return false;
  }
  return Boolean(root.querySelector('.hitl-approval-card:not(.hidden)'));
}

export function pendingApprovalsUrl(agentId, sessionId) {
  const sid = String(sessionId || '').trim();
  const aid = String(agentId || '').trim();
  const params = new URLSearchParams();
  if (sid) {
    params.set('session_id', sid);
  }
  if (aid && !sid) {
    params.set('agent_id', aid);
  }
  const qs = params.toString();
  return qs ? `/api/approvals/pending?${qs}` : '/api/approvals/pending';
}

export function pendingHitlLabel(approval) {
  if (!approval || !approval.routine_id) {
    return 'Approval required';
  }
  const name = String(approval.routine_name || '').trim();
  return name ? `Routine: ${name}` : 'Routine';
}

export function approvalBelongsToOriginSession(approvalSessionId, originSessionId) {
  const approvalSid = String(approvalSessionId || '').trim();
  const originSid = String(originSessionId || '').trim();
  if (!approvalSid || !originSid) return false;
  return (
    approvalSid === originSid
    || approvalSid.startsWith(originSid + '_child_')
    || approvalSid.startsWith(originSid + '::phase::')
  );
}

export function shouldResumeChatAfterHitl({ approvalSessionId, openSessionId, backendResumed, nestedStatus }) {
  if (backendResumed) return false;
  if (nestedStatus === 'approval_required') return false;
  const approvalSid = String(approvalSessionId || '').trim();
  const openSid = String(openSessionId || '').trim();
  if (!approvalSid || !openSid) {
    return Boolean(openSid);
  }
  return approvalBelongsToOriginSession(approvalSid, openSid);
}

/**
 * Determine whether a pending approval item should be skipped from rendering into #pendingHitlHost.
 * [CARD-076, CARD-295, CARD-343]
 */
export function shouldSkipPendingHitlCard({
  id,
  item = {},
  liveIds = new Set(),
  isStreaming = false,
  originSid = '',
} = {}) {
  if (!id) return true;
  // If not actively streaming (idle, parked, or turn finished), pending approvals must ALWAYS surface in the pinned tray.
  if (!isStreaming) return false;
  const approvalSid = String(item.session_id || '').trim();
  const origin = String(originSid || '').trim();
  const isPhaseChild = Boolean(
    approvalSid && origin && approvalSid !== origin
    && (approvalSid.startsWith(origin + '_child_') || approvalSid.startsWith(origin + '::phase::'))
  );
  // Phase child approvals and routines must always surface in the pinned tray even while parent stream is alive.
  if (isPhaseChild || item.routine_id) return false;
  // For same-session live turns, only skip if an inline approval card is actually rendered in the message container.
  return liveIds.has(id);
}

export function buildHitlCardInnerHtml({ title, toolName, message, argsText, resolved = null, statusText = '' }) {
  if (resolved) {
    const isApproved = String(resolved).toUpperCase() === 'APPROVED';
    return `
    <div class="font-semibold ${isApproved ? 'text-emerald-200' : 'text-rose-200'}">${escapeHtml(title || (isApproved ? 'Approved' : 'Rejected'))}</div>
    <div class="text-slate-300">Tool: <strong class="text-white">${escapeHtml(toolName || 'tool')}</strong></div>
    ${message ? `<div class="text-slate-400">${escapeHtml(message)}</div>` : ''}
    ${argsText ? `<pre class="text-[11px] font-mono whitespace-pre-wrap text-slate-300 bg-slate-950/40 p-2 rounded border border-slate-800 max-h-32 overflow-y-auto">${escapeHtml(argsText)}</pre>` : ''}
    <div class="flex items-center space-x-2 pt-1">
      <button type="button" disabled data-hitl-decision="APPROVED" class="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-50 pointer-events-none text-xs font-semibold">Approve</button>
      <button type="button" disabled data-hitl-decision="REJECTED" class="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-50 pointer-events-none text-xs font-semibold">Reject</button>
      <span class="hitl-card-status ${isApproved ? 'text-emerald-300' : 'text-rose-300'}">${escapeHtml(statusText || (isApproved ? 'Approved.' : 'Rejected.'))}</span>
    </div>
  `;
  }
  return `
    <div class="font-semibold text-amber-200">${escapeHtml(title || 'Approval required')}</div>
    <div class="text-slate-300">Tool: <strong class="text-white">${escapeHtml(toolName || 'tool')}</strong></div>
    <div class="text-slate-400">${escapeHtml(message || 'Waiting for operator approval')}</div>
    <pre class="text-[11px] font-mono whitespace-pre-wrap text-slate-300 bg-slate-950/40 p-2 rounded border border-slate-800 max-h-32 overflow-y-auto">${escapeHtml(argsText || '')}</pre>
    <div class="flex items-center space-x-2 pt-1">
      <button type="button" data-hitl-decision="APPROVED" class="px-2.5 py-1 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none text-white text-xs font-semibold">Approve</button>
      <button type="button" data-hitl-decision="REJECTED" class="px-2.5 py-1 rounded-lg bg-rose-800 hover:bg-rose-700 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none text-white text-xs font-semibold">Reject</button>
      <span class="hitl-card-status text-amber-200"></span>
    </div>
  `;
}

export async function submitHitlDecision(approvalId, decision, cardEl, sessionId) {
  const buttons = cardEl.querySelectorAll('[data-hitl-decision]');
  buttons.forEach((btn) => {
    btn.disabled = true;
    if (btn.classList && typeof btn.classList.add === 'function') {
      btn.classList.add('opacity-50', 'cursor-not-allowed', 'pointer-events-none');
    }
  });
  const statusEl = cardEl.querySelector('.hitl-card-status');
  if (statusEl) {
    statusEl.textContent = decision === 'APPROVED' ? 'Approving…' : 'Rejecting…';
  }
  try {
    const res = await fetch(`/api/approvals/${encodeURIComponent(approvalId)}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, session_id: sessionId || undefined }),
    });
    let body = {};
    try {
      body = await res.json();
    } catch {
      body = {};
    }
    if (!res.ok) {
      const detail = body.detail || `HTTP ${res.status}`;
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    const ran = Boolean(body.execution && body.execution.ran);
    if (statusEl) {
      if (decision === 'APPROVED') {
        statusEl.textContent = ran ? 'Approved. Tool ran.' : 'Approved.';
      } else {
        statusEl.textContent = 'Rejected. Tool did not run.';
      }
    }
    buttons.forEach((btn) => {
      btn.disabled = true;
      if (btn.classList) {
        if (typeof btn.classList.remove === 'function') {
          btn.classList.remove(
            'bg-emerald-700',
            'hover:bg-emerald-600',
            'bg-rose-800',
            'hover:bg-rose-700',
            'hover:bg-emerald-700',
            'hover:bg-rose-800',
            'text-white'
          );
        }
        if (typeof btn.classList.add === 'function') {
          btn.classList.add(
            'bg-slate-800',
            'text-slate-500',
            'border',
            'border-slate-700/60',
            'cursor-not-allowed',
            'opacity-50',
            'pointer-events-none'
          );
        }
      }
    });
    if (cardEl.classList) {
      cardEl.classList.remove('border-amber-500/30', 'bg-amber-950/20');
      if (decision === 'APPROVED') {
        cardEl.classList.add('border-emerald-500/30', 'bg-emerald-950/20');
      } else {
        cardEl.classList.add('border-rose-500/30', 'bg-rose-950/20');
      }
    }
    const execution = body.execution || null;
    const output = execution ? execution.output : null;
    const error = execution ? execution.error : null;
    if ((output != null || error != null) && typeof cardEl.appendChild === 'function' && typeof document !== 'undefined') {
      const pre = document.createElement('pre');
      pre.className =
        'mt-2 text-[11px] font-mono whitespace-pre-wrap text-slate-300 bg-slate-950/40 p-2 rounded border border-slate-800 max-h-40 overflow-y-auto';
      const formatted = formatHitlOutput(output);
      pre.textContent = error && !formatted.includes(error) ? `Error: ${error}\n${formatted}`.trim() : formatted;
      cardEl.appendChild(pre);
    }
    return { ok: true, body };
  } catch (err) {
    buttons.forEach((btn) => {
      btn.disabled = false;
      if (btn.classList && typeof btn.classList.remove === 'function') {
        btn.classList.remove('opacity-50', 'cursor-not-allowed', 'pointer-events-none');
      }
    });
    if (statusEl) {
      statusEl.textContent = `Failed: ${err.message || err}`;
    }
    return { ok: false, body: {} };
  }
}

/** CARD-251: Forge Approve response resumes same job_id (no orphan / soft-delete). */
export function forgeApproveResumesSameJob(payload) {
  const p = payload || {};
  const jobId = String(p.job_id || '').trim();
  if (!jobId) return false;
  if (p.soft_deleted === true || p.orphan === true) return false;
  if (p.resumed !== true && p.same_job !== true) return false;
  return true;
}

export function shouldPreventOrphanMint({ openJobStatus, resume }) {
  if (resume) return false;
  return String(openJobStatus || '').toLowerCase() === 'waiting_approval';
}

export function isGoalPlanReviewTool(toolName) {
  return String(toolName || '') === 'goal_plan_review';
}

export function setupPendingHitl(state, messagesContainer, { onResumeTurn, showToastFn } = {}) {
  const showToast = showToastFn || (() => {});

  async function refreshPendingHitl() {
    try {
      const res = await fetch(pendingApprovalsUrl(state.activeSessionId));
      if (!res.ok) return;
      const data = await res.json();
      renderPendingHitlCards(data.pending || []);
    } catch (e) {
      console.warn('Failed to fetch pending approvals:', e);
    }
  }

  function renderPendingHitlCards(pending) {
    if (!messagesContainer) return;
    messagesContainer.querySelectorAll('.hitl-pending-card').forEach((el) => el.remove());
    if (!pending || pending.length === 0) return;

    pending.forEach((req) => {
      if (shouldSkipPendingHitlCard(req, state.activeSessionId)) return;
      const el = document.createElement('div');
      el.className = 'hitl-pending-card my-3 p-4 rounded-xl border border-amber-500/50 bg-amber-950/20 text-slate-200 text-xs shadow-md animate-fade-in';
      el.setAttribute('data-request-id', req.id);
      el.innerHTML = buildHitlCardInnerHtml(req, { pendingHitlLabel, formatHitlArgs });
      messagesContainer.appendChild(el);

      const approveBtn = el.querySelector('.hitl-approve-btn');
      const rejectBtn = el.querySelector('.hitl-reject-btn');

      if (approveBtn) {
        approveBtn.addEventListener('click', async () => {
          approveBtn.disabled = true;
          if (rejectBtn) rejectBtn.disabled = true;
          approveBtn.textContent = 'Approving...';
          const success = await submitHitlDecision(req.id, true);
          if (success) {
            approveBtn.textContent = 'Approved ✓';
            approveBtn.className = 'hitl-approve-btn px-3 py-1.5 rounded-lg bg-emerald-900/60 text-emerald-300 font-semibold cursor-default border border-emerald-700/50';
            if (rejectBtn) rejectBtn.remove();
            showToast('Action approved and running', 'success');
            await refreshPendingHitl();
            if (shouldResumeChatAfterHitl(req, isGoalPlanReviewTool(req.tool_name)) && onResumeTurn) {
              await onResumeTurn('Approved. Proceed with execution.', { isResume: true, resumeJobId: req.job_id || null });
            }
          } else {
            approveBtn.disabled = false;
            if (rejectBtn) rejectBtn.disabled = false;
            approveBtn.textContent = 'Approve & Run';
            showToast('Failed to submit approval', 'error');
          }
        });
      }

      if (rejectBtn) {
        rejectBtn.addEventListener('click', async () => {
          if (approveBtn) approveBtn.disabled = true;
          rejectBtn.disabled = true;
          rejectBtn.textContent = 'Rejecting...';
          const success = await submitHitlDecision(req.id, false);
          if (success) {
            rejectBtn.textContent = 'Rejected ✗';
            rejectBtn.className = 'hitl-reject-btn px-3 py-1.5 rounded-lg bg-rose-900/60 text-rose-300 font-semibold cursor-default border border-rose-700/50';
            if (approveBtn) approveBtn.remove();
            showToast('Action rejected', 'info');
            await refreshPendingHitl();
          } else {
            if (approveBtn) approveBtn.disabled = false;
            rejectBtn.disabled = false;
            rejectBtn.textContent = 'Reject';
            showToast('Failed to submit rejection', 'error');
          }
        });
      }

      el.scrollIntoView({ behavior: 'smooth', block: 'end' });
    });
    safeCreateIcons();
  }

  function startPendingHitlPoll() {
    return setInterval(() => {
      if (document.visibilityState === 'visible') {
        refreshPendingHitl();
      }
    }, 4000);
  }

  return {
    refreshPendingHitl,
    renderPendingHitlCards,
    startPendingHitlPoll,
  };
}

