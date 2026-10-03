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
export * from './chat/scroll.js';
export * from './chat/stream.js';
export * from './chat/job_chrome.js';
export * from './chat/journey.js';
export * from './chat/render.js';
export * from './chat/composer.js';
export * from './chat/chrome.js';
export * from './chat/workbench.js';
export * from './chat/teach_modal.js'; // CARD-472
export * from './chat/session_select.js'; // CARD-485 (hydrateJobPhaseStateFromJourney moved here)
export * from './chat/job_strip.js'; // CARD-490: strip model moved out of chat.js

import { setupPendingHitl, renderInlineHitlCard } from './chat/hitl.js'; // CARD-470

import { setupRuntimeModeToggles, setupRunAsJobToggle, setRunAsJob, takeRunAsJob } from './chat/runtime_toggles.js'; // CARD-470, CARD-572
import { setupChatScroll } from './chat/scroll.js';
import { ensureActiveSession, singleFlight, trackSessionsLoad, LAST_SESSION_KEY } from './chat/session_guard.js'; // CARD-476
import { createSessionSelect } from './chat/session_select.js'; // CARD-485
import { createStopHandler } from './chat/stop.js'; // CARD-486
import { createOwnStreamTracker } from './chat/own_stream.js'; // CARD-488
import { sendDeveloperIntent } from './chat/developer_intent.js'; // CARD-497 REQ-497-016
import { handleTurnRunning } from './chat/turn_running.js'; // CARD-530 REQ-530-003
import { showFailedTurn } from './chat/failed_send.js'; // CARD-484: a failed send keeps the typed text
import { createSessionActivityPoller } from './chat/session_activity.js'; // CARD-493
import { formatJobPhaseStrip, reactStateToneClass, isHitlParkSseEvent, applyJobPhaseEvent, isJobPhaseChromeEvent } from './chat/job_strip.js'; // CARD-490

import {
  buildChatStreamPayload,
  consumeChatStream,
  trackStreamOutcome, reportStreamOutcome, // CARD-469: failed replies are shown
  applyQueueNote, // CARD-494: "Waiting for another reply to finish."
  querySessionStatus,
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
  renderSessionList, // CARD-493: re-render markers between list loads
  syncChatJobViewButton,
  bindChatJobViewShortcut,
} from './chat/chrome.js';

import { initWorkbench, collectWorkbenchElements } from './chat/workbench.js';
import { setupTeachAgentModal } from './chat/teach_modal.js'; // CARD-472

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
  const ownStream = createOwnStreamTracker(state, { sendBtn, stopBtn, messagesContainer }); // CARD-488: detached on switch
  const verifyToggle = $('verifyToggle');
  const approvalToggle = $('approvalToggle');
  const runAsJobEls = { runAsJobToggle: $('runAsJobToggle'), runAsJobBadge: $('runAsJobBadge') }; // CARD-572
  const goalBadge = $('goalBadge');
  const jobPhaseStatusStrip = $('jobPhaseStatusStrip');

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
    const resumeBtn = jobPhaseStatusStrip.querySelector('[data-job-phase="resume"]'); // CARD-490
    if (resumeBtn) resumeBtn.classList.toggle('hidden', !(view.stopped && !state.isStreaming && !state.sessionBusy));
  }

  if (jobPhaseStatusStrip && !jobPhaseStatusStrip.dataset.copyJobBound) {
    jobPhaseStatusStrip.dataset.copyJobBound = '1';
    jobPhaseStatusStrip.addEventListener('click', (ev) => {
      const resume = ev.target && ev.target.closest ? ev.target.closest('[data-job-phase="resume"]') : null;
      if (resume) { // CARD-490 REQ-490-002: a resume turn continues the same job id
        if (state.isStreaming || state.sessionBusy || !state.activeSessionId) return;
        if (jobPhaseState) jobPhaseState = { ...jobPhaseState, stopped: false };
        renderJobPhaseStrip();
        void executeChatTurn('', { isResume: true });
        return;
      }
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
    void sessionActivity.kick(); // CARD-493: keep the markers fresh while a chat replies
  }

  const sessionActivity = createSessionActivityPoller(state, { // CARD-493
    onChange: () => renderSessionList({ sessionList, sessions: state.sessions, activeSessionId: state.activeSessionId, onSelectSession: selectSession }),
  });

  // Dual-Pane Workbench Canvas [CARD-138, CARD-306, CARD-472] /api/sessions/ /api/artifacts/
  const workbench = initWorkbench(collectWorkbenchElements(), { renderMarkdownFn: renderChatMarkdown, copyToClipboardFn: copyToClipboard,
    showToastFn: showToast, exportMessageToWikiFn: callbacks.exportMessageToWiki || null, getActiveSessionId: () => state.activeSessionId });
  function openWorkbench(artifact = {}) { return workbench.openWorkbench(artifact); }
  function closeWorkbench() { return workbench.closeWorkbench(); }
  function openArtifactById(id) { return workbench.openArtifactById(id); }
  function refreshWorkbenchArtifactCount() { return workbench.refreshWorkbenchArtifactCount(); }
  function renderChatMarkdown(el, md, opts = {}) { // every chat render opens artifacts the same way
    return renderMarkdown(el, md, { onOpenArtifact: openArtifactById, onRefreshWorkbench: refreshWorkbenchArtifactCount, ...opts });
  }

  const ensureSession = () => ensureActiveSession(state, { createNewSession, showToastFn: showToast });
  const sessionSelect = createSessionSelect(state, { // CARD-485: list, drawer, journey strip, running status
    sessionList, onSelectSession: selectSession, chatSessionsDrawer, viewChat, sendBtn, stopBtn,
    getStreamSessionId: ownStream.sessionId, detachOwnStream: ownStream.detach, // CARD-488
    loadMessages, refreshPendingHitl, refreshWorkbenchArtifactCount, jumpToLatest: jumpMessagesToLatest,
    setJobPhaseState: (next) => { jobPhaseState = next; renderJobPhaseStrip(); },
    setInlineJobChromeModel: (model) => { inlineJobChromeModel = model; remountInlineJobChrome(); },
    refreshActivity: () => sessionActivity.kick(), // CARD-493
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
        renderMarkdownFn: renderChatMarkdown, openWorkbenchFn: openWorkbench,
        onRefreshWorkbench: refreshWorkbenchArtifactCount,
        onTeachAgent: teachAgentModalCtrl.openTeachAgentModal,
        proposalOptions: { sessionId, activeAgentId: state.selectedAgentId, showToastFn: showToast }, // CARD-500
        exportMessageToWikiFn: callbacks.exportMessageToWiki || null,
        maybeAutoscrollMessagesFn: maybeAutoscrollMessages,
      });
      maybeAutoscrollMessages();
    } catch (e) {
      console.warn('Failed to load messages:', e);
    }
  }

  // Composer sizing: grows on focus up to min(8 lines, 40% of visible column) [CARD-465]
  setupComposerSizing({
    promptInput,
    columnEl: $('chatMessagesViewport')?.parentElement || null,
    messagesContainer,
    composerRegion: $('chatInputWrapper'),
    pressRegions: [$('pendingHitlHost'), messagesContainer], // CARD-470; CARD-472: View Full Report / Workbench clicks
    isStickToBottom,
  });

  // Composer paperclip + Enter-to-send on the real template IDs [CARD-469]
  wireComposer(state, { chatForm, promptInput, showToastFn: showToast, onBeforeAttach: () => { closeChatOptionsDrawer(); return ensureSession(); } });
  setupRuntimeModeToggles(state, { approvalToggle, verifyToggle, approvalBadge: $('approvalBadge'), verifyBadge: $('verifyBadge') }); // CARD-470
  setupRunAsJobToggle(state, runAsJobEls); // CARD-572

  // Teach Agent Modal [CARD-352, REQ-SKIL-011]
  const teachAgentModalCtrl = setupTeachAgentModal(state, {}, {
    showToastFn: showToast,
    callbacks,
    messagesContainer,
    openDeveloperSessionFn: openDeveloperSession, // CARD-472: needs-tool proposals open a Developer chat
  });

  // Chat Chrome, Options Drawer, Diagnostics & Quick Prompts [CARD-135, CARD-136, CARD-152, CARD-161]
  // REQ-JOBMINT-005 journey markers: journey-copy-job-id, data-journey-job-id
  setupChatChrome(state, { promptInput }, {
    showToastFn: showToast,
    callbacks,
    getJobPhaseState: () => jobPhaseState,
  });

  // Click delegation on messages container for agent handoff cards
  setupMessagesContainerDelegation(messagesContainer, {
    callbacks,
    showToast,
    loadAgents,
  });

  // Main chat turn execution and streaming
  async function executeChatTurn(userPrompt, options = {}) {
    sessionSelect.stopWatching(); // CARD-485: this tab's own stream takes over
    resetInlineJobChrome();
    const turnCtl = new AbortController();
    const turn = ownStream.begin(state.activeSessionId, turnCtl); // CARD-488: sets state.isStreaming
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

    if (messagesContainer) {
      messagesContainer.appendChild(streamBubble);
      maybeAutoscrollMessages();
    }

    const streamContentEl = streamBubble.querySelector('.stream-content');
    const queueNoteEl = streamBubble.querySelector('.stream-queue-note'); // CARD-494
    const reasoningDrawer = streamBubble.querySelector('.reasoning-drawer');
    const reasoningContent = streamBubble.querySelector('.reasoning-content');
    const reasoningToggle = streamBubble.querySelector('.reasoning-toggle');
    const reasoningIndicator = streamBubble.querySelector('.reasoning-indicator');
    const toolBadge = streamBubble.querySelector('.tool-status-badge');
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

    let accumulatedContent = '';
    let accumulatedReasoning = '';
    const outcome = trackStreamOutcome();

    // CARD-572: Run as a job applies to this one send, then the box unticks.
    const runAsJob = options.isResume ? false : takeRunAsJob(state, runAsJobEls);
    try {
      const payload = buildChatStreamPayload({
        agentId: state.selectedAgentId,
        sessionId: state.activeSessionId,
        content: userPrompt,
        resume: options.isResume,
        runAsJob,
        selfVerify: verifyToggle ? verifyToggle.checked : false,
        approvalAutoRun: !!approvalToggle?.checked, // CARD-470: checked = run, unchecked = ask
        attachments: [...(state.stagedAttachments || [])],
      });

      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: turnCtl.signal,
      });

      // CARD-530 REQ-530-003: a 409 turn_running is a gentle notice (chat/turn_running.js), not a failure.
      if (response.status === 409 && runAsJob) setRunAsJob(state, true, runAsJobEls); // refused send keeps the box
      if (response.status === 409) return handleTurnRunning({ state, streamBubble, isResume: options.isResume, userPrompt, restoreComposer: (t) => promptInput && setComposerText(promptInput, t), showToast, loadMessages });
      if (!response.ok) throw new Error(`Stream error: HTTP ${response.status}`);

      clearStagedAttachments(state, $('chatAttachmentsPreviewList'));
      void sessionActivity.kick(); // CARD-493: this chat now shows Replying in Recent Chats

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
          applyQueueNote(queueNoteEl, eventType); // CARD-494
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
          }
        },
      });

      if (!ownStream.isCurrent(turn)) return; // CARD-488: detached; the chat on screen is another one
      state.messages.push({ role: 'assistant', content: accumulatedContent, reasoning: accumulatedReasoning });
      const streamingBadge = streamBubble.querySelector('.text-brand-400.animate-pulse');
      if (streamingBadge) streamingBadge.remove();

      // CARD-415: finalize onto the same hydrate path as refresh (actions + tool rows + reasoning)
      state.isStreaming = false;
      if (state.activeSessionId) {
        await loadMessages(state.activeSessionId);
      } else if (streamContentEl && accumulatedContent) {
        await renderChatMarkdown(streamContentEl, accumulatedContent);
        // Promote ephemeral stream bubble → durable assistant bubble with action row
        streamBubble.remove();
        appendMessageBubbleDirect('assistant', accumulatedContent, {
          messageId: null,
          reasoning: accumulatedReasoning || '',
        }, {
          messagesContainer,
          activeAgentTitle,
          renderMarkdownFn: renderChatMarkdown,
          openWorkbenchFn: openWorkbench,
          onTeachAgent: teachAgentModalCtrl.openTeachAgentModal,
          exportMessageToWikiFn: callbacks.exportMessageToWiki || null,
        });
      }
      if (ownStream.isCurrent(turn)) reportStreamOutcome(outcome, { messagesContainer, showToastFn: showToast });

      await refreshPendingHitl();
      await refreshWorkbenchArtifactCount();
    } catch (err) {
      if (err.name !== 'AbortError' && ownStream.isCurrent(turn)) {
        showFailedTurn({ err, showToast, streamContentEl, streamBubble, isResume: options.isResume, userPrompt, replyStarted: accumulatedContent.length > 0, promptInput, setText: setComposerText }); // CARD-484
      }
    } finally {
      if (ownStream.end(turn)) { // CARD-488: a detached turn leaves the view alone
        if (sendBtn) { sendBtn.disabled = false; sendBtn.classList.remove('hidden'); }
        if (stopBtn) { stopBtn.disabled = true; stopBtn.classList.add('hidden'); }
        maybeAutoscrollMessages();
      }
    }
  }

  const stopHandler = createStopHandler(state, { // CARD-486: Stop tells the server to stop
    getController: ownStream.controller, clearController: ownStream.detach, getStreamSessionId: ownStream.sessionId, // CARD-488
    stopWatching: sessionSelect.stopWatching, setBusy: sessionSelect.setBusy, sendBtn, stopBtn, loadMessages,
    recheckStatus: sessionSelect.watchSessionStatus, showToast,
    afterStop: async (sessionId) => { // CARD-490: Resume on a stopped job; CARD-493: list markers
      if (state.activeSessionId === sessionId) await sessionSelect.rehydrateJobChrome(sessionId);
      void sessionActivity.kick();
    },
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

  // CARD-571: Ask Developer chats belong to Toolsmith; the agent comes from the Talk reply.
  async function openDeveloperSession(sessionId, composerText = '', agentId = 'toolsmith') {
    const id = String(sessionId || '').trim();
    if (!id) return null;
    const agent = String(agentId || 'toolsmith');
    state.selectedAgentId = agent;
    storageSet('autoreiv_active_agent_id', agent);
    updateEngineSelectorUi(agent);
    updateActiveAgentHeader();
    state.activeSessionId = id;
    await loadSessions();
    await selectSession(id);
    // CARD-497 REQ-497-016: a real send - the Toolsmith reply starts now, as if typed and Enter pressed.
    const outcome = sendDeveloperIntent({
      sessionId: id,
      prompt: composerText,
      state,
      send: (text) => {
        if (promptInput) setComposerText(promptInput, '');
        return executeChatTurn(text);
      },
      fillComposer: (text) => { if (promptInput) setComposerText(promptInput, text); },
      toast: showToast,
    });
    if (promptInput && outcome.status !== 'sent') promptInput.focus();
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
