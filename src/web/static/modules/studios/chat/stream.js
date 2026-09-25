/**
 * Chat Studio: Stream Payload & Session Context Submodule [REQ-ARCH-003]
 * Encapsulates stream payload construction, session context queries, compaction, and handoff cards.
 */

import { escapeHtml } from '../../utils/formatters.js';
import { setComposerText } from './composer.js';

export const AUTOREIV_AGENT_ID = 'autoreiv';
export const NEW_AGENT_STARTER_PROMPT = 'I am ready to create a new agent.';

export function buildChatStreamPayload({
  agentId,
  sessionId,
  content = '',
  resume = false,
  goalMode = false,
  selfVerify = false,
  approvalAutoRun = false,
  attachments = [],
}) {
  const isResume = Boolean(resume);
  void goalMode;
  const payload = {
    agent_id: agentId,
    session_id: sessionId,
    content: isResume ? '' : content,
    resume: isResume,
    goal_mode: false,
    self_verify: isResume ? false : !!selfVerify,
    approval_mode: approvalAutoRun ? 'run' : 'ask',
  };
  if (Array.isArray(attachments) && attachments.length > 0) {
    payload.attachments = attachments;
  }
  return payload;
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
  if (agent.id === 'agent-builder' || agent.id === 'coding' || agent.id === 'review' || agent.id === 'conductor' || agent.id === 'hyperv' || agent.id === 'assistant' || agent.id === 'wiki') return false;
  if (agent.visibility === 'internal') return false;
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
    setComposerText(promptInput, starterPrompt, { focus: true });
  }
  return { filled: true, sent: false, prompt: starterPrompt, agentId };
}

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

export async function consumeChatStream(response, {
  onEvent = null,
  onToken = null,
  onReasoning = null,
} = {}) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = 'message';

  while (true) {
    const { value, done } = await reader.read();
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
        const eventType = ev.type || ev.event || currentEvent;
        const text = ev.text ?? ev.content ?? ev.data ?? '';

        if (eventType === 'token' && onToken) {
          onToken(text, ev);
        } else if (eventType === 'reasoning' && onReasoning) {
          onReasoning(text, ev);
        }

        if (onEvent) {
          onEvent(eventType, ev);
        }
      } catch (pErr) {
        console.warn('[AutoReiv UI] Stream parse error:', pErr);
      }
    }
  }
}
