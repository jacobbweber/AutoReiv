/**
 * Chat Studio Stream Bubble DOM Helpers [CARD-716].
 */

import { escapeHtml } from '../../utils/formatters.js';

export function buildStreamBubbleHtml(agentTitle, streamBubble = {}) {
  streamBubble.innerHTML = `
      <div class="max-w-4xl w-full rounded-2xl p-4 shadow-md bg-slate-900/90 border border-slate-800/80 text-slate-100 rounded-bl-sm space-y-3" data-job-chrome-card="1">
        <div class="flex items-center justify-between text-xs font-bold uppercase tracking-wider opacity-70">
          <span>${escapeHtml(agentTitle || 'Agent')}</span>
          <span class="text-brand-400 font-mono text-[10px] animate-pulse">Streaming...</span>
        </div>
        <div class="job-chrome-phases space-y-1.5 hidden" data-job-chrome-phases="1"></div>
        <div class="plan-milestone-card hidden rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-3 space-y-2 text-xs">
          <div class="plan-card-header flex items-center justify-between font-semibold text-indigo-300">
            <span class="flex items-center space-x-1.5">
              <span>📋</span>
              <span class="plan-goal-title">Execution Plan</span>
            </span>
            <span class="plan-step-counter text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-900/60 text-indigo-300"></span>
          </div>
          <div class="plan-steps-container space-y-1.5 pt-1"></div>
        </div>
        <div class="reflexion-status-badge hidden p-2 rounded-lg bg-amber-950/40 border border-amber-500/30 text-xs text-amber-300 items-center space-x-2"></div>
        <div class="tool-status-badge hidden p-2 rounded-lg bg-slate-800/80 border border-slate-700 text-xs text-brand-300 items-center space-x-2"></div>
        <div class="reasoning-drawer hidden rounded-xl border border-amber-500/30 bg-amber-950/20 overflow-hidden text-xs">
          <button type="button" class="reasoning-toggle flex items-center justify-between w-full px-3 py-2 bg-amber-900/20 text-amber-300 font-semibold cursor-pointer">
            <span class="flex items-center space-x-1.5">
              <span>💭</span>
              <span>Thinking Process</span>
            </span>
            <span class="reasoning-indicator text-[10px] uppercase font-mono">Show</span>
          </button>
          <div class="reasoning-content hidden p-3 font-mono text-[11px] text-amber-100 whitespace-pre-wrap max-h-60 overflow-y-auto"></div>
        </div>
        <div class="stream-queue-note hidden text-xs text-amber-200/90 italic" data-stream-queue-note="1" role="status"></div>
        <div class="stream-content text-sm leading-relaxed prose prose-invert max-w-none text-slate-100 break-words"></div>
        <div class="hitl-approval-card hidden p-3 rounded-xl border border-amber-500/50 bg-amber-950/30 text-slate-200 text-xs space-y-2"></div>
      </div>
    `;
  return streamBubble.innerHTML;
}

export function bindStreamBubbleElements(streamBubble) {
  const streamContentEl = streamBubble.querySelector('.stream-content');
  const queueNoteEl = streamBubble.querySelector('.stream-queue-note');
  const reasoningDrawer = streamBubble.querySelector('.reasoning-drawer');
  const reasoningContent = streamBubble.querySelector('.reasoning-content');
  const reasoningToggle = streamBubble.querySelector('.reasoning-toggle');
  const reasoningIndicator = streamBubble.querySelector('.reasoning-indicator');
  const toolBadge = streamBubble.querySelector('.tool-status-badge');
  const reflexionBadge = streamBubble.querySelector('.reflexion-status-badge');
  const hitlCard = streamBubble.querySelector('.hitl-approval-card');
  const planMilestoneCard = streamBubble.querySelector('.plan-milestone-card');
  const planStepsContainer = streamBubble.querySelector('.plan-steps-container');
  const planStepCounter = streamBubble.querySelector('.plan-step-counter');

  if (reasoningToggle && reasoningContent && reasoningIndicator) {
    reasoningToggle.addEventListener('click', () => {
      const isHidden = reasoningContent.classList.toggle('hidden');
      reasoningIndicator.textContent = isHidden ? 'Show' : 'Hide';
    });
  }

  return {
    streamContentEl,
    queueNoteEl,
    reasoningDrawer,
    reasoningContent,
    toolBadge,
    reflexionBadge,
    hitlCard,
    planMilestoneCard,
    planStepsContainer,
    planStepCounter,
  };
}

export function renderToolStatusBadge(toolBadge, badge, safeCreateIconsFn) {
  if (!toolBadge || !badge) return;
  toolBadge.classList.remove('hidden');
  toolBadge.classList.add('flex');
  if (badge.state === 'running') {
    toolBadge.innerHTML = `<i data-lucide="wrench" class="w-3.5 h-3.5 text-brand-400 animate-spin"></i><span>Using tool: <strong>${escapeHtml(badge.name)}</strong></span>`;
  } else if (badge.state === 'refused') {
    toolBadge.innerHTML = `<i data-lucide="alert-triangle" class="w-3.5 h-3.5 text-amber-400"></i><span>Did not run: <strong>${escapeHtml(badge.name)}</strong> - ${escapeHtml(badge.reason)}</span>`;
  } else {
    toolBadge.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400"></i><span>Completed: <strong>${escapeHtml(badge.name)}</strong></span>`;
  }
  if (typeof safeCreateIconsFn === 'function') safeCreateIconsFn();
}

export function updateStandingJobPayload(job) {
  const id = String((job && (job.jobId || job.job_id)) || '').trim();
  if (!id) return null;
  const agentId = (job && (job.agentId || job.agent_id)) || 'autoreiv';
  return {
    id,
    agentId,
    event: {
      job_id: id,
      status: (job && (job.status || job.jobStatus)) || 'queued',
      agent_id: agentId,
      phase_name: 'Author',
      phase_count: 1,
      index: 0,
    },
  };
}
