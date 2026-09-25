/**
 * Chat Studio: what happens when a chat is selected [CARD-485, CARD-295, CARD-296, CARD-154]
 * Restores the pre-CARD-397 select path: highlight in the list, close the sessions drawer on a
 * user pick, rebuild the job strip and inline phases from the journey, and show a busy state
 * (2 s status re-check) while the chat's reply is still running elsewhere. Live replay is CARD-487.
 */

import { querySessionStatus } from './stream.js';
import { createInlineJobChromeModel, applyInlineJobChromeModel } from './job_chrome.js';
import { renderSessionList, loadChatSessionContext } from './chrome.js';
import { collapseChatSessionsDrawer } from './scroll.js';

export const SESSION_STATUS_POLL_MS = 2000;

const JOB_RANK = (s) => {
  const v = String(s || '').toLowerCase();
  if (v === 'waiting_approval') return 0;
  if (v === 'running' || v === 'in_progress' || v === 'queued') return 1;
  return v === 'failed' ? 2 : 3;
};

/** The journey job to show: waiting for approval first, then running, then failed, then the rest. */
export function pickJourneyJob(journey) {
  const jobs = journey && Array.isArray(journey.jobs) ? journey.jobs : [];
  if (!jobs.length) return null;
  const job = [...jobs].sort((a, b) => JOB_RANK(a.status) - JOB_RANK(b.status))[0];
  return job && job.id ? job : null;
}

const sortedPhases = (job) => (job && Array.isArray(job.phases)
  ? [...job.phases].sort((a, b) => Number(a.index || 0) - Number(b.index || 0))
  : []);

/** Job strip state from a session journey [CARD-295]. Null when the chat has no job. */
export function hydrateJobPhaseStateFromJourney(journey) {
  const job = pickJourneyJob(journey);
  if (!job) return null;
  const phases = sortedPhases(job);
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
    next.reactState = 'THINKING';
  } else if (jobStatus === 'done') {
    next.reactState = 'DONE';
  } else if (jobStatus === 'failed') {
    next.reactState = 'FAILED';
  }
  return next;
}

/** Inline phase chips for the same job (pre-split L1590-1619). Null when it has no phases. */
export function buildInlineJobChromeFromJourney(journey) {
  const job = pickJourneyJob(journey);
  const phases = sortedPhases(job);
  if (!phases.length) return null;
  let model = createInlineJobChromeModel();
  phases.forEach((p) => {
    const st = String(p.status || '').toLowerCase();
    model = applyInlineJobChromeModel(model, 'phase_start', {
      job_id: job.id, phase_id: p.id, phase_name: p.name, index: p.index, phase_count: phases.length, assigned_agent_id: p.assigned_agent_id,
    });
    if (st === 'done') {
      model = applyInlineJobChromeModel(model, 'phase_complete', { job_id: job.id, phase_id: p.id, phase_name: p.name, index: p.index, status: 'done' });
    } else if (st === 'waiting_approval') {
      model = applyInlineJobChromeModel(model, 'approval_required', { job_id: job.id, job_status: 'waiting_approval', react_state: 'PARKED' });
    }
  });
  return model;
}

/**
 * Fetch the chat's journey and restore its job strip and inline phases [REQ-485-003/004/007].
 * Soft-fails; ignores the result if another chat was opened meanwhile.
 */
export async function hydrateJobChromeFromSession(state, sessionId, {
  fetchFn = null,
  setJobPhaseState = () => {},
  setInlineJobChromeModel = () => {},
} = {}) {
  if (!sessionId) return false;
  const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
  try {
    const res = await fn(`/api/chat/sessions/${encodeURIComponent(sessionId)}/journey`);
    if (!res || !res.ok) return false;
    const data = await res.json();
    if (state.activeSessionId !== sessionId) return false;
    const next = hydrateJobPhaseStateFromJourney(data);
    if (!next) return false;
    setJobPhaseState(next);
    const model = buildInlineJobChromeFromJourney(data);
    if (model) setInlineJobChromeModel(model);
    return true;
  } catch (err) {
    console.warn('[AutoReiv UI] CARD-485 journey hydrate soft-fail:', err);
    return false;
  }
}

/** Show or clear the busy state for a reply running elsewhere (Send hidden, Stop shown). */
export function setSessionBusy(state, { sendBtn = null, stopBtn = null } = {}, busy = false) {
  const on = Boolean(busy);
  state.sessionBusy = on;
  if (sendBtn) {
    sendBtn.disabled = on;
    sendBtn.classList.toggle('hidden', on);
  }
  if (stopBtn) {
    stopBtn.disabled = !on;
    stopBtn.classList.toggle('hidden', !on);
  }
}

const pageVisible = () => typeof document === 'undefined' || document.visibilityState !== 'hidden';

/**
 * Watch whether the open chat's reply is still running (pre-split checkSessionBackgroundStatus,
 * L1667-1725) [REQ-485-005/006/007, D3]. Exported for CARD-473 (phone return).
 * - running: busy on, re-check every 2 s while that chat stays open and the page is visible;
 * - finished: busy off, then `onFinished(sessionId)` reloads the reply;
 * - never touches this tab's own stream (state.isStreaming without watcher busy).
 */
export function createSessionStatusWatcher(state, {
  queryStatusFn = querySessionStatus,
  setBusy = () => {},
  onFinished = async () => {},
  intervalMs = SESSION_STATUS_POLL_MS,
  isPageVisible = pageVisible,
  setIntervalFn = (fn, ms) => setInterval(fn, ms),
  clearIntervalFn = (id) => clearInterval(id),
} = {}) {
  let timer = null;
  let watchedId = null;
  let busy = false;
  let inFlight = null;
  let inFlightId = null;

  function clearTimer() {
    if (timer != null) {
      clearIntervalFn(timer);
      timer = null;
    }
  }

  function stop() {
    clearTimer();
    watchedId = null;
    if (busy) {
      busy = false;
      setBusy(false);
    }
  }

  function check(sessionId = watchedId) {
    if (!sessionId || sessionId !== state.activeSessionId) return Promise.resolve(null);
    if (inFlight && inFlightId === sessionId) return inFlight;
    inFlightId = sessionId;
    inFlight = (async () => {
      const data = await queryStatusFn(sessionId);
      if (sessionId !== state.activeSessionId || sessionId !== watchedId) return data;
      if (data && data.is_running) {
        if (state.isStreaming && !busy) return data; // this tab's own stream
        if (!busy) {
          busy = true;
          setBusy(true);
        }
        if (timer == null) {
          timer = setIntervalFn(() => {
            if (isPageVisible()) check(sessionId);
          }, intervalMs);
        }
      } else {
        clearTimer();
        if (busy) {
          busy = false;
          setBusy(false);
          await onFinished(sessionId);
        }
      }
      return data;
    })().finally(() => {
      if (inFlightId === sessionId) {
        inFlight = null;
        inFlightId = null;
      }
    });
    return inFlight;
  }

  function watch(sessionId) {
    if (watchedId !== sessionId) stop();
    watchedId = sessionId || null;
    return check(sessionId);
  }

  return { watch, check, stop, isBusy: () => busy, watchedId: () => watchedId };
}

/**
 * The select path shared by list clicks, restore on load and New chat [REQ-485-001..008].
 * `chat.js` sets the id and resets the strips, then awaits `afterSelect`.
 */
export function createSessionSelect(state, deps = {}) {
  const {
    sessionList = null,
    onSelectSession = null,
    chatSessionsDrawer = null,
    viewChat = null,
    sendBtn = null,
    stopBtn = null,
    loadMessages = async () => {},
    refreshPendingHitl = async () => {},
    refreshWorkbenchArtifactCount = async () => {},
    setJobPhaseState = () => {},
    setInlineJobChromeModel = () => {},
    jumpToLatest = () => {},
    fetchFn = null,
    queryStatusFn = querySessionStatus,
    isPageVisible = pageVisible,
    getEl = (id) => (typeof document !== 'undefined' ? document.getElementById(id) : null),
    refreshContext = () => loadChatSessionContext(state, {
      chatContextTokensBadge: getEl('chatContextTokensBadge'),
      chatContextProgressBar: getEl('chatContextProgressBar'),
      chatToolsCountBadge: getEl('chatToolsCountBadge'),
    }),
  } = deps;

  const watcher = createSessionStatusWatcher(state, {
    queryStatusFn,
    isPageVisible,
    setBusy: (busy) => setSessionBusy(state, { sendBtn, stopBtn }, busy),
    onFinished: async (sessionId) => {
      await loadMessages(sessionId);
      await refreshPendingHitl();
    },
  });

  const stale = (sessionId) => state.activeSessionId !== sessionId;

  async function afterSelect(sessionId, { userPick = false } = {}) {
    if (!sessionId) return;
    watcher.stop();
    renderSessionList({ sessionList, sessions: state.sessions, activeSessionId: sessionId, onSelectSession });
    if (userPick) collapseChatSessionsDrawer(chatSessionsDrawer, viewChat);
    await loadMessages(sessionId);
    if (stale(sessionId)) return;
    await refreshPendingHitl();
    await hydrateJobChromeFromSession(state, sessionId, { fetchFn, setJobPhaseState, setInlineJobChromeModel });
    if (stale(sessionId)) return;
    await watcher.watch(sessionId);
    await refreshWorkbenchArtifactCount();
    const options = getEl('chatOptionsDrawer');
    if (options && options.classList && !options.classList.contains('hidden')) {
      try {
        await refreshContext();
      } catch (err) {
        console.warn('[AutoReiv UI] CARD-485 context refresh soft-fail:', err);
      }
    }
    if (!stale(sessionId)) jumpToLatest();
  }

  return {
    afterSelect,
    stopWatching: () => watcher.stop(),
    watchSessionStatus: (sessionId = state.activeSessionId) => watcher.watch(sessionId),
    watcher,
  };
}
