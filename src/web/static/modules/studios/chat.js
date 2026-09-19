/**
 * Chat Studio Module [REQ-FE-001, REQ-WEB-001, REQ-WEB-002]
 */

import { $, $query, safeCreateIcons } from '../dom.js';
import { escapeHtml, formatBytes, formatJsonDeliverableToMarkdown, formatSessionTimestamp } from '../utils/formatters.js';
import { copyToClipboard } from '../utils/clipboard.js';
import { storageGet, storageSet } from '../utils/storage.js';
import { showToast } from '../ui/toast.js';


// Re-export submodules for complete backward compatibility [REQ-ARCH-003]
export * from './chat/hitl.js';
export * from './chat/training.js';
export * from './chat/scroll.js';
export * from './chat/stream.js';

import {
  formatHitlArgs,
  readLastApprovalAutoRun,
  writeLastApprovalAutoRun,
  pendingApprovalsUrl,
  pendingHitlLabel,
  shouldResumeChatAfterHitl,
  shouldSkipPendingHitlCard,
  buildHitlCardInnerHtml,
  submitHitlDecision,
  hasVisibleHitlCard,
  isGoalPlanReviewTool,
} from './chat/hitl.js';

import {
  buildTrainAgentPayload,
  submitTrainAgentJob,
  populateTrainAgentTargetOptions,
  updateTrainAgentLiveIndicator,
} from './chat/training.js';

import {
  isScrolledNearBottom,
  shouldAutoscrollOnStream,
  shouldShowJumpToLatest,
  isChatSessionsDrawerOpen,
  openChatSessionsDrawer,
  collapseChatSessionsDrawer,
} from './chat/scroll.js';

import {
  buildChatStreamPayload,
  querySessionStatus,
  formatContextBudgetBadge,
  filterToolsList,
  querySessionContext,
  postSessionCompaction,
  prepareNewAgentAuthoringSession,
  renderAgentHandoffCardHtml,
} from './chat/stream.js';

// Explicitly defined in chat.js to maintain AST and text regex invariants [CARD-119 / REQ-FACT-048]
export function isAgentVisibleInChat(agent) {
  if (agent == null) return true;
  if (agent.id === 'agent-builder' || agent.id === 'coding' || agent.id === 'review' || agent.id === 'conductor' || agent.id === 'hyperv' || agent.id === 'assistant' || agent.id === 'wiki') return false;
  if (agent.visibility === 'internal') return false;
  return agent.show_in_chat !== false;
}

export function agentsVisibleInChat(agents) {
  return (agents || []).filter(isAgentVisibleInChat);
}

// ADR-0054 / CARD-361: Dual-Engine Front Door channels (AutoReiv Core & Direct Mode)
export const DUAL_ENGINE_IDS = Object.freeze(['autoreiv', 'direct']);

export function dualEngineAgentsVisibleInChat(agents) {
  return agentsVisibleInChat(agents).filter((a) => DUAL_ENGINE_IDS.includes(a.id));
}

export const JOB_PHASE_REACT_STATES = Object.freeze([
  'THINKING',
  'CALLING_TOOLS',
  'PARKED',
  'DONE',
  'FAILED',
]);

/** SSE event types that drive the shared Job phase strip (Chat + Education origin). [CARD-240] */
export const JOB_PHASE_CHROME_EVENTS = Object.freeze([
  'job_created',
  'resumed_from_checkpoint',
  'phase_start',
  'phase_complete',
  'react_state',
  'plan_formulated',
  'approval_required',
]);

export function isJobPhaseChromeEvent(eventType) {
  return JOB_PHASE_CHROME_EVENTS.includes(String(eventType || ''));
}

export function humanizeJobStatus(status) {
  const raw = String(status || "").trim();
  if (!raw || raw.toLowerCase() === "unknown") return "";
  return raw.replace(/_/g, " ");
}

export function formatJobPhaseStrip(state) {
  const jobId = (state && (state.jobId || state.job_id)) || "";
  const jobStatus = humanizeJobStatus(state && state.jobStatus);
  const phaseName = (state && state.phaseName) || "";
  const phaseIndex = state && state.phaseIndex;
  const phaseCount = state && state.phaseCount;
  let phaseLabel = phaseName || "Phase";
  if (phaseIndex != null && phaseIndex !== "") {
    const n = Number(phaseIndex) + 1;
    if (phaseCount != null && phaseCount !== "") {
      phaseLabel = `Phase ${n}/${phaseCount} ${phaseName}`.trim();
    } else {
      phaseLabel = `Phase ${n} ${phaseName}`.trim();
    }
  }
  const agent = (state && (state.assignedAgentId || state.agentId)) || "agent";
  const reactState = String((state && state.reactState) || "").toUpperCase();
  const resumed = Boolean(state && state.resumedFromCheckpoint);
  let jobStatusLabel = jobStatus ? `Job ${jobStatus}` : (jobId ? "Job" : "");
  if (resumed && jobStatusLabel) {
    jobStatusLabel = `${jobStatusLabel} | Resumed (resumed_from_checkpoint)`;
  }
  const parentJobId = (state && (state.parentJobId || state.parent_job_id)) || "";
  const childJobId = (state && (state.childJobId || state.child_job_id)) || "";
  const childJobIds = (state && (state.childJobIds || state.child_job_ids)) || [];
  let parentChildLabel = "";
  if (parentJobId && (childJobId || (Array.isArray(childJobIds) && childJobIds.length))) {
    const childBit = childJobId || childJobIds[0];
    parentChildLabel = `parent↔child ${parentJobId} ↔ ${childBit}`;
  } else if (childJobId || (Array.isArray(childJobIds) && childJobIds.length)) {
    const childBit = childJobId || childJobIds[0];
    parentChildLabel = `parent↔child → ${childBit}`;
  } else if (parentJobId) {
    parentChildLabel = `parent↔child ← ${parentJobId}`;
  }
  return {
    jobStatusLabel,
    phaseLabel,
    agentLabel: agent,
    reactState,
    resumedFromCheckpoint: resumed,
    jobId,
    parentJobId,
    childJobId,
    childJobIds,
    parentChildLabel,
  };
}

export function reactStateToneClass(reactState) {
  switch (String(reactState || '').toUpperCase()) {
    case 'PARKED':
      return 'job-phase-react px-2 py-0.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300 font-semibold tracking-wide';
    case 'FAILED':
      return 'job-phase-react px-2 py-0.5 rounded bg-rose-950/80 border border-rose-800 text-rose-300 font-semibold tracking-wide';
    case 'DONE':
      return 'job-phase-react px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-semibold tracking-wide';
    case 'CALLING_TOOLS':
      return 'job-phase-react px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-800 text-indigo-300 font-semibold tracking-wide';
    case 'THINKING':
      return 'job-phase-react px-2 py-0.5 rounded bg-sky-950/80 border border-sky-800 text-sky-300 font-semibold tracking-wide';
    default:
      return 'job-phase-react px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-semibold tracking-wide';
  }
}

export function isHitlParkSseEvent(eventType, ev = {}) {
  const type = String(eventType || '');
  if (type === 'approval_required') return true;
  const data = ev || {};
  const status = String(data.status || data.job_status || '').toLowerCase();
  const react = String(data.react_state || '').toUpperCase();
  if (type === 'phase_complete' || type === 'react_state' || type === 'turn_done') {
    if (status === 'waiting_approval' || react === 'PARKED') return true;
    if (data.waiting_approval || data.need_sources) return true;
  }
  return false;
}

/**
 * Rebuild Job phase strip state from /api/chat/sessions/:id/journey so refresh
 * keeps Formulate/Execute chrome bound to the same job_id [CARD-295].
 */
export function hydrateJobPhaseStateFromJourney(journey) {
  const jobs = journey && Array.isArray(journey.jobs) ? journey.jobs : [];
  if (!jobs.length) return null;
  const rank = (status) => {
    const s = String(status || '').toLowerCase();
    if (s === 'waiting_approval') return 0;
    if (s === 'running' || s === 'in_progress' || s === 'queued') return 1;
    if (s === 'failed') return 2;
    return 3;
  };
  const sorted = [...jobs].sort((a, b) => rank(a.status) - rank(b.status));
  const job = sorted[0];
  if (!job || !job.id) return null;
  const phases = Array.isArray(job.phases) ? [...job.phases].sort((a, b) => Number(a.index || 0) - Number(b.index || 0)) : [];
  const activePhase = phases.find((p) => {
    const s = String(p.status || '').toLowerCase();
    return s === 'waiting_approval' || s === 'running' || s === 'in_progress';
  }) || phases[phases.length - 1] || null;
  const jobStatus = String(job.status || '').toLowerCase() || 'unknown';
  const next = {
    jobId: job.id,
    jobStatus,
    phaseCount: phases.length || undefined,
    phaseName: activePhase ? activePhase.name : undefined,
    phaseIndex: activePhase != null && activePhase.index != null ? activePhase.index : undefined,
    phaseId: activePhase ? activePhase.id : undefined,
    assignedAgentId: activePhase ? activePhase.assigned_agent_id : undefined,
  };
  if (jobStatus === 'waiting_approval' || (activePhase && String(activePhase.status || '').toLowerCase() === 'waiting_approval')) {
    next.reactState = 'PARKED';
    next.jobStatus = 'waiting_approval';
  } else if (jobStatus === 'running' || jobStatus === 'in_progress') {
    next.reactState = next.reactState || 'THINKING';
  } else if (jobStatus === 'done') {
    next.reactState = 'DONE';
  } else if (jobStatus === 'failed') {
    next.reactState = 'FAILED';
  }
  return next;
}

export function applyJobPhaseEvent(current, eventType, ev) {
  const next = { ...(current || {}) };
  const data = ev || {};
  if (data.job_id) next.jobId = data.job_id;
  if (data.phase_id) next.phaseId = data.phase_id;
  if (data.phase_name) next.phaseName = data.phase_name;
  if (data.assigned_agent_id) next.assignedAgentId = data.assigned_agent_id;
  if (data.agent_id && !next.assignedAgentId) next.assignedAgentId = data.agent_id;
  if (data.job_status) next.jobStatus = data.job_status;
  if (data.react_state) next.reactState = data.react_state;
  if (data.phase_count != null) next.phaseCount = data.phase_count;
  if (data.index != null) next.phaseIndex = data.index;

  if (eventType === 'job_created') {
    next.jobId = data.job_id || next.jobId;
    next.jobStatus = data.status || next.jobStatus || 'queued';
    next.assignedAgentId = data.agent_id || next.assignedAgentId;
    next.phaseCount = data.phase_count != null ? data.phase_count : next.phaseCount;
    if (data.status === 'waiting_approval') {
      next.reactState = next.reactState || 'PARKED';
    }
  } else if (eventType === 'phase_start') {
    if (!next.jobStatus || next.jobStatus === 'queued') {
      next.jobStatus = 'running';
    }
    if (!next.reactState) next.reactState = 'THINKING';
  } else if (eventType === 'phase_complete') {
    if (data.status) next.jobStatus = data.status;
    if (data.react_state) next.reactState = data.react_state;
  } else if (eventType === 'react_state') {
    if (data.react_state) next.reactState = data.react_state;
    if (data.job_status) next.jobStatus = data.job_status;
  } else if (eventType === 'resumed_from_checkpoint') {
    next.resumedFromCheckpoint = true;
    if (data.job_id) next.jobId = data.job_id;
    if (data.phase_index != null) next.phaseIndex = data.phase_index;
    if (data.phase_id) next.phaseId = data.phase_id;
    if (data.verifier_status) next.verifyStatus = data.verifier_status;
    if (data.hitl_park_state) next.reactState = next.reactState || 'PARKED';
    if (!next.jobStatus || next.jobStatus === 'queued') next.jobStatus = 'running';
  } else if (eventType === 'plan_formulated') {
    if (data.job_id) next.jobId = data.job_id;
    if (Array.isArray(data.steps)) next.phaseCount = data.steps.length;
    if (data.standing) {
      next.jobStatus = next.jobStatus || data.status || 'queued';
    } else {
      next.jobStatus = next.jobStatus || 'waiting_approval';
      next.reactState = next.reactState || 'PARKED';
    }
  } else if (eventType === 'approval_required') {
    next.reactState = data.react_state || next.reactState || 'PARKED';
    next.jobStatus = data.job_status || next.jobStatus || 'waiting_approval';
  } else if (eventType === 'supervisor_pick' || eventType === 'a2a_child') {
    if (data.parent_job_id) next.parentJobId = data.parent_job_id;
    if (data.child_job_id) next.childJobId = data.child_job_id;
    if (Array.isArray(data.child_job_ids)) next.childJobIds = data.child_job_ids;
    if (data.picked_agent_id) next.assignedAgentId = data.picked_agent_id;
  }
  if (data.parent_job_id) next.parentJobId = data.parent_job_id;
  if (data.child_job_id) next.childJobId = data.child_job_id;
  if (Array.isArray(data.child_job_ids)) next.childJobIds = data.child_job_ids;
  return next;
}

/**
 * Inline Job chrome (grape-vine Formulate/Execute + plan-steps).
 * Reused by Chat Ask stream bubble path and Education origin forwarder [CARD-240 AC].
 */
export function createInlineJobChromeModel() {
  return {
    phases: {},
    phaseOrder: [],
    goal: '',
    steps: [],
    streaming: true,
  };
}

export function shouldMountInlineJobChrome(model) {
  if (!model) return false;
  const hasPhases = (model.phaseOrder || []).length > 0;
  const hasSteps = (model.steps || []).length > 0;
  return Boolean(hasPhases || hasSteps);
}


export function applyInlineJobChromeModel(model, eventType, ev) {
  const next = model || createInlineJobChromeModel();
  const data = ev || {};
  const type = String(eventType || '');

  if (data.assigned_agent_id) next.assignedAgentId = data.assigned_agent_id;
  if (data.agent_id && !next.assignedAgentId) next.assignedAgentId = data.agent_id;
  if (data.agent_name) next.agentName = data.agent_name;

  const upsertPhase = (name, status, index) => {
    const key = String(name || '').trim() || `Phase ${(index != null ? Number(index) + 1 : next.phaseOrder.length + 1)}`;
    if (!next.phases[key]) {
      next.phaseOrder.push(key);
      next.phases[key] = {
        name: key,
        status: status || 'pending',
        index: index != null ? Number(index) : next.phaseOrder.length - 1,
      };
    } else {
      if (status) next.phases[key].status = status;
      if (index != null) next.phases[key].index = Number(index);
    }
  };

  if (type === 'phase_start') {
    upsertPhase(data.phase_name || data.phaseName, 'running', data.index);
    next.streaming = true;
  } else if (type === 'phase_complete') {
    const st = String(data.status || 'done').toLowerCase();
    const norm = st === 'failed' || st === 'error' ? 'failed' : 'done';
    upsertPhase(data.phase_name || data.phaseName, norm, data.index);
  } else if (type === 'plan_formulated') {
    next.goal = data.goal || next.goal || 'Execution Plan';
    if (Array.isArray(data.steps)) {
      next.steps = data.steps.map((s) => ({
        title: (s && (s.title || s.action || s.name)) || 'step',
        status: 'pending',
      }));
    }
    if (!next.phaseOrder.length) {
      upsertPhase('Formulate', 'running', 0);
    }
  } else if (type === 'step_start') {
    const idx = data.step_index !== undefined ? Number(data.step_index) : -1;
    if (idx >= 0 && next.steps[idx]) next.steps[idx].status = 'running';
  } else if (type === 'step_complete') {
    const idx = data.step_index !== undefined ? Number(data.step_index) : -1;
    if (idx >= 0 && next.steps[idx]) next.steps[idx].status = 'done';
  } else if (type === 'approval_required') {
    next.streaming = false;
  } else if (type === 'job_created') {
    next.streaming = true;
    if (data.phase_count != null && Number(data.phase_count) >= 2 && !next.phaseOrder.length) {
      upsertPhase('Formulate', 'pending', 0);
      upsertPhase('Execute', 'pending', 1);
    }
  }
  return next;
}

export function escapeChromeText(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function formatMilestoneGoalTitle(rawGoal, maxLength = 80) {
  if (!rawGoal || typeof rawGoal !== 'string') return 'Execution Plan';
  const lines = rawGoal.split('\n').map((l) => l.trim()).filter(Boolean);
  const firstCleanLine = lines.find((l) => !l.startsWith('[Attachment:')) || lines[0] || '';
  const sanitized = firstCleanLine.replace(/\[Attachment:[^\]]*\]/gi, '').trim();
  if (!sanitized) return 'Execution Plan';
  if (sanitized.length <= maxLength) return sanitized;
  return sanitized.slice(0, maxLength - 3).trimEnd() + '...';
}

export function formatJobChromePhasesRowsHtml(model) {
  const m = model || createInlineJobChromeModel();
  return (m.phaseOrder || []).map((key) => {
    const p = m.phases[key] || { name: key, status: 'pending' };
    const status = String(p.status || 'pending').toLowerCase();
    const isDone = status === 'done';
    const isRunning = status === 'running' || status === 'waiting_approval';
    const isFailed = status === 'failed' || status === 'error';
    const label = isDone ? 'Done' : (isRunning ? 'Running...' : (isFailed ? 'Failed' : 'Pending'));
    const rowTone = isDone
      ? 'border-emerald-500/40 bg-emerald-950/30 text-emerald-200'
      : (isRunning
        ? 'border-indigo-500/50 bg-indigo-950/40 text-indigo-200 ring-1 ring-indigo-500/20'
        : (isFailed ? 'border-rose-500/40 bg-rose-950/30 text-rose-200' : 'border-slate-700/60 bg-slate-800/40 text-slate-300'));
    const icon = isDone ? '✓' : (isRunning ? '⚡' : (isFailed ? '!' : '·'));
    const labelTone = isDone ? 'text-emerald-300' : (isRunning ? 'text-indigo-300 animate-pulse' : 'text-slate-400');
    return `
      <div data-phase-chrome="${escapeChromeText(p.name)}" data-phase-status="${escapeChromeText(status)}"
           class="job-chrome-phase flex items-center justify-between px-2.5 py-1.5 rounded-lg border ${rowTone} text-xs">
        <span class="flex items-center gap-1.5 font-semibold">
          <span aria-hidden="true">${icon}</span>
          <span>${escapeChromeText(p.name)}</span>
        </span>
        <span class="font-mono text-[10px] uppercase tracking-wide ${labelTone}">${label}</span>
      </div>`;
  }).join('');
}

export function renderJobChromePhasesIntoElement(containerEl, model) {
  if (!containerEl) return;
  const phasesEl = containerEl.querySelector
    ? (containerEl.querySelector('.job-chrome-phases') || containerEl.querySelector('[data-job-chrome-phases="1"]'))
    : null;
  if (!phasesEl) return;
  const rowsHtml = formatJobChromePhasesRowsHtml(model);
  phasesEl.innerHTML = rowsHtml;
  if (rowsHtml.trim()) {
    if (typeof phasesEl.classList?.remove === 'function') phasesEl.classList.remove('hidden');
  } else {
    if (typeof phasesEl.classList?.add === 'function') phasesEl.classList.add('hidden');
  }
}

export function formatInlineJobChromeHtml(model) {
  const m = model || createInlineJobChromeModel();
  const phaseRows = formatJobChromePhasesRowsHtml(m);

  const steps = Array.isArray(m.steps) ? m.steps : [];
  const stepsHtml = steps.map((s, idx) => {
    const st = String(s.status || 'pending').toLowerCase();
    const running = st === 'running';
    const done = st === 'done';
    const rowClass = running
      ? 'plan-step-item p-2 rounded-lg bg-indigo-950/60 border border-indigo-500/50 text-indigo-200 ring-1 ring-indigo-500/30 flex items-center justify-between text-xs transition'
      : (done
        ? 'plan-step-item p-2 rounded-lg bg-slate-800/40 border border-slate-700/40 text-slate-300 opacity-80 flex items-center justify-between text-xs transition'
        : 'plan-step-item p-2 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-between text-xs transition');
    const badge = running ? 'Running...' : (done ? 'Done' : 'Pending');
    const badgeClass = running
      ? 'step-badge text-[10px] font-mono text-indigo-400 animate-pulse shrink-0'
      : (done ? 'step-badge text-[10px] font-mono text-emerald-400 shrink-0' : 'step-badge text-[10px] font-mono text-slate-400 shrink-0');
    const icon = running ? '…' : (done ? '✓' : '○');
    return `
      <div id="plan-step-${idx}" class="${rowClass}">
        <div class="flex items-center space-x-2 truncate mr-2">
          <span class="step-status-icon text-slate-400">${icon}</span>
          <span class="step-title font-medium text-slate-200 truncate">${escapeChromeText(s.title)}</span>
        </div>
        <span class="${badgeClass}">${badge}</span>
      </div>`;
  }).join('');

  const planHidden = steps.length ? '' : 'hidden';
  const streamLabel = m.streaming ? 'STREAMING...' : 'JOB';
  const streamClass = m.streaming ? 'text-brand-400 font-mono text-[10px] animate-pulse' : 'text-slate-400 font-mono text-[10px]';
  const activeTitleEl = typeof $ === 'function' ? $('activeAgentTitle') : null;
  const agentLabel = m.agentName
    || (activeTitleEl && activeTitleEl.textContent ? activeTitleEl.textContent.trim() : '')
    || (m.assignedAgentId ? m.assignedAgentId.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : '')
    || 'Agent';

  return `
    <div class="max-w-4xl w-full rounded-2xl p-4 shadow-md bg-slate-900/90 border border-slate-800/80 text-slate-100 rounded-bl-sm space-y-3" data-job-chrome-card="1">
      <div class="flex items-center justify-between text-xs font-bold uppercase tracking-wider opacity-70">
        <span>${escapeChromeText(agentLabel)}</span>
        <span class="${streamClass}">${streamLabel}</span>
      </div>
      <div class="job-chrome-phases space-y-1.5 ${phaseRows ? '' : 'hidden'}" data-job-chrome-phases="1">
        ${phaseRows}
      </div>
      <div class="plan-milestone-card ${planHidden} rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-3 space-y-2 text-xs">
        <div class="plan-card-header flex items-center justify-between font-semibold text-indigo-300">
          <span class="flex items-center space-x-1.5">
            <span>📋</span>
            <span class="plan-goal-title">${escapeChromeText(formatMilestoneGoalTitle(m.goal))}</span>
          </span>
          <span class="plan-step-counter text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-900/60 text-indigo-300">${steps.length} STEPS</span>
        </div>
        <div class="plan-steps-container space-y-1.5 pt-1">${stepsHtml}</div>
      </div>
    </div>`.trim();
}

export function buildInlineJobChromeBubble() {
  if (typeof document === 'undefined' || !document.createElement) {
    return {
      className: 'flex justify-start w-full',
      innerHTML: '',
      attributes: { 'data-job-chrome': 'inline' },
      setAttribute(k, v) { this.attributes[k] = v; },
      getAttribute(k) { return this.attributes[k]; },
      querySelector(sel) {
        const html = this.innerHTML || '';
        if (sel === '.plan-steps-container') {
          return html.includes('plan-steps-container') ? { classList: { contains: () => false } } : null;
        }
        if (sel === '.plan-milestone-card') {
          const hidden = /plan-milestone-card\s+hidden/.test(html);
          return { classList: { contains: (c) => c === 'hidden' && hidden } };
        }
        if (sel && sel.startsWith('[data-phase-chrome=')) {
          const name = sel.match(/data-phase-chrome=["']([^"']+)/);
          if (name && html.includes(`data-phase-chrome="${name[1]}"`)) return {};
          return null;
        }
        return null;
      },
      querySelectorAll(sel) {
        if (sel === '.plan-step-item') {
          const matches = (this.innerHTML || '').match(/plan-step-item/g) || [];
          return matches.map(() => ({}));
        }
        return [];
      },
    };
  }
  const wrap = document.createElement('div');
  wrap.className = 'flex justify-start w-full';
  wrap.setAttribute('data-job-chrome', 'inline');
  wrap.innerHTML = formatInlineJobChromeHtml(createInlineJobChromeModel());
  return wrap;
}

export function applyInlineJobChromeEvent(bubble, eventType, ev, priorModel) {
  if (!bubble) {
    return applyInlineJobChromeModel(priorModel || createInlineJobChromeModel(), eventType, ev);
  }
  const prev = priorModel || bubble.__jobChromeModel || createInlineJobChromeModel();
  const next = applyInlineJobChromeModel(prev, eventType, ev);
  bubble.__jobChromeModel = next;
  bubble.innerHTML = formatInlineJobChromeHtml(next);
  if (typeof bubble.setAttribute === 'function') bubble.setAttribute('data-job-chrome', 'inline');
  return next;
}

export function renderReflexionBadge(badgeEl, eventType, ev = {}) {
  if (!badgeEl) return;
  if (typeof badgeEl.classList?.remove === 'function') badgeEl.classList.remove('hidden');
  if (typeof badgeEl.classList?.add === 'function') badgeEl.classList.add('flex', 'flex-col');

  if (eventType === 'reflexion_attempt') {
    badgeEl.className = 'reflexion-status-badge p-2 rounded-lg bg-amber-950/40 border border-amber-500/30 text-xs text-amber-300 flex flex-col space-y-1';
    const checkerTag = ev.checker ? ` <span class="text-slate-400 font-mono text-[10px]">(${escapeHtml(ev.checker)})</span>` : '';
    badgeEl.innerHTML = `
      <div class="flex items-center space-x-2">
        <span>🔍</span>
        <span>Reflexion Check: <strong>Attempt ${ev.attempt || 1}/${ev.max_attempts || 1}</strong>${checkerTag}...</span>
      </div>
    `;
  } else if (eventType === 'reflexion_critique') {
    badgeEl.className = 'reflexion-status-badge p-2 rounded-lg bg-amber-950/60 border border-amber-500/50 text-xs text-amber-200 flex flex-col space-y-1';
    const critiqueText = ev.critique || 'Refining output...';
    badgeEl.innerHTML = `
      <div class="flex items-center justify-between cursor-pointer reflexion-badge-toggle" title="Click to toggle critique details">
        <div class="flex items-center space-x-2">
          <span>⚠️</span>
          <span>Critique: <strong class="text-amber-100">${escapeHtml(critiqueText)}</strong></span>
        </div>
        <span class="text-[10px] text-amber-400 font-mono hover:underline">Details ▾</span>
      </div>
      <div class="reflexion-details hidden mt-1 pt-1 border-t border-amber-500/30 font-mono text-[11px] text-amber-100 whitespace-pre-wrap">
        ${escapeHtml(JSON.stringify(ev.discrepancies || critiqueText, null, 2))}
      </div>
    `;
    const toggle = badgeEl.querySelector('.reflexion-badge-toggle');
    const details = badgeEl.querySelector('.reflexion-details');
    if (toggle && details && typeof toggle.addEventListener === 'function') {
      toggle.addEventListener('click', () => {
        if (typeof details.classList?.toggle === 'function') {
          details.classList.toggle('hidden');
        }
      });
    }
  } else if (eventType === 'reflexion_verified') {
    const passed = Boolean(ev.passed);
    const skipped = ev.status === 'skipped' || ev.status === 'skipped_no_checker';
    const hasDiscrepancies = Array.isArray(ev.discrepancies) && ev.discrepancies.length > 0;
    const checker = ev.checker || '';
    const checkerTag = checker ? ` <span class="text-slate-400 font-mono text-[10px]">(${escapeHtml(checker)})</span>` : '';

    if (passed) {
      badgeEl.className = 'reflexion-status-badge p-2 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-xs text-emerald-300 flex flex-col space-y-1';
      badgeEl.innerHTML = `
        <div class="flex items-center justify-between cursor-pointer reflexion-badge-toggle" title="Click to toggle verification details">
          <div class="flex items-center space-x-2">
            <span>✅</span>
            <span>Self-Verification <strong>Passed</strong>!${checkerTag}</span>
          </div>
          <span class="text-[10px] text-emerald-400 font-mono hover:underline">Details ▾</span>
        </div>
        <div class="reflexion-details hidden mt-1 pt-1 border-t border-emerald-500/30 font-mono text-[11px] text-emerald-200">
          Status: Verified • Checker: ${escapeHtml(checker || 'default')}
        </div>
      `;
    } else if (skipped) {
      badgeEl.className = 'reflexion-status-badge p-2 rounded-lg bg-slate-800/80 border border-slate-700 text-xs text-slate-300 flex flex-col space-y-1';
      badgeEl.innerHTML = `
        <div class="flex items-center space-x-2">
          <span>ℹ️</span>
          <span>Self-Verification: <em>skipped_no_checker</em> (no named checker)</span>
        </div>
      `;
    } else {
      const status = ev.status || 'unverified';
      badgeEl.className = 'reflexion-status-badge p-2 rounded-lg bg-rose-950/40 border border-rose-500/30 text-xs text-rose-300 flex flex-col space-y-1';
      badgeEl.innerHTML = `
        <div class="flex items-center justify-between cursor-pointer reflexion-badge-toggle" title="Click to toggle failure details">
          <div class="flex items-center space-x-2">
            <span>❌</span>
            <span>Self-Verification <strong>Failed</strong> (${escapeHtml(status)})${checkerTag}</span>
          </div>
          <span class="text-[10px] text-rose-400 font-mono hover:underline">Details ▾</span>
        </div>
        <div class="reflexion-details hidden mt-1 pt-1 border-t border-rose-500/30 font-mono text-[11px] text-rose-200 whitespace-pre-wrap">
          ${escapeHtml(hasDiscrepancies ? ev.discrepancies.join('\n') : `Verification failed: ${status}`)}
        </div>
      `;
    }

    const toggle = badgeEl.querySelector('.reflexion-badge-toggle');
    const details = badgeEl.querySelector('.reflexion-details');
    if (toggle && details && typeof toggle.addEventListener === 'function') {
      toggle.addEventListener('click', () => {
        if (typeof details.classList?.toggle === 'function') {
          details.classList.toggle('hidden');
        }
      });
    }
  }
}

export function initChatStudio(state, callbacks = {}) {
  const agentSelect = $('agentSelect');
  const engineBtnCore = $('engineBtnCore');
  const engineBtnDirect = $('engineBtnDirect');
  const sessionList = $('sessionList');
  const newChatBtn = $('newChatBtn');
  const activeAgentTitle = $('activeAgentTitle');
  const activeAgentTone = $('activeAgentTone');
  const messagesContainer = $('messagesContainer');
  const chatSessionsDrawer = $('chatSessionsDrawer');
  const chatSessionsDrawerCloseBtn = $('chatSessionsDrawerCloseBtn');
  const chatJumpToLatestBtn = $('chatJumpToLatestBtn');
  const viewChat = $('view-chat');
  let chatStickToBottom = true;

  function refreshJumpToLatestBtn() {
    if (!chatJumpToLatestBtn || !messagesContainer) return;
    const hasOverflow = messagesContainer.scrollHeight > messagesContainer.clientHeight + 4;
    const show = shouldShowJumpToLatest({ stickToBottom: chatStickToBottom, hasOverflow });
    chatJumpToLatestBtn.classList.toggle('hidden', !show);
    chatJumpToLatestBtn.classList.toggle('flex', show);
  }

  function maybeAutoscrollMessages() {
    if (!messagesContainer) return;
    if (shouldAutoscrollOnStream(chatStickToBottom)) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    refreshJumpToLatestBtn();
  }

  function jumpMessagesToLatest() {
    chatStickToBottom = true;
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    refreshJumpToLatestBtn();
  }

  if (messagesContainer) {
    messagesContainer.addEventListener('scroll', () => {
      chatStickToBottom = isScrolledNearBottom(messagesContainer);
      refreshJumpToLatestBtn();
    }, { passive: true });
  }
  if (chatJumpToLatestBtn) {
    chatJumpToLatestBtn.addEventListener('click', jumpMessagesToLatest);
  }
  if (chatSessionsDrawerCloseBtn) {
    chatSessionsDrawerCloseBtn.addEventListener('click', () => {
      collapseChatSessionsDrawer(chatSessionsDrawer, viewChat);
    });
  }
  // Legacy sidebar toggle (non-capture) also opens in-studio drawer when present
  const toggleSidebarBtn = $('toggleSidebarBtn');
  if (toggleSidebarBtn && !toggleSidebarBtn.dataset.card296Bound) {
    toggleSidebarBtn.dataset.card296Bound = '1';
    toggleSidebarBtn.addEventListener('click', () => {
      // Desktop capture handler in agent-desktop runs first; this covers non-desktop.
      if (document.body.classList.contains('radical-desktop-demo')) return;
      if (!chatSessionsDrawer) return;
      if (isChatSessionsDrawerOpen(chatSessionsDrawer)) {
        collapseChatSessionsDrawer(chatSessionsDrawer, viewChat);
      } else {
        openChatSessionsDrawer(chatSessionsDrawer, viewChat);
      }
    });
  }

  const chatForm = $('chatForm');
  const promptInput = $('promptInput');
  const sendBtn = $('sendBtn');
  const stopBtn = $('stopBtn');
  let activeAbortController = null;
  let backgroundPollInterval = null;
  let isCheckingBackgroundStatus = false;
  const copyThreadBtn = $('copyThreadBtn');
  const exportThreadWikiBtn = $('exportThreadWikiBtn');
  const verifyToggle = $('verifyToggle');
  const approvalToggle = $('approvalToggle');
  const approvalBadge = $('approvalBadge');
  const verifyBadge = $('verifyBadge');
  const goalBadge = $('goalBadge');
  const trainAgentToggle = $('trainAgentToggle');
  const trainAgentBadge = $('trainAgentBadge');
  const trainAgentHandshakeModal = $('trainAgentHandshakeModal');
  const trainAgentTargetSelect = $('trainAgentTargetSelect');
  const trainAgentLiveInfo = $('trainAgentLiveInfo');
  const trainAgentLivePackPath = $('trainAgentLivePackPath');
  const trainAgentLiveCounts = $('trainAgentLiveCounts');
  const trainAgentLiveInfoText = $('trainAgentLiveInfoText');
  const closeTrainAgentModalBtn = $('closeTrainAgentModalBtn');
  const cancelTrainAgentBtn = $('cancelTrainAgentBtn');
  const startTrainAgentBtn = $('startTrainAgentBtn');
  const trainTargetLocation = $('trainTargetLocation');
  const trainSeedObjectives = $('trainSeedObjectives');
  const trainRequireApproval = $('trainRequireApproval');
  const chatOptionsToggleBtn = $('chatOptionsToggleBtn');
  const chatOptionsToggleIcon = $('chatOptionsToggleIcon');
  const chatOptionsDrawer = $('chatOptionsDrawer');
  const chatOptionsCloseBtn = $('chatOptionsCloseBtn');
  // CARD-215/235: Goal suggestion theatre retired — no chip / Enable / dismiss controls.

  // Context Budget & Compaction [CARD-161]
  const chatContextTokensBadge = $('chatContextTokensBadge');
  const chatContextProgressBar = $('chatContextProgressBar');
  const chatManualCompactBtn = $('chatManualCompactBtn');

  // Loaded Tools Inspector [CARD-161]
  const chatToolsCountBadge = $('chatToolsCountBadge');
  const chatViewToolsBtn = $('chatViewToolsBtn');
  const chatToolsModal = $('chatToolsModal');
  const chatToolsModalTitle = $('chatToolsModalTitle');
  const chatToolsModalBadge = $('chatToolsModalBadge');
  const chatToolsSearchInput = $('chatToolsSearchInput');
  const chatToolsModalList = $('chatToolsModalList');
  const chatToolsModalCloseBtn = $('chatToolsModalCloseBtn');
  const chatToolsModalDismissBtn = $('chatToolsModalDismissBtn');
  let cachedSessionContext = null;

  // Media & File Attachments [CARD-143]
  const chatAttachBtn = $('chatAttachBtn');
  const chatFileInput = $('chatFileInput');
  const chatAttachmentsPreviewList = $('chatAttachmentsPreviewList');
  let stagedAttachments = [];

  // Lightweight Quick Prompt Picker [CARD-152]
  const chatPromptsBtn = $('chatPromptsBtn');
  const chatPromptsQuickPicker = $('chatPromptsQuickPicker');
  const chatPromptsQuickSearch = $('chatPromptsQuickSearch');
  const chatPromptsQuickList = $('chatPromptsQuickList');
  const chatManagePromptsBtn = $('chatManagePromptsBtn');
  let quickPrompts = [];

  const pendingHitlHost = $('pendingHitlHost');

  // Journey & Debug Inspectors [CARD-135, CARD-136]
  const chatShowJourneyBtn = $('chatShowJourneyBtn');
  const chatJourneyDrawer = $('chatJourneyDrawer');
  const chatJourneyCloseBtn = $('chatJourneyCloseBtn');
  const chatJourneyContent = $('chatJourneyContent');

  const chatDebugToggleBtn = $('chatDebugToggleBtn');
  const chatDebugPane = $('chatDebugPane');
  const chatDebugCloseBtn = $('chatDebugCloseBtn');
  const chatDebugCopyBtn = $('chatDebugCopyBtn');
  const chatDebugContent = $('chatDebugContent');
  const chatDebugTabMessages = $('chatDebugTabMessages');
  const chatDebugTabTools = $('chatDebugTabTools');
  const chatDebugTabMetrics = $('chatDebugTabMetrics');
  const chatDebugTabSystem = $('chatDebugTabSystem');
  let activeDebugData = null;
  let activeDebugTab = 'messages';

  // CARD-307: close + Options when opening Journey/Debug
  function closeChatOptionsDrawer() {
    if (!chatOptionsDrawer) return;
    chatOptionsDrawer.classList.add('hidden');
    if (chatOptionsToggleBtn) chatOptionsToggleBtn.setAttribute('aria-expanded', 'false');
  }

  // Teach Agent & Skill Distillation Subsystem [CARD-352, REQ-SKIL-011]
  const teachAgentModal = $('teachAgentModal');
  const closeTeachAgentModalBtn = $('closeTeachAgentModalBtn');
  const cancelTeachAgentBtn = $('cancelTeachAgentBtn');
  const submitTeachAgentBtn = $('submitTeachAgentBtn');
  const teachAgentTargetAgentBadge = $('teachAgentTargetAgentBadge');
  const teachAgentGuidanceInput = $('teachAgentGuidanceInput');
  const teachAgentErrorMsg = $('teachAgentErrorMsg');

  let currentTeachMessageId = null;
  let currentTeachTargetAgent = null;

  function openTeachAgentModal(opts = {}) {
    currentTeachMessageId = opts.messageId || null;
    currentTeachTargetAgent = opts.targetAgentId || state.selectedAgentId || 'autoreiv';

    if (teachAgentTargetAgentBadge) {
      teachAgentTargetAgentBadge.textContent = currentTeachTargetAgent;
    }
    if (teachAgentGuidanceInput) {
      teachAgentGuidanceInput.value = opts.guidance || '';
    }
    if (teachAgentErrorMsg) {
      teachAgentErrorMsg.classList.add('hidden');
      teachAgentErrorMsg.textContent = '';
    }
    if (teachAgentModal) {
      teachAgentModal.classList.remove('hidden');
    }
    if (teachAgentGuidanceInput) {
      setTimeout(() => teachAgentGuidanceInput.focus(), 50);
    }
    safeCreateIcons();
  }

  function closeTeachAgentModal() {
    if (teachAgentModal) {
      teachAgentModal.classList.add('hidden');
    }
    currentTeachMessageId = null;
  }

  if (closeTeachAgentModalBtn) closeTeachAgentModalBtn.addEventListener('click', closeTeachAgentModal);
  if (cancelTeachAgentBtn) cancelTeachAgentBtn.addEventListener('click', closeTeachAgentModal);

  if (submitTeachAgentBtn) {
    submitTeachAgentBtn.addEventListener('click', async () => {
      if (!state.activeSessionId) {
        showToast('No active conversation session to distill from.', 'warning');
        return;
      }
      submitTeachAgentBtn.disabled = true;
      const originalHtml = submitTeachAgentBtn.innerHTML;
      submitTeachAgentBtn.innerHTML = '<span>⏳ Diagnosing turn...</span>';
      if (teachAgentErrorMsg) teachAgentErrorMsg.classList.add('hidden');

      try {
        const payload = {
          session_id: state.activeSessionId,
          message_id: currentTeachMessageId,
          guidance: teachAgentGuidanceInput ? teachAgentGuidanceInput.value.trim() : null,
          target_agent_id: currentTeachTargetAgent || state.selectedAgentId || 'autoreiv',
        };

        const res = await fetch('/api/skills/distill', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `HTTP ${res.status}`);
        }

        const proposal = await res.json();
        closeTeachAgentModal();
        if (state.activeSessionId) {
          await loadMessages(state.activeSessionId, { force: true });
        } else {
          renderSkillProposalCard(proposal);
        }
        showToast('Skill proposal generated from turn context.', 'success');
      } catch (err) {
        if (teachAgentErrorMsg) {
          teachAgentErrorMsg.textContent = `Distillation error: ${err.message}`;
          teachAgentErrorMsg.classList.remove('hidden');
        }
        showToast(`Distillation failed: ${err.message}`, 'error');
      } finally {
        submitTeachAgentBtn.disabled = false;
        submitTeachAgentBtn.innerHTML = originalHtml;
        safeCreateIcons();
      }
    });
  }

  function renderSkillProposalCard(proposal) {
    if (!messagesContainer || !proposal) return;

    const messageId = proposal.message_id || '';
    if (messageId && messagesContainer.querySelector(`.skill-proposal-card[data-message-id="${messageId}"]`)) {
      return;
    }

    const el = document.createElement('div');
    el.className = 'skill-proposal-card flex justify-start w-full my-3';
    el.dataset.skillId = proposal.skill_id || '';
    el.dataset.targetAgentId = proposal.target_agent_id || state.selectedAgentId || 'autoreiv';
    el.dataset.runbookMarkdown = proposal.runbook_markdown || '';
    el.dataset.messageId = messageId;
    if (proposal.factory_escalation) {
      el.dataset.factoryEscalation = JSON.stringify(proposal.factory_escalation);
    }

    const isAdopted = proposal.adoption_state === 'adopted' || proposal.status === 'adopted';
    if (isAdopted) {
      el.dataset.adopted = 'true';
    }

    const needsTool = Boolean(proposal.needs_tool);
    const slipText = proposal.plain_summary?.observed_slip || 'Procedural friction detected.';
    const remedyText = proposal.plain_summary?.remedy || 'Standard operating procedure created.';

    let actionButtonsHtml;
    if (isAdopted) {
      actionButtonsHtml = `
        <div class="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-xs text-emerald-300 font-medium flex items-center space-x-2">
          <span>✓</span>
          <span>Skill mounted to <strong>${escapeHtml(proposal.target_agent_id || 'Agent')}</strong>. Active for your next message.</span>
        </div>
      `;
    } else if (needsTool) {
      actionButtonsHtml = `
        <button type="button" class="btn-escalate-factory flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-md shadow-indigo-600/20 transition">
          <span>🚀 Send to Factory Studio</span>
        </button>
        <button type="button" class="btn-dismiss-proposal text-xs text-slate-400 hover:text-slate-200 transition">
          ✕ Dismiss
        </button>
      `;
    } else {
      actionButtonsHtml = `
        <button type="button" class="btn-adopt-skill flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow-md shadow-emerald-600/20 transition">
          <span>✅ Adopt Skill to ${escapeHtml(proposal.target_agent_id || 'Agent')}</span>
        </button>
        <button type="button" class="btn-dismiss-proposal text-xs text-slate-400 hover:text-slate-200 transition">
          ✕ Dismiss
        </button>
      `;
    }

    el.innerHTML = `
      <div class="max-w-3xl w-full rounded-2xl p-4 shadow-lg bg-[#121520] border border-amber-500/40 text-slate-100 space-y-3.5">
        <div class="flex items-center justify-between border-b border-white/[0.08] pb-2.5">
          <div class="flex items-center space-x-2.5">
            <span class="p-1.5 rounded-lg bg-amber-500/20 text-amber-300">💡</span>
            <div>
              <h4 class="font-bold text-sm text-white">${escapeHtml(proposal.name || proposal.skill_id || 'Distilled Skill')}</h4>
              <p class="text-[11px] text-slate-400">${escapeHtml(proposal.description || '')}</p>
            </div>
          </div>
          <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/80 border border-amber-800/80 text-amber-300">Skill Proposal</span>
        </div>

        <!-- Plain-language summary (Observed Slip + Remedy) [REQ-SKIL-012] -->
        <div class="p-3 rounded-xl bg-slate-900/80 border border-white/[0.06] text-xs space-y-2">
          <div>
            <span class="font-bold text-amber-300">⚠️ Observed Slip:</span>
            <p class="text-slate-300 mt-0.5 leading-relaxed">${escapeHtml(slipText)}</p>
          </div>
          <div>
            <span class="font-bold text-emerald-300">🎯 Remedy:</span>
            <p class="text-slate-300 mt-0.5 leading-relaxed">${escapeHtml(remedyText)}</p>
          </div>
        </div>

        ${
          needsTool
            ? `
          <div class="p-3 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-xs text-indigo-200 space-y-1.5">
            <div class="flex items-center space-x-1.5 font-semibold text-indigo-300">
              <span>⚙️</span>
              <span>Missing Native Tool Detected</span>
            </div>
            <p class="text-slate-300 leading-relaxed">This capability requires writing new host code or an API tool, which needs sandbox verification in Factory Studio.</p>
          </div>
        `
            : `
          <!-- Accordion preview for raw SKILL.md -->
          <details class="group rounded-xl bg-slate-900/50 border border-slate-800 p-2.5 text-xs">
            <summary class="cursor-pointer font-medium text-slate-400 group-hover:text-slate-200 flex items-center justify-between select-none list-none">
              <span>📄 View Raw Runbook (SKILL.md)</span>
              <span class="text-[10px] text-slate-500 group-open:rotate-180 transition-transform">▼</span>
            </summary>
            <div class="mt-2.5 pt-2.5 border-t border-slate-800 font-mono text-[11px] text-slate-300 whitespace-pre-wrap max-h-56 overflow-y-auto bg-slate-950 p-2 rounded">
              ${escapeHtml(proposal.runbook_markdown || '')}
            </div>
          </details>
        `
        }

        <!-- Action buttons [REQ-SKIL-012, REQ-SKIL-013, REQ-SKIL-014, REQ-SKIL-016] -->
        <div class="card-actions flex items-center justify-between pt-1">
          <div class="flex items-center space-x-2">
            ${actionButtonsHtml}
          </div>
        </div>
      </div>
    `;

    messagesContainer.appendChild(el);
    maybeAutoscrollMessages();
    safeCreateIcons();
  }

  function escalateToFactoryStudio(escalation = {}) {
    const targetAgentId = escalation.target_agent_id || state.selectedAgentId || 'autoreiv';
    if (typeof callbacks.openFactoryStudio === 'function') {
      callbacks.openFactoryStudio(targetAgentId);
    } else if (typeof callbacks.switchTab === 'function') {
      callbacks.switchTab('factory');
    }
    const intentInput = $('factoryIntakeIntentInput');
    const objInput = $('factoryIntakeObjectivesInput');
    const deliverableType = $('factoryIntakeDeliverableType');

    if (intentInput && escalation.seed_intent) {
      intentInput.value = escalation.seed_intent;
    }
    if (objInput) {
      const objectives = escalation.starter_objectives || escalation.objectives || [];
      if (Array.isArray(objectives) && objectives.length > 0) {
        objInput.value = objectives.join('\n');
      }
    }
    if (deliverableType && escalation.deliverable_type) {
      deliverableType.value = escalation.deliverable_type;
    }
    showToast('Sent to Factory Studio Intake with pre-filled objectives.', 'info');
  }

  // Dual-Pane Workbench Canvas [CARD-138]
  const chatWorkbenchPane = $('chatWorkbenchPane');
  const workbenchArtifactTitle = $('workbenchArtifactTitle');
  const workbenchArtifactMeta = $('workbenchArtifactMeta');
  const _workbenchArtifactIcon = $('workbenchArtifactIcon');
  const workbenchTabPreview = $('workbenchTabPreview');
  const workbenchTabRaw = $('workbenchTabRaw');
  const workbenchContentPreview = $('workbenchContentPreview');
  const workbenchContentRaw = $('workbenchContentRaw');
  const workbenchCopyBtn = $('workbenchCopyBtn');
  const workbenchSaveWikiBtn = $('workbenchSaveWikiBtn');
  const workbenchCloseBtn = $('workbenchCloseBtn');
  const workbenchMobileBackBtn = $('workbenchMobileBackBtn');
  const workbenchToggleBtn = $('workbenchToggleBtn');
  const workbenchArtifactBadge = $('workbenchArtifactBadge');

  let activeWorkbenchArtifact = {
    title: 'Workbench Canvas',
    meta: 'Artifact Viewer',
    content: '',
    raw: '',
  };
  let activeWorkbenchTab = 'preview';

  const jobPhaseStatusStrip = $('jobPhaseStatusStrip');
  let jobPhaseState = {};

  function resetJobPhaseStrip() {
    jobPhaseState = {};
    if (jobPhaseStatusStrip) jobPhaseStatusStrip.classList.add('hidden');
  }

  function renderJobPhaseStrip() {
    if (!jobPhaseStatusStrip) return;
    if (state.selectedAgentId === 'direct') {
      jobPhaseStatusStrip.classList.add('hidden');
      return;
    }
    const boundJobId = (jobPhaseState && (jobPhaseState.jobId || jobPhaseState.job_id)) || '';
    if (!boundJobId) {
      jobPhaseStatusStrip.classList.add('hidden');
      return;
    }
    const view = formatJobPhaseStrip(jobPhaseState);
    const jobEl = jobPhaseStatusStrip.querySelector('[data-job-phase="status"]');
    const jobIdEl = jobPhaseStatusStrip.querySelector('[data-job-phase="job-id"]');
    const copyJobBtn = jobPhaseStatusStrip.querySelector('[data-job-phase="copy-job-id"]');
    const phaseEl = jobPhaseStatusStrip.querySelector('[data-job-phase="phase"]');
    const agentEl = jobPhaseStatusStrip.querySelector('[data-job-phase="agent"]');
    const reactEl = jobPhaseStatusStrip.querySelector('[data-job-phase="react"]');
    const linkEl = jobPhaseStatusStrip.querySelector('[data-job-phase="link"]');
    if (jobEl) jobEl.textContent = view.jobStatusLabel;
    if (jobIdEl) {
      jobIdEl.textContent = boundJobId;
      jobIdEl.classList.remove('hidden');
    }
    if (copyJobBtn) {
      copyJobBtn.dataset.jobId = boundJobId;
      copyJobBtn.classList.remove('hidden');
    }
    if (phaseEl) {
      phaseEl.textContent = view.phaseLabel || 'Phase';
      if (view.phaseLabel) {
        phaseEl.classList.remove('hidden');
      } else {
        phaseEl.classList.add('hidden');
      }
    }
    if (agentEl) {
      agentEl.textContent = view.agentLabel || '';
      if (view.agentLabel) {
        agentEl.classList.remove('hidden');
      } else {
        agentEl.classList.add('hidden');
      }
    }
    if (reactEl) {
      reactEl.textContent = view.reactState || '';
      reactEl.className = reactStateToneClass(view.reactState);
    }
    jobPhaseStatusStrip.classList.remove('hidden');
    if (linkEl) {
      if (view.parentChildLabel) {
        linkEl.textContent = view.parentChildLabel;
        linkEl.classList.remove('hidden');
      } else {
        linkEl.textContent = '';
        linkEl.classList.add('hidden');
      }
    }
  }

  if (jobPhaseStatusStrip && !jobPhaseStatusStrip.dataset.copyJobBound) {
    jobPhaseStatusStrip.dataset.copyJobBound = '1';
    jobPhaseStatusStrip.addEventListener('click', (ev) => {
      const btn = ev.target && ev.target.closest ? ev.target.closest('[data-job-phase="copy-job-id"]') : null;
      if (!btn) return;
      const id = btn.dataset.jobId || jobPhaseState.jobId || '';
      if (!id) return;
      copyToClipboard(id);
      showToast(`Copied ${id}`, 'success');
    });
  }

  function updateJobPhaseFromEvent(eventType, ev) {
    jobPhaseState = applyJobPhaseEvent(jobPhaseState, eventType, ev);
    renderJobPhaseStrip();
    if (goalBadge && typeof goalBadge.classList?.toggle === 'function') {
      const multi = Number(jobPhaseState.phaseCount || 0) > 1;
      goalBadge.classList.toggle('hidden', !multi);
    }
  }

  // Grape-vine inline Formulate/Execute + plan-steps chrome (Education origin + Chat). [CARD-240 AC, REQ-JOB-CHROME-001]
  // Phase rows are tagged with data-phase-chrome for unified lifecycle inspection.
  let inlineJobChromeModel = null;
  let inlineJobChromeLog = [];

  function ensureInlineJobChromeBubble() {
    if (!messagesContainer) return null;
    const streamBubble = messagesContainer.querySelector('[data-stream-bubble="true"]');
    if (streamBubble) return streamBubble;
    let el = messagesContainer.querySelector('[data-job-chrome="inline"]');
    if (!el) {
      el = buildInlineJobChromeBubble();
      if (!el) return null;
      // Prefer real DOM node; buildInlineJobChromeBubble always returns one in browser.
      if (!el.setAttribute && typeof document !== 'undefined') {
        const wrap = document.createElement('div');
        wrap.className = 'flex justify-start w-full';
        wrap.setAttribute('data-job-chrome', 'inline');
        el = wrap;
      }
      messagesContainer.appendChild(el);
      maybeAutoscrollMessages();
    }
    return el;
  }

  function paintInlineJobChrome() {
    if (!inlineJobChromeModel) return null;
    if (!shouldMountInlineJobChrome(inlineJobChromeModel)) {
      if (messagesContainer) {
        const existing = messagesContainer.querySelector('[data-job-chrome="inline"]');
        if (existing) existing.remove();
      }
      return null;
    }
    const el = ensureInlineJobChromeBubble();
    if (!el) return null;
    if (el.getAttribute && el.getAttribute('data-stream-bubble') === 'true') {
      // Deduplicate: If reusing active stream bubble, update its phases without wiping the stream [REQ-CHAT-015]
      const orphan = messagesContainer ? messagesContainer.querySelector('[data-job-chrome="inline"]:not([data-stream-bubble="true"])') : null;
      if (orphan) orphan.remove();
      renderJobChromePhasesIntoElement(el, inlineJobChromeModel);
      maybeAutoscrollMessages();
      safeCreateIcons();
      return el;
    }
    el.innerHTML = formatInlineJobChromeHtml(inlineJobChromeModel);
    el.setAttribute('data-job-chrome', 'inline');
    maybeAutoscrollMessages();
    safeCreateIcons();
    return el;
  }

  function remountInlineJobChrome() {
    if (!shouldMountInlineJobChrome(inlineJobChromeModel)) return false;
    paintInlineJobChrome();
    // Strip may have been reset by selectSession — rebuild from last known jobPhaseState.
    renderJobPhaseStrip();
    return true;
  }

  function updateJobChromeFromEvent(eventType, ev) {
    updateJobPhaseFromEvent(eventType, ev);
    const type = String(eventType || '');
    if (
      isJobPhaseChromeEvent(type)
      || type === 'step_start'
      || type === 'step_complete'
    ) {
      inlineJobChromeLog.push({ type, ev: ev || {} });
      if (inlineJobChromeLog.length > 80) inlineJobChromeLog = inlineJobChromeLog.slice(-80);
      inlineJobChromeModel = applyInlineJobChromeModel(
        inlineJobChromeModel || createInlineJobChromeModel(),
        type,
        ev || {},
      );
      paintInlineJobChrome();
    }
    return true;
  }

  function resetInlineJobChrome() {
    inlineJobChromeModel = null;
    inlineJobChromeLog = [];
    if (messagesContainer) {
      messagesContainer.querySelectorAll('[data-job-chrome="inline"]').forEach((n) => n.remove());
    }
  }

  const PENDING_HITL_POLL_MS = 12000;
  let pendingHitlTimer = null;

  async function refreshPendingHitl() {
    if (!pendingHitlHost) return;
    try {
      const res = await fetch(pendingApprovalsUrl(state.selectedAgentId, state.activeSessionId));
      if (!res.ok) return;
      const pending = await res.json();
      renderPendingHitlCards(Array.isArray(pending) ? pending : []);
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load pending approvals:', err);
    }
  }

  function renderPendingHitlCards(pending) {
    if (!pendingHitlHost) return;
    const liveIds = new Set();
    if (messagesContainer) {
      messagesContainer.querySelectorAll('[data-approval-id]').forEach((el) => {
        liveIds.add(el.getAttribute('data-approval-id'));
      });
    }
    const keep = new Set();
    pending.forEach((item) => {
      const id = item && item.id;
      if (shouldSkipPendingHitlCard({
        id,
        item,
        liveIds,
        isStreaming: state.isStreaming,
        originSid: state.activeSessionId,
      })) return;
      keep.add(id);
      let card = pendingHitlHost.querySelector(`[data-approval-id="${id}"]`);
      if (card) return;
      card = document.createElement('div');
      card.className = 'hitl-approval-card rounded-xl border border-amber-500/30 bg-amber-950/20 p-3 space-y-2 text-xs';
      card.setAttribute('data-approval-id', id);
      card.setAttribute('data-approval-session', item.session_id || '');
      if (item.routine_id) card.setAttribute('data-routine-id', item.routine_id);
      const approvalSid = String(item.session_id || '');
      const originSid = String(state.activeSessionId || '');
      const isPhaseChild = approvalSid && originSid && approvalSid !== originSid
        && (approvalSid.startsWith(originSid + '_child_') || approvalSid.startsWith(originSid + '::phase::'));
      card.innerHTML = buildHitlCardInnerHtml({
        title: pendingHitlLabel(item),
        toolName: item.tool_name || 'tool',
        message: item.routine_id
          ? 'Parked by a routine. Approve or Reject here to continue that run.'
          : (isPhaseChild
            ? 'Phase HITL on this Job — Approve here on the origin chat (no need to open Formulate/Execute orphans).'
            : (item.message || 'Waiting for operator approval')),
        argsText: formatHitlArgs(item.arguments),
      });
      card.querySelectorAll('[data-hitl-decision]').forEach((btn) => {
        btn.addEventListener('click', async () => {
          const result = await submitHitlDecision(
            id,
            btn.getAttribute('data-hitl-decision'),
            card,
            state.activeSessionId,
          );
          if (result.ok && shouldResumeChatAfterHitl({
            approvalSessionId: item.session_id,
            openSessionId: state.activeSessionId,
            backendResumed: Boolean(result.body && result.body.resumed),
            nestedStatus: result.body && result.body.nested ? result.body.nested.status : null,
          })) {
            await executeChatTurn('', { resume: true });
          }
          await refreshPendingHitl();
        });
      });
      pendingHitlHost.appendChild(card);
    });
    pendingHitlHost.querySelectorAll('[data-approval-id]').forEach((el) => {
      const id = el.getAttribute('data-approval-id');
      if (!keep.has(id)) el.remove();
    });
  }

  function startPendingHitlPoll() {
    if (pendingHitlTimer) return;
    pendingHitlTimer = setInterval(() => {
      if (document.visibilityState !== 'visible') return;
      refreshPendingHitl();
    }, PENDING_HITL_POLL_MS);
  }

  async function loadAgents() {
    try {
      const res = await fetch('/api/agents');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      state.agents = await res.json();
      const chatAgents = dualEngineAgentsVisibleInChat(state.agents);

      if (agentSelect) {
        agentSelect.innerHTML = '';
        chatAgents.forEach((agent) => {
          const opt = document.createElement('option');
          opt.value = agent.id;
          opt.textContent = `${agent.name} (${agent.tone})`;
          agentSelect.appendChild(opt);
        });
      }


      const savedAgentId = storageGet('autoreiv_active_agent_id');
      const visibleIds = chatAgents.map((a) => a.id);
      if (savedAgentId && visibleIds.includes(savedAgentId)) {
        state.selectedAgentId = savedAgentId;
      } else if (!state.selectedAgentId || !visibleIds.includes(state.selectedAgentId)) {
        state.selectedAgentId = chatAgents.length > 0 ? chatAgents[0].id : 'autoreiv';
      }

      if (agentSelect) agentSelect.value = state.selectedAgentId;

      if (trainAgentTargetSelect) {
        populateTrainAgentTargetOptions(trainAgentTargetSelect, state.agents, state.selectedAgentId || 'autoreiv');
      }

      updateActiveAgentHeader();
      await loadSessions();
      await refreshPendingHitl();
      safeCreateIcons();
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load agents:', err);
    }
  }

  async function switchSelectedAgent(agentId) {
    if (!agentId) return;
    state.selectedAgentId = agentId;
    storageSet('autoreiv_active_agent_id', agentId);

    if (agentSelect && agentSelect.value !== agentId) agentSelect.value = agentId;

    updateActiveAgentHeader();

    const sidebar = $('sidebar');
    if (window.innerWidth < 768 && sidebar) {
      sidebar.classList.add('-translate-x-full');
    }

    await loadSessions();
    await refreshPendingHitl();
  }

  function updateEngineSelectorUi(activeId) {
    const isDirect = activeId === 'direct';
    if (engineBtnCore) {
      if (!isDirect) {
        engineBtnCore.className = 'flex items-center space-x-1 px-2.5 py-1 rounded-md bg-brand-600 text-white shadow-sm font-semibold transition text-xs';
        const icon = engineBtnCore.querySelector('i');
        if (icon) icon.className = 'w-3.5 h-3.5 text-amber-300';
      } else {
        engineBtnCore.className = 'flex items-center space-x-1 px-2.5 py-1 rounded-md text-slate-400 hover:text-slate-200 transition text-xs';
        const icon = engineBtnCore.querySelector('i');
        if (icon) icon.className = 'w-3.5 h-3.5 text-slate-400';
      }
    }
    if (engineBtnDirect) {
      if (isDirect) {
        engineBtnDirect.className = 'flex items-center space-x-1 px-2.5 py-1 rounded-md bg-brand-600 text-white shadow-sm font-semibold transition text-xs';
        const icon = engineBtnDirect.querySelector('i');
        if (icon) icon.className = 'w-3.5 h-3.5 text-emerald-300';
      } else {
        engineBtnDirect.className = 'flex items-center space-x-1 px-2.5 py-1 rounded-md text-slate-400 hover:text-slate-200 transition text-xs';
        const icon = engineBtnDirect.querySelector('i');
        if (icon) icon.className = 'w-3.5 h-3.5 text-slate-400';
      }
    }
    if (jobPhaseStatusStrip && isDirect) {
      jobPhaseStatusStrip.classList.add('hidden');
    }
  }

  async function switchEngineChannel(engineId) {
    if (engineId !== 'autoreiv' && engineId !== 'direct') return;
    await switchSelectedAgent(engineId);
  }

  if (engineBtnCore) {
    engineBtnCore.addEventListener('click', () => switchEngineChannel('autoreiv'));
  }
  if (engineBtnDirect) {
    engineBtnDirect.addEventListener('click', () => switchEngineChannel('direct'));
  }

  if (agentSelect) {
    agentSelect.addEventListener('change', (e) => switchSelectedAgent(e.target.value));
  }

  function updateActiveAgentHeader() {
    updateEngineSelectorUi(state.selectedAgentId);
    const isDirect = state.selectedAgentId === 'direct';
    const agent = state.agents.find((a) => a.id === state.selectedAgentId);
    if (agent) {
      if (activeAgentTitle) activeAgentTitle.textContent = agent.name;
      if (activeAgentTone) {
        activeAgentTone.textContent = isDirect
          ? 'Engine: Direct LLM (Zero Tools)'
          : 'Engine: AutoReiv Core (Orchestrated)';
      }
      if (agentSelect && agentSelect.value !== agent.id) agentSelect.value = agent.id;
    } else {
      const opt = agentSelect ? agentSelect.querySelector(`option[value="${state.selectedAgentId}"]`) : null;
      if (opt && activeAgentTitle) {
        activeAgentTitle.textContent = opt.textContent;
      }
      if (agentSelect && agentSelect.value !== state.selectedAgentId) agentSelect.value = state.selectedAgentId;
    }
  }

  async function loadSessions() {
    try {
      const exclude = state.activeSessionId ? `&exclude_session_id=${encodeURIComponent(state.activeSessionId)}` : '';
      const res = await fetch(`/api/sessions?agent_id=${state.selectedAgentId}${exclude}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      state.sessions = await res.json();
      renderSessionList();
      const stillThere =
        state.activeSessionId &&
        Array.isArray(state.sessions) &&
        state.sessions.some((s) => s.id === state.activeSessionId);
      if (stillThere || state.isStreaming) {
        return;
      }
      if (state.sessions && state.sessions.length > 0) {
        await selectSession(state.sessions[0].id);
      } else {
        await createNewSession();
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load sessions:', err);
    }
  }

  function renderSessionList() {
    if (!sessionList) return;
    sessionList.innerHTML = '';
    state.sessions.forEach((sess) => {
      const item = document.createElement('div');
      const isActive = sess.id === state.activeSessionId;
      item.className = `px-2.5 py-2 rounded-xl cursor-pointer text-xs transition flex flex-col space-y-1 ${
        isActive
          ? 'bg-slate-800 text-white font-medium border border-slate-700/80 shadow-sm'
          : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200 border border-transparent'
      }`;
      const timeStr = formatSessionTimestamp(sess.updated_at || sess.created_at);
      item.innerHTML = `
        <div class="flex items-center space-x-2 min-w-0">
          <span class="w-1.5 h-1.5 rounded-full ${isActive ? 'bg-brand-400 ring-2 ring-brand-400/20' : 'bg-slate-600'} flex-shrink-0"></span>
          <span class="truncate font-medium text-slate-200 text-xs">${escapeHtml(sess.title || 'Conversation')}</span>
        </div>
        ${timeStr ? `<div class="text-[10px] text-slate-500 font-mono pl-3.5 leading-none">${escapeHtml(timeStr)}</div>` : ''}
      `;
      item.addEventListener('click', () => selectSession(sess.id));
      sessionList.appendChild(item);
    });
  }

  if (newChatBtn) newChatBtn.addEventListener('click', createNewSession);

  async function createNewSession() {
    const isDirect = state.selectedAgentId === 'direct';
    const agent = state.agents.find((a) => a.id === state.selectedAgentId);
    const title = isDirect ? 'Direct Chat' : `${agent ? agent.name : 'AutoReiv'} Chat`;
    try {
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: state.selectedAgentId, title }),
      });
      const sess = await res.json();
      state.sessions.unshift(sess);
      await selectSession(sess.id);
    } catch (err) {
      console.error('[AutoReiv UI] Failed to create session:', err);
    }
  }


  async function hydrateJobChromeFromSession(sessionId) {
    if (!sessionId) return false;
    try {
      const res = await fetch(`/api/chat/sessions/${encodeURIComponent(sessionId)}/journey`);
      if (!res.ok) return false;
      const data = await res.json();
      const next = hydrateJobPhaseStateFromJourney(data);
      if (!next) return false;
      jobPhaseState = next;
      renderJobPhaseStrip();
      const job = Array.isArray(data.jobs) && data.jobs.length
        ? [...data.jobs].sort((a, b) => {
            const rank = (s) => {
              const v = String(s || '').toLowerCase();
              if (v === 'waiting_approval') return 0;
              if (v === 'running' || v === 'in_progress' || v === 'queued') return 1;
              return 2;
            };
            return rank(a.status) - rank(b.status);
          })[0]
        : null;
      const phases = job && Array.isArray(job.phases) ? [...job.phases].sort((a, b) => Number(a.index || 0) - Number(b.index || 0)) : [];
      if (phases.length) {
        inlineJobChromeModel = createInlineJobChromeModel();
        phases.forEach((p) => {
          const st = String(p.status || '').toLowerCase();
          inlineJobChromeModel = applyInlineJobChromeModel(inlineJobChromeModel, 'phase_start', {
            job_id: job.id,
            phase_id: p.id,
            phase_name: p.name,
            index: p.index,
            phase_count: phases.length,
            assigned_agent_id: p.assigned_agent_id,
          });
          if (st === 'done') {
            inlineJobChromeModel = applyInlineJobChromeModel(inlineJobChromeModel, 'phase_complete', {
              job_id: job.id,
              phase_id: p.id,
              phase_name: p.name,
              index: p.index,
              status: 'done',
            });
          } else if (st === 'waiting_approval') {
            inlineJobChromeModel = applyInlineJobChromeModel(inlineJobChromeModel, 'approval_required', {
              job_id: job.id,
              job_status: 'waiting_approval',
              react_state: 'PARKED',
            });
          }
        });
        remountInlineJobChrome();
      }
      return true;
    } catch (err) {
      console.warn('[AutoReiv UI] CARD-295 journey hydrate soft-fail:', err);
      return false;
    }
  }

  async function selectSession(sessionId) {
    if (backgroundPollInterval) {
      clearInterval(backgroundPollInterval);
      backgroundPollInterval = null;
    }
    state.activeSessionId = sessionId;
    resetJobPhaseStrip();
    resetInlineJobChrome();
    renderSessionList();
    await loadMessages(sessionId, { force: true });
    await refreshPendingHitl();
    // CARD-295: after refresh/select, restore journey chrome for the same job_id.
    await hydrateJobChromeFromSession(sessionId);
    await checkSessionBackgroundStatus(sessionId);
    await refreshWorkbenchArtifactCount();
    if (chatOptionsDrawer && !chatOptionsDrawer.classList.contains('hidden')) {
      await loadChatSessionContext();
    }
    // CARD-296: selecting a recent chat loads it and auto-collapses the sessions drawer.
    collapseChatSessionsDrawer(chatSessionsDrawer, viewChat);
    chatStickToBottom = true;
    jumpMessagesToLatest();
  }

  async function loadMessages(sessionId, options = {}) {
    const force = Boolean(options && options.force);
    try {
      const res = await fetch(`/api/sessions/${sessionId}/messages`);
      const data = await res.json();
      if (state.activeSessionId !== sessionId) return;
      state.messages = Array.isArray(data) ? data : [];
      if (state.isStreaming) return;
      if (!force && hasVisibleHitlCard(messagesContainer)) return;
      renderMessages();
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load messages:', err);
    }
  }

  async function checkSessionBackgroundStatus(sessionId = state.activeSessionId) {
    if (!sessionId || sessionId !== state.activeSessionId || isCheckingBackgroundStatus) return;
    isCheckingBackgroundStatus = true;
    try {
      const data = await querySessionStatus(sessionId);
      if (sessionId !== state.activeSessionId) return;

      if (!data.is_running) {
        if (backgroundPollInterval) {
          clearInterval(backgroundPollInterval);
          backgroundPollInterval = null;
        }
        if (state.isStreaming) {
          if (activeAbortController) {
            try {
              activeAbortController.abort();
            } catch {
              // ignore abort errors
            }
            activeAbortController = null;
          }
          state.isStreaming = false;
          if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.classList.remove('hidden');
          }
          if (stopBtn) {
            stopBtn.classList.add('hidden');
          }
        }
        await loadMessages(sessionId, { force: true });
        await refreshPendingHitl();
        safeCreateIcons();
      } else {
        state.isStreaming = true;
        if (sendBtn) {
          sendBtn.disabled = true;
          sendBtn.classList.add('hidden');
        }
        if (stopBtn) {
          stopBtn.classList.remove('hidden');
        }
        if (!backgroundPollInterval) {
          backgroundPollInterval = setInterval(() => {
            if (state.activeSessionId === sessionId) {
              checkSessionBackgroundStatus(sessionId);
            } else {
              clearInterval(backgroundPollInterval);
              backgroundPollInterval = null;
            }
          }, 2000);
        }
      }
    } catch (e) {
      console.warn('Failed to check session background status:', e);
    } finally {
      isCheckingBackgroundStatus = false;
    }
  }

  function renderMessages() {
    if (!messagesContainer) return;
    if (state.isStreaming) return;
    messagesContainer.innerHTML = '';
    if (state.messages.length === 0) {
      messagesContainer.innerHTML = `
        <div class="text-center py-12 text-slate-400 space-y-2">
          <div class="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-brand-400">
            <i data-lucide="bot" class="w-6 h-6"></i>
          </div>
          <p class="text-sm font-medium">Start a new conversation with ${escapeHtml(activeAgentTitle ? activeAgentTitle.textContent : 'Agent')}.</p>
        </div>
      `;
      safeCreateIcons();
      return;
    }

    state.messages.forEach((msg, idx) => {
      renderMessageItem(msg, idx, state.messages);
    });

    maybeAutoscrollMessages();
    safeCreateIcons();
  }

  function renderMessageItem(msg, _idx, _allMessages) {
    if (!messagesContainer || !msg) return;

    const role = (msg.role || '').toLowerCase();

    // 1. User Message
    if (role === 'user') {
      if (msg.content && msg.content.trim()) {
        appendMessageBubble('user', msg.content);
      }
      return;
    }

    // 2. Tool Execution Result
    if (role === 'tool') {
      const isDelegation = msg.name === 'handoff_to_agent';
      if (isDelegation) {
        let data;
        try {
          data = JSON.parse(msg.content);
        } catch {
          data = { status: 'success', output: msg.content };
        }

        const isOk = data.status === 'success' || !data.error;
        const recipient = data.recipient_agent_id || data.recipient || 'Specialist Agent';
        const recipientName = recipient.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
        const el = document.createElement('div');
        el.className = 'flex justify-start w-full my-1.5';
        el.innerHTML = `
          <div class="max-w-2xl w-full rounded-xl bg-indigo-950/40 border border-indigo-500/30 p-3 text-xs text-indigo-200 space-y-1.5 shadow-sm">
            <div class="flex items-center justify-between font-semibold ${isOk ? 'text-indigo-300' : 'text-rose-300'}">
              <span class="flex items-center space-x-1.5">
                <span>🤝</span>
                <span>Delegation to <strong>${escapeHtml(recipientName)}</strong> ${isOk ? 'Completed' : 'Failed'}</span>
              </span>
              <span class="font-mono text-[10px] ${isOk ? 'text-emerald-400' : 'text-rose-400'} font-bold">${isOk ? '✓ Done' : '✗ Error'}</span>
            </div>
            ${data.directive || data.task_intent ? `<div class="text-[11px] text-slate-300 font-mono bg-indigo-950/60 p-1.5 rounded border border-indigo-900/50">"${escapeHtml(data.directive || data.task_intent)}"</div>` : ''}
            ${data.error ? `<div class="text-[11px] text-rose-300 font-mono bg-rose-950/40 p-1.5 rounded border border-rose-900/50">${escapeHtml(data.error)}</div>` : ''}
          </div>
        `;
        messagesContainer.appendChild(el);
        return;
      }

      // Agent Pack Creation Result [CARD-197, REQ-FACT-048]
      if (msg.name === 'scaffold_agent_pack') {
        let data;
        try {
          data = typeof msg.content === 'object' ? msg.content : JSON.parse(msg.content);
        } catch {
          data = {};
        }
        if (data.success && data.agent_id) {
          const el = document.createElement('div');
          el.className = 'flex justify-start w-full my-1.5';
          el.innerHTML = renderAgentHandoffCardHtml({
            agentId: data.agent_id,
            agentName: data.name || data.agent_id,
            folder: data.folder || `packs/${data.agent_id}`,
          });
          messagesContainer.appendChild(el);
          return;
        }
      }

      // Generic Tool Execution Result (collapsible)
      const el = document.createElement('div');
      el.className = 'flex justify-start w-full my-1';
      el.innerHTML = `
        <details class="max-w-2xl w-full rounded-xl bg-slate-900/90 border border-slate-800 p-2.5 text-xs text-slate-300 group transition hover:border-slate-700 shadow-sm">
          <summary class="cursor-pointer font-medium flex items-center justify-between select-none list-none">
            <span class="flex items-center space-x-1.5">
              <span class="text-brand-400">🔧</span>
              <span>Tool: <strong class="text-slate-200">${escapeHtml(msg.name || 'tool')}</strong></span>
            </span>
            <span class="text-[10px] text-emerald-400 font-mono">✓ Complete</span>
          </summary>
          <div class="mt-2 pt-2 border-t border-slate-800/80 font-mono text-[11px] text-slate-400 whitespace-pre-wrap max-h-48 overflow-y-auto bg-slate-950/60 p-2 rounded">
            ${escapeHtml(msg.content)}
          </div>
        </details>
      `;
      messagesContainer.appendChild(el);
      return;
    }

    // 3. Assistant Message
    if (role === 'assistant') {
      const content = (msg.content || '').trim();
      if (!content) {
        // Skip empty intermediate tool-calling turn messages
        return;
      }
      appendMessageBubble('assistant', content, { messageId: msg.id || null });
      return;
    }

    // 4. Skill Proposal Message [CARD-358, REQ-SKIL-016]
    if (role === 'skill_proposal') {
      let proposalData;
      try {
        proposalData = typeof msg.content === 'string' ? JSON.parse(msg.content) : msg.content;
      } catch {
        proposalData = null;
      }
      if (proposalData && typeof proposalData === 'object') {
        proposalData.message_id = msg.id || proposalData.message_id || null;
        renderSkillProposalCard(proposalData);
      }
      return;
    }

    // 5. Fallback for other message types
    if (msg.content && msg.content.trim()) {
      appendMessageBubble(role, msg.content);
    }
  }


  async function renderMarkdown(targetEl, rawMarkdown) {
    if (!targetEl) return;
    const formattedText = formatJsonDeliverableToMarkdown(rawMarkdown || '');
    if (!window.marked) {
      targetEl.innerHTML = `<pre class="whitespace-pre-wrap font-mono text-xs text-slate-200">${escapeHtml(formattedText)}</pre>`;
      return;
    }

    try {
      const parsedHtml = window.marked.parse(formattedText || '');
      targetEl.innerHTML = parsedHtml;

      const mermaidBlocks = targetEl.querySelectorAll(
        'pre code.language-mermaid, pre code.lang-mermaid, pre code.mermaid'
      );
      if (mermaidBlocks.length > 0 && window.mermaid) {
        for (let i = 0; i < mermaidBlocks.length; i++) {
          const codeEl = mermaidBlocks[i];
          const preEl = codeEl.closest('pre');
          const graphCode = codeEl.textContent.trim();
          const graphId = `mermaid-svg-${Date.now()}-${i}-${Math.floor(Math.random() * 10000)}`;

          try {
            const { svg } = await window.mermaid.render(graphId, graphCode);

            const wrapper = document.createElement('div');
            wrapper.className = 'mermaid-wrapper relative group my-4 overflow-x-auto';

            const containerDiv = document.createElement('div');
            containerDiv.className = 'mermaid flex justify-center py-2';
            containerDiv.innerHTML = svg;

            wrapper.appendChild(containerDiv);

            if (preEl && preEl.parentNode) {
              preEl.parentNode.replaceChild(wrapper, preEl);
            }
          } catch (mErr) {
            console.warn('[AutoReiv UI] Mermaid rendering error:', mErr);
            if (preEl) preEl.classList.add('border-amber-700/60');
          }
        }
      }

      // Convert artifact:// links to rich interactive cards [REQ-ART-005]
      const artifactLinks = targetEl.querySelectorAll('a[href^="artifact://"]');
      artifactLinks.forEach((a) => {
        const artId = a.getAttribute('href').replace('artifact://', '').trim();
        const linkText = a.textContent || artId;
        const card = document.createElement('div');
        card.className = 'my-2.5 p-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-brand-500/50 transition flex items-center justify-between gap-3 shadow-sm group not-prose';
        card.innerHTML = `
          <div class="flex items-center space-x-2.5 min-w-0">
            <div class="w-8 h-8 rounded-lg bg-brand-600/30 border border-brand-500/50 flex items-center justify-center text-brand-400 shrink-0">
              <i data-lucide="file-text" class="w-4 h-4"></i>
            </div>
            <div class="truncate">
              <div class="text-xs font-bold text-white truncate">${escapeHtml(linkText)}</div>
              <div class="text-[10px] text-slate-400 font-mono">${escapeHtml(artId)} • Session Artifact</div>
            </div>
          </div>
          <button type="button" class="open-artifact-btn px-2.5 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition shrink-0 shadow-sm" data-artifact-id="${escapeHtml(artId)}">
            <i data-lucide="eye" class="w-3.5 h-3.5"></i>
            <span>View Full Report</span>
          </button>
        `;
        a.parentNode.replaceChild(card, a);
        card.querySelector('.open-artifact-btn')?.addEventListener('click', (e) => {
          e.stopPropagation();
          openArtifactModal(artId);
        });
      });
      if (artifactLinks.length) {
        refreshWorkbenchArtifactCount();
      }

      safeCreateIcons();
    } catch (err) {
      console.warn('[AutoReiv UI] Markdown rendering error:', err);
    }
  }

  async function openArtifactModal(artifactId) {
    if (!artifactId) return;
    const modal = $('artifactModal');
    const titleEl = $('artifactModalTitle');
    const subtitleEl = $('artifactModalSubtitle');
    const summaryBox = $('artifactSummaryBox');
    const bodyContent = $('artifactBodyContent');
    const itemCountBadge = $('artifactItemCountBadge');
    const statusBadge = $('artifactStatusBadge');
    const promoteBtn = $('artifactPromoteBtn');
    const pinBtn = $('artifactPinBtn');
    const pinText = $('artifactPinText');
    const deleteBtn = $('artifactDeleteBtn');
    const closeBtn = $('artifactCloseBtn');

    if (!modal) return;

    try {
      const res = await fetch(`/api/artifacts/${encodeURIComponent(artifactId)}`);
      if (!res.ok) {
        showToast('error', `Failed to load artifact ${artifactId}`);
        return;
      }
      const data = await res.json();
      const art = data.artifact;
      if (!art) return;

      if (titleEl) titleEl.textContent = art.title || 'Session Artifact Report';
      if (subtitleEl) subtitleEl.textContent = `ID: ${art.id} | Session: ${art.session_id}`;
      if (summaryBox) summaryBox.textContent = art.summary || 'No summary available.';
      if (bodyContent) bodyContent.textContent = art.content || '';
      if (itemCountBadge) itemCountBadge.textContent = `${art.item_count || 0} items scanned`;
      
      const updatePinUI = (isPinned) => {
        if (statusBadge) {
          if (isPinned) {
            statusBadge.textContent = 'Pinned (Permanent)';
            statusBadge.className = 'font-mono text-emerald-400 font-semibold';
          } else {
            statusBadge.textContent = 'Ephemeral (7-Day TTL)';
            statusBadge.className = 'font-mono text-amber-400';
          }
        }
        if (pinText) pinText.textContent = isPinned ? 'Unpin' : 'Pin';
      };

      updatePinUI(art.is_pinned);

      modal.classList.remove('hidden');
      modal.classList.add('flex');
      safeCreateIcons();

      const closeModal = () => {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
      };

      if (closeBtn) closeBtn.onclick = closeModal;
      modal.onclick = (e) => {
        if (e.target === modal) closeModal();
      };

      if (pinBtn) {
        pinBtn.onclick = async () => {
          try {
            const nextPinned = !art.is_pinned;
            const pRes = await fetch(`/api/artifacts/${encodeURIComponent(art.id)}/pin`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ is_pinned: nextPinned }),
            });
            if (pRes.ok) {
              art.is_pinned = nextPinned;
              updatePinUI(nextPinned);
              showToast('success', nextPinned ? 'Artifact pinned (immune to TTL cleanup)' : 'Artifact unpinned (7-day TTL active)');
            }
          } catch (err) {
            showToast('error', `Failed to toggle pin: ${err.message}`);
          }
        };
      }

      if (promoteBtn) {
        promoteBtn.onclick = async () => {
          try {
            const cleanSlug = `reports/${art.id.replace(/[^a-zA-Z0-9_-]/g, '_')}`;
            const promRes = await fetch(`/api/artifacts/${encodeURIComponent(art.id)}/promote`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                wiki_slug: cleanSlug,
                title: art.title,
                category: 'reports',
              }),
            });
            if (promRes.ok) {
              showToast('success', `Promoted artifact to Wiki Vault at '${cleanSlug}'!`);
              closeModal();
            } else {
              const errData = await promRes.json();
              showToast('error', `Promotion failed: ${errData.detail || 'Unknown error'}`);
            }
          } catch (err) {
            showToast('error', `Promotion failed: ${err.message}`);
          }
        };
      }

      if (deleteBtn) {
        deleteBtn.onclick = async () => {
          if (!confirm(`Are you sure you want to delete artifact ${art.id}?`)) return;
          try {
            const dRes = await fetch(`/api/artifacts/${encodeURIComponent(art.id)}`, { method: 'DELETE' });
            if (dRes.ok) {
              showToast('success', 'Artifact deleted.');
              closeModal();
            }
          } catch (err) {
            showToast('error', `Deletion failed: ${err.message}`);
          }
        };
      }

    } catch (err) {
      showToast('error', `Error opening artifact: ${err.message}`);
    }
  }

  function appendMessageBubble(role, content, options = null) {
    if (!messagesContainer) return;

    const isUser = role.toLowerCase() === 'user';
    const bubble = document.createElement('div');
    bubble.className = `flex ${isUser ? 'justify-end' : 'justify-start'} w-full`;

    const copyBtnHtml = !isUser
      ? `
      <div class="mt-2 pt-2 border-t border-white/10 flex flex-wrap gap-1.5 items-center">
        <button class="msg-teach-agent-btn flex items-center space-x-1.5 px-2 py-0.5 rounded-md bg-amber-950/60 hover:bg-amber-900/80 text-amber-300 border border-amber-800/50 transition shadow-sm" data-message-id="${escapeHtml(options?.messageId || '')}" data-content="${escapeHtml(content)}" title="Teach agent a runbook skill from this turn [CARD-352]">
          <i data-lucide="lightbulb" class="w-3 h-3 text-amber-400"></i>
          <span>Teach Agent</span>
        </button>
        <button class="workbench-msg-btn flex items-center space-x-1.5 px-2 py-0.5 rounded-md bg-slate-800/70 hover:bg-slate-700/80 text-brand-300 border border-slate-700/50 transition" data-content="${escapeHtml(content)}" title="Open message artifact in Dual-Pane Workbench">
          <i data-lucide="layout" class="w-3 h-3"></i>
          <span>Workbench</span>
        </button>
        <button class="copy-msg-btn flex items-center space-x-1.5 px-2 py-0.5 rounded-md bg-slate-800/70 hover:bg-slate-700/80 text-slate-300 border border-slate-700/50 transition" data-content="${escapeHtml(content)}">
          <i data-lucide="copy" class="w-3 h-3"></i>
          <span>Copy</span>
        </button>
        <button class="wiki-msg-btn flex items-center space-x-1.5 px-2 py-0.5 rounded-md bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 border border-indigo-800/50 transition" data-content="${escapeHtml(content)}">
          <i data-lucide="book-open" class="w-3 h-3"></i>
          <span>Save to Wiki</span>
        </button>
      </div>
    `
      : '';

    let attachmentsHtml = '';
    const attachments = (options && options.attachments) || [];
    if (Array.isArray(attachments) && attachments.length > 0) {
      attachmentsHtml = `
        <div class="attachments-grid flex flex-wrap gap-2 mt-2 pt-2 border-t border-white/20">
          ${attachments
            .map((att) => {
              const isImg = att.content_type?.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg)$/i.test(att.filename || '');
              if (isImg && att.url) {
                return `
                  <a href="${escapeHtml(att.url)}" target="_blank" rel="noopener noreferrer" class="block rounded-lg overflow-hidden border border-white/30 hover:opacity-90 transition">
                    <img src="${escapeHtml(att.url)}" alt="${escapeHtml(att.filename)}" class="max-w-[140px] max-h-[100px] object-cover rounded-md">
                  </a>
                `;
              }
              return `
                <a href="${escapeHtml(att.url || '#')}" target="_blank" rel="noopener noreferrer" class="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-black/20 hover:bg-black/40 border border-white/30 text-xs text-white transition">
                  <span>📄</span>
                  <span class="font-medium truncate max-w-[120px]">${escapeHtml(att.filename || 'file')}</span>
                  <span class="text-[10px] opacity-80">(${formatBytes(att.size_bytes || 0)})</span>
                </a>
              `;
            })
            .join('')}
        </div>
      `;
    }

    bubble.innerHTML = `
      <div class="${
        isUser
          ? 'max-w-3xl rounded-2xl p-3.5 md:p-4 shadow-md bg-brand-600 text-white rounded-br-sm border border-brand-500/40'
          : 'max-w-4xl w-full rounded-2xl p-4 shadow-md bg-slate-900/90 border border-slate-800/80 text-slate-100 rounded-bl-sm'
      }">
        <div class="text-xs font-bold uppercase tracking-wider mb-1 opacity-70">
          ${isUser ? 'You' : escapeHtml(activeAgentTitle ? activeAgentTitle.textContent : 'Agent')}
        </div>
        <div class="msg-body prose prose-invert text-sm break-words leading-relaxed">
        </div>
        ${attachmentsHtml}
        ${copyBtnHtml}
      </div>
    `;

    messagesContainer.appendChild(bubble);
    const bodyEl = bubble.querySelector('.msg-body');
    renderMarkdown(bodyEl, content || '');

    bubble.querySelectorAll('.workbench-msg-btn').forEach((b) => {
      b.addEventListener('click', () => {
        openWorkbench({
          title: `${activeAgentTitle ? activeAgentTitle.textContent : 'Agent'} Output`,
          meta: 'Turn Artifact',
          content: b.dataset.content || '',
        });
      });
    });

    bubble.querySelectorAll('.copy-msg-btn').forEach((b) => {
      b.addEventListener('click', () => copyToClipboard(b.dataset.content || ''));
    });

    bubble.querySelectorAll('.wiki-msg-btn').forEach((b) => {
      b.addEventListener('click', () => {
        if (callbacks.exportMessageToWiki) callbacks.exportMessageToWiki(b.dataset.content || '');
      });
    });
  }

  // Toggles
  if (verifyToggle) {
    verifyToggle.addEventListener('change', (e) => {
      state.verifyEnabled = e.target.checked;
      if (verifyBadge) verifyBadge.classList.toggle('hidden', !state.verifyEnabled);
    });
  }

  const rememberedAutoRun = readLastApprovalAutoRun();
  state.approvalAutoRun = rememberedAutoRun;
  if (approvalToggle) {
    approvalToggle.checked = rememberedAutoRun;
    approvalToggle.addEventListener('change', (e) => {
      state.approvalAutoRun = e.target.checked;
      writeLastApprovalAutoRun(Boolean(e.target.checked));
      if (approvalBadge) approvalBadge.classList.toggle('hidden', !state.approvalAutoRun);
    });
  }
  if (approvalBadge) approvalBadge.classList.toggle('hidden', !rememberedAutoRun);

  // CARD-215: Goal toggle retired; standing Job-Graph runtime routes multi-step turns.

  if (trainAgentToggle) {
    trainAgentToggle.addEventListener('change', (e) => {
      if (e.target.checked) {
        if (trainAgentBadge) trainAgentBadge.classList.remove('hidden');
        if (trainAgentHandshakeModal) {
          const agentId = state.selectedAgentId || 'autoreiv';
          trainAgentHandshakeModal.dataset.agentId = agentId;

          if (trainAgentTargetSelect) {
            populateTrainAgentTargetOptions(trainAgentTargetSelect, state.agents, agentId);
          }

          updateTrainAgentLiveIndicator(
            {
              nameGroup: $('trainAgentNameGroup'),
              liveInfo: trainAgentLiveInfo,
              livePackPath: trainAgentLivePackPath,
              liveCounts: trainAgentLiveCounts,
              liveInfoText: trainAgentLiveInfoText,
              modalTitle: $('trainAgentModalTitle'),
              intentInput: $('trainSeedIntentInput'),
              seedObj: $('trainSeedObjectives'),
            },
            agentId,
            state.agents
          );

          const targetLoc = $('trainTargetLocation');
          if (targetLoc) targetLoc.value = '';

          const intentInput = $('trainSeedIntentInput');
          if (intentInput && promptInput) {
            intentInput.value = promptInput.value.trim();
          }

          const seedObj = $('trainSeedObjectives');
          if (seedObj) seedObj.value = '';

          trainAgentHandshakeModal.classList.remove('hidden');
          safeCreateIcons();
        }
        toggleChatOptionsDrawer(false);
      } else {
        if (trainAgentBadge) trainAgentBadge.classList.add('hidden');
        if (trainAgentHandshakeModal) trainAgentHandshakeModal.classList.add('hidden');
      }
    });
  }

  if (trainAgentTargetSelect) {
    trainAgentTargetSelect.addEventListener('change', (e) => {
      const chosen = e.target.value;
      if (trainAgentHandshakeModal) {
        if (chosen === '__new__') {
          delete trainAgentHandshakeModal.dataset.agentId;
        } else {
          trainAgentHandshakeModal.dataset.agentId = chosen;
        }
      }
      updateTrainAgentLiveIndicator(
        {
          nameGroup: $('trainAgentNameGroup'),
          liveInfo: trainAgentLiveInfo,
          livePackPath: trainAgentLivePackPath,
          liveCounts: trainAgentLiveCounts,
          liveInfoText: trainAgentLiveInfoText,
          modalTitle: $('trainAgentModalTitle'),
          intentInput: $('trainSeedIntentInput'),
          seedObj: $('trainSeedObjectives'),
        },
        chosen,
        state.agents
      );
      safeCreateIcons();
    });
  }

  function closeTrainModal() {
    if (trainAgentHandshakeModal) {
      trainAgentHandshakeModal.classList.add('hidden');
      delete trainAgentHandshakeModal.dataset.agentId;
    }
    if (trainAgentTargetSelect && state.agents && state.agents.length > 0) {
      trainAgentTargetSelect.value = state.selectedAgentId || state.agents[0].id;
    }
    const targetLoc = $('trainTargetLocation');
    if (targetLoc) targetLoc.value = '';
    const intentInput = $('trainSeedIntentInput');
    if (intentInput) intentInput.value = '';
    const seedObj = $('trainSeedObjectives');
    if (seedObj) seedObj.value = '';
    const nameInput = $('trainAgentNameInput');
    if (nameInput) nameInput.value = '';
    const deliverableSelect = $('trainDeliverableType');
    if (deliverableSelect) deliverableSelect.value = 'auto';
    const constraintsInput = $('trainConstraintsInput');
    if (constraintsInput) constraintsInput.value = '';
    const prereqsInput = $('trainPrerequisitesInput');
    if (prereqsInput) prereqsInput.value = '';
    const refDocsInput = $('trainReferenceDocsInput');
    if (refDocsInput) refDocsInput.value = '';
    const advContent = $('trainAdvancedReqsContent');
    if (advContent) advContent.classList.add('hidden');
    const chevron = $('trainAdvancedChevron');
    if (chevron) chevron.classList.remove('rotate-180');
    if (trainAgentToggle) trainAgentToggle.checked = false;
    if (trainAgentBadge) trainAgentBadge.classList.add('hidden');
  }

  const toggleTrainAdvancedReqsBtn = $('toggleTrainAdvancedReqsBtn');
  if (toggleTrainAdvancedReqsBtn) {
    toggleTrainAdvancedReqsBtn.addEventListener('click', () => {
      const content = $('trainAdvancedReqsContent');
      const advChevron = $('trainAdvancedChevron');
      if (content) {
        const isHidden = content.classList.contains('hidden');
        content.classList.toggle('hidden', !isHidden);
        if (advChevron) {
          advChevron.classList.toggle('rotate-180', isHidden);
        }
      }
    });
  }

  if (closeTrainAgentModalBtn) {
    closeTrainAgentModalBtn.addEventListener('click', closeTrainModal);
  }
  if (cancelTrainAgentBtn) {
    cancelTrainAgentBtn.addEventListener('click', closeTrainModal);
  }

  if (startTrainAgentBtn) {
    startTrainAgentBtn.addEventListener('click', async () => {
      const selectedTargetValue = trainAgentTargetSelect ? trainAgentTargetSelect.value : null;
      const isNew = selectedTargetValue === '__new__';
      const explicitAgentId = (!isNew && selectedTargetValue)
        ? selectedTargetValue
        : (trainAgentHandshakeModal?.dataset?.agentId || null);
      const trainAgentNameInput = $('trainAgentNameInput');
      const customAgentName = trainAgentNameInput ? trainAgentNameInput.value.trim() : '';

      let targetAgentId = isNew ? null : explicitAgentId;
      const trainSeedIntentInput = $('trainSeedIntentInput');
      const explicitIntent = trainSeedIntentInput ? trainSeedIntentInput.value.trim() : '';
      let seedIntent = explicitIntent || (promptInput ? promptInput.value.trim() : '');

      const rawObjectives = trainSeedObjectives ? trainSeedObjectives.value.trim() : '';
      const objectives = rawObjectives
        ? rawObjectives.split('\n').map((s) => s.trim().replace(/^-\s*/, '')).filter(Boolean)
        : [];

      if (!targetAgentId && !customAgentName) {
        showToast('Please select a target agent to train.', 'warning');
        return;
      }

      if (!targetAgentId && customAgentName) {
        targetAgentId = customAgentName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
        if (!seedIntent && objectives.length > 0) {
          seedIntent = objectives[0].length > 120 ? objectives[0].slice(0, 117) + '...' : objectives[0];
        } else if (!seedIntent) {
          seedIntent = `Train capabilities for ${customAgentName}`;
        }
      } else if (!seedIntent && objectives.length > 0) {
        // Derive from first objective if user didn't write an explicit intent [CARD-186]
        seedIntent = objectives[0].length > 120 ? objectives[0].slice(0, 117) + '...' : objectives[0];
      } else if (!seedIntent && explicitAgentId) {
        const agentObj = (state.agents || []).find((a) => a.id === explicitAgentId);
        seedIntent = (agentObj && agentObj.description) ? agentObj.description : `Train capabilities for ${explicitAgentId}`;
      } else if (!seedIntent) {
        seedIntent = 'Custom Specialist Agent';
      }

      const targetTypeInput = $query('input[name="trainTargetType"]');
      const targetType = targetTypeInput ? targetTypeInput.value : 'local';
      const targetLocation = trainTargetLocation ? trainTargetLocation.value.trim() : '';

      const requireApproval = trainRequireApproval ? trainRequireApproval.checked : true;

      const deliverableSelect = $('trainDeliverableType');
      const deliverableType = deliverableSelect ? deliverableSelect.value : 'auto';

      const constraintsInput = $('trainConstraintsInput');
      const constraints = constraintsInput ? constraintsInput.value.trim() : '';

      const prereqsInput = $('trainPrerequisitesInput');
      const prerequisites = prereqsInput ? prereqsInput.value.trim() : '';

      const refDocsInput = $('trainReferenceDocsInput');
      const referenceDocs = refDocsInput ? refDocsInput.value.trim() : '';

      const payload = buildTrainAgentPayload({
        seedIntent,
        targetType,
        targetLocation,
        objectives,
        requireApproval,
        sessionId: (state.selectedAgentId === 'autoreiv' || !state.selectedAgentId) ? state.activeSessionId : null,
        targetAgentId: targetAgentId,
        deliverableType,
        constraints,
        prerequisites,
        referenceDocs,
      });

      if (trainAgentHandshakeModal) {
        trainAgentHandshakeModal.classList.add('hidden');
        delete trainAgentHandshakeModal.dataset.agentId;
      }
      if (trainTargetLocation) trainTargetLocation.value = '';
      if (trainAgentNameInput) trainAgentNameInput.value = '';
      if (trainSeedObjectives) trainSeedObjectives.value = '';
      if (deliverableSelect) deliverableSelect.value = 'auto';
      if (constraintsInput) constraintsInput.value = '';
      if (prereqsInput) prereqsInput.value = '';
      if (refDocsInput) refDocsInput.value = '';
      startTrainAgentBtn.disabled = true;

      try {
        const result = await submitTrainAgentJob(payload);
        showToast(`Training Job ${result.job_id} initiated!`, 'success');

        // Auto-open Lab Monitor drawer so user can track live execution
        if (typeof window.openLabMonitorDrawer === 'function') {
          window.openLabMonitorDrawer(result.job_id);
        }

        if (messagesContainer) {
          const infoBubble = document.createElement('div');
          infoBubble.className = 'flex justify-start w-full';
          infoBubble.innerHTML = `
            <div class="max-w-4xl w-full rounded-2xl p-4 shadow-md bg-slate-900/90 border border-emerald-500/40 text-slate-100 rounded-bl-sm space-y-2">
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2 text-emerald-400 font-semibold text-xs">
                  <i data-lucide="cpu" class="w-4 h-4"></i>
                  <span>Autonomous Factory Loop Started</span>
                </div>
                <button type="button" class="open-lab-drawer-btn text-xs text-emerald-400 hover:text-emerald-300 underline font-medium" data-job-id="${escapeHtml(result.job_id)}">
                  View in Lab Monitor &rarr;
                </button>
              </div>
              <p class="text-xs text-slate-300">Job <strong class="font-mono text-emerald-300">${escapeHtml(result.job_id)}</strong> queued for <strong class="font-mono">${escapeHtml(payload.target_agent_id || 'specialist')}</strong>.</p>
            </div>
          `;
          messagesContainer.appendChild(infoBubble);
          maybeAutoscrollMessages();
          safeCreateIcons();
        }
      } catch (err) {
        showToast(`Failed to start training loop: ${err.message}`, 'error');
      } finally {
        startTrainAgentBtn.disabled = false;
      }
    });
  }

  if (messagesContainer) {
    messagesContainer.addEventListener('click', async (e) => {
      // Handoff card actions [CARD-197, REQ-FACT-048]
      const launchFactoryBtn = e.target.closest('[data-action="launch-factory"]');
      if (launchFactoryBtn) {
        const agentId = launchFactoryBtn.getAttribute('data-agent-id');
        if (typeof callbacks.openFactoryStudio === 'function') {
          callbacks.openFactoryStudio(agentId);
        } else if (typeof window.openFactoryStudioForAgent === 'function') {
          window.openFactoryStudioForAgent(agentId);
        }
        return;
      }
      const openStudioBtn = e.target.closest('[data-action="open-studio"]');
      if (openStudioBtn) {
        const agentId = openStudioBtn.getAttribute('data-agent-id');
        if (typeof callbacks.openAgentForge === 'function') {
          callbacks.openAgentForge(agentId);
        } else if (typeof window.openForgeStudioForAgent === 'function') {
          window.openForgeStudioForAgent(agentId);
        }
        return;
      }

      const openLabBtn = e.target.closest('.open-lab-drawer-btn');
      if (openLabBtn) {
        const jobId = openLabBtn.getAttribute('data-job-id');
        if (typeof window.openLabMonitorDrawer === 'function') {
          window.openLabMonitorDrawer(jobId);
        } else {
          const labDrawer = $('labMonitorDrawer');
          if (labDrawer) {
            labDrawer.classList.remove('hidden');
            const jobSelect = $('labJobSelect');
            if (jobSelect && jobId) {
              jobSelect.value = jobId;
              jobSelect.dispatchEvent(new Event('change'));
            }
          }
        }
        return;
      }
      const approveBtn = e.target.closest('.approve-factory-btn');
      if (approveBtn) {
        const jobId = approveBtn.getAttribute('data-job-id');
        if (!jobId) return;
        approveBtn.disabled = true;
        approveBtn.textContent = 'Deploying...';
        try {
          const res = await fetch(`/api/agent_training_factory/jobs/${encodeURIComponent(jobId)}/promote`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || err.error || `HTTP ${res.status}`);
          }
          showToast('Agent Pack approved and deployed to platform!', 'success');
          approveBtn.textContent = 'Deployed';
          approveBtn.classList.remove('bg-emerald-600', 'hover:bg-emerald-500');
          approveBtn.classList.add('bg-slate-700', 'cursor-default');
          await loadAgents();
        } catch (err) {
          approveBtn.disabled = false;
          approveBtn.textContent = 'Approve & Deploy';
          showToast(`Promotion failed: ${err.message}`, 'error');
        }
        return;
      }
      const rejectBtn = e.target.closest('.reject-factory-btn');
      if (rejectBtn) {
        const card = rejectBtn.closest('.factory-promotion-card');
        if (card) card.remove();
        return;
      }

      // Teach Agent & Skill Proposal Actions [CARD-352, REQ-SKIL-011, REQ-SKIL-013, REQ-SKIL-014]
      const teachBtn = e.target.closest('.msg-teach-agent-btn');
      if (teachBtn) {
        const messageId = teachBtn.getAttribute('data-message-id') || null;
        openTeachAgentModal({
          messageId,
          targetAgentId: state.selectedAgentId || 'autoreiv',
        });
        return;
      }

      const adoptBtn = e.target.closest('.btn-adopt-skill');
      if (adoptBtn) {
        const card = adoptBtn.closest('.skill-proposal-card');
        const skillId = card?.dataset?.skillId;
        const targetAgent = card?.dataset?.targetAgentId || state.selectedAgentId || 'autoreiv';
        const runbookMarkdown = card?.dataset?.runbookMarkdown || '';
        const messageId = card?.dataset?.messageId || null;
        if (!skillId) return;

        adoptBtn.disabled = true;
        const originalText = adoptBtn.innerHTML;
        adoptBtn.innerHTML = '<span>⏳ Adopting...</span>';

        try {
          const res = await fetch('/api/skills/adopt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              target_agent_id: targetAgent,
              skill_id: skillId,
              runbook_markdown: runbookMarkdown,
              message_id: messageId,
              session_id: state.activeSessionId,
            }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${res.status}`);
          }
          if (card) {
            card.dataset.adopted = 'true';
          }
          const actionsContainer = card.querySelector('.card-actions');
          if (actionsContainer) {
            actionsContainer.innerHTML = `
              <div class="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-xs text-emerald-300 font-medium flex items-center space-x-2">
                <span>✓</span>
                <span>Skill mounted to <strong>${escapeHtml(targetAgent)}</strong>. Active for your next message.</span>
              </div>
            `;
          }
          showToast(`Skill mounted to ${targetAgent}. Active for your next message.`, 'success');
          await loadAgents();
        } catch (err) {
          adoptBtn.disabled = false;
          adoptBtn.innerHTML = originalText;
          showToast(`Adoption failed: ${err.message}`, 'error');
        }
        return;
      }

      const escalateBtn = e.target.closest('.btn-escalate-factory');
      if (escalateBtn) {
        const card = escalateBtn.closest('.skill-proposal-card');
        let escalationData;
        try {
          escalationData = JSON.parse(card?.dataset?.factoryEscalation || '{}');
        } catch {
          escalationData = {};
        }
        escalateToFactoryStudio(escalationData);
        return;
      }

      const dismissBtn = e.target.closest('.btn-dismiss-proposal');
      if (dismissBtn) {
        const card = dismissBtn.closest('.skill-proposal-card');
        if (card) card.remove();
        return;
      }
    });
  }

  function toggleChatOptionsDrawer(open) {
    if (!chatOptionsDrawer) return;
    const shouldOpen = typeof open === 'boolean' ? open : chatOptionsDrawer.classList.contains('hidden');
    chatOptionsDrawer.classList.toggle('hidden', !shouldOpen);
    if (chatOptionsToggleBtn) {
      chatOptionsToggleBtn.setAttribute('aria-expanded', String(shouldOpen));
      if (shouldOpen) {
        chatOptionsToggleBtn.classList.add('bg-brand-600', 'text-white', 'border-brand-500');
        chatOptionsToggleBtn.classList.remove('bg-slate-800/90', 'text-slate-300');
      } else {
        chatOptionsToggleBtn.classList.remove('bg-brand-600', 'text-white', 'border-brand-500');
        chatOptionsToggleBtn.classList.add('bg-slate-800/90', 'text-slate-300');
      }
    }
    if (chatOptionsToggleIcon) {
      chatOptionsToggleIcon.classList.toggle('rotate-45', shouldOpen);
    }
    if (shouldOpen) {
      safeCreateIcons();
      loadChatSessionContext();
    }
  }

  if (chatOptionsToggleBtn) {
    chatOptionsToggleBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleChatOptionsDrawer();
    });
  }

  if (chatOptionsCloseBtn) {
    chatOptionsCloseBtn.addEventListener('click', () => {
      toggleChatOptionsDrawer(false);
    });
  }

  document.addEventListener('click', (e) => {
    if (chatOptionsDrawer && !chatOptionsDrawer.classList.contains('hidden')) {
      if (!chatOptionsDrawer.contains(e.target) && !chatOptionsToggleBtn?.contains(e.target)) {
        toggleChatOptionsDrawer(false);
      }
    }
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (chatToolsModal && !chatToolsModal.classList.contains('hidden')) {
        toggleToolsModal(false);
      } else if (chatPromptsQuickPicker && !chatPromptsQuickPicker.classList.contains('hidden')) {
        chatPromptsQuickPicker.classList.add('hidden');
      } else if (chatOptionsDrawer && !chatOptionsDrawer.classList.contains('hidden')) {
        toggleChatOptionsDrawer(false);
      }
    }
  });

  async function loadChatSessionContext() {
    if (!state.activeSessionId) {
      if (chatContextTokensBadge) chatContextTokensBadge.textContent = '0 / 8,192 tokens (0%)';
      if (chatContextProgressBar) chatContextProgressBar.style.width = '0%';
      if (chatToolsCountBadge) chatToolsCountBadge.textContent = '0 tools';
      return;
    }
    const data = await querySessionContext(state.activeSessionId);
    if (!data) return;
    cachedSessionContext = data;

    if (chatContextTokensBadge) {
      chatContextTokensBadge.textContent = formatContextBudgetBadge(data.used_tokens, data.max_tokens, data.percent_used);
    }
    if (chatContextProgressBar) {
      chatContextProgressBar.style.width = `${Math.min(100, Math.max(0, data.percent_used))}%`;
      if (data.percent_used >= 85) {
        chatContextProgressBar.className = 'bg-rose-500 h-full rounded-full transition-all duration-300';
      } else if (data.percent_used >= 60) {
        chatContextProgressBar.className = 'bg-amber-500 h-full rounded-full transition-all duration-300';
      } else {
        chatContextProgressBar.className = 'bg-brand-500 h-full rounded-full transition-all duration-300';
      }
    }
    if (chatToolsCountBadge) {
      const count = Number(data.tools_count || 0);
      chatToolsCountBadge.textContent = `${count} tool${count === 1 ? '' : 's'}`;
    }
  }

  function renderToolsModal(filter = '') {
    if (!chatToolsModalList) return;
    const tools = (cachedSessionContext && cachedSessionContext.tools) || [];
    const filtered = filterToolsList(tools, filter);

    if (filtered.length === 0) {
      chatToolsModalList.innerHTML = `
        <div class="text-center py-8 text-slate-500 text-xs">
          <i data-lucide="wrench" class="w-8 h-8 mx-auto mb-2 opacity-40"></i>
          <p>${filter ? 'No tools match your search.' : 'No tools loaded for this agent.'}</p>
        </div>
      `;
      safeCreateIcons();
      return;
    }

    chatToolsModalList.innerHTML = filtered
      .map(
        (t) => `
        <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700/80 transition space-y-1">
          <div class="flex items-center space-x-2">
            <span class="w-1.5 h-1.5 rounded-full bg-sky-400 flex-shrink-0"></span>
            <span class="font-mono text-xs font-semibold text-sky-300">${escapeHtml(t.name || '')}</span>
          </div>
          <p class="text-xs text-slate-400 pl-3.5 leading-relaxed">${escapeHtml(t.description || 'No description provided.')}</p>
        </div>
      `
      )
      .join('');
    safeCreateIcons();
  }

  function toggleToolsModal(open) {
    if (!chatToolsModal) return;
    const shouldOpen = typeof open === 'boolean' ? open : chatToolsModal.classList.contains('hidden');
    chatToolsModal.classList.toggle('hidden', !shouldOpen);
    if (shouldOpen) {
      if (chatToolsModalTitle) {
        const agentName = (cachedSessionContext && cachedSessionContext.agent_name) || state.selectedAgentId || 'Agent';
        chatToolsModalTitle.textContent = `Active Tools (${agentName})`;
      }
      if (chatToolsModalBadge) {
        const count = (cachedSessionContext && cachedSessionContext.tools_count) || 0;
        chatToolsModalBadge.textContent = `${count} tool${count === 1 ? '' : 's'}`;
      }
      if (chatToolsSearchInput) chatToolsSearchInput.value = '';
      renderToolsModal();
      safeCreateIcons();
    }
  }

  if (chatManualCompactBtn) {
    chatManualCompactBtn.addEventListener('click', async () => {
      if (!state.activeSessionId) {
        showToast('No active chat session to compact.', 'info');
        return;
      }
      chatManualCompactBtn.disabled = true;
      const originalText = chatManualCompactBtn.innerHTML;
      chatManualCompactBtn.innerHTML = '<span class="animate-spin mr-1">⏳</span> Compacting...';
      try {
        const res = await postSessionCompaction(state.activeSessionId);
        if (!res.success) {
          throw new Error(res.error || 'Compaction failed');
        }
        if (res.compaction_applied) {
          const saved = Math.max(0, (res.original_tokens || 0) - (res.compacted_tokens || 0));
          showToast(`Compacted ${res.turns_compacted} turns (freed ${saved.toLocaleString()} tokens)`, 'success');
          await loadMessages(state.activeSessionId, { force: true });
          await loadChatSessionContext();
        } else {
          showToast('Conversation is already compact. No earlier turns to compress.', 'info');
          await loadChatSessionContext();
        }
      } catch (err) {
        showToast(err.message || 'Failed to compact context', 'error');
      } finally {
        chatManualCompactBtn.disabled = false;
        chatManualCompactBtn.innerHTML = originalText;
        safeCreateIcons();
      }
    });
  }

  if (chatViewToolsBtn) {
    chatViewToolsBtn.addEventListener('click', () => {
      toggleToolsModal(true);
    });
  }

  if (chatToolsModalCloseBtn) {
    chatToolsModalCloseBtn.addEventListener('click', () => {
      toggleToolsModal(false);
    });
  }

  if (chatToolsModalDismissBtn) {
    chatToolsModalDismissBtn.addEventListener('click', () => {
      toggleToolsModal(false);
    });
  }

  if (chatToolsModal) {
    chatToolsModal.addEventListener('click', (e) => {
      if (e.target === chatToolsModal) {
        toggleToolsModal(false);
      }
    });
  }

  if (chatToolsSearchInput) {
    chatToolsSearchInput.addEventListener('input', (e) => {
      renderToolsModal(e.target.value);
    });
  }

  // Media & File Attachments Handling [CARD-143]
  function renderStagedAttachments() {
    if (!chatAttachmentsPreviewList) return;
    if (stagedAttachments.length === 0) {
      chatAttachmentsPreviewList.innerHTML = '';
      chatAttachmentsPreviewList.classList.add('hidden');
      return;
    }
    chatAttachmentsPreviewList.classList.remove('hidden');
    chatAttachmentsPreviewList.innerHTML = stagedAttachments
      .map((att, idx) => {
        const isImg = att.content_type?.startsWith('image/') || /\.(png|jpe?g|gif|webp|svg)$/i.test(att.filename || '');
        const icon = isImg ? '🖼️' : '📄';
        return `
          <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-800/90 border border-slate-700 text-xs text-slate-200 flex-shrink-0 shadow-sm" data-att-idx="${idx}">
            <span class="text-xs">${icon}</span>
            <span class="font-medium max-w-[120px] truncate text-[11px]" title="${escapeHtml(att.filename || 'file')}">${escapeHtml(att.filename || 'file')}</span>
            <span class="text-[10px] text-slate-400 font-mono">(${formatBytes(att.size_bytes || 0)})</span>
            <button type="button" class="remove-attachment-btn text-slate-400 hover:text-rose-400 p-0.5 rounded transition" data-att-idx="${idx}" title="Remove file">
              <svg class="w-3 h-3 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
          </div>
        `;
      })
      .join('');

    chatAttachmentsPreviewList.querySelectorAll('.remove-attachment-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.getAttribute('data-att-idx'), 10);
        if (!isNaN(idx) && idx >= 0 && idx < stagedAttachments.length) {
          stagedAttachments.splice(idx, 1);
          renderStagedAttachments();
        }
      });
    });
  }

  async function uploadStagedFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    if (state.activeSessionId) {
      formData.append('session_id', state.activeSessionId);
    }
    const res = await fetch('/api/chat/upload', {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload file');
    return await res.json();
  }

  if (chatAttachBtn && chatFileInput) {
    chatAttachBtn.addEventListener('click', () => {
      chatFileInput.click();
    });

    chatFileInput.addEventListener('change', async (e) => {
      const files = Array.from(e.target.files || []);
      if (files.length === 0) return;
      toggleChatOptionsDrawer(false);
      for (const file of files) {
        try {
          const uploaded = await uploadStagedFile(file);
          stagedAttachments.push({
            id: uploaded.id,
            filename: uploaded.filename,
            size_bytes: uploaded.size_bytes,
            content_type: uploaded.content_type,
            url: uploaded.url,
            path: uploaded.path,
          });
          renderStagedAttachments();
          showToast(`Attached ${uploaded.filename}`, 'info');
        } catch (err) {
          console.error('[AutoReiv UI] Failed to attach file:', err);
          showToast(`Failed to upload ${file.name}: ${err.message}`, 'error');
        }
      }
      chatFileInput.value = '';
    });
  }

  // Prompt Catalog Modal Controller [CARD-147]
  // Lightweight Quick Prompt Picker Controller [CARD-152]
  async function loadQuickPrompts() {
    try {
      const res = await fetch('/api/prompts');
      if (!res.ok) return;
      quickPrompts = await res.json();
      renderQuickPrompts();
    } catch (err) {
      console.error('[Quick Prompts] Load error:', err);
    }
  }

  function renderQuickPrompts() {
    if (!chatPromptsQuickList) return;
    const q = (chatPromptsQuickSearch ? chatPromptsQuickSearch.value : '').toLowerCase().trim();
    const filtered = quickPrompts.filter(p => {
      if (!q) return true;
      return (p.title || '').toLowerCase().includes(q) ||
        (p.category || '').toLowerCase().includes(q) ||
        (p.description || '').toLowerCase().includes(q) ||
        (p.template_text || '').toLowerCase().includes(q);
    });

    if (filtered.length === 0) {
      chatPromptsQuickList.innerHTML = '<div class="p-3 text-center text-slate-500 text-[11px]">No matching prompts</div>';
      return;
    }

    chatPromptsQuickList.innerHTML = filtered.map(item => `
      <div data-quick-id="${escapeHtml(item.id)}" class="quick-prompt-item p-2 rounded-xl bg-slate-950/70 hover:bg-slate-800/80 border border-slate-800/80 hover:border-slate-700 cursor-pointer transition flex items-center justify-between gap-2 group">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-1.5">
            <span class="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">${escapeHtml(item.category || 'general')}</span>
            <span class="text-xs font-semibold text-slate-200 truncate">${escapeHtml(item.title)}</span>
          </div>
          ${item.description ? `<p class="text-[10px] text-slate-400 truncate mt-0.5">${escapeHtml(item.description)}</p>` : ''}
        </div>
        <button type="button" class="px-2 py-1 bg-brand-600/80 group-hover:bg-brand-600 text-white rounded-lg text-[10px] font-semibold flex-shrink-0 transition">
          Insert
        </button>
      </div>
    `).join('');

    chatPromptsQuickList.querySelectorAll('.quick-prompt-item').forEach(el => {
      el.addEventListener('click', () => {
        const id = el.getAttribute('data-quick-id');
        const target = quickPrompts.find(p => p.id === id);
        if (target && promptInput) {
          promptInput.value = target.template_text || '';
          promptInput.dispatchEvent(new Event('input'));
          promptInput.focus();
          if (chatPromptsQuickPicker) chatPromptsQuickPicker.classList.add('hidden');
          toggleChatOptionsDrawer(false);
          showToast(`Loaded "${target.title}"`, 'info');
        }
      });
    });
  }

  if (chatPromptsBtn && chatPromptsQuickPicker) {
    chatPromptsBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isHidden = chatPromptsQuickPicker.classList.contains('hidden');
      if (isHidden) {
        chatPromptsQuickPicker.classList.remove('hidden');
        if (chatPromptsQuickSearch) {
          chatPromptsQuickSearch.value = '';
          setTimeout(() => chatPromptsQuickSearch.focus(), 50);
        }
        loadQuickPrompts();
      } else {
        chatPromptsQuickPicker.classList.add('hidden');
      }
    });

    document.addEventListener('click', (e) => {
      if (!chatPromptsQuickPicker.contains(e.target) && e.target !== chatPromptsBtn && !chatPromptsBtn.contains(e.target)) {
        chatPromptsQuickPicker.classList.add('hidden');
      }
    });
  }

  if (chatPromptsQuickSearch) {
    chatPromptsQuickSearch.addEventListener('input', () => {
      renderQuickPrompts();
    });
  }

  if (chatManagePromptsBtn) {
    chatManagePromptsBtn.addEventListener('click', () => {
      if (chatPromptsQuickPicker) chatPromptsQuickPicker.classList.add('hidden');
      toggleChatOptionsDrawer(false);
      const navPrompts = $('navPrompts');
      if (navPrompts) navPrompts.click();
    });
  }

  // Prompt listeners [CARD-215 standing runtime — no Goal-mode suggestion theatre]
  if (promptInput) {
    promptInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (chatForm) {
          if (typeof chatForm.requestSubmit === 'function') {
            chatForm.requestSubmit();
          } else {
            chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
          }
        }
      }
    });
  }


  // Chat Submission & Streaming
  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = promptInput ? promptInput.value.trim() : '';
      if ((!text && stagedAttachments.length === 0) || state.isStreaming) return;

      if (text.startsWith('/learn')) {
        if (promptInput) promptInput.value = '';
        const guidance = text.replace(/^\/learn\s*/, '').trim();
        openTeachAgentModal({
          messageId: null,
          targetAgentId: state.selectedAgentId || 'autoreiv',
          guidance,
        });
        return;
      }

      if (!state.activeSessionId) {
        await createNewSession();
      }

      const attachmentsToSend = [...stagedAttachments];
      stagedAttachments = [];
      renderStagedAttachments();

      if (messagesContainer) {
        const emptyPlaceholder = messagesContainer.querySelector('.text-center');
        if (emptyPlaceholder) emptyPlaceholder.remove();
      }

      appendMessageBubble('user', text, { attachments: attachmentsToSend });
      if (promptInput) promptInput.value = '';
      maybeAutoscrollMessages();

      await executeChatTurn(text, { attachments: attachmentsToSend });
    });
  }

  async function executeChatTurn(userPrompt, options = {}) {
    resetInlineJobChrome();
    resetJobPhaseStrip();
    state.isStreaming = true;
    if (messagesContainer) {
      const emptyPlaceholder = messagesContainer.querySelector('.text-center');
      if (emptyPlaceholder) emptyPlaceholder.remove();
    }
    if (sendBtn) {
      sendBtn.disabled = true;
      sendBtn.classList.add('hidden');
    }
    if (stopBtn) stopBtn.classList.remove('hidden');
    activeAbortController = new AbortController();

    const streamBubble = document.createElement('div');
    streamBubble.className = 'flex justify-start w-full';
    streamBubble.setAttribute('data-stream-bubble', 'true');
    streamBubble.setAttribute('data-job-chrome', 'inline');
    streamBubble.innerHTML = `
      <div class="max-w-4xl w-full rounded-2xl p-4 shadow-md bg-slate-900/90 border border-slate-800/80 text-slate-100 rounded-bl-sm space-y-3" data-job-chrome-card="1">
        <div class="flex items-center justify-between text-xs font-bold uppercase tracking-wider opacity-70">
          <span>${escapeHtml(activeAgentTitle ? activeAgentTitle.textContent : 'Agent')}</span>
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
        <div class="handoff-status-badge hidden p-2.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-xs text-indigo-200 flex-col space-y-1"></div>
        <div class="reasoning-drawer hidden rounded-xl border border-amber-500/30 bg-amber-950/20 overflow-hidden text-xs">
          <button type="button" class="reasoning-toggle w-full p-2.5 flex items-center justify-between bg-amber-950/40 text-amber-300 font-semibold hover:bg-amber-950/60 transition">
            <span class="flex items-center space-x-1.5">
              <i data-lucide="brain" class="w-3.5 h-3.5 text-amber-400"></i>
              <span>Thought Process (<span class="reasoning-time">0.0s</span>)</span>
            </span>
            <i data-lucide="chevron-down" class="w-3.5 h-3.5 transition-transform duration-200"></i>
          </button>
          <div class="reasoning-content p-3 text-slate-300 font-mono text-[11px] whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto hidden border-t border-amber-500/20"></div>
        </div>
        <div class="stream-content prose prose-invert text-sm break-words leading-relaxed"></div>
        <div class="hitl-approval-card hidden rounded-xl border border-amber-500/30 bg-amber-950/20 p-3 space-y-2 text-xs"></div>
      </div>
    `;

    if (messagesContainer) {
      messagesContainer.appendChild(streamBubble);
      maybeAutoscrollMessages();
    }
    safeCreateIcons();

    const streamContentEl = streamBubble.querySelector('.stream-content');
    const planMilestoneCardEl = streamBubble.querySelector('.plan-milestone-card');
    const planGoalTitleEl = streamBubble.querySelector('.plan-goal-title');
    const planStepCounterEl = streamBubble.querySelector('.plan-step-counter');
    const planStepsContainerEl = streamBubble.querySelector('.plan-steps-container');
    const reflexionStatusBadgeEl = streamBubble.querySelector('.reflexion-status-badge');
    const toolStatusBadgeEl = streamBubble.querySelector('.tool-status-badge');
    const hitlApprovalCardEl = streamBubble.querySelector('.hitl-approval-card');
    const handoffStatusBadgeEl = streamBubble.querySelector('.handoff-status-badge');
    const reasoningDrawerEl = streamBubble.querySelector('.reasoning-drawer');
    const reasoningToggleBtn = streamBubble.querySelector('.reasoning-toggle');
    const reasoningContentEl = streamBubble.querySelector('.reasoning-content');
    const reasoningTimeEl = streamBubble.querySelector('.reasoning-time');

    if (reasoningToggleBtn && reasoningContentEl) {
      reasoningToggleBtn.addEventListener('click', () => {
        reasoningContentEl.classList.toggle('hidden');
        const icon = reasoningToggleBtn.querySelector('[data-lucide="chevron-down"]');
        if (icon) icon.classList.toggle('rotate-180');
      });
    }

    let fullAssistantText = '';
    let fullReasoningText = '';
    const startTime = Date.now();

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: activeAbortController ? activeAbortController.signal : undefined,
        body: JSON.stringify(buildChatStreamPayload({
          agentId: state.selectedAgentId,
          sessionId: state.activeSessionId,
          content: userPrompt,
          resume: Boolean(options && options.resume),
          selfVerify: !!state.verifyEnabled,
          approvalAutoRun: state.approvalAutoRun,
          attachments: (options && options.attachments) || [],
        })),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = 'message';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) {
            currentEvent = 'message';
            continue;
          }
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.slice(6).trim();
            continue;
          }
          if (!trimmed.startsWith('data:')) continue;
          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr || jsonStr === '[DONE]') continue;

          try {
            const ev = JSON.parse(jsonStr);
            const eventType = ev.type || currentEvent;
            const tokenText = ev.text ?? ev.data ?? '';

            if (
              eventType === 'job_created'
              || eventType === 'resumed_from_checkpoint'
              || eventType === 'phase_start'
              || eventType === 'phase_complete'
              || eventType === 'react_state'
              || eventType === 'plan_formulated'
              || eventType === 'approval_required'
              || eventType === 'step_start'
              || eventType === 'step_complete'
            ) {
              // CARD-295: full chrome (strip + inline Formulate/Execute), not strip-only.
              updateJobChromeFromEvent(eventType, ev);
            }
            if (isHitlParkSseEvent(eventType, ev)) {
              // Pull Approve/Deny into the live thread without requiring a browser refresh.
              refreshPendingHitl();
            }

            if (eventType === 'plan_formulated') {
              if (planMilestoneCardEl) {
                planMilestoneCardEl.classList.remove('hidden');
                if (planGoalTitleEl) planGoalTitleEl.textContent = formatMilestoneGoalTitle(ev.goal);
                if (planStepCounterEl) planStepCounterEl.textContent = `${ev.steps ? ev.steps.length : 0} Steps`;
                if (planStepsContainerEl && Array.isArray(ev.steps)) {
                  planStepsContainerEl.innerHTML = '';
                  ev.steps.forEach((s, idx) => {
                    const stepItem = document.createElement('div');
                    stepItem.id = `plan-step-${idx}`;
                    stepItem.className = 'plan-step-item p-2 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-between text-xs transition';
                    stepItem.innerHTML = `
                      <div class="flex items-center space-x-2 truncate mr-2">
                        <span class="step-status-icon text-slate-400">⏳</span>
                        <span class="step-title font-medium text-slate-200 truncate">${escapeHtml(s.title)}</span>
                      </div>
                      <span class="step-badge text-[10px] font-mono text-slate-400 shrink-0">Pending</span>
                    `;
                    planStepsContainerEl.appendChild(stepItem);
                  });
                }
                if (ev.approval_id) {
                  const existing = planMilestoneCardEl.querySelector(".plan-review-actions");
                  if (existing) existing.remove();
                  const actions = document.createElement("div");
                  actions.className = "plan-review-actions space-y-2 pt-2";
                  actions.innerHTML = `
                    <p class="text-slate-400">Approve to run these steps. Reject or send a message to revise.</p>
                    <div class="flex items-center space-x-2">
                      <button type="button" data-hitl-decision="APPROVED" class="px-2.5 py-1 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none text-white text-xs font-semibold">Approve</button>
                      <button type="button" data-hitl-decision="REJECTED" class="px-2.5 py-1 rounded-lg bg-rose-800 hover:bg-rose-700 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none text-white text-xs font-semibold">Reject</button>
                      <span class="hitl-card-status text-amber-200"></span>
                    </div>
                  `;
                  planMilestoneCardEl.appendChild(actions);
                  actions.querySelectorAll("[data-hitl-decision]").forEach((btn) => {
                    btn.addEventListener("click", async () => {
                      const result = await submitHitlDecision(
                        ev.approval_id,
                        btn.getAttribute("data-hitl-decision"),
                        planMilestoneCardEl,
                        state.activeSessionId,
                      );
                      if (result.ok && shouldResumeChatAfterHitl({
                        approvalSessionId: state.activeSessionId,
                        openSessionId: state.activeSessionId,
                        backendResumed: Boolean(result.body && result.body.resumed),
                        nestedStatus: result.body && result.body.nested ? result.body.nested.status : null,
                      })) {
                        await executeChatTurn("", { resume: true });
                      }
                    });
                  });
                }
              }
            } else if (eventType === 'step_start') {
              const stepIdx = ev.step_index !== undefined ? ev.step_index : -1;
              const stepEl = streamBubble.querySelector(`#plan-step-${stepIdx}`);
              if (stepEl) {
                stepEl.className = 'plan-step-item p-2 rounded-lg bg-indigo-950/60 border border-indigo-500/50 text-indigo-200 ring-1 ring-indigo-500/30 flex items-center justify-between text-xs transition';
                const icon = stepEl.querySelector('.step-status-icon');
                const badge = stepEl.querySelector('.step-badge');
                if (icon) icon.innerHTML = '<span class="animate-pulse">⚡</span>';
                if (badge) {
                  badge.className = 'step-badge text-[10px] font-mono text-indigo-400 animate-pulse shrink-0';
                  badge.textContent = 'Running...';
                }
              }
            } else if (eventType === 'step_complete') {
              const stepIdx = ev.step_index !== undefined ? ev.step_index : -1;
              const stepEl = streamBubble.querySelector(`#plan-step-${stepIdx}`);
              if (stepEl) {
                stepEl.className = 'plan-step-item p-2 rounded-lg bg-slate-800/40 border border-slate-700/40 text-slate-300 opacity-80 flex items-center justify-between text-xs transition';
                const icon = stepEl.querySelector('.step-status-icon');
                const badge = stepEl.querySelector('.step-badge');
                if (icon) icon.innerHTML = '<span class="text-emerald-400 font-bold">✓</span>';
                if (badge) {
                  badge.className = 'step-badge text-[10px] font-mono text-emerald-400 shrink-0';
                  badge.textContent = 'Done';
                }
              }
            } else if (eventType === 'reflexion_attempt' || eventType === 'reflexion_critique' || eventType === 'reflexion_verified') {
              renderReflexionBadge(reflexionStatusBadgeEl, eventType, ev);
            } else if (eventType === 'token') {
              fullAssistantText += tokenText;
              if (streamContentEl) {
                streamContentEl.innerHTML = window.marked
                  ? window.marked.parse(fullAssistantText)
                  : escapeHtml(fullAssistantText);
              }
            } else if (eventType === 'reasoning') {
              fullReasoningText += tokenText;
              if (reasoningDrawerEl) reasoningDrawerEl.classList.remove('hidden');
              if (reasoningContentEl) reasoningContentEl.textContent = fullReasoningText;
              const durationSec = ((Date.now() - startTime) / 1000).toFixed(1);
                            if (reasoningTimeEl) reasoningTimeEl.textContent = `${durationSec}s`;
            } else if (eventType === 'approval_required') {
              const msg = ev.message || 'Waiting for operator approval';
              const id = ev.approval_id || '';
              const toolName = ev.tool_name || 'tool';
              const pulseBadge = streamBubble.querySelector('.animate-pulse');
              if (pulseBadge) {
                pulseBadge.remove();
              }
              if (isGoalPlanReviewTool(toolName)) {
                // Plan card owns Approve/Reject; do not also show the tool HITL card.
              } else {
              fullAssistantText += `\n\n**Approval required** for \`${toolName}\`\n`;
              if (streamContentEl) {
                streamContentEl.innerHTML = window.marked
                  ? window.marked.parse(fullAssistantText)
                  : escapeHtml(fullAssistantText);
              }
              if (toolStatusBadgeEl) {
                toolStatusBadgeEl.classList.remove('hidden');
                toolStatusBadgeEl.classList.add('flex');
                toolStatusBadgeEl.innerHTML = `<span>⏸️</span> Approval required: <strong class="text-amber-200">${escapeHtml(toolName)}</strong>`;
              }
              if (hitlApprovalCardEl && id) {
                hitlApprovalCardEl.classList.remove('hidden');
                const argsText = formatHitlArgs(ev.arguments);
                hitlApprovalCardEl.setAttribute('data-approval-id', id);
                hitlApprovalCardEl.innerHTML = buildHitlCardInnerHtml({
                  title: 'Approval required',
                  toolName,
                  message: msg,
                  argsText,
                });
                hitlApprovalCardEl.querySelectorAll('[data-hitl-decision]').forEach((btn) => {
                  btn.addEventListener('click', async () => {
                    const result = await submitHitlDecision(
                      id,
                      btn.getAttribute('data-hitl-decision'),
                      hitlApprovalCardEl,
                      state.activeSessionId,
                    );
                    if (result.ok && shouldResumeChatAfterHitl({
                      approvalSessionId: ev.session_id || state.activeSessionId,
                      openSessionId: state.activeSessionId,
                      backendResumed: Boolean(result.body && result.body.resumed),
                      nestedStatus: result.body && result.body.nested ? result.body.nested.status : null,
                    })) {
                      await executeChatTurn('', { resume: true });
                    }
                    await refreshPendingHitl();
                  });
                });
                if (typeof hitlApprovalCardEl.scrollIntoView === 'function') {
                  hitlApprovalCardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
              }
              }
            } else if (eventType === 'auto_train_progress') {
              const stage = ev.stage || (ev.data && ev.data.stage) || 'synthesizing';
              const detail = ev.detail || (ev.data && ev.data.detail) || 'Synthesizing missing tool in sandbox...';
              if (toolStatusBadgeEl) {
                toolStatusBadgeEl.classList.remove('hidden');
                toolStatusBadgeEl.classList.add('flex');
                toolStatusBadgeEl.innerHTML = `<span>⚡</span> <strong class="text-amber-300 font-mono">[Auto-Train ${escapeHtml(stage)}]</strong> <span class="text-slate-200">${escapeHtml(detail)}</span>`;
              }
            } else if (eventType === 'tool_start' || eventType === 'tool_call') {


              const toolName = ev.tool_name || (ev.data && ev.data.name) || 'tool';
              if (toolStatusBadgeEl) {
                toolStatusBadgeEl.classList.remove('hidden');
                toolStatusBadgeEl.classList.add('flex');
                toolStatusBadgeEl.innerHTML = `<span class="font-mono text-cyan-400 font-semibold mr-1.5">[EXEC] ↳</span> Invoking tool: <strong class="text-white font-mono">${escapeHtml(toolName)}</strong>...`;
              }
            } else if (eventType === 'tool_output' || eventType === 'tool_result') {
              const toolName = ev.tool_name || (ev.data && ev.data.name) || 'tool';
              if (toolStatusBadgeEl) {
                toolStatusBadgeEl.classList.remove('hidden');
                toolStatusBadgeEl.classList.add('flex');
                toolStatusBadgeEl.innerHTML = `<span class="font-mono text-emerald-400 font-semibold mr-1.5">[DONE] ↳</span> Tool complete: <strong class="text-emerald-300 font-mono">${escapeHtml(toolName)}</strong>`;
              }
            } else if (eventType === 'handoff_start') {
              const recipient = ev.recipient || 'Specialist Agent';
              const directive = ev.directive || '';
              if (handoffStatusBadgeEl) {
                handoffStatusBadgeEl.classList.remove('hidden');
                handoffStatusBadgeEl.classList.add('flex');
                handoffStatusBadgeEl.innerHTML = `
                  <div class="flex items-center justify-between font-semibold text-indigo-300">
                    <span class="flex items-center space-x-1.5">
                      <span>🤝</span>
                      <span>Delegating to <strong>${escapeHtml(recipient)}</strong>...</span>
                    </span>
                    <span class="font-mono text-[10px] text-indigo-400 animate-pulse">Delegating</span>
                  </div>
                  ${directive ? `<div class="text-[11px] text-slate-300 font-mono bg-indigo-950/60 p-1.5 rounded border border-indigo-900/50">"${escapeHtml(directive)}"</div>` : ''}
                `;
              }
            } else if (eventType === 'handoff_complete') {
              const recipient = ev.recipient || 'Specialist Agent';
              const isParked = ev.status === 'approval_required';
              const isOk = ev.status === 'completed';
              if (handoffStatusBadgeEl) {
                handoffStatusBadgeEl.classList.remove('hidden');
                handoffStatusBadgeEl.classList.add('flex');
                const tone = isParked ? 'text-amber-300' : (isOk ? 'text-emerald-300' : 'text-rose-300');
                const label = isParked ? 'Waiting for approval' : (isOk ? 'Completed' : 'Failed');
                const tag = isParked ? 'Parked' : (isOk ? 'Done' : 'Error');
                const tagTone = isParked ? 'text-amber-400' : (isOk ? 'text-emerald-400' : 'text-rose-400');
                handoffStatusBadgeEl.innerHTML = `
                  <div class="flex items-center justify-between font-semibold ${tone}">
                    <span class="flex items-center space-x-1.5">
                      <span>${isParked ? '⏸️' : (isOk ? '✓' : '✗')}</span>
                      <span>Delegation to <strong>${escapeHtml(recipient)}</strong> ${label}</span>
                    </span>
                    <span class="font-mono text-[10px] ${tagTone}">${tag}</span>
                  </div>
                  ${ev.error ? `<div class="text-[11px] text-rose-300 font-mono bg-rose-950/40 p-1.5 rounded border border-rose-900/50">${escapeHtml(ev.error)}</div>` : ''}
                `;
              }
            } else if (eventType === 'error') {
              const errText = ev.error || tokenText || 'stream error';
              if (streamContentEl) {
                streamContentEl.innerHTML += `<p class="text-rose-400 font-mono text-xs mt-2">Error: ${escapeHtml(errText)}</p>`;
              }
            }

          } catch {
            // Non-JSON event line
          }
        }
        maybeAutoscrollMessages();
      }

      if (streamContentEl) {
        await renderMarkdown(streamContentEl, fullAssistantText);
      }
    } catch (err) {
      const wasAborted = Boolean(activeAbortController && activeAbortController.signal && activeAbortController.signal.aborted);
      let isBackgroundRunning = false;
      if (!wasAborted && state.activeSessionId) {
        try {
          const status = await querySessionStatus(state.activeSessionId);
          if (status.is_running) {
            isBackgroundRunning = true;
          }
        } catch {
          // ignore status lookup failures
        }
      }

      if (isBackgroundRunning) {
        if (streamContentEl) {
          streamContentEl.innerHTML += `
            <div class="mt-2 p-2 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-xs text-indigo-200 flex items-center space-x-2 animate-pulse">
              <span>⏳</span>
              <span>Subagent or background task is running on server. Reconnecting...</span>
            </div>
          `;
        }
        checkSessionBackgroundStatus(state.activeSessionId);
        return;
      } else if (streamContentEl && !wasAborted) {
        streamContentEl.innerHTML += `<p class="text-rose-400 font-mono text-xs mt-2">Error: ${escapeHtml(err.message)}</p>`;
      }
    } finally {
      const pulseBadge = streamBubble ? streamBubble.querySelector('.animate-pulse') : null;
      if (pulseBadge) {
        pulseBadge.remove();
      }
      if (backgroundPollInterval) {
        clearInterval(backgroundPollInterval);
        backgroundPollInterval = null;
      }
      state.isStreaming = false;
      if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.classList.remove('hidden');
      }
      if (stopBtn) {
        stopBtn.classList.add('hidden');
      }
      activeAbortController = null;
      if (state.activeSessionId) {
        await loadMessages(state.activeSessionId);
        await loadSessions();
        // CARD-295: stream-end must surface pending HITL + keep journey chrome without refresh.
        await refreshPendingHitl();
        remountInlineJobChrome();
        renderJobPhaseStrip();
      }
      safeCreateIcons();
    }
  }

  // Abort generation listener [REQ-RESIL-003, CARD-114 Finding 4]
  if (stopBtn) {
    stopBtn.addEventListener('click', async () => {
      if (backgroundPollInterval) {
        clearInterval(backgroundPollInterval);
        backgroundPollInterval = null;
      }
      if (activeAbortController) {
        activeAbortController.abort();
      }
      if (messagesContainer) {
        messagesContainer.querySelectorAll('.animate-pulse').forEach((el) => el.remove());
      }
      if (state.activeSessionId) {
        try {
          await fetch(`/api/chat/stream/${encodeURIComponent(state.activeSessionId)}/abort`, {
            method: 'POST',
          });
        } catch (e) {
          console.warn('Failed to send stream abort signal:', e);
        }
      }
      state.isStreaming = false;
      if (sendBtn) {
        sendBtn.disabled = false;
        sendBtn.classList.remove('hidden');
      }
      stopBtn.classList.add('hidden');
      if (state.activeSessionId) {
        await loadMessages(state.activeSessionId, { force: true });
      }
      showToast('info', 'Generation stopped');
    });
  }

  // Journey Inspector [CARD-135]
  function renderJourneyTimeline(data) {
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
        showToast(`Copied ${id}`, 'success');
      });
    });
    safeCreateIcons();
  }

  async function loadJourneyTimeline() {
    if (!state.activeSessionId || !chatJourneyContent) return;
    chatJourneyContent.innerHTML = '<div class="text-slate-400 text-center py-8 animate-pulse">Loading journey...</div>';
    try {
      const res = await fetch(`/api/chat/sessions/${encodeURIComponent(state.activeSessionId)}/journey`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderJourneyTimeline(data);
    } catch (err) {
      chatJourneyContent.innerHTML = `<div class="p-3 rounded bg-rose-950/40 border border-rose-800 text-rose-300">Failed to load journey: ${escapeHtml(err.message)}</div>`;
    }
  }

  // Per-Chat Debug Inspector [CARD-136]
  function renderChatDebugTab() {
    if (!chatDebugContent || !activeDebugData) return;

    const tabs = {
      messages: chatDebugTabMessages,
      tools: chatDebugTabTools,
      metrics: chatDebugTabMetrics,
      system: chatDebugTabSystem,
    };
    Object.entries(tabs).forEach(([k, el]) => {
      if (!el) return;
      if (k === activeDebugTab) {
        el.className = 'px-2.5 py-1 rounded bg-brand-600 text-white font-semibold transition';
      } else {
        el.className = 'px-2.5 py-1 rounded text-slate-400 hover:text-slate-200 transition';
      }
    });

    if (activeDebugTab === 'messages') {
      const msgs = activeDebugData.raw_messages || [];
      chatDebugContent.innerHTML = `
        <div class="space-y-2">
          <div class="text-[11px] text-slate-400 mb-1">Messages Payload (${msgs.length} items)</div>
          <pre class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-emerald-400 text-[11px] overflow-x-auto select-all leading-relaxed">${escapeHtml(JSON.stringify(msgs, null, 2))}</pre>
        </div>
      `;
    } else if (activeDebugTab === 'tools') {
      const tools = activeDebugData.tool_payloads || [];
      chatDebugContent.innerHTML = `
        <div class="space-y-2">
          <div class="text-[11px] text-slate-400 mb-1">Tool Executions (${tools.length} spans)</div>
          <pre class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-amber-300 text-[11px] overflow-x-auto select-all leading-relaxed">${escapeHtml(JSON.stringify(tools, null, 2))}</pre>
        </div>
      `;
    } else if (activeDebugTab === 'metrics') {
      const m = activeDebugData.metrics || {};
      chatDebugContent.innerHTML = `
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="p-2 rounded-lg bg-slate-800/60 border border-slate-700">
              <span class="text-slate-400 block text-[10px]">Active Model</span>
              <span class="font-bold text-slate-100">${escapeHtml(activeDebugData.model || 'default')}</span>
            </div>
            <div class="p-2 rounded-lg bg-slate-800/60 border border-slate-700">
              <span class="text-slate-400 block text-[10px]">Provider</span>
              <span class="font-bold text-slate-100 uppercase">${escapeHtml(activeDebugData.provider || 'ollama')}</span>
            </div>
            <div class="p-2 rounded-lg bg-slate-800/60 border border-slate-700">
              <span class="text-slate-400 block text-[10px]">Prompt Tokens</span>
              <span class="font-bold text-indigo-300 font-mono">${m.total_prompt_tokens || 0}</span>
            </div>
            <div class="p-2 rounded-lg bg-slate-800/60 border border-slate-700">
              <span class="text-slate-400 block text-[10px]">Completion Tokens</span>
              <span class="font-bold text-emerald-300 font-mono">${m.total_completion_tokens || 0}</span>
            </div>
            <div class="p-2 rounded-lg bg-slate-800/60 border border-slate-700">
              <span class="text-slate-400 block text-[10px]">Total Latency</span>
              <span class="font-bold text-slate-100 font-mono">${m.total_duration_ms || 0} ms</span>
            </div>
            <div class="p-2 rounded-lg bg-slate-800/60 border border-slate-700">
              <span class="text-slate-400 block text-[10px]">Avg TTFT</span>
              <span class="font-bold text-slate-100 font-mono">${m.avg_ttft_ms || 0} ms</span>
            </div>
          </div>
          <pre class="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-[11px] overflow-x-auto select-all leading-relaxed">${escapeHtml(JSON.stringify(m, null, 2))}</pre>
        </div>
      `;
    } else if (activeDebugTab === 'system') {
      chatDebugContent.innerHTML = `
        <div class="space-y-2">
          <div class="text-[11px] text-slate-400 mb-1">Active Agent System Prompt</div>
          <pre class="p-3 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 text-[11px] whitespace-pre-wrap leading-relaxed select-all">${escapeHtml(activeDebugData.system_prompt || 'No active system prompt configured.')}</pre>
        </div>
      `;
    }
  }

  async function loadChatDebug() {
    if (!state.activeSessionId || !chatDebugContent) return;
    chatDebugContent.innerHTML = '<div class="text-slate-400 text-center py-8 animate-pulse">Loading diagnostics...</div>';
    try {
      const res = await fetch(`/api/chat/sessions/${encodeURIComponent(state.activeSessionId)}/debug`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      activeDebugData = await res.json();
      renderChatDebugTab();
    } catch (err) {
      chatDebugContent.innerHTML = `<div class="p-3 rounded bg-rose-950/40 border border-rose-800 text-rose-300">Failed to load debug data: ${escapeHtml(err.message)}</div>`;
    }
  }

  if (chatShowJourneyBtn) {
    chatShowJourneyBtn.addEventListener('click', () => {
      if (chatDebugPane) chatDebugPane.classList.add('hidden');
      if (chatJourneyDrawer) {
        const isHidden = chatJourneyDrawer.classList.toggle('hidden');
        if (!isHidden) loadJourneyTimeline();
      }
    });
  }

  if (chatJourneyCloseBtn) {
    chatJourneyCloseBtn.addEventListener('click', () => {
      if (chatJourneyDrawer) chatJourneyDrawer.classList.add('hidden');
    });
  }

  if (chatDebugToggleBtn) {
    chatDebugToggleBtn.addEventListener('click', () => {
      if (chatJourneyDrawer) chatJourneyDrawer.classList.add('hidden');
      if (chatDebugPane) {
        const isHidden = chatDebugPane.classList.toggle('hidden');
        if (!isHidden) loadChatDebug();
      }
    });
  }

  if (chatDebugCloseBtn) {
    chatDebugCloseBtn.addEventListener('click', () => {
      if (chatDebugPane) chatDebugPane.classList.add('hidden');
    });
  }

  if (chatDebugCopyBtn) {
    chatDebugCopyBtn.addEventListener('click', () => {
      if (!activeDebugData) return;
      let textToCopy = '';
      if (activeDebugTab === 'messages') textToCopy = JSON.stringify(activeDebugData.raw_messages || [], null, 2);
      else if (activeDebugTab === 'tools') textToCopy = JSON.stringify(activeDebugData.tool_payloads || [], null, 2);
      else if (activeDebugTab === 'metrics') textToCopy = JSON.stringify(activeDebugData.metrics || {}, null, 2);
      else if (activeDebugTab === 'system') textToCopy = activeDebugData.system_prompt || '';
      copyToClipboard(textToCopy);
      showToast('success', `Copied ${activeDebugTab} to clipboard`);
    });
  }

  [
    { btn: chatDebugTabMessages, tab: 'messages' },
    { btn: chatDebugTabTools, tab: 'tools' },
    { btn: chatDebugTabMetrics, tab: 'metrics' },
    { btn: chatDebugTabSystem, tab: 'system' },
  ].forEach(({ btn, tab }) => {
    if (btn) {
      btn.addEventListener('click', () => {
        activeDebugTab = tab;
        renderChatDebugTab();
      });
    }
  });

  // Copy Thread & Wiki Export
  if (copyThreadBtn) {
    copyThreadBtn.addEventListener('click', () => {
      const threadText = state.messages
        .filter((m) => m.content && m.content.trim() && (m.role || '').toLowerCase() !== 'tool')
        .map((m) => `**${(m.role || '').toUpperCase()}**:\n${m.content}\n`)
        .join('\n---\n\n');
      copyToClipboard(threadText);
    });
  }

  if (exportThreadWikiBtn) {
    exportThreadWikiBtn.addEventListener('click', () => {
      const threadText = state.messages
        .filter((m) => m.content && m.content.trim() && (m.role || '').toLowerCase() !== 'tool')
        .map((m) => `### ${(m.role || '').toUpperCase()}\n\n${m.content}`)
        .join('\n\n---\n\n');
      if (callbacks.exportMessageToWiki) callbacks.exportMessageToWiki(threadText);
    });
  }

  // Mobile Tab Visibility & Reconnection Recovery [REQ-MOB-STREAM-002, CARD-154]
  document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState === 'visible' && state.activeSessionId) {
      await checkSessionBackgroundStatus(state.activeSessionId);
      if (!state.isStreaming) {
        await loadMessages(state.activeSessionId);
        await refreshPendingHitl();
      }
    }
  });

  window.addEventListener('focus', async () => {
    if (state.activeSessionId) {
      await checkSessionBackgroundStatus(state.activeSessionId);
      if (!state.isStreaming) {
        await loadMessages(state.activeSessionId);
        await refreshPendingHitl();
      }
    }
  });

  // Dual-Pane Workbench Controller [CARD-138]
  function countDomSessionArtifacts() {
    if (!messagesContainer) return 0;
    const ids = new Set();
    messagesContainer.querySelectorAll('.open-artifact-btn[data-artifact-id]').forEach((btn) => {
      const id = (btn.getAttribute('data-artifact-id') || '').trim();
      if (id) ids.add(id);
    });
    return ids.size;
  }

  function updateWorkbenchArtifactBadge(count) {
    if (!workbenchArtifactBadge) return;
    const n = Math.max(0, Number(count) || 0);
    if (n > 0) {
      workbenchArtifactBadge.textContent = n > 99 ? '99+' : String(n);
      workbenchArtifactBadge.classList.remove('hidden');
      workbenchArtifactBadge.classList.add('flex');
      workbenchArtifactBadge.setAttribute('aria-hidden', 'false');
      if (workbenchToggleBtn) {
        workbenchToggleBtn.setAttribute('aria-label', `Toggle Workbench Canvas, ${n} artifact${n === 1 ? '' : 's'}`);
      }
    } else {
      workbenchArtifactBadge.textContent = '';
      workbenchArtifactBadge.classList.add('hidden');
      workbenchArtifactBadge.classList.remove('flex');
      workbenchArtifactBadge.setAttribute('aria-hidden', 'true');
      if (workbenchToggleBtn) {
        workbenchToggleBtn.setAttribute('aria-label', 'Toggle Workbench Canvas');
      }
    }
  }

  async function refreshWorkbenchArtifactCount() {
    let count = 0;
    if (state.activeSessionId) {
      try {
        const res = await fetch(`/api/sessions/${encodeURIComponent(state.activeSessionId)}/artifacts`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.artifacts)) count = data.artifacts.length;
        }
      } catch {
        // ignore network errors; fall back to DOM count
      }
    }
    count = Math.max(count, countDomSessionArtifacts());
    updateWorkbenchArtifactBadge(count);
  }

  function openWorkbench(artifact = {}) {
    activeWorkbenchArtifact = {
      title: artifact.title || 'Document Artifact',
      meta: artifact.meta || 'Markdown Artifact',
      content: artifact.content || '',
      raw: artifact.raw || artifact.content || '',
    };
    if (workbenchArtifactTitle) workbenchArtifactTitle.textContent = activeWorkbenchArtifact.title;
    if (workbenchArtifactMeta) workbenchArtifactMeta.textContent = activeWorkbenchArtifact.meta;

    if (workbenchContentPreview) {
      if (activeWorkbenchArtifact.content) {
        renderMarkdown(workbenchContentPreview, activeWorkbenchArtifact.content);
      } else {
        workbenchContentPreview.innerHTML = `
          <div class="h-full flex flex-col items-center justify-center text-center p-8 space-y-2 text-slate-500" data-card="306">
            <p class="text-sm font-semibold text-slate-300">Workbench is empty</p>
            <p class="text-xs text-slate-500 max-w-sm">Open a message artifact button, or a row from this session&apos;s artifact shelf. Tool results that save artifacts appear here with a real id.</p>
          </div>
        `;
      }
    }
    if (workbenchContentRaw) {
      workbenchContentRaw.textContent = activeWorkbenchArtifact.raw;
    }

    setWorkbenchTab('preview');

    if (chatWorkbenchPane) {
      chatWorkbenchPane.classList.remove('hidden');
      chatWorkbenchPane.classList.add('flex');
    }
    safeCreateIcons();
  }

  function closeWorkbench() {
    if (chatWorkbenchPane) {
      chatWorkbenchPane.classList.add('hidden');
      chatWorkbenchPane.classList.remove('flex');
    }
  }

  function setWorkbenchTab(tab) {
    activeWorkbenchTab = tab;
    if (workbenchTabPreview && workbenchTabRaw) {
      if (tab === 'preview') {
        workbenchTabPreview.className = 'px-2 py-0.5 rounded bg-brand-600 text-white font-medium transition';
        workbenchTabRaw.className = 'px-2 py-0.5 rounded text-slate-400 hover:text-white transition';
        if (workbenchContentPreview) workbenchContentPreview.classList.remove('hidden');
        if (workbenchContentRaw) workbenchContentRaw.classList.add('hidden');
      } else {
        workbenchTabRaw.className = 'px-2 py-0.5 rounded bg-brand-600 text-white font-medium transition';
        workbenchTabPreview.className = 'px-2 py-0.5 rounded text-slate-400 hover:text-white transition';
        if (workbenchContentPreview) workbenchContentPreview.classList.add('hidden');
        if (workbenchContentRaw) workbenchContentRaw.classList.remove('hidden');
      }
    }
  }

  if (workbenchToggleBtn) {
    workbenchToggleBtn.addEventListener('click', () => {
      if (chatWorkbenchPane && !chatWorkbenchPane.classList.contains('hidden')) {
        closeWorkbench();
      } else {
        openWorkbench(activeWorkbenchArtifact);
      }
    });
  }

  // Desktop + mobile: workbench stays collapsed until explicitly opened (no lg:flex auto-show).
  closeWorkbench();
  updateWorkbenchArtifactBadge(0);

  if (workbenchCloseBtn) workbenchCloseBtn.addEventListener('click', closeWorkbench);
  if (workbenchMobileBackBtn) workbenchMobileBackBtn.addEventListener('click', closeWorkbench);
  if (workbenchTabPreview) workbenchTabPreview.addEventListener('click', () => setWorkbenchTab('preview'));
  if (workbenchTabRaw) workbenchTabRaw.addEventListener('click', () => setWorkbenchTab('raw'));

  if (workbenchCopyBtn) {
    workbenchCopyBtn.addEventListener('click', () => {
      copyToClipboard(activeWorkbenchArtifact.raw || activeWorkbenchArtifact.content || '');
      showToast('success', 'Artifact copied to clipboard');
    });
  }

  if (workbenchSaveWikiBtn) {
    workbenchSaveWikiBtn.addEventListener('click', () => {
      const content = activeWorkbenchArtifact.raw || activeWorkbenchArtifact.content || '';
      if (callbacks.exportMessageToWiki) {
        callbacks.exportMessageToWiki(content);
      } else {
        showToast('info', 'Saving artifact to Wiki...');
      }
    });
  }

  startPendingHitlPoll();
  loadAgents();


  async function startNewAgentAuthoring() {
    return prepareNewAgentAuthoringSession({
      switchSelectedAgent,
      createNewSession,
      promptInput,
      starterPrompt: 'I am ready to create a new agent.',
    });
  }

  async function resumeParkedJob() {
    // CARD-251 / CARD-239: resume open waiting_approval Job on origin session (same job_id).
    return executeChatTurn('', { resume: true });
  }


  // CARD-307 close options on inspect
  if (chatShowJourneyBtn && !chatShowJourneyBtn.dataset.card307Bound) {
    chatShowJourneyBtn.dataset.card307Bound = '1';
    chatShowJourneyBtn.addEventListener('click', () => {
      if (typeof closeChatOptionsDrawer === 'function') closeChatOptionsDrawer();
    });
  }
  if (chatDebugToggleBtn && !chatDebugToggleBtn.dataset.card307Bound) {
    chatDebugToggleBtn.dataset.card307Bound = '1';
    chatDebugToggleBtn.addEventListener('click', () => {
      if (typeof closeChatOptionsDrawer === 'function') closeChatOptionsDrawer();
    });
  }

  return {
    loadAgents,
    loadSessions,
    switchSelectedAgent,
    switchEngineChannel,
    updateEngineSelectorUi,
    startNewAgentAuthoring,
    updateActiveAgentHeader,
    createNewSession,
    selectSession,
    resumeParkedJob,
    renderMessages,
    renderMarkdown,

    openWorkbench,
    closeWorkbench,
    refreshWorkbenchArtifactCount,
    updateWorkbenchArtifactBadge,
    checkSessionBackgroundStatus,
    querySessionStatus,
    updateJobPhaseFromEvent,
    resetJobPhaseStrip,
    updateJobChromeFromEvent,
    remountInlineJobChrome,
    resetInlineJobChrome,
    getActiveWorkbenchTab: () => activeWorkbenchTab,
    getActiveWorkbenchArtifact: () => activeWorkbenchArtifact,
    openTeachAgentModal,
    closeTeachAgentModal,
    renderSkillProposalCard,
  };
}
