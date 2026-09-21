/**
 * Chat Studio: Inline Job Chrome & Multi-Phase Step Strip [CARD-215, CARD-338, CARD-360, CARD-397]
 * Models, templates, and DOM builders for inline multi-phase streaming chrome and self-verification badges.
 */

import { $ } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';

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
