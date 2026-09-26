/**
 * Skill Studio authoring packet and job helpers [CARD-420].
 * The HTTP module stays for a later mediation wire.
 * Skill Studio does not bind these helpers or open Observe from them.
 */

export const PACKET_SCHEMA = 'skill_studio_authoring_packet';
export const PACKET_VERSION = 1;
export const DEVELOPER_AGENT_ID = 'developer';
export const AUTHORING_JOBS_URL = '/api/skill_studio/authoring/jobs';
export const AUTHORING_LINT_URL = '/api/skill_studio/authoring/lint';
export const SILENT_RUNBOOK_URL = '/api/skill_studio/runbook';

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
