/**
 * Chat Studio: Multi-Phase Journey Inspector Submodule [CARD-135, CARD-397]
 * Renders multi-phase milestone milestones, tool invocation spans, and discovered artifacts timeline.
 */

import { safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { copyToClipboard } from '../../utils/clipboard.js';

export function renderJourneyTimeline(data, chatJourneyContent, { jobPhaseState = {}, showToastFn = null } = {}) {
  if (!chatJourneyContent) return;
  if (!data || (!data.jobs?.length && !data.tool_executions?.length && !data.artifacts?.length && !data.facts?.length)) {
    chatJourneyContent.innerHTML = `
      <div class="text-center py-10 space-y-2 text-slate-400">
        <i data-lucide="compass" class="w-8 h-8 mx-auto text-slate-500"></i>
        <p class="font-medium text-slate-300">No Multi-Phase Journey Recorded</p>
        <p class="text-[11px] text-slate-500">This conversation has not executed multi-phase goals or logged tool spans yet.</p>
      </div>
    `;
    safeCreateIcons();
    return;
  }

  let html = '';
  const mainJob = data.jobs?.[0];
  const goalTitle = mainJob ? mainJob.goal : (data.title || 'Conversation Turn');
  const status = mainJob ? mainJob.status : 'active';
  const statusColor = status === 'done'
    ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
    : (status === 'failed'
      ? 'bg-rose-950/60 border-rose-800 text-rose-300'
      : 'bg-indigo-950/60 border-indigo-800 text-indigo-300');

  const journeyJobId = (mainJob && (mainJob.id || mainJob.job_id)) || jobPhaseState.jobId || '';
  html += `
    <div class="p-3 rounded-xl bg-slate-800/80 border border-slate-700 space-y-2">
      <div class="flex items-center justify-between gap-2 flex-wrap">
        <span class="text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusColor}">${escapeHtml(status)}</span>
        <span class="text-[10px] text-slate-400 font-mono">${data.summary?.total_tools_executed || 0} tools | ${data.summary?.total_facts_learned || 0} facts</span>
      </div>
      <h4 class="font-bold text-slate-100 text-sm leading-snug">${escapeHtml(goalTitle)}</h4>
      ${journeyJobId ? `
      <div class="flex items-center gap-1.5 flex-wrap pt-0.5">
        <span class="text-[10px] font-mono text-brand-300 select-all px-2 py-0.5 rounded bg-slate-950 border border-brand-700/50" data-journey-job-id>${escapeHtml(journeyJobId)}</span>
        <button type="button" class="journey-copy-job-id inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 transition" data-job-id="${escapeHtml(journeyJobId)}" title="Copy job id" aria-label="Copy job id">
          <i data-lucide="copy" class="w-3 h-3"></i>
          <span>Copy</span>
        </button>
      </div>` : ''}
    </div>
  `;

  if (mainJob?.phases?.length) {
    html += `
      <div class="space-y-2">
        <h5 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Milestones & Phases</h5>
        <div class="relative pl-4 border-l-2 border-slate-700 space-y-3">
    `;
    mainJob.phases.forEach((phase, idx) => {
      const isDone = phase.status === 'done';
      const isRunning = phase.status === 'running' || phase.status === 'waiting_approval';
      const isFailed = phase.status === 'failed';
      const dotColor = isDone
        ? 'bg-emerald-500 ring-emerald-950'
        : (isRunning
          ? 'bg-indigo-500 ring-indigo-950 animate-pulse'
          : (isFailed ? 'bg-rose-500 ring-rose-950' : 'bg-slate-600 ring-slate-900'));

      html += `
        <div class="relative pl-2">
          <span class="absolute -left-[1.35rem] top-1 w-2.5 h-2.5 rounded-full ring-4 ${dotColor}"></span>
          <div class="p-2.5 rounded-lg bg-slate-800/50 border border-slate-700/60 space-y-1">
            <div class="flex items-center justify-between">
              <span class="font-semibold text-slate-200">${escapeHtml(phase.name || `Phase ${idx + 1}`)}</span>
              <span class="text-[10px] font-mono text-slate-400">${escapeHtml(phase.status)}</span>
            </div>
            ${phase.verify_status ? `<p class="text-[11px] font-mono text-slate-400">verify_status: <span class="text-indigo-300">${escapeHtml(phase.verify_status)}</span></p>` : ''}
            ${phase.success_rule ? `<p class="text-[11px] text-slate-400 font-mono">Rule: ${escapeHtml(phase.success_rule)}</p>` : ''}
          </div>
        </div>
      `;
    });
    html += '</div></div>';
  }

  if (data.tool_executions?.length) {
    html += `
      <div class="space-y-2">
        <h5 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Tool Invocations (${data.tool_executions.length})</h5>
        <div class="space-y-1.5 max-h-56 overflow-y-auto pr-1">
    `;
    data.tool_executions.forEach((t) => {
      const badgeColor = t.success
        ? 'text-emerald-300 border-emerald-800/60 bg-emerald-950/30'
        : 'text-rose-300 border-rose-800/60 bg-rose-950/30';
      html += `
        <div class="flex items-center justify-between p-2 rounded-lg bg-slate-800/40 border border-slate-700/50 text-[11px]">
          <span class="font-mono font-medium text-slate-200">${escapeHtml(t.tool_name)}</span>
          <div class="flex items-center space-x-1.5">
            <span class="text-[10px] text-slate-400 font-mono">${t.duration_ms}ms</span>
            <span class="px-1.5 py-0.5 rounded text-[10px] border font-mono ${badgeColor}">${t.success ? 'OK' : 'ERR'}</span>
          </div>
        </div>
      `;
    });
    html += '</div></div>';
  }

  if (data.artifacts?.length || data.facts?.length) {
    html += `
      <div class="space-y-2">
        <h5 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Key Discoveries & Output</h5>
        <div class="space-y-1.5">
    `;
    (data.artifacts || []).forEach((art) => {
      html += `
        <div class="p-2 rounded-lg bg-indigo-950/20 border border-indigo-800/50 flex items-center justify-between">
          <div class="flex items-center space-x-1.5 truncate">
            <i data-lucide="file-text" class="w-3.5 h-3.5 text-indigo-400 flex-shrink-0"></i>
            <span class="font-medium text-slate-200 truncate">${escapeHtml(art.title)}</span>
          </div>
          <span class="text-[10px] text-indigo-300 font-mono uppercase">${escapeHtml(art.content_type?.split('/')?.[1] || 'doc')}</span>
        </div>
      `;
    });
    (data.facts || []).forEach((fact) => {
      html += `
        <div class="p-2 rounded-lg bg-slate-800/40 border border-slate-700/50 text-[11px] flex items-center justify-between">
          <span class="text-slate-400 font-mono">${escapeHtml(fact.entity)}.${escapeHtml(fact.key)}</span>
          <span class="text-slate-200 font-mono font-semibold">${escapeHtml(fact.value)}</span>
        </div>
      `;
    });
    html += '</div></div>';
  }

  chatJourneyContent.innerHTML = html;
  chatJourneyContent.querySelectorAll('.journey-copy-job-id').forEach((btn) => {
    btn.addEventListener('click', () => {
      const id = btn.getAttribute('data-job-id') || '';
      if (!id) return;
      copyToClipboard(id);
      if (typeof showToastFn === 'function') {
        showToastFn(`Copied ${id}`, 'success');
      }
    });
  });
  safeCreateIcons();
}

export async function loadJourneyTimeline(sessionId, chatJourneyContent, {
  fetchFn = null,
  renderJourneyTimelineFn = renderJourneyTimeline,
  jobPhaseState = {},
  showToastFn = null,
} = {}) {
  if (!sessionId || !chatJourneyContent) return;
  const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
  chatJourneyContent.innerHTML = '<div class="text-slate-400 text-center py-8 animate-pulse">Loading journey...</div>';
  try {
    const res = await fn(`/api/chat/sessions/${encodeURIComponent(sessionId)}/journey`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderJourneyTimelineFn(data, chatJourneyContent, { jobPhaseState, showToastFn });
  } catch (err) {
    chatJourneyContent.innerHTML = `<div class="p-3 rounded bg-rose-950/40 border border-rose-800 text-rose-300">Failed to load journey: ${escapeHtml(err.message)}</div>`;
  }
}
