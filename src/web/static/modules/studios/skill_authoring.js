/**
 * Skill Studio developer-mediated authoring [CARD-420].
 * Build/Review opens a visible developer standing job. Accept updates the draft.
 * Save stays on the existing Skill Studio path. Cheap lint does not mint a job.
 */

import { $, escapeHtml } from '../dom.js';
import { openObserveJob } from './observability.js';

export const PACKET_SCHEMA = 'skill_studio_authoring_packet';
export const PACKET_VERSION = 1;
export const DEVELOPER_AGENT_ID = 'developer';
export const AUTHORING_JOBS_URL = '/api/skill_studio/authoring/jobs';
export const AUTHORING_LINT_URL = '/api/skill_studio/authoring/lint';
export const SILENT_RUNBOOK_URL = '/api/agent_training_factory/scaffold/runbook';

const PATCH_FIELDS = new Set([
  'name',
  'description',
  'tier',
  'safety',
  'requires_tools',
  'markdown',
]);

export function authoringRequestPlan(intent) {
  const clean = intent === 'review' ? 'review' : 'build';
  return {
    url: AUTHORING_JOBS_URL,
    method: 'POST',
    intent: clean,
    opensJob: true,
    llmRewrite: false,
  };
}

export function lintRequestPlan() {
  return {
    url: AUTHORING_LINT_URL,
    method: 'POST',
    opensJob: false,
    llmRewrite: false,
  };
}

export function normalizeAuthoringDraft(raw = {}) {
  const source = raw && typeof raw === 'object' ? raw : {};
  const safety = source.safety && typeof source.safety === 'object' ? source.safety : {};
  const tools = Array.isArray(source.requires_tools)
    ? source.requires_tools.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
  return {
    skill_id: String(source.skill_id || '').trim(),
    name: String(source.name || '').trim(),
    description: String(source.description || '').trim(),
    tier: String(source.tier || 'pack').trim() || 'pack',
    safety: {
      read_only: Boolean(safety.read_only),
      requires_hitl: Boolean(safety.requires_hitl),
      untrusted_input_allowed: Boolean(safety.untrusted_input_allowed),
    },
    requires_tools: tools,
    markdown: String(source.markdown || ''),
    intent_notes: String(source.intent_notes || ''),
    source_context: String(source.source_context || ''),
  };
}

export function buildAuthoringPacket({ intent, draft, blockers = [] } = {}) {
  const cleanIntent = intent === 'review' ? 'review' : 'build';
  return {
    schema: PACKET_SCHEMA,
    version: PACKET_VERSION,
    studio: 'skill',
    intent: cleanIntent,
    agent_id: DEVELOPER_AGENT_ID,
    draft: normalizeAuthoringDraft(draft),
    lint: {
      cheap: true,
      blockers: Array.isArray(blockers) ? blockers : [],
    },
    llm_rewrite: false,
  };
}

/**
 * Apply developer field patches onto a Skill Studio draft.
 * Unknown fields (skill id, agent allowlists) are ignored.
 * This does not persist. The operator still uses Skill Studio Save.
 */
export function applyAuthoringPatches(draft, patches) {
  const next = normalizeAuthoringDraft(draft);
  const ignored = [];
  let changed = false;
  (patches || []).forEach((patch) => {
    const field = patch && patch.field;
    if (!PATCH_FIELDS.has(field)) {
      ignored.push(field);
      return;
    }
    changed = true;
    if (field === 'safety' && patch.value && typeof patch.value === 'object') {
      next.safety = {
        read_only: Boolean(patch.value.read_only),
        requires_hitl: Boolean(patch.value.requires_hitl),
        untrusted_input_allowed: Boolean(patch.value.untrusted_input_allowed),
      };
      return;
    }
    if (field === 'requires_tools' && Array.isArray(patch.value)) {
      next.requires_tools = patch.value.map((item) => String(item || '').trim()).filter(Boolean);
      return;
    }
    if (field === 'name' || field === 'description' || field === 'tier' || field === 'markdown') {
      next[field] = String(patch.value == null ? '' : patch.value);
    }
  });
  return { draft: next, ignored, persisted: false, changed };
}

export function rejectAuthoringPatches(draft) {
  const next = normalizeAuthoringDraft(draft);
  return { draft: next, changed: false, persisted: false };
}

export function planAuthoringWatch(jobId) {
  const id = String(jobId || '').trim();
  if (!id) return null;
  return {
    jobId: id,
    primary: 'observe',
    observe: { studio: 'observe', tab: 'observability', jobId: id },
    chat: { studio: 'chat', jobId: id, agentId: DEVELOPER_AGENT_ID },
  };
}

async function readJson(resp) {
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = data && (data.detail || data.message);
    throw new Error(detail || `Server returned ${resp.status}`);
  }
  return data;
}

export async function runCheapLint(draft, { fetchFn = fetch } = {}) {
  const plan = lintRequestPlan();
  const resp = await fetchFn(plan.url, {
    method: plan.method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ draft: normalizeAuthoringDraft(draft) }),
  });
  const data = await readJson(resp);
  if (data.job_id || data.opened_job) {
    throw new Error('cheap lint must not open a developer job');
  }
  return {
    blockers: Array.isArray(data.blockers) ? data.blockers : [],
    openedJob: false,
    llmRewrite: false,
  };
}

export async function submitSkillAuthoring(draft, intent, { fetchFn = fetch } = {}) {
  const plan = authoringRequestPlan(intent);
  const resp = await fetchFn(plan.url, {
    method: plan.method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      intent: plan.intent,
      draft: normalizeAuthoringDraft(draft),
    }),
  });
  const data = await readJson(resp);
  const jobId = String(data.job_id || '').trim();
  if (!jobId) throw new Error('Authoring job id was empty.');
  if (data.llm_rewrite) throw new Error('Build must not silently rewrite the skill.');
  return {
    jobId,
    agentId: data.agent_id || DEVELOPER_AGENT_ID,
    resumed: Boolean(data.resumed),
    visible: data.visible !== false,
    llmRewrite: false,
    packet: data.packet || null,
    watch: data.watch || planAuthoringWatch(jobId),
    persistedSkill: false,
  };
}

export async function fetchAuthoringJob(jobId, { fetchFn = fetch } = {}) {
  const id = String(jobId || '').trim();
  const resp = await fetchFn(`${AUTHORING_JOBS_URL}/${encodeURIComponent(id)}`);
  const data = await readJson(resp);
  return data;
}

export async function submitAuthoringDecision(jobId, decision, { fetchFn = fetch } = {}) {
  const id = String(jobId || '').trim();
  const resp = await fetchFn(`${AUTHORING_JOBS_URL}/${encodeURIComponent(id)}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision }),
  });
  const data = await readJson(resp);
  return {
    decision: data.decision,
    patches: Array.isArray(data.patches) ? data.patches : [],
    persistedSkill: false,
  };
}

function previewValue(value) {
  if (Array.isArray(value)) return value.join(', ');
  if (value && typeof value === 'object') return JSON.stringify(value);
  const text = String(value == null ? '' : value);
  return text.length > 80 ? `${text.slice(0, 77)}...` : text;
}

export function lintPanelHtml(blockers) {
  if (!blockers || !blockers.length) {
    return '<p class="text-[11px] text-emerald-300">Cheap lint: no blockers.</p>';
  }
  const rows = blockers.map((item) => (
    `<li><span class="font-mono text-amber-200">${escapeHtml(item.code || 'LINT')}</span> ${escapeHtml(item.message || '')}</li>`
  )).join('');
  return `<p class="text-[11px] font-semibold text-amber-200">Cheap lint (in-form, no developer job)</p><ul class="mt-1 space-y-1 text-[11px] text-amber-100">${rows}</ul>`;
}

export function proposalPanelHtml(proposals) {
  const patches = proposals && Array.isArray(proposals.patches) ? proposals.patches : [];
  if (!patches.length || (proposals && proposals.decision)) return '';
  const rows = patches.map((patch) => (
    `<li><span class="font-mono text-sky-200">${escapeHtml(patch.field || '')}</span> <span class="text-slate-300">${escapeHtml(previewValue(patch.value))}</span></li>`
  )).join('');
  return `<p class="text-[11px] text-slate-200">Developer proposed field patches. Accept updates this draft. Save still writes the skill.</p><ul class="mt-1 space-y-1 text-[11px]">${rows}</ul>`;
}

/**
 * Wire Skill Studio Build/Review. Accept updates the draft through writeDraft.
 * It does not call the skill save endpoint.
 */
export function bindSkillStudioAuthoring({ callbacks = {}, showToast, collectDraft, writeDraft }) {
  const skillStudioBuildBtn = $('skillStudioBuildBtn');
  const skillStudioReviewBtn = $('skillStudioReviewBtn');
  const skillStudioLintPanel = $('skillStudioLintPanel');
  const skillStudioAuthoringBar = $('skillStudioAuthoringBar');
  const skillStudioAuthoringStatus = $('skillStudioAuthoringStatus');
  const skillStudioWatchBtn = $('skillStudioWatchBtn');
  const skillStudioChatBtn = $('skillStudioChatBtn');
  const skillStudioProposalPanel = $('skillStudioProposalPanel');
  const skillStudioProposalBody = $('skillStudioProposalBody');
  const skillStudioAcceptBtn = $('skillStudioAcceptBtn');
  const skillStudioRejectBtn = $('skillStudioRejectBtn');
  const factorySkillNameInput = $('factorySkillNameInput');
  const factorySkillMarkdownEditor = $('factorySkillMarkdownEditor');

  let authoringJobId = '';
  let authoringPoll = null;
  let lintTimer = null;

  function showLint(blockers) {
    if (!skillStudioLintPanel) return;
    skillStudioLintPanel.innerHTML = lintPanelHtml(blockers);
    skillStudioLintPanel.classList.remove('hidden');
  }

  async function refreshCheapLint() {
    try {
      const result = await runCheapLint(collectDraft());
      showLint(result.blockers);
    } catch (err) {
      console.error('[SkillStudio] Cheap lint failed:', err);
    }
  }

  function scheduleCheapLint() {
    if (lintTimer) clearTimeout(lintTimer);
    lintTimer = setTimeout(() => { refreshCheapLint(); }, 400);
  }

  function showAuthoringJob(result) {
    authoringJobId = result.jobId;
    if (skillStudioAuthoringBar) skillStudioAuthoringBar.classList.remove('hidden');
    if (skillStudioAuthoringStatus) {
      const verb = result.resumed ? 'Resumed' : 'Opened';
      skillStudioAuthoringStatus.textContent = `${verb} developer job ${result.jobId}. Watch it in Observe. Save still writes this skill.`;
    }
  }

  function showProposals(proposals) {
    if (!skillStudioProposalPanel || !skillStudioProposalBody) return;
    const html = proposalPanelHtml(proposals);
    if (!html) {
      skillStudioProposalPanel.classList.add('hidden');
      skillStudioProposalBody.innerHTML = '';
      return;
    }
    skillStudioProposalBody.innerHTML = html;
    skillStudioProposalPanel.classList.remove('hidden');
  }

  async function pollAuthoringJob() {
    if (!authoringJobId) return;
    try {
      const data = await fetchAuthoringJob(authoringJobId);
      showProposals(data.proposals);
    } catch (err) {
      console.error('[SkillStudio] Authoring job poll failed:', err);
    }
  }

  function startAuthoringPoll() {
    if (authoringPoll) clearInterval(authoringPoll);
    authoringPoll = setInterval(() => { pollAuthoringJob(); }, 4000);
    pollAuthoringJob();
  }

  async function watchAuthoringJob() {
    if (!authoringJobId) return;
    await openObserveJob(authoringJobId, { switchTab: callbacks.switchTab });
  }

  async function openAuthoringChat() {
    if (!authoringJobId) return;
    if (typeof callbacks.switchTab === 'function') callbacks.switchTab('chat');
    const chat = typeof callbacks.getChatCtrl === 'function' ? callbacks.getChatCtrl() : null;
    if (chat && typeof chat.switchSelectedAgent === 'function') {
      await chat.switchSelectedAgent('developer');
    }
    if (chat && typeof chat.showStandingJob === 'function') {
      chat.showStandingJob({
        jobId: authoringJobId,
        status: 'queued',
        agentId: 'developer',
      });
    }
  }

  async function handleAuthoring(intent) {
    const draft = collectDraft();
    if (!draft.skill_id) {
      showToast('Enter a skill name before Build or Review.', 'warning');
      if (factorySkillNameInput) factorySkillNameInput.focus();
      return;
    }
    const buttons = [skillStudioBuildBtn, skillStudioReviewBtn];
    buttons.forEach((btn) => {
      if (!btn) return;
      btn.disabled = true;
      btn.classList.add('opacity-50', 'cursor-not-allowed');
    });
    try {
      const lint = await runCheapLint(draft);
      showLint(lint.blockers);
      const result = await submitSkillAuthoring(draft, intent);
      showAuthoringJob(result);
      startAuthoringPoll();
      await watchAuthoringJob();
      showToast(`${intent === 'review' ? 'Review' : 'Build'} opened ${result.jobId}`, 'success');
    } catch (err) {
      console.error('[SkillStudio] Authoring failed:', err);
      showToast(`Build/Review failed: ${err.message}`, 'error');
    } finally {
      buttons.forEach((btn) => {
        if (!btn) return;
        btn.disabled = false;
        btn.classList.remove('opacity-50', 'cursor-not-allowed');
      });
    }
  }

  async function handleAcceptPatches() {
    if (!authoringJobId) return;
    const before = collectDraft();
    try {
      const data = await fetchAuthoringJob(authoringJobId);
      const patches = (data.proposals && data.proposals.patches) || [];
      await submitAuthoringDecision(authoringJobId, 'accept');
      const applied = applyAuthoringPatches(before, patches);
      writeDraft(applied.draft);
      showProposals(null);
      showToast('Draft updated. Save skill still writes the store.', 'success');
    } catch (err) {
      console.error('[SkillStudio] Accept failed:', err);
      showToast(`Accept failed: ${err.message}`, 'error');
    }
  }

  async function handleRejectPatches() {
    if (!authoringJobId) return;
    try {
      await submitAuthoringDecision(authoringJobId, 'reject');
      showProposals(null);
      showToast('Rejected. The draft was left unchanged.', 'info');
    } catch (err) {
      console.error('[SkillStudio] Reject failed:', err);
      showToast(`Reject failed: ${err.message}`, 'error');
    }
  }

  if (skillStudioBuildBtn) {
    skillStudioBuildBtn.addEventListener('click', () => { handleAuthoring('build'); });
  }
  if (skillStudioReviewBtn) {
    skillStudioReviewBtn.addEventListener('click', () => { handleAuthoring('review'); });
  }
  if (skillStudioWatchBtn) {
    skillStudioWatchBtn.addEventListener('click', () => { watchAuthoringJob(); });
  }
  if (skillStudioChatBtn) {
    skillStudioChatBtn.addEventListener('click', () => { openAuthoringChat(); });
  }
  if (skillStudioAcceptBtn) {
    skillStudioAcceptBtn.addEventListener('click', () => { handleAcceptPatches(); });
  }
  if (skillStudioRejectBtn) {
    skillStudioRejectBtn.addEventListener('click', () => { handleRejectPatches(); });
  }
  if (factorySkillMarkdownEditor) {
    factorySkillMarkdownEditor.addEventListener('blur', () => { scheduleCheapLint(); });
  }

  return {
    stop() {
      if (authoringPoll) clearInterval(authoringPoll);
      authoringPoll = null;
      if (lintTimer) clearTimeout(lintTimer);
      lintTimer = null;
    },
  };
}
