/**
 * Chat Studio Module [REQ-FE-001, REQ-WEB-001, REQ-WEB-002, CARD-397]
 * Coordinates chat interactions, sessions, message streaming, job chrome, and decomposed submodules.
 */

import { $, isMobile, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { copyToClipboard } from '../utils/clipboard.js';
import { storageSet } from '../utils/storage.js';
import { publishAgentsLoaded } from '../state/store.js';
import { showToast } from '../ui/toast.js';

// Re-export all decomposed submodules for complete backward compatibility [REQ-ARCH-003, CARD-397]
export * from './chat/hitl.js';
export * from './chat/training.js';
export * from './chat/scroll.js';
export * from './chat/stream.js';
export * from './chat/job_chrome.js';
export * from './chat/journey.js';
export * from './chat/render.js';
export * from './chat/composer.js';
export * from './chat/chrome.js';
export * from './chat/workbench.js';
export * from './chat/train_modal.js';
export * from './chat/session_select.js'; // CARD-485 (hydrateJobPhaseStateFromJourney moved here)

import { setupPendingHitl, renderInlineHitlCard } from './chat/hitl.js'; // CARD-470

import { populateTrainAgentTargetOptions } from './chat/training.js';
import { setupRuntimeModeToggles } from './chat/runtime_toggles.js'; // CARD-470
import { setupChatScroll } from './chat/scroll.js';
import { ensureActiveSession, singleFlight, trackSessionsLoad, LAST_SESSION_KEY } from './chat/session_guard.js'; // CARD-476
import { createSessionSelect } from './chat/session_select.js'; // CARD-485
import { createStopHandler } from './chat/stop.js'; // CARD-486

import {
  buildChatStreamPayload,
  consumeChatStream,
  trackStreamOutcome, reportStreamOutcome, // CARD-469: failed replies are shown
  querySessionStatus,
  renderAgentHandoffCardHtml,
} from './chat/stream.js';

import {
  shouldMountInlineJobChrome,
  applyInlineJobChromeModel,
  formatMilestoneGoalTitle,
  renderJobChromePhasesIntoElement,
  formatInlineJobChromeHtml,
} from './chat/job_chrome.js';

import {
  appendMessageBubble as appendMessageBubbleDirect,
  renderMessages as renderMessagesDirect,
  setupMessagesContainerDelegation,
  renderMarkdown,
} from './chat/render.js';

import {
  wireComposer,
  clearStagedAttachments,
  setupComposerControls,
  setupComposerSizing,
  setComposerText,
} from './chat/composer.js';

import {
  loadSessions as loadSessionsDirect,
  createNewSession as createNewSessionDirect,
  setupChatChrome,
  closeChatOptionsDrawer,
  syncChatJobViewButton,
  bindChatJobViewShortcut,
} from './chat/chrome.js';

import {
  initWorkbench,
  refreshWorkbenchArtifactCount as refreshWorkbenchArtifactCountDirect,
} from './chat/workbench.js';

import {
  setupTrainModal,
  setupTeachAgentModal,
} from './chat/train_modal.js';

// Verification tokens for REQ-VERIFY-EXT-004: 'verified', 'skipped_no_checker', 'failed'
export const VERIFY_STATUS_SKIPPED = 'skipped_no_checker';
export const VERIFY_STATUS_VERIFIED = 'verified';
export const VERIFY_STATUS_FAILED = 'failed';

// Retired legacy agent IDs preserved in a frozen set for backward-compatibility [CARD-383]
export const RETIRED_LEGACY_AGENT_IDS = Object.freeze(
  new Set(['agent-builder', 'coding', 'review', 'conductor', 'hyperv', 'assistant', 'wiki'])
);

export function isAgentVisibleInChat(agent) {
  if (agent == null) return true;
  if (agent.visibility === 'internal') return false;
  if (agent.origin === 'system' || agent.is_builtin) return false;
  if (RETIRED_LEGACY_AGENT_IDS.has(agent.id)) return false;
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
  const resumed = Boolean(state && state.resumedFromCheckpoint);
  let jobStatusLabel = jobStatus ? `Job ${jobStatus}` : (jobId ? "Job" : "");
  if (resumed && jobStatusLabel) {
    jobStatusLabel = `${jobStatusLabel} | Resumed (resumed_from_checkpoint)`;
  }
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
    case 'PARKED': return 'job-phase-react px-2 py-0.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300 font-semibold tracking-wide';
    case 'FAILED': return 'job-phase-react px-2 py-0.5 rounded bg-rose-950/80 border border-rose-800 text-rose-300 font-semibold tracking-wide';
    case 'DONE': return 'job-phase-react px-2 py-0.5 rounded bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-semibold tracking-wide';
    case 'CALLING_TOOLS': return 'job-phase-react px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-800 text-indigo-300 font-semibold tracking-wide';
    case 'THINKING': return 'job-phase-react px-2 py-0.5 rounded bg-sky-950/80 border border-sky-800 text-sky-300 font-semibold tracking-wide';
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
    if (!next.jobStatus || next.jobStatus === 'queued') next.jobStatus = 'running';
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

export function initChatStudio(state, callbacks = {}) {
  const agentSelect = $('agentSelect');
  const sessionList = $('sessionList');
  const newChatBtn = $('newChatBtn');
  const activeAgentTitle = $('activeAgentTitle');
  const activeAgentTone = $('activeAgentTone');
  const chatActiveProjectPill = $('chatActiveProjectPill');
  const chatActiveProjectName = $('chatActiveProjectName');
  const messagesContainer = $('messagesContainer');
  const chatSessionsDrawer = $('chatSessionsDrawer');
  const chatSessionsDrawerCloseBtn = $('chatSessionsDrawerCloseBtn');
  const chatJumpToLatestBtn = $('chatJumpToLatestBtn');
  const viewChat = $('view-chat');
  const toggleSidebarBtn = $('toggleSidebarBtn');

  const {
    maybeAutoscrollMessages,
    isStickToBottom,
    jumpMessagesToLatest,
  } = setupChatScroll({
    messagesContainer,
    chatJumpToLatestBtn,
    chatSessionsDrawer,
    chatSessionsDrawerCloseBtn,
    toggleSidebarBtn,
    viewChat,
  });

  if (chatActiveProjectPill) {
    chatActiveProjectPill.addEventListener('click', () => {
      const tabProjects = $('tab-projects');
      if (tabProjects) tabProjects.click();
    });
  }

  const tabChat = $('tab-chat');
  if (tabChat) {
    tabChat.addEventListener('click', () => {
      syncActiveProjectIndicator();
    });
  }

  const chatForm = $('chatForm');
  const promptInput = $('promptInput');
  const sendBtn = $('sendBtn');
  const stopBtn = $('stopBtn');
  let activeAbortController = null;
  const verifyToggle = $('verifyToggle');
  const approvalToggle = $('approvalToggle');
  const goalBadge = $('goalBadge');
  const jobPhaseStatusStrip = $('jobPhaseStatusStrip');
  const trainAgentTargetSelect = $('trainAgentTargetSelect');

  let jobPhaseState = null;
  let inlineJobChromeModel = null;

  function resetJobPhaseStrip() {
    jobPhaseState = null;
    if (jobPhaseStatusStrip) jobPhaseStatusStrip.classList.add('hidden');
    if (goalBadge && typeof goalBadge.classList?.add === 'function') goalBadge.classList.add('hidden');
  }

  function renderJobPhaseStrip() {
    if (!jobPhaseStatusStrip) return;
    if (state.selectedAgentId === 'direct') {
      syncChatJobViewButton(jobPhaseStatusStrip, '');
      jobPhaseStatusStrip.classList.add('hidden');
      return;
    }
    const boundJobId = (jobPhaseState && (jobPhaseState.jobId || jobPhaseState.job_id)) || '';
    if (!boundJobId) {
      syncChatJobViewButton(jobPhaseStatusStrip, '');
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
    if (jobIdEl) { jobIdEl.textContent = boundJobId; jobIdEl.classList.remove('hidden'); }
    if (copyJobBtn) { copyJobBtn.dataset.jobId = boundJobId; copyJobBtn.classList.remove('hidden'); }
    syncChatJobViewButton(jobPhaseStatusStrip, boundJobId);
    if (phaseEl) { phaseEl.textContent = view.phaseLabel || 'Phase'; phaseEl.classList.toggle('hidden', !view.phaseLabel); }
    if (agentEl) { agentEl.textContent = view.agentLabel || ''; agentEl.classList.toggle('hidden', !view.agentLabel); }
    if (reactEl) { reactEl.textContent = view.reactState || ''; reactEl.className = reactStateToneClass(view.reactState); }
    jobPhaseStatusStrip.classList.remove('hidden');
    if (linkEl) { linkEl.textContent = view.parentChildLabel || ''; linkEl.classList.toggle('hidden', !view.parentChildLabel); }
  }

  if (jobPhaseStatusStrip && !jobPhaseStatusStrip.dataset.copyJobBound) {
    jobPhaseStatusStrip.dataset.copyJobBound = '1';
    jobPhaseStatusStrip.addEventListener('click', (ev) => {
      const btn = ev.target && ev.target.closest ? ev.target.closest('[data-job-phase="copy-job-id"]') : null;
      if (!btn) return;
      const id = btn.dataset.jobId || (jobPhaseState && jobPhaseState.jobId) || '';
      if (!id) return;
      copyToClipboard(id);
      showToast(`Copied ${id}`, 'success');
    });
  }

  bindChatJobViewShortcut(jobPhaseStatusStrip, {
    switchTab: callbacks.switchTab,
  });

  function updateJobPhaseFromEvent(eventType, ev) {
    jobPhaseState = applyJobPhaseEvent(jobPhaseState, eventType, ev);
    renderJobPhaseStrip();
    if (goalBadge && typeof goalBadge.classList?.toggle === 'function') {
      const multi = Number(jobPhaseState.phaseCount || 0) > 1;
      goalBadge.classList.toggle('hidden', !multi);
    }
    return true;
  }

  function ensureInlineJobChromeBubble() {
    if (!messagesContainer) return null;
    const streamBubble = messagesContainer.querySelector('[data-stream-bubble="true"]');
    if (streamBubble) return streamBubble;
    let el = messagesContainer.querySelector('[data-job-chrome="inline"]');
    if (!el) {
      el = document.createElement('div');
      el.className = 'flex justify-start w-full my-2 animate-fade-in';
      el.setAttribute('data-job-chrome', 'inline');
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
        if (existing) {
          if (existing.getAttribute && existing.getAttribute('data-stream-bubble') === 'true') {
            const phasesEl = existing.querySelector('.job-chrome-phases, [data-job-chrome-phases="1"]');
            if (phasesEl && typeof phasesEl.classList?.add === 'function') phasesEl.classList.add('hidden');
          } else {
            existing.remove();
          }
        }
      }
      return null;
    }
    const el = ensureInlineJobChromeBubble();
    if (!el) return null;
    if (el.getAttribute && el.getAttribute('data-stream-bubble') === 'true') {
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
    return paintInlineJobChrome();
  }

  function updateJobChromeFromEvent(eventType, ev) {
    updateJobPhaseFromEvent(eventType, ev);
    const type = String(eventType || '');
    if (
      isJobPhaseChromeEvent(type)
      || type === 'step_start'
      || type === 'step_complete'
      || type === 'turn_done'
      || type === 'tool_execution_start'
      || type === 'tool_execution_complete'
    ) {
      inlineJobChromeModel = applyInlineJobChromeModel(inlineJobChromeModel, type, ev);
      paintInlineJobChrome();
      return true;
    }
    return false;
  }

  function resetInlineJobChrome() {
    inlineJobChromeModel = null;
    if (!messagesContainer) return;
    messagesContainer.querySelectorAll('[data-job-chrome="inline"]').forEach((el) => {
      if (el.getAttribute && el.getAttribute('data-stream-bubble') !== 'true') {
        el.remove();
      }
    });
  }

  // Pending HITL Approvals [CARD-295, CARD-343]
  const pendingHitl = setupPendingHitl(state, messagesContainer, { pendingHitlHost: $('pendingHitlHost'), onResumeTurn: executeChatTurn });
  const refreshPendingHitl = pendingHitl.refreshPendingHitl;

  // Agents & Engine Selection
  async function loadAgents() {
    try {
      const res = await fetch('/api/agents');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      publishAgentsLoaded(await res.json());

      if (trainAgentTargetSelect) {
        populateTrainAgentTargetOptions(trainAgentTargetSelect, state.agents, state.selectedAgentId || 'autoreiv');
      }

      updateActiveAgentHeader();
      await loadSessions();
      await refreshPendingHitl();
      await syncActiveProjectIndicator();
      safeCreateIcons();
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load agents:', err);
    }
  }

  function updateEngineSelectorUi(activeId) {
    if (agentSelect && agentSelect.value !== activeId) {
      agentSelect.value = activeId;
    }
    const isDirect = activeId === 'direct';
    if (jobPhaseStatusStrip && isDirect) {
      jobPhaseStatusStrip.classList.add('hidden');
    }
  }

  async function switchSelectedAgent(agentId) {
    if (!agentId) return;
    state.selectedAgentId = agentId;
    storageSet('autoreiv_active_agent_id', agentId);
    updateEngineSelectorUi(agentId);
    updateActiveAgentHeader();

    const sidebar = $('sidebar');
    if (isMobile() && sidebar) {
      sidebar.classList.add('-translate-x-full');
    }

    await loadSessions();
    await refreshPendingHitl();
    await syncActiveProjectIndicator();
  }

  async function syncActiveProjectIndicator() {
    if (!chatActiveProjectPill || !chatActiveProjectName) return;
    try {
      const res = await fetch('/api/projects/selected');
      if (!res.ok) {
        chatActiveProjectPill.classList.add('hidden');
        chatActiveProjectPill.classList.remove('inline-flex');
        return;
      }
      const data = await res.json();
      const proj = data && data.selected;
      const isDeveloper = state.selectedAgentId === 'developer';
      if (isDeveloper && proj && (proj.slug || proj.name || proj.path)) {
        chatActiveProjectName.textContent = proj.slug || proj.name || 'active project';
        chatActiveProjectPill.classList.remove('hidden');
        chatActiveProjectPill.classList.add('inline-flex');
      } else {
        chatActiveProjectPill.classList.add('hidden');
        chatActiveProjectPill.classList.remove('inline-flex');
      }
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to sync active project pill:', err);
      chatActiveProjectPill.classList.add('hidden');
      chatActiveProjectPill.classList.remove('inline-flex');
    }
  }

  async function switchEngineChannel(engineId) {
    if (!engineId) return;
    updateEngineSelectorUi(engineId);
    await switchSelectedAgent(engineId);
    if (engineId === 'direct') {
      resetJobPhaseStrip();
    }
  }

  function updateActiveAgentHeader() {
    const curAgent = (state.agents || []).find((a) => a.id === state.selectedAgentId);
    if (activeAgentTitle) {
      activeAgentTitle.textContent = curAgent ? curAgent.name : (state.selectedAgentId || 'AutoReiv');
    }
    if (activeAgentTone) {
      activeAgentTone.textContent = curAgent && curAgent.role ? curAgent.role : 'Autonomous Multi-Agent Orchestrator';
    }
  }

  if (agentSelect) {
    agentSelect.addEventListener('change', (e) => {
      switchSelectedAgent(e.target.value);
    });
  }

  // Sessions and Messages Management via Submodules
  async function loadSessions() {
    await trackSessionsLoad(state, loadSessionsDirect(state, {
      sessionList,
      onSelectSession: selectSession,
      createNewSessionFn: createNewSession, // CARD-476: an agent with no chats gets one (pre-split)
      showToastFn: showToast,
    }));
  }

  const ensureSession = () => ensureActiveSession(state, { createNewSession, showToastFn: showToast });
  const sessionSelect = createSessionSelect(state, { // CARD-485: list, drawer, journey strip, running status
    sessionList, onSelectSession: selectSession, chatSessionsDrawer, viewChat, sendBtn, stopBtn,
    loadMessages, refreshPendingHitl, refreshWorkbenchArtifactCount, jumpToLatest: jumpMessagesToLatest,
    setJobPhaseState: (next) => { jobPhaseState = next; renderJobPhaseStrip(); },
    setInlineJobChromeModel: (model) => { inlineJobChromeModel = model; remountInlineJobChrome(); },
  });

  async function createNewSession() {
    await singleFlight(state, 'sessionCreating', () => createNewSessionDirect(state, {
      sessionList,
      messagesContainer,
      onSelectSession: selectSession,
      showToastFn: showToast,
      resetJobPhaseStrip,
      resetInlineJobChrome,
      refreshPendingHitl,
      refreshWorkbenchArtifactCount,
    }), state.selectedAgentId);
  }

  async function selectSession(sessionId, { userPick = false } = {}) {
    if (!sessionId) return;
    state.activeSessionId = sessionId;
    storageSet(LAST_SESSION_KEY, sessionId);
    resetJobPhaseStrip();
    resetInlineJobChrome();
    await sessionSelect.afterSelect(sessionId, { userPick });
  }

  async function loadMessages(sessionId) {
    if (!messagesContainer || !sessionId) return;
    try {
      const res = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/messages`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (state.activeSessionId !== sessionId) return;
      state.messages = Array.isArray(data) ? data : (data.messages || []);
      renderMessagesDirect({
        messagesContainer,
        messages: state.messages,
        isStreaming: state.isStreaming,
        activeAgentTitle,
        renderMarkdownFn: renderMarkdown,
        openWorkbenchFn: openWorkbench,
        onRefreshWorkbench: refreshWorkbenchArtifactCount,
        onTeachAgent: teachAgentModalCtrl.openTeachAgentModal,
        exportMessageToWikiFn: callbacks.exportMessageToWiki || null,
        maybeAutoscrollMessagesFn: maybeAutoscrollMessages,
      });
      maybeAutoscrollMessages();
    } catch (e) {
      console.warn('Failed to load messages:', e);
    }
  }

  // Dual-Pane Workbench Canvas [CARD-138, CARD-306] /api/sessions/ /api/artifacts/
  const workbench = initWorkbench(state, { showToastFn: showToast });
  function openWorkbench(artifact = {}) {
    return workbench.openWorkbench(artifact);
  }
  function closeWorkbench() {
    return workbench.closeWorkbench();
  }
  function refreshWorkbenchArtifactCount() {
    return refreshWorkbenchArtifactCountDirect(state.activeSessionId);
  }

  // Composer sizing: grows on focus up to min(8 lines, 40% of visible column) [CARD-465]
  setupComposerSizing({
    promptInput,
    columnEl: $('chatMessagesViewport')?.parentElement || null,
    messagesContainer,
    composerRegion: $('chatInputWrapper'),
    pressRegions: [$('pendingHitlHost')], // CARD-470
    isStickToBottom,
  });

  // Composer paperclip + Enter-to-send on the real template IDs [CARD-469]
  wireComposer(state, { chatForm, promptInput, showToastFn: showToast, onBeforeAttach: () => { closeChatOptionsDrawer(); return ensureSession(); } });
  setupRuntimeModeToggles(state, { approvalToggle, verifyToggle, approvalBadge: $('approvalBadge'), verifyBadge: $('verifyBadge') }); // CARD-470

  // Train Modal [CARD-119, CARD-165, CARD-306]
  setupTrainModal(state, {
    trainAgentTargetSelect,
    showToastFn: showToast,
    onJobSubmitted: loadAgents,
  });

  // Teach Agent Modal [CARD-352, REQ-SKIL-011]
  const teachAgentModalCtrl = setupTeachAgentModal(state, {}, {
    showToastFn: showToast,
    callbacks,
    messagesContainer,
  });

  // Chat Chrome, Options Drawer, Diagnostics & Quick Prompts [CARD-135, CARD-136, CARD-152, CARD-161]
  // REQ-JOBMINT-005 journey markers: journey-copy-job-id, data-journey-job-id
  setupChatChrome(state, { promptInput }, {
    showToastFn: showToast,
    callbacks,
    getJobPhaseState: () => jobPhaseState,
  });

  // Click delegation on messages container for handoff cards and laboratory
  setupMessagesContainerDelegation(messagesContainer, {
    callbacks,
    showToast,
    loadAgents,
  });

  // Main chat turn execution and streaming
  async function executeChatTurn(userPrompt, options = {}) {
    sessionSelect.stopWatching(); // CARD-485: this tab's own stream takes over
    resetInlineJobChrome();
    state.isStreaming = true;
    const emptyPlaceholder = messagesContainer?.querySelector('.text-center');
    if (emptyPlaceholder) emptyPlaceholder.remove();
    if (sendBtn) { sendBtn.disabled = true; sendBtn.classList.add('hidden'); }
    if (stopBtn) { stopBtn.disabled = false; stopBtn.classList.remove('hidden'); }

    if (!options.isResume && userPrompt) {
      appendMessageBubbleDirect('user', userPrompt, null, {
        messagesContainer,
        activeAgentId: state.selectedAgentId,
        sessionId: state.activeSessionId,
      });
      state.messages.push({ role: 'user', content: userPrompt });
      maybeAutoscrollMessages();
    }

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
          <button type="button" class="reasoning-toggle flex items-center justify-between w-full px-3 py-2 bg-amber-900/20 text-amber-300 font-semibold cursor-pointer">
            <span class="flex items-center space-x-1.5">
              <span>💭</span>
              <span>Thinking Process</span>
            </span>
            <span class="reasoning-indicator text-[10px] uppercase font-mono">Show</span>
          </button>
          <div class="reasoning-content hidden p-3 font-mono text-[11px] text-amber-100 whitespace-pre-wrap max-h-60 overflow-y-auto"></div>
        </div>
        <div class="stream-content text-sm leading-relaxed prose prose-invert max-w-none text-slate-100 break-words"></div>
        <div class="hitl-approval-card hidden p-3 rounded-xl border border-amber-500/50 bg-amber-950/30 text-slate-200 text-xs space-y-2"></div>
      </div>
    `;

    if (messagesContainer) {
      messagesContainer.appendChild(streamBubble);
      maybeAutoscrollMessages();
    }

    const streamContentEl = streamBubble.querySelector('.stream-content');
    const reasoningDrawer = streamBubble.querySelector('.reasoning-drawer');
    const reasoningContent = streamBubble.querySelector('.reasoning-content');
    const reasoningToggle = streamBubble.querySelector('.reasoning-toggle');
    const reasoningIndicator = streamBubble.querySelector('.reasoning-indicator');
    const toolBadge = streamBubble.querySelector('.tool-status-badge');
    const handoffBadge = streamBubble.querySelector('.handoff-status-badge');
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

    activeAbortController = new AbortController();
    let accumulatedContent = '';
    let accumulatedReasoning = '';
    const outcome = trackStreamOutcome();

    try {
      const payload = buildChatStreamPayload({
        agentId: state.selectedAgentId,
        sessionId: state.activeSessionId,
        content: userPrompt,
        resume: options.isResume,
        selfVerify: verifyToggle ? verifyToggle.checked : false,
        approvalAutoRun: !!approvalToggle?.checked, // CARD-470: checked = run, unchecked = ask
        attachments: [...(state.stagedAttachments || [])],
      });

      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: activeAbortController.signal,
      });

      if (!response.ok) throw new Error(`Stream error: HTTP ${response.status}`);

      clearStagedAttachments(state, $('chatAttachmentsPreviewList'));

      await consumeChatStream(response, {
        onToken: (text) => {
          accumulatedContent += text;
          if (streamContentEl) streamContentEl.textContent = accumulatedContent;
          maybeAutoscrollMessages();
        },
        onReasoning: (text) => {
          accumulatedReasoning += text;
          if (reasoningDrawer && reasoningContent) {
            reasoningDrawer.classList.remove('hidden');
            reasoningContent.textContent = accumulatedReasoning;
          }
          maybeAutoscrollMessages();
        },
        onEvent: (eventType, ev) => {
          outcome.note(eventType, ev);
          updateJobChromeFromEvent(eventType, ev);
          if (isHitlParkSseEvent(eventType, ev)) refreshPendingHitl(); // CARD-470: live Approve/Reject tray

          if (eventType === 'tool_execution_start' && toolBadge) {
            toolBadge.classList.remove('hidden');
            toolBadge.classList.add('flex');
            toolBadge.innerHTML = `<i data-lucide="wrench" class="w-3.5 h-3.5 text-brand-400 animate-spin"></i><span>Using tool: <strong>${escapeHtml(ev.tool_name || 'tool')}</strong></span>`;
            safeCreateIcons();
          } else if (eventType === 'tool_execution_complete' && toolBadge) {
            toolBadge.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400"></i><span>Completed: <strong>${escapeHtml(ev.tool_name || 'tool')}</strong></span>`;
            safeCreateIcons();
          } else if (eventType === 'handoff' && handoffBadge) {
            handoffBadge.classList.remove('hidden');
            handoffBadge.classList.add('flex');
            handoffBadge.innerHTML = renderAgentHandoffCardHtml(ev);
            safeCreateIcons();
          } else if (eventType === 'approval_required') {
            renderInlineHitlCard(hitlCard, ev, { state, onResumeTurn: executeChatTurn, onDone: refreshPendingHitl }); // CARD-470
          } else if (eventType === 'plan_formulated') {
            if (planMilestoneCard && planStepsContainer) {
              planMilestoneCard.classList.remove('hidden');
              const titleEl = planMilestoneCard.querySelector('.plan-goal-title');
              if (titleEl) titleEl.textContent = formatMilestoneGoalTitle(ev.goal);
              if (Array.isArray(ev.steps)) {
                if (planStepCounter) planStepCounter.textContent = `${ev.steps.length} steps`;
                planStepsContainer.innerHTML = ev.steps
                  .map((s, idx) => `<div class="plan-step-item p-2 rounded-lg bg-indigo-950/40 border border-indigo-500/20 text-indigo-300 text-xs" id="plan-step-${idx}">${idx + 1}. ${escapeHtml(s.title || s.name || 'Step')}</div>`)
                  .join('');
              }
            }
          } else if (eventType === 'step_start') {
            const stepEl = streamBubble.querySelector(`#plan-step-${ev.step_index !== undefined ? ev.step_index : -1}`);
            if (stepEl) stepEl.className = 'plan-step-item p-2 rounded-lg bg-indigo-950/60 border border-indigo-500/50 text-indigo-200 ring-1 ring-indigo-500/30 flex items-center justify-between text-xs transition';
          } else if (eventType === 'step_complete') {
            const stepEl = streamBubble.querySelector(`#plan-step-${ev.step_index !== undefined ? ev.step_index : -1}`);
            if (stepEl) stepEl.className = 'plan-step-item p-2 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-emerald-300 flex items-center justify-between text-xs transition';
          } else if (eventType === 'auto_train_progress' && toolBadge) {
            toolBadge.classList.remove('hidden');
            toolBadge.classList.add('flex');
            toolBadge.innerHTML = `<i data-lucide="cpu" class="w-3.5 h-3.5 text-brand-400 animate-spin"></i><span>Training: ${escapeHtml(ev.message || ev.stage || '')}</span>`;
            safeCreateIcons();
          }
        },
      });

      state.messages.push({ role: 'assistant', content: accumulatedContent, reasoning: accumulatedReasoning });
      const streamingBadge = streamBubble.querySelector('.text-brand-400.animate-pulse');
      if (streamingBadge) streamingBadge.remove();

      // CARD-415: finalize onto the same hydrate path as refresh (actions + tool rows + reasoning)
      state.isStreaming = false;
      if (state.activeSessionId) {
        await loadMessages(state.activeSessionId);
      } else if (streamContentEl && accumulatedContent) {
        await renderMarkdown(streamContentEl, accumulatedContent, {
          onOpenArtifact: openWorkbench,
          onRefreshWorkbench: refreshWorkbenchArtifactCount,
        });
        // Promote ephemeral stream bubble → durable assistant bubble with action row
        streamBubble.remove();
        appendMessageBubbleDirect('assistant', accumulatedContent, {
          messageId: null,
          reasoning: accumulatedReasoning || '',
        }, {
          messagesContainer,
          activeAgentTitle,
          renderMarkdownFn: renderMarkdown,
          openWorkbenchFn: openWorkbench,
          onTeachAgent: teachAgentModalCtrl.openTeachAgentModal,
          exportMessageToWikiFn: callbacks.exportMessageToWiki || null,
        });
      }
      reportStreamOutcome(outcome, { messagesContainer, showToastFn: showToast });

      await refreshPendingHitl();
      await refreshWorkbenchArtifactCount();
    } catch (err) {
      if (err.name !== 'AbortError') {
        showToast(`Chat turn failed: ${err.message}`, 'error');
        if (streamContentEl) streamContentEl.innerHTML = `<span class="text-rose-400">Error: ${escapeHtml(err.message)}</span>`;
      }
    } finally {
      state.isStreaming = false;
      activeAbortController = null;
      if (sendBtn) { sendBtn.disabled = false; sendBtn.classList.remove('hidden'); }
      if (stopBtn) { stopBtn.disabled = true; stopBtn.classList.add('hidden'); }
      maybeAutoscrollMessages();
    }
  }

  const stopHandler = createStopHandler(state, { // CARD-486: Stop tells the server to stop
    getController: () => activeAbortController, clearController: () => { activeAbortController = null; },
    stopWatching: sessionSelect.stopWatching, setBusy: sessionSelect.setBusy, sendBtn, stopBtn, loadMessages,
    recheckStatus: sessionSelect.watchSessionStatus, showToast,
  });

  setupComposerControls({
    chatForm,
    promptInput,
    sendBtn,
    stopBtn,
    state,
    onExecuteTurn: executeChatTurn,
    ensureSession,
    onOpenTeachAgent: teachAgentModalCtrl.openTeachAgentModal,
    onCancelStream: stopHandler.stop,
  });

  if (newChatBtn) {
    newChatBtn.addEventListener('click', createNewSession);
  }

  async function startNewAgentAuthoring() {
    state.selectedAgentId = 'autoreiv';
    await createNewSession();
    setComposerText(promptInput, 'I am ready to create a new agent.');
  }

  async function openDeveloperSession(sessionId, composerText = '') {
    const id = String(sessionId || '').trim();
    if (!id) return null;
    state.selectedAgentId = 'developer';
    storageSet('autoreiv_active_agent_id', 'developer');
    updateEngineSelectorUi('developer');
    updateActiveAgentHeader();
    state.activeSessionId = id;
    await loadSessions();
    await selectSession(id);
    const needle = String(composerText || '').trim().slice(0, 80);
    const visible = Boolean(
      needle && (state.messages || []).some((msg) => String((msg && msg.content) || '').includes(needle)),
    );
    if (promptInput) {
      if (!visible && composerText) {
        setComposerText(promptInput, composerText);
      }
      promptInput.focus();
    }
    return id;
  }

  async function resumeParkedJob() {
    if (state.activeSessionId) {
      await refreshPendingHitl();
    }
  }

  // Initial startup
  pendingHitl.startPendingHitlPoll();
  trackSessionsLoad(state, loadAgents()); // CARD-476: an early send waits for the first load
  syncActiveProjectIndicator();

  return {
    loadAgents,
    switchSelectedAgent,
    updateActiveAgentHeader,
    loadSessions,
    createNewSession,
    selectSession,
    loadMessages,
    renderMessages: renderMessagesDirect,
    renderMarkdown,
    openWorkbench,
    closeWorkbench,
    startNewAgentAuthoring,
    openDeveloperSession,
    resumeParkedJob,
    switchEngineChannel,
    syncActiveProjectIndicator,
    updateJobPhaseFromEvent,
    showStandingJob: (job) => {
      const id = String((job && (job.jobId || job.job_id)) || '').trim();
      if (!id) return null;
      updateJobPhaseFromEvent('job_created', {
        job_id: id,
        status: (job && (job.status || job.jobStatus)) || 'queued',
        agent_id: (job && (job.agentId || job.agent_id)) || 'developer',
        phase_name: 'Author',
        phase_count: 1,
        index: 0,
      });
      return { jobId: id, agentId: (job && (job.agentId || job.agent_id)) || 'developer' };
    },
    resetJobPhaseStrip,
    updateJobChromeFromEvent,
    remountInlineJobChrome,
    resetInlineJobChrome,
    refreshWorkbenchArtifactCount,
    watchSessionStatus: (sessionId = state.activeSessionId) => sessionSelect.watchSessionStatus(sessionId), // CARD-485, for CARD-473
    querySessionStatus,
  };
}
