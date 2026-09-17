/**
 * Chat Studio: Agent Training Handshake & Promotion Submodule [REQ-ARCH-003]
 * Handles training job payloads, live training indicators, and promotion cards.
 */

import { $ } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';

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
