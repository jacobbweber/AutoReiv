/**
 * Chat Studio Module [REQ-FE-001, REQ-WEB-001, REQ-WEB-002]
 */

import { $, safeCreateIcons } from '../dom.js';
import { escapeHtml, formatJsonDeliverableToMarkdown } from '../utils/formatters.js';
import { copyToClipboard } from '../utils/clipboard.js';
import { storageGet, storageSet } from '../utils/storage.js';
import { showToast } from '../ui/toast.js';


function formatHitlArgs(args) {
  try {
    const text = JSON.stringify(args || {}, null, 2);
    return text.length > 800 ? `${text.slice(0, 800)}…` : text;
  } catch {
    return String(args || "");
  }
}


export function isGoalPlanReviewTool(toolName) {
  return String(toolName || "") === "goal_plan_review";
}

export function isAgentVisibleInChat(agent) {
  if (agent == null) return true;
  return agent.show_in_chat !== false;
}

export function agentsVisibleInChat(agents) {
  return (agents || []).filter(isAgentVisibleInChat);
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
    next.jobStatus = next.jobStatus || "waiting_approval";
    next.reactState = next.reactState || "PARKED";
  } else if (eventType === "approval_required") {
    next.reactState = data.react_state || next.reactState || "PARKED";
    next.jobStatus = data.job_status || next.jobStatus || "waiting_approval";
  }
  return next;
}


export const WORKFLOW_PICKER_EMPTY_LABEL = "No workflows yet";

export function buildChatStreamPayload({
  agentId,
  sessionId,
  content = "",
  resume = false,
  goalMode = false,
  selfVerify = false,
  approvalAutoRun = false,
  workflowId = "",
}) {
  const isResume = Boolean(resume);
  return {
    agent_id: agentId,
    session_id: sessionId,
    content: isResume ? "" : content,
    resume: isResume,
    goal_mode: isResume ? false : !!goalMode,
    self_verify: isResume ? false : !!selfVerify,
    approval_mode: approvalAutoRun ? "run" : "ask",
    workflow_id: isResume ? "" : String(workflowId || "").trim(),
  };
}

export function workflowPickerOptionsHtml(workflows) {
  const items = Array.isArray(workflows) ? workflows : [];
  if (!items.length) {
    return `<option value="">${WORKFLOW_PICKER_EMPTY_LABEL}</option>`;
  }
  const opts = ['<option value="">No workflow (plain chat)</option>'];
  items.forEach((wf) => {
    const id = String((wf && wf.id) || "");
    const name = String((wf && wf.name) || id);
    opts.push(`<option value="${id}">${name}</option>`);
  });
  return opts.join("");
}

export function canSaveJobAsWorkflow(phaseCount) {
  return Number(phaseCount || 0) >= 2;
}

export function pendingApprovalsUrl(agentId) {
  const id = String(agentId || "").trim();
  if (!id) return "/api/approvals/pending";
  return `/api/approvals/pending?agent_id=${encodeURIComponent(id)}`;
}

export function pendingHitlLabel(approval) {
  if (!approval || !approval.routine_id) {
    return "Approval required";
  }
  const name = String(approval.routine_name || "").trim();
  return name ? `Routine: ${name}` : "Routine";
}

export function shouldResumeChatAfterHitl({ approvalSessionId, openSessionId, backendResumed }) {
  if (backendResumed) return false;
  const approvalSid = String(approvalSessionId || "").trim();
  const openSid = String(openSessionId || "").trim();
  if (!approvalSid || !openSid) {
    return Boolean(openSid);
  }
  return approvalSid === openSid;
}

export function buildHitlCardInnerHtml({ title, toolName, message, argsText }) {
  return `
    <div class="font-semibold text-amber-200">${escapeHtml(title || "Approval required")}</div>
    <div class="text-slate-300">Tool: <strong class="text-white">${escapeHtml(toolName || "tool")}</strong></div>
    <div class="text-slate-400">${escapeHtml(message || "Waiting for operator approval")}</div>
    <pre class="text-[11px] font-mono whitespace-pre-wrap text-slate-300 bg-slate-950/40 p-2 rounded border border-slate-800 max-h-32 overflow-y-auto">${escapeHtml(argsText || "")}</pre>
    <div class="flex items-center space-x-2 pt-1">
      <button type="button" data-hitl-decision="APPROVED" class="px-2.5 py-1 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold">Approve</button>
      <button type="button" data-hitl-decision="REJECTED" class="px-2.5 py-1 rounded-lg bg-rose-800 hover:bg-rose-700 text-white text-xs font-semibold">Reject</button>
      <span class="hitl-card-status text-amber-200"></span>
    </div>
  `;
}

async function submitHitlDecision(approvalId, decision, cardEl, sessionId) {
  const buttons = cardEl.querySelectorAll("[data-hitl-decision]");
  buttons.forEach((btn) => {
    btn.disabled = true;
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
    cardEl.classList.remove("border-amber-500/30", "bg-amber-950/20");
    if (decision === "APPROVED") {
      cardEl.classList.add("border-emerald-500/30", "bg-emerald-950/20");
    } else {
      cardEl.classList.add("border-rose-500/30", "bg-rose-950/20");
    }
    const output = body.execution ? body.execution.output : null;
    if (output != null) {
      const pre = document.createElement("pre");
      pre.className =
        "mt-2 text-[11px] font-mono whitespace-pre-wrap text-slate-300 bg-slate-950/40 p-2 rounded border border-slate-800 max-h-40 overflow-y-auto";
      pre.textContent = typeof output === "string" ? output : JSON.stringify(output, null, 2);
      cardEl.appendChild(pre);
    }
    return { ok: true, body };
  } catch (err) {
    buttons.forEach((btn) => {
      btn.disabled = false;
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
  const copyThreadBtn = $('copyThreadBtn');
  const exportThreadWikiBtn = $('exportThreadWikiBtn');
  const verifyToggle = $('verifyToggle');
  const approvalToggle = $('approvalToggle');
  const approvalBadge = $('approvalBadge');
  const verifyBadge = $('verifyBadge');
  const goalToggle = $('goalToggle');
  const goalBadge = $('goalBadge');
  const workflowPicker = $('workflowPicker');
  const saveAsWorkflowBtn = $('saveAsWorkflowBtn');
  let lastSaveableJobId = '';
  let lastSaveablePhaseCount = 0;
  const pendingHitlHost = $('pendingHitlHost');

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
  }

  const PENDING_HITL_POLL_MS = 12000;
  let pendingHitlTimer = null;

  async function refreshPendingHitl() {
    const agentId = state.selectedAgentId;
    if (!agentId || !pendingHitlHost) return;
    try {
      const res = await fetch(pendingApprovalsUrl(agentId));
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

      updateActiveAgentHeader();
      await loadWorkflowPicker();
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
    await loadWorkflowPicker();

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
      item.className = `p-2 rounded-lg cursor-pointer text-xs flex items-center justify-between transition ${
        isActive
          ? 'bg-slate-800 text-white font-medium border border-slate-700'
          : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
      }`;
      item.innerHTML = `
        <span class="truncate max-w-[170px]">${escapeHtml(sess.title)}</span>
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
    state.activeSessionId = sessionId;
    resetJobPhaseStrip();
    renderSessionList();
    await loadMessages(sessionId, { force: true });
    await refreshPendingHitl();
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

  function appendMessageBubble(role, content, _msgIdx = null) {
    if (!messagesContainer) return;

    const isUser = role.toLowerCase() === 'user';
    const bubble = document.createElement('div');
    bubble.className = `flex ${isUser ? 'justify-end' : 'justify-start'} w-full`;

    const copyBtnHtml = !isUser
      ? `
      <div class="flex items-center space-x-2 mt-2 pt-2 border-t border-slate-700/50 text-[11px] text-slate-400">
        <button class="copy-msg-btn flex items-center space-x-1 hover:text-white transition" data-content="${escapeHtml(content)}">
          <i data-lucide="copy" class="w-3 h-3"></i>
          <span>Copy</span>
        </button>
        <button class="wiki-msg-btn flex items-center space-x-1 hover:text-indigo-300 text-indigo-400 transition" data-content="${escapeHtml(content)}">
          <i data-lucide="book-open" class="w-3 h-3"></i>
          <span>Save to Wiki</span>
        </button>
      </div>
    `
      : '';

    bubble.innerHTML = `
      <div class="max-w-2xl rounded-2xl p-4 shadow-sm ${
        isUser
          ? 'bg-brand-600 text-white rounded-br-none'
          : 'bg-slate-900 border border-slate-800 text-slate-100 rounded-bl-none'
      }">
        <div class="text-xs font-bold uppercase tracking-wider mb-1 opacity-70">
          ${isUser ? 'You' : escapeHtml(activeAgentTitle ? activeAgentTitle.textContent : 'Agent')}
        </div>
        <div class="msg-body prose prose-invert text-sm break-words leading-relaxed">
        </div>
        ${copyBtnHtml}
      </div>
    `;

    messagesContainer.appendChild(bubble);
    const bodyEl = bubble.querySelector('.msg-body');
    renderMarkdown(bodyEl, content || '');

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

  if (goalToggle) {
    goalToggle.addEventListener('change', (e) => {
      state.goalEnabled = e.target.checked;
      if (goalBadge) goalBadge.classList.toggle('hidden', !state.goalEnabled);
    });
  }

  async function loadWorkflowPicker() {
    if (!workflowPicker) return;
    const agentId = state.selectedAgentId;
    if (!agentId) {
      workflowPicker.innerHTML = workflowPickerOptionsHtml([]);
      workflowPicker.disabled = true;
      return;
    }
    try {
      const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/workflows`);
      const items = res.ok ? await res.json() : [];
      const list = Array.isArray(items) ? items : [];
      workflowPicker.innerHTML = workflowPickerOptionsHtml(list);
      workflowPicker.disabled = list.length === 0;
    } catch (err) {
      console.warn('[AutoReiv UI] Failed to load workflows:', err);
      workflowPicker.innerHTML = workflowPickerOptionsHtml([]);
      workflowPicker.disabled = true;
    }
  }

  function setSaveAsWorkflowVisible(jobId, phaseCount) {
    lastSaveableJobId = jobId || '';
    lastSaveablePhaseCount = Number(phaseCount || 0);
    if (saveAsWorkflowBtn) {
      saveAsWorkflowBtn.classList.toggle('hidden', !canSaveJobAsWorkflow(lastSaveablePhaseCount) || !lastSaveableJobId);
    }
  }

  if (saveAsWorkflowBtn) {
    saveAsWorkflowBtn.addEventListener('click', async () => {
      if (!canSaveJobAsWorkflow(lastSaveablePhaseCount) || !lastSaveableJobId || !state.selectedAgentId) return;
      const name = window.prompt('Name this workflow (chapter list only, not the chat transcript)');
      if (!name || !name.trim()) return;
      try {
        const res = await fetch(`/api/agents/${encodeURIComponent(state.selectedAgentId)}/workflows/from-job`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name.trim(), job_id: lastSaveableJobId, session_id: state.activeSessionId }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const chapters = (data.workflow && data.workflow.chapters) || [];
        showToast(`Saved ${chapters.length} chapter${chapters.length === 1 ? '' : 's'} (not the chat transcript).`);
        await loadWorkflowPicker();
        if (workflowPicker && data.workflow && data.workflow.id) {
          workflowPicker.value = data.workflow.id;
          workflowPicker.disabled = false;
        }
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save workflow:', err);
        showToast('Could not save workflow.');
      }
    });
  }

  // Chat Submission & Streaming
  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = promptInput ? promptInput.value.trim() : '';
      if (!text || state.isStreaming) return;

      if (!state.activeSessionId) {
        await createNewSession();
      }

      appendMessageBubble('user', text);
      if (promptInput) promptInput.value = '';
      if (messagesContainer) messagesContainer.scrollTop = messagesContainer.scrollHeight;

      await executeChatTurn(text);
    });
  }

  async function executeChatTurn(userPrompt, options = {}) {
    const resume = Boolean(options && options.resume);
    if (state.activeSessionId && !resume) {
      await loadMessages(state.activeSessionId, { force: true });
    }
    state.isStreaming = true;
    if (sendBtn) sendBtn.disabled = true;

    const streamBubble = document.createElement('div');
    streamBubble.className = 'flex justify-start w-full';
    streamBubble.innerHTML = `
      <div class="max-w-2xl w-full rounded-2xl p-4 shadow-sm bg-slate-900 border border-slate-800 text-slate-100 rounded-bl-none space-y-3">
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
        body: JSON.stringify(buildChatStreamPayload({
          agentId: state.selectedAgentId,
          sessionId: state.activeSessionId,
          content: userPrompt,
          resume,
          goalMode: !!state.goalEnabled,
          selfVerify: !!state.verifyEnabled,
          approvalAutoRun: state.approvalAutoRun,
          workflowId: workflowPicker ? workflowPicker.value : "",
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

            if (eventType === 'job_created' || eventType === 'plan_formulated') {
              const phaseCount = ev.phase_count != null ? ev.phase_count : (Array.isArray(ev.steps) ? ev.steps.length : 0);
              setSaveAsWorkflowVisible(ev.job_id || lastSaveableJobId, phaseCount);
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
                      <button type="button" data-hitl-decision="APPROVED" class="px-2.5 py-1 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-semibold">Approve</button>
                      <button type="button" data-hitl-decision="REJECTED" class="px-2.5 py-1 rounded-lg bg-rose-800 hover:bg-rose-700 text-white text-xs font-semibold">Reject</button>
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
            } else if (eventType === 'reflexion_attempt') {
              if (reflexionStatusBadgeEl) {
                reflexionStatusBadgeEl.classList.remove('hidden');
                reflexionStatusBadgeEl.classList.add('flex');
                reflexionStatusBadgeEl.className = 'reflexion-status-badge p-2 rounded-lg bg-amber-950/40 border border-amber-500/30 text-xs text-amber-300 flex items-center space-x-2';
                reflexionStatusBadgeEl.innerHTML = `<span>🔍</span><span>Reflexion Check: <strong>Attempt ${ev.attempt || 1}/${ev.max_attempts || 3}</strong>...</span>`;
              }
            } else if (eventType === 'reflexion_critique') {
              if (reflexionStatusBadgeEl) {
                reflexionStatusBadgeEl.classList.remove('hidden');
                reflexionStatusBadgeEl.classList.add('flex');
                reflexionStatusBadgeEl.className = 'reflexion-status-badge p-2 rounded-lg bg-amber-950/60 border border-amber-500/50 text-xs text-amber-200 flex items-center space-x-2';
                reflexionStatusBadgeEl.innerHTML = `<span>⚠️</span><span>Critique: <strong class="text-amber-100">${escapeHtml(ev.critique || 'Refining output...')}</strong></span>`;
              }
            } else if (eventType === 'reflexion_verified') {
              if (reflexionStatusBadgeEl) {
                reflexionStatusBadgeEl.classList.remove('hidden');
                reflexionStatusBadgeEl.classList.add('flex');
                if (ev.passed) {
                  reflexionStatusBadgeEl.className = 'reflexion-status-badge p-2 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-xs text-emerald-300 flex items-center space-x-2';
                  reflexionStatusBadgeEl.innerHTML = `<span>✅</span><span>Self-Verification <strong>Passed</strong>!</span>`;
                } else {
                  const status = ev.status || 'unverified';
                  reflexionStatusBadgeEl.className = 'reflexion-status-badge p-2 rounded-lg bg-rose-950/40 border border-rose-500/30 text-xs text-rose-300 flex items-center space-x-2';
                  reflexionStatusBadgeEl.innerHTML = `<span>❌</span><span>Self-Verification <strong>Failed</strong> (${status})</span>`;
                }
              }
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
                    })) {
                      await executeChatTurn('', { resume: true });
                    }
                    await refreshPendingHitl();
                  });
                });
              }
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
      if (streamContentEl) {
        streamContentEl.innerHTML += `<p class="text-rose-400 font-mono text-xs mt-2">Error: ${escapeHtml(err.message)}</p>`;
      }
    } finally {
      state.isStreaming = false;
      if (sendBtn) sendBtn.disabled = false;
      if (state.activeSessionId) {
        await loadMessages(state.activeSessionId);
      }
      safeCreateIcons();
    }
  }

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

  // Mobile Tab Visibility & Reconnection Recovery [REQ-MOB-STREAM-002]
  document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState === 'visible' && state.activeSessionId && !state.isStreaming) {
      await loadMessages(state.activeSessionId);
      await refreshPendingHitl();
    }
  });

  window.addEventListener('focus', async () => {
    if (state.activeSessionId && !state.isStreaming) {
      await loadMessages(state.activeSessionId);
      await refreshPendingHitl();
    }
  });

  startPendingHitlPoll();
  loadAgents();

  return {
    loadAgents,
    loadSessions,
    switchSelectedAgent,
    updateActiveAgentHeader,
    createNewSession,
    selectSession,
    renderMessages,
    renderMarkdown,
  };
}
