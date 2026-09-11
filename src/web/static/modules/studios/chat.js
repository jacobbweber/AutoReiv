/**
 * Chat Studio Module [REQ-FE-001, REQ-WEB-001, REQ-WEB-002]
 */

import { $, $query, safeCreateIcons } from '../dom.js';
import { escapeHtml, formatBytes, formatJsonDeliverableToMarkdown, formatSessionTimestamp } from '../utils/formatters.js';
import { copyToClipboard } from '../utils/clipboard.js';
import { storageGet, storageSet } from '../utils/storage.js';
import { showToast } from '../ui/toast.js';


const CODE_KEYS = [
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
  if (args == null) return "";
  let obj = args;

  if (typeof args === "string") {
    const trimmed = args.trim();
    if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
      try {
        obj = JSON.parse(trimmed);
      } catch {
        return args;
      }
    } else {
      return args;
    }
  }

  if (typeof obj !== "object" || obj === null) {
    return String(obj);
  }

  // Check if obj contains a primary code or command key
  const keys = Object.keys(obj);
  const primaryKey = keys.find((k) => CODE_KEYS.includes(k.toLowerCase()));

  if (primaryKey && typeof obj[primaryKey] === "string") {
    const primaryText = obj[primaryKey];
    const otherKeys = keys.filter((k) => k !== primaryKey);
    const metaLines = otherKeys.map((k) => {
      const v = obj[k];
      if (typeof v === "object" && v !== null) {
        return `${k}: ${JSON.stringify(v)}`;
      }
      return `${k}: ${v}`;
    });

    const header = metaLines.length > 0 ? `${metaLines.join("\n")}\n\n` : "";
    const cleanPrimary = String(primaryText).replace(/\r\n/g, "\n");
    const fullText = `${header}${cleanPrimary}`;
    return fullText.length > 4000 ? `${fullText.slice(0, 4000)}…` : fullText;
  }

  // If there are multi-line string properties without a primary key, format each key cleanly
  const hasMultiline = keys.some((k) => typeof obj[k] === "string" && obj[k].includes("\n"));
  if (hasMultiline) {
    const lines = keys.map((k) => {
      const v = obj[k];
      if (typeof v === "string") {
        const cleanV = v.replace(/\r\n/g, "\n");
        if (cleanV.includes("\n")) {
          return `${k}:\n${cleanV}`;
        }
        return `${k}: ${cleanV}`;
      }
      if (typeof v === "object" && v !== null) {
        return `${k}: ${JSON.stringify(v, null, 2)}`;
      }
      return `${k}: ${v}`;
    });
    const fullText = lines.join("\n\n");
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
  if (output == null) return "";

  if (typeof output === "object" && output !== null) {
    if (output.error && !output.stdout && !output.stderr && !output.output) {
      return `Error: ${output.error}`;
    }

    let text = "";
    if (output.stdout !== undefined && output.stdout !== null) {
      text = String(output.stdout);
    } else if (output.output !== undefined && output.output !== null) {
      text = typeof output.output === "string" ? output.output : JSON.stringify(output.output, null, 2);
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

    text = text.replace(/\r\n/g, "\n");
    const trimmed = text.trim();
    if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
      try {
        const parsed = JSON.parse(trimmed);
        return JSON.stringify(parsed, null, 2);
      } catch {
        // Not valid JSON, return clean text
      }
    }
    return text;
  }

  if (typeof output === "string") {
    const clean = output.replace(/\r\n/g, "\n");
    const trimmed = clean.trim();
    if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
      try {
        const parsed = JSON.parse(trimmed);
        if (parsed && typeof parsed === "object" && (parsed.stdout !== undefined || parsed.stderr !== undefined)) {
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


export function isGoalPlanReviewTool(toolName) {
  return String(toolName || "") === "goal_plan_review";
}

export function coupleGoalAndVerify(goalChecked, state, { verifyToggle, verifyBadge, goalBadge } = {}) {
  const isChecked = Boolean(goalChecked);
  if (state) state.goalEnabled = isChecked;
  if (goalBadge && typeof goalBadge.classList?.toggle === 'function') {
    goalBadge.classList.toggle('hidden', !isChecked);
  }
  if (isChecked) {
    if (state) state.verifyEnabled = true;
    if (verifyToggle) verifyToggle.checked = true;
    if (verifyBadge && typeof verifyBadge.classList?.remove === 'function') {
      verifyBadge.classList.remove('hidden');
    }
  }
}

export function isComplexMultiStepPrompt(text) {
  if (!text || typeof text !== 'string') return false;
  const trimmed = text.trim();
  if (trimmed.length < 25) return false;

  // Pattern 1: Numbered list with 2 or more steps (e.g. "1. ... \n2. ...")
  const numberedSteps = trimmed.match(/(?:^|\n)\s*(?:\d+[.)]|\(\d+\))\s+[^\n]+/g);
  if (numberedSteps && numberedSteps.length >= 2) return true;

  // Pattern 2: Explicit step / phase / milestone markers (e.g. "Step 1:", "Phase 1:")
  const stepPhaseMarkers = trimmed.match(/(?:^|\n|\b)(?:step|phase|milestone|task)\s+[1-9]\b/gi);
  if (stepPhaseMarkers && stepPhaseMarkers.length >= 2) return true;

  // Pattern 3: Sequential transition words in multi-sentence prompt
  const hasFirst = /\b(?:first|step\s+one|initially)\b/i.test(trimmed);
  const hasThen = /\b(?:then|next|after\s+that|secondly|afterwards)\b/i.test(trimmed);
  const hasFinally = /\b(?:finally|lastly|in\s+the\s+end)\b/i.test(trimmed);
  if (hasFirst && (hasThen || hasFinally) && trimmed.length >= 40) return true;

  return false;
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

export async function querySessionStatus(sessionId, fetchFn = null) {
  if (!sessionId) return { session_id: sessionId, is_running: false, active_agent: null };
  try {
    const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
    const res = await fn(`/api/sessions/${encodeURIComponent(sessionId)}/status`);
    if (!res.ok) return { session_id: sessionId, is_running: false, active_agent: null };
    return await res.json();
  } catch {
    return { session_id: sessionId, is_running: false, active_agent: null };
  }
}

export function formatContextBudgetBadge(usedTokens, maxTokens, percentUsed) {
  const used = Number(usedTokens || 0).toLocaleString();
  const max = Number(maxTokens || 0).toLocaleString();
  const pct = Number(percentUsed || 0).toFixed(1);
  return `${used} / ${max} tokens (${pct}%)`;
}

export function filterToolsList(tools, query) {
  if (!Array.isArray(tools)) return [];
  const q = String(query || '').trim().toLowerCase();
  if (!q) return [...tools];
  return tools.filter((t) => {
    const name = String(t?.name || '').toLowerCase();
    const desc = String(t?.description || '').toLowerCase();
    return name.includes(q) || desc.includes(q);
  });
}

export async function querySessionContext(sessionId, fetchFn = null) {
  if (!sessionId) return null;
  try {
    const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
    const res = await fn(`/api/sessions/${encodeURIComponent(sessionId)}/context`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function postSessionCompaction(sessionId, fetchFn = null) {
  if (!sessionId) return { success: false, error: 'No active session' };
  try {
    const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
    const res = await fn(`/api/sessions/${encodeURIComponent(sessionId)}/compact`, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      return { success: false, error: err.detail || `HTTP ${res.status}` };
    }
    return await res.json();
  } catch (err) {
    return { success: false, error: err.message || 'Compaction request failed' };
  }
}

export function isAgentVisibleInChat(agent) {
  if (agent == null) return true;
  if (agent.id === 'agent-builder' || agent.id === 'coding' || agent.id === 'review' || agent.id === 'conductor' || agent.id === 'hyperv') return false;
  if (agent.visibility === 'internal') return false;
  return agent.show_in_chat !== false;
}

export function agentsVisibleInChat(agents) {
  return (agents || []).filter(isAgentVisibleInChat);
}

export const AUTOREIV_AGENT_ID = 'autoreiv';
export const NEW_AGENT_STARTER_PROMPT = 'I am ready to create a new agent.';

export async function prepareNewAgentAuthoringSession({
  switchSelectedAgent,
  createNewSession,
  promptInput,
  agentId = AUTOREIV_AGENT_ID,
  starterPrompt = NEW_AGENT_STARTER_PROMPT,
} = {}) {
  if (typeof switchSelectedAgent === 'function') {
    await switchSelectedAgent(agentId);
  }
  if (typeof createNewSession === 'function') {
    await createNewSession();
  }
  if (promptInput) {
    promptInput.value = starterPrompt;
    if (typeof promptInput.focus === 'function') {
      promptInput.focus();
    }
  }
  return { filled: true, sent: false, prompt: starterPrompt, agentId };
}


export const APPROVAL_AUTORUN_STORAGE_KEY = "autoreiv_approval_autorun";

export function readLastApprovalAutoRun(reader = storageGet) {
  try {
    const raw = reader(APPROVAL_AUTORUN_STORAGE_KEY, "");
    return String(raw || "").trim().toLowerCase() === "run";
  } catch {
    return false;
  }
}

export function writeLastApprovalAutoRun(enabled, writer = storageSet) {
  try {
    writer(APPROVAL_AUTORUN_STORAGE_KEY, enabled ? "run" : "ask");
  } catch {
    // Fail closed: next load without memory stays ask.
  }
}

export function hasVisibleHitlCard(root) {
  if (!root || typeof root.querySelector !== "function") {
    return false;
  }
  return Boolean(root.querySelector(".hitl-approval-card:not(.hidden)"));
}

/**
 * Render post-creation interactive handoff card with Factory and Studio actions [CARD-197, REQ-FACT-048].
 */
export function renderAgentHandoffCardHtml({
  agentId = '',
  agentName = '',
  folder = '',
} = {}) {
  const safeId = escapeHtml(agentId || '');
  const safeName = escapeHtml(agentName || agentId || 'Specialist Agent');
  const safeFolder = escapeHtml(folder || `packs/${agentId}`);

  return `
    <div class="agent-created-handoff-card my-3 p-4 bg-slate-900/90 border border-brand-500/40 rounded-2xl shadow-xl space-y-3 animate-in fade-in zoom-in-95 duration-200">
      <div class="flex items-center space-x-3">
        <div class="w-9 h-9 rounded-xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center text-brand-400">
          <i data-lucide="sparkles" class="w-5 h-5"></i>
        </div>
        <div>
          <h4 class="text-sm font-bold text-white flex items-center space-x-1.5">
            <span>🎉 Agent "${safeName}" Created Successfully!</span>
          </h4>
          <p class="text-xs text-slate-400 font-mono">${safeFolder} &bull; Manifest &amp; storage initialized</p>
        </div>
      </div>
      <p class="text-xs text-slate-300">
        Specialist agent is ready for capability training. Open Factory Studio to blueprint and author custom tools and operating runbooks.
      </p>
      <div class="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800">
        <button type="button" data-action="launch-factory" data-agent-id="${safeId}" class="px-3.5 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition shadow-sm">
          <i data-lucide="rocket" class="w-3.5 h-3.5"></i>
          <span>Launch Training in Factory</span>
        </button>
        <button type="button" data-action="open-studio" data-agent-id="${safeId}" class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition shadow-sm">
          <i data-lucide="settings" class="w-3.5 h-3.5"></i>
          <span>Open in Studio</span>
        </button>
      </div>
    </div>
  `.trim();
}

export const JOB_PHASE_REACT_STATES = Object.freeze([
  "THINKING",
  "CALLING_TOOLS",
  "PARKED",
  "DONE",
  "FAILED",
]);

export function humanizeJobStatus(status) {
  const raw = String(status || "").trim();
  if (!raw) return "unknown";
  return raw.replace(/_/g, " ");
}

export function formatJobPhaseStrip(state) {
  const jobStatus = humanizeJobStatus(state && state.jobStatus);
  const phaseName = (state && state.phaseName) || "Phase";
  const phaseIndex = state && state.phaseIndex;
  const phaseCount = state && state.phaseCount;
  let phaseLabel = phaseName;
  if (phaseIndex != null && phaseIndex !== "") {
    const n = Number(phaseIndex) + 1;
    if (phaseCount != null && phaseCount !== "") {
      phaseLabel = `Phase ${n}/${phaseCount} ${phaseName}`;
    } else {
      phaseLabel = `Phase ${n} ${phaseName}`;
    }
  }
  const agent = (state && (state.assignedAgentId || state.agentId)) || "agent";
  const reactState = String((state && state.reactState) || "").toUpperCase();
  return {
    jobStatusLabel: `Job ${jobStatus}`,
    phaseLabel,
    agentLabel: agent,
    reactState,
  };
}

export function reactStateToneClass(reactState) {
  switch (String(reactState || "").toUpperCase()) {
    case "PARKED":
      return "job-phase-react px-2 py-0.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300 font-semibold tracking-wide";
    case "FAILED":
      return "job-phase-react px-2 py-0.5 rounded bg-rose-950/80 border border-rose-800 text-rose-300 font-semibold tracking-wide";
    case "DONE":
      return "job-phase-react px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-semibold tracking-wide";
    case "CALLING_TOOLS":
      return "job-phase-react px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-800 text-indigo-300 font-semibold tracking-wide";
    case "THINKING":
      return "job-phase-react px-2 py-0.5 rounded bg-sky-950/80 border border-sky-800 text-sky-300 font-semibold tracking-wide";
    default:
      return "job-phase-react px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-semibold tracking-wide";
  }
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

  if (eventType === "job_created") {
    next.jobId = data.job_id || next.jobId;
    next.jobStatus = data.status || next.jobStatus || "queued";
    next.assignedAgentId = data.agent_id || next.assignedAgentId;
    next.phaseCount = data.phase_count != null ? data.phase_count : next.phaseCount;
    if (data.status === "waiting_approval") {
      next.reactState = next.reactState || "PARKED";
    }
  } else if (eventType === "phase_start") {
    if (!next.jobStatus || next.jobStatus === "queued") {
      next.jobStatus = "running";
    }
    if (!next.reactState) next.reactState = "THINKING";
  } else if (eventType === "phase_complete") {
    if (data.status) next.jobStatus = data.status;
    if (data.react_state) next.reactState = data.react_state;
  } else if (eventType === "react_state") {
    if (data.react_state) next.reactState = data.react_state;
    if (data.job_status) next.jobStatus = data.job_status;
  } else if (eventType === "plan_formulated") {
    if (data.job_id) next.jobId = data.job_id;
    if (Array.isArray(data.steps)) next.phaseCount = data.steps.length;
    if (data.standing) {
      // Standing runtime executes immediately — not plan-review park theatre [CARD-215].
      next.jobStatus = next.jobStatus || data.status || "queued";
    } else {
      next.jobStatus = next.jobStatus || "waiting_approval";
      next.reactState = next.reactState || "PARKED";
    }
  } else if (eventType === "approval_required") {
    next.reactState = data.react_state || next.reactState || "PARKED";
    next.jobStatus = data.job_status || next.jobStatus || "waiting_approval";
  }
  return next;
}
export function buildTrainAgentPayload({
  seedIntent = '',
  targetType = 'remote',
  targetLocation = '',
  objectives = [],
  requireApproval = true,
  sessionId = null,
  targetAgentId = null,
  deliverableType = 'auto',
  constraints = '',
  prerequisites = '',
  referenceDocs = '',
} = {}) {
  let target_agent_id = targetAgentId;
  if (!target_agent_id) {
    let cleaned = (seedIntent || '').trim().toLowerCase();
    cleaned = cleaned.replace(/^(build|create|train|make)\s+(a|an|the)\s+/i, '');
    target_agent_id = cleaned
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'custom-agent';
  }

  return {
    target_agent_id,
    seed_intent: seedIntent,
    target_host: targetType === 'remote' ? (targetLocation || null) : null,
    target_directory: targetType === 'local' ? (targetLocation || null) : null,
    objectives: Array.isArray(objectives) ? objectives : [],
    risk_policy: requireApproval ? 'ask' : 'run',
    session_id: sessionId || null,
    deliverable_type: deliverableType || 'auto',
    constraints: constraints || null,
    prerequisites: prerequisites || null,
    reference_docs: referenceDocs || null,
  };
}

export async function submitTrainAgentJob(payload, fetchFn = null) {
  const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
  const res = await fn('/api/agent_training_factory/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }
  return await res.json();
}

export function renderTrainPromotionCard(jobData = {}) {
  const jobId = escapeHtml(jobData.job_id || '');
  const agentId = escapeHtml(jobData.target_agent_id || 'new-agent');
  const intent = escapeHtml(jobData.seed_intent || '');
  const tools = (jobData.tools_authored || []).map((t) => escapeHtml(t)).join(', ');
  const stagesPassed = jobData.stages_passed != null ? jobData.stages_passed : 4;

  return `
    <div class="factory-promotion-card p-4 rounded-2xl bg-emerald-950/40 border border-emerald-500/40 text-slate-200 space-y-3 shadow-lg" data-job-id="${jobId}">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="p-1.5 rounded-lg bg-emerald-900/60 text-emerald-400">
            <i data-lucide="award" class="w-4 h-4"></i>
          </span>
          <h4 class="font-bold text-sm text-emerald-200">Agent Training Certified</h4>
        </div>
        <span class="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-900/80 text-emerald-300 border border-emerald-700/60">${stagesPassed}/4 Stages Passed</span>
      </div>
      <p class="text-xs text-slate-300">Pack for <strong class="text-emerald-300 font-mono">${agentId}</strong> is verified and ready for deployment.</p>
      ${intent ? `<p class="text-[11px] text-slate-400 italic">"${intent}"</p>` : ''}
      ${tools ? `
        <div class="text-[11px] bg-slate-900/80 p-2 rounded-xl border border-slate-800">
          <span class="text-slate-400 block text-[10px] uppercase font-semibold">Authored Tools</span>
          <span class="font-mono text-emerald-400 text-xs">${tools}</span>
        </div>
      ` : ''}
      <div class="flex items-center space-x-2 pt-1">
        <button type="button" class="approve-factory-btn px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs shadow transition flex items-center space-x-1.5" data-job-id="${jobId}">
          <i data-lucide="check-circle" class="w-3.5 h-3.5"></i>
          <span>Approve &amp; Deploy</span>
        </button>
        <button type="button" class="reject-factory-btn px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition" data-job-id="${jobId}">
          Dismiss
        </button>
      </div>
    </div>
  `;
}

export function populateTrainAgentTargetOptions(selectEl, agents = [], selectedId = null) {
  if (!selectEl) return;
  selectEl.innerHTML = '';

  (agents || []).forEach((agent) => {
    const opt = typeof document !== 'undefined' ? document.createElement('option') : { value: '', textContent: '' };
    const aId = agent.id || agent.agent_id;
    const aName = agent.name || aId;
    opt.value = aId;
    opt.textContent = `${aName} (${aId})`;
    selectEl.appendChild(opt);
  });

  const newOpt = typeof document !== 'undefined' ? document.createElement('option') : { value: '', textContent: '' };
  newOpt.value = '__new__';
  newOpt.textContent = '+ Create Brand New Agent...';
  selectEl.appendChild(newOpt);

  if (selectedId) {
    selectEl.value = selectedId;
  } else if (agents && agents.length > 0) {
    selectEl.value = agents[0].id || agents[0].agent_id;
  } else {
    selectEl.value = '__new__';
  }
}

export function updateTrainAgentLiveIndicator(elements = {}, selectedAgentId = null, agents = []) {
  const nameGroup = elements.nameGroup || (typeof $ !== 'undefined' ? $('trainAgentNameGroup') : null);
  const liveInfo = elements.liveInfo || (typeof $ !== 'undefined' ? $('trainAgentLiveInfo') : null);
  const livePackPath = elements.livePackPath || (typeof $ !== 'undefined' ? $('trainAgentLivePackPath') : null);
  const liveCounts = elements.liveCounts || (typeof $ !== 'undefined' ? $('trainAgentLiveCounts') : null);
  const liveInfoText = elements.liveInfoText || (typeof $ !== 'undefined' ? $('trainAgentLiveInfoText') : null);
  const modalTitle = elements.modalTitle || (typeof $ !== 'undefined' ? $('trainAgentModalTitle') : null);
  const intentInput = elements.intentInput || (typeof $ !== 'undefined' ? $('trainSeedIntentInput') : null);
  const seedObj = elements.seedObj || (typeof $ !== 'undefined' ? $('trainSeedObjectives') : null);
  const targetNameEl = elements.targetName || (typeof $ !== 'undefined' ? $('trainAgentTargetName') : null);
  const targetIdBadgeEl = elements.targetIdBadge || (typeof $ !== 'undefined' ? $('trainAgentTargetIdBadge') : null);

  const isNew = !selectedAgentId || selectedAgentId === '__new__';

  if (isNew) {
    if (nameGroup && nameGroup.classList) nameGroup.classList.remove('hidden');
    if (liveInfo && liveInfo.classList) liveInfo.classList.add('hidden');
    if (targetNameEl) targetNameEl.textContent = 'New Specialist Agent';
    if (targetIdBadgeEl) targetIdBadgeEl.textContent = 'new';
    if (livePackPath) livePackPath.textContent = 'packs/new/';
    if (liveCounts) liveCounts.textContent = '0 skills · 0 tools';
    if (modalTitle) {
      modalTitle.innerHTML = `
        <i data-lucide="cpu" class="w-4 h-4 text-emerald-400"></i>
        <span>Train Specialist Agent (Lab Loop)</span>
      `;
    }
    if (intentInput) {
      intentInput.placeholder = 'e.g. Docker Specialist, Network Admin, or Database Operator';
    }
    if (seedObj) {
      seedObj.placeholder = 'List 1 to 3 primary capabilities or tasks this agent should master (one per line)...';
    }
    return;
  }

  // Existing agent
  if (nameGroup && nameGroup.classList) nameGroup.classList.add('hidden');
  if (liveInfo && liveInfo.classList) liveInfo.classList.remove('hidden');

  const agent = (agents || []).find((a) => (a.id || a.agent_id) === selectedAgentId);
  const agentName = agent ? (agent.name || agent.id) : selectedAgentId;
  const skillsCount = agent && agent.pack_skills ? agent.pack_skills.length : 0;
  const toolsCount = agent
    ? (agent.allowed_tool_names || agent.tools || agent.pack_tool_names || []).length
    : 0;

  if (targetNameEl) {
    targetNameEl.textContent = agentName;
  }
  if (targetIdBadgeEl) {
    targetIdBadgeEl.textContent = selectedAgentId;
  }
  if (livePackPath) {
    livePackPath.textContent = `packs/${selectedAgentId}/`;
  }
  if (liveCounts) {
    liveCounts.textContent = `${skillsCount} skills · ${toolsCount} tools`;
  }
  if (liveInfoText) {
    liveInfoText.textContent = `Augmenting existing "${agentName}" pack. Grounding and Author phases will inspect existing skills/tools and avoid duplicate declarations.`;
  }
  if (modalTitle) {
    modalTitle.innerHTML = `
      <i data-lucide="flask-conical" class="w-4 h-4 text-emerald-400"></i>
      <span>Train ${typeof escapeHtml === 'function' ? escapeHtml(agentName) : agentName} (Lab Loop)</span>
    `;
  }
  if (intentInput) {
    intentInput.placeholder = agent && agent.description ? agent.description : `e.g. Expand ${agentName} capabilities`;
  }
  if (seedObj) {
    seedObj.placeholder = `List 1 to 3 capabilities to train for ${agentName} (one per line)...`;
  }
}



export function buildChatStreamPayload({
  agentId,
  sessionId,
  content = "",
  resume = false,
  goalMode = false, // deprecated [CARD-215]; ignored — standing runtime decides
  selfVerify = false,
  approvalAutoRun = false,
  attachments = [],
}) {
  const isResume = Boolean(resume);
  void goalMode;
  const payload = {
    agent_id: agentId,
    session_id: sessionId,
    content: isResume ? "" : content,
    resume: isResume,
    goal_mode: false,
    self_verify: isResume ? false : !!selfVerify,
    approval_mode: approvalAutoRun ? "run" : "ask",
  };
  if (Array.isArray(attachments) && attachments.length > 0) {
    payload.attachments = attachments;
  }
  return payload;
}

export function pendingApprovalsUrl(agentId, sessionId) {
  const sid = String(sessionId || "").trim();
  const aid = String(agentId || "").trim();
  const params = new URLSearchParams();
  if (sid) {
    params.set("session_id", sid);
  }
  if (aid && !sid) {
    params.set("agent_id", aid);
  }
  const qs = params.toString();
  return qs ? `/api/approvals/pending?${qs}` : "/api/approvals/pending";
}

export function pendingHitlLabel(approval) {
  if (!approval || !approval.routine_id) {
    return "Approval required";
  }
  const name = String(approval.routine_name || "").trim();
  return name ? `Routine: ${name}` : "Routine";
}

export function shouldResumeChatAfterHitl({ approvalSessionId, openSessionId, backendResumed, nestedStatus }) {
  if (backendResumed) return false;
  if (nestedStatus === "approval_required") return false;
  const approvalSid = String(approvalSessionId || "").trim();
  const openSid = String(openSessionId || "").trim();
  if (!approvalSid || !openSid) {
    return Boolean(openSid);
  }
  return approvalSid === openSid || approvalSid.startsWith(`${openSid}_child_`) || approvalSid.startsWith(`${openSid}::phase::`);
}

export function buildHitlCardInnerHtml({ title, toolName, message, argsText, resolved = null, statusText = "" }) {
  if (resolved) {
    const isApproved = String(resolved).toUpperCase() === "APPROVED";
    return `
    <div class="font-semibold ${isApproved ? "text-emerald-200" : "text-rose-200"}">${escapeHtml(title || (isApproved ? "Approved" : "Rejected"))}</div>
    <div class="text-slate-300">Tool: <strong class="text-white">${escapeHtml(toolName || "tool")}</strong></div>
    ${message ? `<div class="text-slate-400">${escapeHtml(message)}</div>` : ""}
    ${argsText ? `<pre class="text-[11px] font-mono whitespace-pre-wrap text-slate-300 bg-slate-950/40 p-2 rounded border border-slate-800 max-h-32 overflow-y-auto">${escapeHtml(argsText)}</pre>` : ""}
    <div class="flex items-center space-x-2 pt-1">
      <button type="button" disabled data-hitl-decision="APPROVED" class="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-50 pointer-events-none text-xs font-semibold">Approve</button>
      <button type="button" disabled data-hitl-decision="REJECTED" class="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-50 pointer-events-none text-xs font-semibold">Reject</button>
      <span class="hitl-card-status ${isApproved ? "text-emerald-300" : "text-rose-300"}">${escapeHtml(statusText || (isApproved ? "Approved." : "Rejected."))}</span>
    </div>
  `;
  }
  return `
    <div class="font-semibold text-amber-200">${escapeHtml(title || "Approval required")}</div>
    <div class="text-slate-300">Tool: <strong class="text-white">${escapeHtml(toolName || "tool")}</strong></div>
    <div class="text-slate-400">${escapeHtml(message || "Waiting for operator approval")}</div>
    <pre class="text-[11px] font-mono whitespace-pre-wrap text-slate-300 bg-slate-950/40 p-2 rounded border border-slate-800 max-h-32 overflow-y-auto">${escapeHtml(argsText || "")}</pre>
    <div class="flex items-center space-x-2 pt-1">
      <button type="button" data-hitl-decision="APPROVED" class="px-2.5 py-1 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none text-white text-xs font-semibold">Approve</button>
      <button type="button" data-hitl-decision="REJECTED" class="px-2.5 py-1 rounded-lg bg-rose-800 hover:bg-rose-700 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none text-white text-xs font-semibold">Reject</button>
      <span class="hitl-card-status text-amber-200"></span>
    </div>
  `;
}

export async function submitHitlDecision(approvalId, decision, cardEl, sessionId) {
  const buttons = cardEl.querySelectorAll("[data-hitl-decision]");
  buttons.forEach((btn) => {
    btn.disabled = true;
    if (btn.classList && typeof btn.classList.add === "function") {
      btn.classList.add("opacity-50", "cursor-not-allowed", "pointer-events-none");
    }
  });
  const statusEl = cardEl.querySelector(".hitl-card-status");
  if (statusEl) {
    statusEl.textContent = decision === "APPROVED" ? "Approving…" : "Rejecting…";
  }
  try {
    const res = await fetch(`/api/approvals/${encodeURIComponent(approvalId)}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    const ran = Boolean(body.execution && body.execution.ran);
    if (statusEl) {
      if (decision === "APPROVED") {
        statusEl.textContent = ran ? "Approved. Tool ran." : "Approved.";
      } else {
        statusEl.textContent = "Rejected. Tool did not run.";
      }
    }
    buttons.forEach((btn) => {
      btn.disabled = true;
      if (btn.classList) {
        if (typeof btn.classList.remove === "function") {
          btn.classList.remove(
            "bg-emerald-700",
            "hover:bg-emerald-600",
            "bg-rose-800",
            "hover:bg-rose-700",
            "hover:bg-emerald-700",
            "hover:bg-rose-800",
            "text-white"
          );
        }
        if (typeof btn.classList.add === "function") {
          btn.classList.add(
            "bg-slate-800",
            "text-slate-500",
            "border",
            "border-slate-700/60",
            "cursor-not-allowed",
            "opacity-50",
            "pointer-events-none"
          );
        }
      }
    });
    if (cardEl.classList) {
      cardEl.classList.remove("border-amber-500/30", "bg-amber-950/20");
      if (decision === "APPROVED") {
        cardEl.classList.add("border-emerald-500/30", "bg-emerald-950/20");
      } else {
        cardEl.classList.add("border-rose-500/30", "bg-rose-950/20");
      }
    }
    const execution = body.execution || null;
    const output = execution ? execution.output : null;
    const error = execution ? execution.error : null;
    if ((output != null || error != null) && typeof cardEl.appendChild === "function" && typeof document !== "undefined") {
      const pre = document.createElement("pre");
      pre.className =
        "mt-2 text-[11px] font-mono whitespace-pre-wrap text-slate-300 bg-slate-950/40 p-2 rounded border border-slate-800 max-h-40 overflow-y-auto";
      const formatted = formatHitlOutput(output);
      pre.textContent = error && !formatted.includes(error) ? `Error: ${error}\n${formatted}`.trim() : formatted;
      cardEl.appendChild(pre);
    }
    return { ok: true, body };
  } catch (err) {
    buttons.forEach((btn) => {
      btn.disabled = false;
      if (btn.classList && typeof btn.classList.remove === "function") {
        btn.classList.remove("opacity-50", "cursor-not-allowed", "pointer-events-none");
      }
    });
    if (statusEl) {
      statusEl.textContent = `Failed: ${err.message || err}`;
    }
    return { ok: false, body: {} };
  }
}

export function initChatStudio(state, callbacks = {}) {
  const agentSelect = $('agentSelect');
  const chatTopBarAgentSelect = $('chatTopBarAgentSelect');
  const sessionList = $('sessionList');
  const newChatBtn = $('newChatBtn');
  const activeAgentTitle = $('activeAgentTitle');
  const activeAgentTone = $('activeAgentTone');
  const messagesContainer = $('messagesContainer');
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
  const goalToggle = $('goalToggle');
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
  const chatGoalSuggestionChip = $('chatGoalSuggestionChip');
  const chatEnableGoalSuggestionBtn = $('chatEnableGoalSuggestionBtn');
  const chatDismissGoalSuggestionBtn = $('chatDismissGoalSuggestionBtn');
  let suggestionDismissedForText = '';

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
    if (!jobPhaseState.jobId && !jobPhaseState.reactState && !jobPhaseState.jobStatus) {
      jobPhaseStatusStrip.classList.add('hidden');
      return;
    }
    const view = formatJobPhaseStrip(jobPhaseState);
    const jobEl = jobPhaseStatusStrip.querySelector('[data-job-phase="status"]');
    const phaseEl = jobPhaseStatusStrip.querySelector('[data-job-phase="phase"]');
    const agentEl = jobPhaseStatusStrip.querySelector('[data-job-phase="agent"]');
    const reactEl = jobPhaseStatusStrip.querySelector('[data-job-phase="react"]');
    if (jobEl) jobEl.textContent = view.jobStatusLabel;
    if (phaseEl) phaseEl.textContent = view.phaseLabel;
    if (agentEl) agentEl.textContent = view.agentLabel;
    if (reactEl) {
      reactEl.textContent = view.reactState || '';
      reactEl.className = reactStateToneClass(view.reactState);
    }
    jobPhaseStatusStrip.classList.remove('hidden');
  }

  function updateJobPhaseFromEvent(eventType, ev) {
    jobPhaseState = applyJobPhaseEvent(jobPhaseState, eventType, ev);
    renderJobPhaseStrip();
    if (goalBadge && typeof goalBadge.classList?.toggle === 'function') {
      const multi = Number(jobPhaseState.phaseCount || 0) > 1;
      goalBadge.classList.toggle('hidden', !multi);
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
      if (!id || liveIds.has(id)) return;
      keep.add(id);
      let card = pendingHitlHost.querySelector(`[data-approval-id="${id}"]`);
      if (card) return;
      card = document.createElement('div');
      card.className = 'hitl-approval-card rounded-xl border border-amber-500/30 bg-amber-950/20 p-3 space-y-2 text-xs';
      card.setAttribute('data-approval-id', id);
      card.setAttribute('data-approval-session', item.session_id || '');
      if (item.routine_id) card.setAttribute('data-routine-id', item.routine_id);
      card.innerHTML = buildHitlCardInnerHtml({
        title: pendingHitlLabel(item),
        toolName: item.tool_name || 'tool',
        message: item.routine_id
          ? 'Parked by a routine. Approve or Reject here to continue that run.'
          : (item.message || 'Waiting for operator approval'),
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
      const chatAgents = agentsVisibleInChat(state.agents);

      if (agentSelect) {
        agentSelect.innerHTML = '';
        chatAgents.forEach((agent) => {
          const opt = document.createElement('option');
          opt.value = agent.id;
          opt.textContent = `${agent.name} (${agent.tone})`;
          agentSelect.appendChild(opt);
        });
      }

      if (chatTopBarAgentSelect) {
        chatTopBarAgentSelect.innerHTML = '';
        chatAgents.forEach((agent) => {
          const opt = document.createElement('option');
          opt.value = agent.id;
          opt.textContent = agent.name;
          chatTopBarAgentSelect.appendChild(opt);
        });
      }

      const savedAgentId = storageGet('autoreiv_active_agent_id');
      const visibleIds = chatAgents.map((a) => a.id);
      if (savedAgentId && visibleIds.includes(savedAgentId)) {
        state.selectedAgentId = savedAgentId;
      } else if (!state.selectedAgentId || !visibleIds.includes(state.selectedAgentId)) {
        state.selectedAgentId = chatAgents.length > 0 ? chatAgents[0].id : 'assistant';
      }

      if (agentSelect) agentSelect.value = state.selectedAgentId;
      if (chatTopBarAgentSelect) chatTopBarAgentSelect.value = state.selectedAgentId;

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
    if (chatTopBarAgentSelect && chatTopBarAgentSelect.value !== agentId) chatTopBarAgentSelect.value = agentId;

    updateActiveAgentHeader();

    const sidebar = $('sidebar');
    if (window.innerWidth < 768 && sidebar) {
      sidebar.classList.add('-translate-x-full');
    }

    await loadSessions();
    await refreshPendingHitl();
  }

  if (agentSelect) {
    agentSelect.addEventListener('change', (e) => switchSelectedAgent(e.target.value));
  }
  if (chatTopBarAgentSelect) {
    chatTopBarAgentSelect.addEventListener('change', (e) => switchSelectedAgent(e.target.value));
  }

  function updateActiveAgentHeader() {
    const agent = state.agents.find((a) => a.id === state.selectedAgentId);
    if (agent) {
      if (activeAgentTitle) activeAgentTitle.textContent = agent.name;
      if (activeAgentTone)
        activeAgentTone.textContent = `Tone: ${(agent.tone || 'standard').toUpperCase()} • Tools: ${agent.allowed_tools ? agent.allowed_tools.length : 0}`;
      if (agentSelect && agentSelect.value !== agent.id) agentSelect.value = agent.id;
      if (chatTopBarAgentSelect && chatTopBarAgentSelect.value !== agent.id) chatTopBarAgentSelect.value = agent.id;
    } else {
      const opt = chatTopBarAgentSelect?.querySelector(`option[value="${state.selectedAgentId}"]`);
      if (opt && activeAgentTitle) {
        activeAgentTitle.textContent = opt.textContent;
      }
      if (agentSelect && agentSelect.value !== state.selectedAgentId) agentSelect.value = state.selectedAgentId;
      if (chatTopBarAgentSelect && chatTopBarAgentSelect.value !== state.selectedAgentId) chatTopBarAgentSelect.value = state.selectedAgentId;
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
    const agent = state.agents.find((a) => a.id === state.selectedAgentId);
    const title = `${agent ? agent.name : 'Agent'} Chat`;
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

  async function selectSession(sessionId) {
    if (backgroundPollInterval) {
      clearInterval(backgroundPollInterval);
      backgroundPollInterval = null;
    }
    state.activeSessionId = sessionId;
    resetJobPhaseStrip();
    renderSessionList();
    await loadMessages(sessionId, { force: true });
    await refreshPendingHitl();
    await checkSessionBackgroundStatus(sessionId);
    await refreshWorkbenchArtifactCount();
    if (chatOptionsDrawer && !chatOptionsDrawer.classList.contains('hidden')) {
      await loadChatSessionContext();
    }
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

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
      appendMessageBubble('assistant', content);
      return;
    }

    // 4. Fallback for other message types
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
            wrapper.className = 'mermaid-wrapper relative group my-4';

            const containerDiv = document.createElement('div');
            containerDiv.className = 'mermaid cursor-pointer hover:border-brand-500/60 transition';
            containerDiv.innerHTML = svg;
            containerDiv.title = 'Click to open Pan & Zoom Inspector';

            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'mermaid-actions';
            actionsDiv.innerHTML = `
              <button type="button" class="mermaid-inspect-btn px-2.5 py-1 bg-brand-600/90 hover:bg-brand-500 text-white rounded-lg text-[11px] font-semibold flex items-center space-x-1.5 shadow-lg backdrop-blur transition border border-brand-400/30">
                <i data-lucide="zoom-in" class="w-3.5 h-3.5"></i>
                <span>Inspect & Zoom</span>
              </button>
            `;

            wrapper.appendChild(containerDiv);
            wrapper.appendChild(actionsDiv);

            if (preEl && preEl.parentNode) {
              preEl.parentNode.replaceChild(wrapper, preEl);
            }

            const triggerInspector = () => {
              if (callbacks.openMermaidInspector) {
                callbacks.openMermaidInspector(svg, 'Architecture Diagram');
              }
            };
            actionsDiv.querySelector('.mermaid-inspect-btn')?.addEventListener('click', (e) => {
              e.stopPropagation();
              triggerInspector();
            });
            containerDiv.addEventListener('click', triggerInspector);
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
        <button class="train-lab-msg-btn flex items-center space-x-1.5 px-2 py-0.5 rounded-md bg-amber-950/60 hover:bg-amber-900/80 text-amber-300 border border-amber-800/50 transition" data-content="${escapeHtml(content)}" title="Train missing capability in Lab Loop [REQ-FACT-028]">
          <i data-lucide="sparkles" class="w-3 h-3"></i>
          <span>Train in Lab</span>
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

    bubble.querySelectorAll('.train-lab-msg-btn').forEach((b) => {
      b.addEventListener('click', async () => {
        const agentId = state.selectedAgentId || 'autoreiv';
        const msgContent = b.dataset.content || '';

        // Find preceding user prompt
        let prev = bubble.previousElementSibling;
        let precedingUserPrompt = '';
        while (prev) {
          if (prev.classList.contains('justify-end') || prev.querySelector('.justify-end')) {
            const body = prev.querySelector('.msg-body');
            if (body) {
              precedingUserPrompt = body.textContent.trim();
              break;
            }
          }
          prev = prev.previousElementSibling;
        }

        b.disabled = true;
        const origHtml = b.innerHTML;
        b.innerHTML = '<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i><span>Analyzing...</span>';
        safeCreateIcons();

        try {
          const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/gaps`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_prompt: precedingUserPrompt,
              assistant_response: msgContent,
              session_id: state.activeSessionId,
            }),
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);

          const capTitle = data.gap?.identified_capability || 'Missing capability';
          const agentObj = (state.agents || []).find((a) => a.id === agentId);
          const agentDisplayName = agentObj ? agentObj.name : (agentId.charAt(0).toUpperCase() + agentId.slice(1));

          showToast(`Queued to ${agentDisplayName}'s Needs Training backlog: "${capTitle}"`, 'success');
        } catch (err) {
          showToast('Failed to queue training gap: ' + (err.message || err), 'error');
        } finally {
          b.disabled = false;
          b.innerHTML = origHtml;
          safeCreateIcons();
        }
      });
    });

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
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
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

      if (chatGoalSuggestionChip) {
        chatGoalSuggestionChip.classList.add('hidden');
        chatGoalSuggestionChip.classList.remove('flex');
      }
      suggestionDismissedForText = '';

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
      if (messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;

      await executeChatTurn(text, { attachments: attachmentsToSend });
    });
  }

  async function executeChatTurn(userPrompt, options = {}) {
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
    streamBubble.innerHTML = `
      <div class="max-w-4xl w-full rounded-2xl p-4 shadow-md bg-slate-900/90 border border-slate-800/80 text-slate-100 rounded-bl-sm space-y-3">
        <div class="flex items-center justify-between text-xs font-bold uppercase tracking-wider opacity-70">
          <span>${escapeHtml(activeAgentTitle ? activeAgentTitle.textContent : 'Agent')}</span>
          <span class="text-brand-400 font-mono text-[10px] animate-pulse">Streaming...</span>
        </div>
        <div class="plan-milestone-card hidden rounded-xl border border-indigo-500/30 bg-indigo-950/20 p-3 space-y-2 text-xs">
          <div class="plan-card-header flex items-center justify-between font-semibold text-indigo-300">
            <span class="flex items-center space-x-1.5">
              <span>🎯</span>
              <span class="plan-goal-title">Execution Plan</span>
            </span>
            <span class="plan-step-counter text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-indigo-900/60 text-indigo-300"></span>
          </div>
          <div class="plan-steps-container space-y-1.5 pt-1"></div>
        </div>
        <div class="reflexion-status-badge hidden p-2 rounded-lg bg-amber-950/40 border border-amber-500/30 text-xs text-amber-300 items-center space-x-2"></div>
        <div class="tool-status-badge hidden p-2 rounded-lg bg-slate-800/80 border border-slate-700 text-xs text-brand-300 items-center space-x-2"></div>
        <div class="hitl-approval-card hidden rounded-xl border border-amber-500/30 bg-amber-950/20 p-3 space-y-2 text-xs"></div>
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
      </div>
    `;

    if (messagesContainer) {
      messagesContainer.appendChild(streamBubble);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
              || eventType === 'phase_start'
              || eventType === 'phase_complete'
              || eventType === 'react_state'
              || eventType === 'plan_formulated'
              || eventType === 'approval_required'
            ) {
              updateJobPhaseFromEvent(eventType, ev);
            }

            if (eventType === 'plan_formulated') {
              if (planMilestoneCardEl) {
                planMilestoneCardEl.classList.remove('hidden');
                if (planGoalTitleEl) planGoalTitleEl.textContent = ev.goal || 'Execution Plan';
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
                toolStatusBadgeEl.innerHTML = `<span>🔧</span> Invoking tool: <strong class="text-white">${escapeHtml(toolName)}</strong>...`;
              }
            } else if (eventType === 'tool_output' || eventType === 'tool_result') {
              const toolName = ev.tool_name || (ev.data && ev.data.name) || 'tool';
              if (toolStatusBadgeEl) {
                toolStatusBadgeEl.classList.remove('hidden');
                toolStatusBadgeEl.classList.add('flex');
                toolStatusBadgeEl.innerHTML = `<span>✓</span> Tool complete: <strong class="text-emerald-300">${escapeHtml(toolName)}</strong>`;
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
        if (messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;
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

    html += `
      <div class="p-3 rounded-xl bg-slate-800/80 border border-slate-700 space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusColor}">${escapeHtml(status)}</span>
          <span class="text-[10px] text-slate-400 font-mono">${data.summary?.total_tools_executed || 0} tools | ${data.summary?.total_facts_learned || 0} facts</span>
        </div>
        <h4 class="font-bold text-slate-100 text-sm leading-snug">${escapeHtml(goalTitle)}</h4>
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
          <div class="text-center py-12 text-slate-400 space-y-2">
            <i data-lucide="layout" class="w-8 h-8 text-slate-600 mx-auto"></i>
            <p class="text-xs">No active artifact selected. Click an artifact chip in chat to inspect.</p>
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
    });
  }

  return {
    loadAgents,
    loadSessions,
    switchSelectedAgent,
    startNewAgentAuthoring,
    updateActiveAgentHeader,
    createNewSession,
    selectSession,
    renderMessages,
    renderMarkdown,
    openWorkbench,
    closeWorkbench,
    refreshWorkbenchArtifactCount,
    updateWorkbenchArtifactBadge,
    checkSessionBackgroundStatus,
    querySessionStatus,
    getActiveWorkbenchTab: () => activeWorkbenchTab,
    getActiveWorkbenchArtifact: () => activeWorkbenchArtifact,
  };
}
