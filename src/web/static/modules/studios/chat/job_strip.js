/**
 * Chat Studio: the Job / phase strip model [REQ-ORCH-042, CARD-240, CARD-338, CARD-530, CARD-490].
 * Pure helpers moved out of chat.js (CARD-490 kept chat.js under its size budget); chat.js re-exports them.
 */

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
  const raw = String(status || '').trim();
  if (!raw || raw.toLowerCase() === "unknown") return "";
  return raw.replace(/_/g, ' ');
}

export function formatJobPhaseStrip(state) {
  const jobId = (state && (state.jobId || state.job_id)) || '';
  const jobStatus = humanizeJobStatus(state && state.jobStatus);
  const phaseName = (state && state.phaseName) || '';
  const phaseIndex = state && state.phaseIndex;
  const phaseCount = state && state.phaseCount;
  let phaseLabel = phaseName || 'Phase';
  if (phaseIndex != null && phaseIndex !== '') {
    const n = Number(phaseIndex) + 1;
    phaseLabel = phaseCount != null && phaseCount !== '' ? `Phase ${n}/${phaseCount} ${phaseName}`.trim() : `Phase ${n} ${phaseName}`.trim();
  }
  const agent = (state && (state.assignedAgentId || state.agentId)) || 'agent';
  const reactState = String((state && state.reactState) || '').toUpperCase();
  const failReason = String((state && state.failReason) || '').trim();
  const failed = String((state && state.jobStatus) || '').toLowerCase() === 'failed';
  const resumed = Boolean(state && state.resumedFromCheckpoint) && !failed;
  let jobStatusLabel = jobStatus ? `Job ${jobStatus}` : (jobId ? "Job" : "");
  if (failed && failReason) {
    // CARD-530 REQ-530-007: say why, never DONE next to a failed job.
    jobStatusLabel = `Job failed: ${failReason.length > 160 ? `${failReason.slice(0, 157)}...` : failReason}`;
  }
  if (resumed && jobStatusLabel) {
    jobStatusLabel = `${jobStatusLabel} | Resumed (resumed_from_checkpoint)`;
  }
  const stopped = Boolean(state && state.stopped) && !failed; // CARD-490
  if (stopped) jobStatusLabel = 'Job stopped';
  const parentJobId = (state && (state.parentJobId || state.parent_job_id)) || '';
  const childJobId = (state && (state.childJobId || state.child_job_id)) || '';
  const childJobIds = (state && (state.childJobIds || state.child_job_ids)) || [];
  let parentChildLabel = '';
  if (parentJobId && (childJobId || (Array.isArray(childJobIds) && childJobIds.length))) {
    parentChildLabel = `parent↔child ${parentJobId} ↔ ${childJobId || childJobIds[0]}`;
  } else if (childJobId || (Array.isArray(childJobIds) && childJobIds.length)) {
    parentChildLabel = `parent↔child → ${childJobId || childJobIds[0]}`;
  } else if (parentJobId) {
    parentChildLabel = `parent↔child ← ${parentJobId}`;
  }
  return {
    jobStatusLabel,
    phaseLabel,
    agentLabel: agent,
    reactState: stopped ? 'STOPPED' : reactState,
    resumedFromCheckpoint: resumed,
    stopped,
    jobId,
    parentJobId,
    childJobId,
    childJobIds,
    parentChildLabel,
  };
}

export function reactStateToneClass(reactState) {
  switch (String(reactState || '').toUpperCase()) {
    case 'PARKED': return 'job-phase-react px-2 py-0.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300 font-semibold tracking-wide';
    case 'FAILED': return 'job-phase-react px-2 py-0.5 rounded bg-rose-950/80 border border-rose-800 text-rose-300 font-semibold tracking-wide';
    case 'DONE': return 'job-phase-react px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-semibold tracking-wide';
    case 'CALLING_TOOLS': return 'job-phase-react px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-800 text-indigo-300 font-semibold tracking-wide';
    case 'THINKING': return 'job-phase-react px-2 py-0.5 rounded bg-sky-950/80 border border-sky-800 text-sky-300 font-semibold tracking-wide';
    case 'STOPPED': return 'job-phase-react px-2 py-0.5 rounded bg-slate-800 border border-amber-800/70 text-amber-200 font-semibold tracking-wide'; // CARD-490
    default: return 'job-phase-react px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-semibold tracking-wide';
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
    if (data.status === 'waiting_approval') next.reactState = next.reactState || 'PARKED';
  } else if (eventType === 'phase_start') {
    next.stopped = false; // CARD-490: running again
    if (!next.jobStatus || next.jobStatus === 'queued' || next.jobStatus === 'waiting_for_answer') next.jobStatus = 'running'; // CARD-613
    if (!next.reactState || String(next.reactState).toUpperCase() === 'STOPPED') next.reactState = 'THINKING';
  } else if (eventType === 'phase_complete') {
    if (data.status) next.jobStatus = data.status;
    if (data.react_state) next.reactState = data.react_state;
    if (data.status === 'done' || data.status === 'failed') next.resumedFromCheckpoint = false; // CARD-530
    if (data.status === 'failed' && (data.reason || data.last_fail_reason)) next.failReason = data.reason || data.last_fail_reason;
  } else if (eventType === 'error' || (eventType === 'turn_done' && (data.error || data.job_failed))) {
    // CARD-530 REQ-530-007: a failed turn shows Failed and the reason, not the last react_state.
    next.jobStatus = 'failed';
    next.reactState = 'FAILED';
    next.resumedFromCheckpoint = false;
    const reason = String(data.error || data.reason || '').trim();
    if (reason) next.failReason = reason;
  } else if (eventType === 'react_state') {
    if (data.react_state) next.reactState = data.react_state;
    if (data.job_status) next.jobStatus = data.job_status;
  } else if (eventType === 'resumed_from_checkpoint') {
    next.resumedFromCheckpoint = true;
    next.stopped = false; // CARD-490
    if (data.job_id) next.jobId = data.job_id;
    if (data.phase_index != null) next.phaseIndex = data.phase_index;
    if (data.phase_id) next.phaseId = data.phase_id;
    if (data.verifier_status) next.verifyStatus = data.verifier_status;
    if (String(next.reactState || '').toUpperCase() === 'STOPPED') next.reactState = data.hitl_park_state ? 'PARKED' : 'THINKING'; // CARD-490
    if (data.hitl_park_state) next.reactState = next.reactState || 'PARKED';
    if (!next.jobStatus || next.jobStatus === 'queued') next.jobStatus = 'running';
  } else if (eventType === 'plan_formulated') {
    if (data.job_id) next.jobId = data.job_id;
    if (Array.isArray(data.steps)) next.phaseCount = data.steps.length;
    next.jobStatus = data.standing ? (next.jobStatus || data.status || 'queued') : (next.jobStatus || 'waiting_approval');
    if (!data.standing) next.reactState = next.reactState || 'PARKED';
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
