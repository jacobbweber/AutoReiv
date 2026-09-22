/**
 * Chat Studio: Chrome, Navigation, Options Drawer & Session Shelf Submodule [CARD-136, CARD-150, CARD-161, CARD-397]
 * Manages sessions list, session switching/persistence, options drawer, tools inspector modal, and debug tabs.
 */

import { escapeHtml, formatSessionTimestamp } from '../../utils/formatters.js';
import { $, safeCreateIcons } from '../../dom.js';
import { copyToClipboard } from '../../utils/clipboard.js';
import { filterToolsList, formatContextBudgetBadge, querySessionContext } from './stream.js';
import { loadJourneyTimeline } from './journey.js';

export function renderSessionList({
  sessionList,
  sessions,
  activeSessionId,
  onSelectSession,
} = {}) {
  if (!sessionList) return;
  sessionList.innerHTML = '';
  (sessions || []).forEach((sess) => {
    const item = document.createElement('div');
    const isActive = sess.id === activeSessionId;
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
    item.addEventListener('click', () => {
      if (typeof onSelectSession === 'function') onSelectSession(sess.id);
    });
    sessionList.appendChild(item);
  });
}

export async function loadSessions(arg1 = {}, arg2 = {}) {
  const isDirectState = arg1 && (arg1.selectedAgentId !== undefined || arg1.activeSessionId !== undefined || Array.isArray(arg1.sessions));
  const state = isDirectState ? arg1 : (arg1.state || {});
  const opts = isDirectState ? arg2 : arg1;
  const sessionList = opts.sessionList || null;
  const selectSessionFn = opts.selectSessionFn || opts.onSelectSession || null;
  const createNewSessionFn = opts.createNewSessionFn || null;
  const fetchFn = opts.fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);

  try {
    const exclude = state.activeSessionId ? `&exclude_session_id=${encodeURIComponent(state.activeSessionId)}` : '';
    const agentParam = state.selectedAgentId ? `agent_id=${encodeURIComponent(state.selectedAgentId)}` : 'agent_id=autoreiv';
    const res = await fetchFn(`/api/sessions?${agentParam}${exclude}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    state.sessions = await res.json();
    renderSessionList({
      sessionList,
      sessions: state.sessions,
      activeSessionId: state.activeSessionId,
      onSelectSession: selectSessionFn,
    });
    const stillThere =
      state.activeSessionId &&
      Array.isArray(state.sessions) &&
      state.sessions.some((s) => s.id === state.activeSessionId);
    if (stillThere || state.isStreaming) {
      return;
    }
    if (state.sessions && state.sessions.length > 0) {
      if (typeof selectSessionFn === 'function') await selectSessionFn(state.sessions[0].id);
    } else {
      if (typeof createNewSessionFn === 'function') await createNewSessionFn();
    }
  } catch (err) {
    console.error('[AutoReiv UI] Failed to load sessions:', err);
  }
}

export async function createNewSession(arg1 = {}, arg2 = {}) {
  const isDirectState = arg1 && (arg1.selectedAgentId !== undefined || arg1.activeSessionId !== undefined || Array.isArray(arg1.sessions));
  const state = isDirectState ? arg1 : (arg1.state || {});
  const opts = isDirectState ? arg2 : arg1;
  const selectSessionFn = opts.selectSessionFn || opts.onSelectSession || null;
  const fetchFn = opts.fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);

  const isDirect = state.selectedAgentId === 'direct';
  const agent = (state.agents || []).find((a) => a.id === state.selectedAgentId);
  const title = isDirect ? 'Direct Chat' : `${agent ? agent.name : 'AutoReiv'} Chat`;
  try {
    const res = await fetchFn('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agent_id: state.selectedAgentId || 'autoreiv', title }),
    });
    const sess = await res.json();
    if (!Array.isArray(state.sessions)) state.sessions = [];
    state.sessions.unshift(sess);
    if (typeof selectSessionFn === 'function') await selectSessionFn(sess.id);
    return sess;
  } catch (err) {
    console.error('[AutoReiv UI] Failed to create session:', err);
    return null;
  }
}

export function toggleChatOptionsDrawer(openOrOptions = {}, maybeOptions = {}) {
  const isExplicitBool = typeof openOrOptions === 'boolean';
  const opts = isExplicitBool ? (maybeOptions || {}) : (openOrOptions || {});
  const open = isExplicitBool ? openOrOptions : opts.open;
  const {
    chatOptionsDrawer,
    chatOptionsToggleBtn,
    chatOptionsToggleIcon,
    loadChatSessionContextFn = null,
  } = opts;
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
    if (typeof loadChatSessionContextFn === 'function') {
      loadChatSessionContextFn();
    }
  }
}

export async function loadChatSessionContext(state, {
  chatContextTokensBadge = null,
  chatContextProgressBar = null,
  chatToolsCountBadge = null,
  queryContextFn = querySessionContext,
} = {}) {
  if (!state.activeSessionId) {
    if (chatContextTokensBadge) chatContextTokensBadge.textContent = '0 / 8,192 tokens (0%)';
    if (chatContextProgressBar) chatContextProgressBar.style.width = '0%';
    if (chatToolsCountBadge) chatToolsCountBadge.textContent = '0 tools';
    return null;
  }
  const data = await queryContextFn(state.activeSessionId);
  if (!data) return null;

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
  return data;
}

export function renderToolsModal(cachedSessionContext, {
  chatToolsModalList,
  filter = '',
} = {}) {
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

export function toggleToolsModal({
  chatToolsModal,
  chatToolsModalTitle,
  chatToolsModalBadge,
  cachedSessionContext,
  state,
  open = undefined,
  renderToolsModalFn = null,
} = {}) {
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
    if (typeof renderToolsModalFn === 'function') {
      renderToolsModalFn();
    }
  }
}

export function renderQuickPrompts({
  chatPromptsModalList,
  quickPrompts,
  onSelectPrompt,
} = {}) {
  if (!chatPromptsModalList) return;
  if (!Array.isArray(quickPrompts) || quickPrompts.length === 0) {
    chatPromptsModalList.innerHTML = `
      <div class="text-center py-8 text-slate-500 text-xs">
        <i data-lucide="sparkles" class="w-8 h-8 mx-auto mb-2 opacity-40"></i>
        <p>No quick prompts configured.</p>
      </div>
    `;
    safeCreateIcons();
    return;
  }

  chatPromptsModalList.innerHTML = quickPrompts
    .map(
      (p, idx) => `
      <div class="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-brand-500/50 cursor-pointer transition space-y-1 group" data-prompt-idx="${idx}">
        <div class="flex items-center justify-between">
          <span class="font-semibold text-xs text-slate-200 group-hover:text-brand-300 transition">${escapeHtml(p.title || 'Quick Prompt')}</span>
          <span class="text-[10px] text-slate-500 font-mono uppercase">${escapeHtml(p.category || 'General')}</span>
        </div>
        <p class="text-xs text-slate-400 leading-relaxed line-clamp-2">${escapeHtml(p.prompt || p.content || '')}</p>
      </div>
    `
    )
    .join('');

  chatPromptsModalList.querySelectorAll('[data-prompt-idx]').forEach((el) => {
    el.addEventListener('click', () => {
      const idx = parseInt(el.getAttribute('data-prompt-idx'), 10);
      const item = quickPrompts[idx];
      if (item && typeof onSelectPrompt === 'function') {
        onSelectPrompt(item.prompt || item.content || '');
      }
    });
  });
  safeCreateIcons();
}

export async function loadQuickPrompts({
  chatPromptsModalList,
  onSelectPrompt,
  fetchFn = null,
} = {}) {
  const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
  try {
    const res = await fn('/api/prompts');
    if (!res.ok) return;
    const data = await res.json();
    const list = Array.isArray(data) ? data : (data?.prompts || []);
    renderQuickPrompts({ chatPromptsModalList, quickPrompts: list, onSelectPrompt });
  } catch (err) {
    console.warn('[AutoReiv UI] Failed to load quick prompts:', err);
  }
}

export function renderChatDebugTab({
  chatDebugContent,
  activeDebugData,
  activeDebugTab,
  tabs = {},
} = {}) {
  if (!chatDebugContent || !activeDebugData) return;

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

export async function loadChatDebug(sessionId, {
  chatDebugContent,
  activeDebugTab = 'messages',
  tabs = {},
  fetchFn = null,
} = {}) {
  if (!sessionId || !chatDebugContent) return null;
  const fn = fetchFn || (typeof window !== 'undefined' ? window.fetch : globalThis.fetch);
  chatDebugContent.innerHTML = '<div class="text-slate-400 text-center py-8 animate-pulse">Loading diagnostics...</div>';
  try {
    const res = await fn(`/api/chat/sessions/${encodeURIComponent(sessionId)}/debug`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const activeDebugData = await res.json();
    renderChatDebugTab({
      chatDebugContent,
      activeDebugData,
      activeDebugTab,
      tabs,
    });
    return activeDebugData;
  } catch (err) {
    chatDebugContent.innerHTML = `<div class="p-3 rounded bg-rose-950/40 border border-rose-800 text-rose-300">Failed to load debug data: ${escapeHtml(err.message)}</div>`;
    return null;
  }
}

export function setupChatChrome(state, elements = {}, callbacks = {}) {
  const getEl = (key) => elements[key] || $(key);
  const chatOptionsToggleBtn = getEl('chatOptionsToggleBtn');
  const chatOptionsDrawer = getEl('chatOptionsDrawer');
  const chatOptionsCloseBtn = getEl('chatOptionsCloseBtn');
  const chatOptionsToggleIcon = getEl('chatOptionsToggleIcon');
  const chatContextTokensBadge = getEl('chatContextTokensBadge');
  const chatContextProgressBar = getEl('chatContextProgressBar');
  const chatToolsCountBadge = getEl('chatToolsCountBadge');
  const chatCompactBtn = getEl('chatCompactBtn');
  const chatInspectToolsBtn = getEl('chatInspectToolsBtn');
  const chatToolsModal = getEl('chatToolsModal');
  const chatToolsModalCloseBtn = getEl('chatToolsModalCloseBtn');
  const chatToolsModalList = getEl('chatToolsModalList');
  const chatToolsModalTitle = getEl('chatToolsModalTitle');
  const chatToolsModalBadge = getEl('chatToolsModalBadge');
  const chatToolsSearchInput = getEl('chatToolsSearchInput');
  const chatPromptCatalogBtn = getEl('chatPromptCatalogBtn');
  const chatClosePromptsModalBtn = getEl('chatClosePromptsModalBtn');
  const chatPromptsQuickPicker = getEl('chatPromptsQuickPicker');
  const chatPromptsModalList = getEl('chatPromptsModalList');
  const promptInput = getEl('promptInput');
  const chatShowJourneyBtn = getEl('chatShowJourneyBtn');
  const chatJourneyDrawer = getEl('chatJourneyDrawer');
  const chatJourneyCloseBtn = getEl('chatJourneyCloseBtn');
  const chatJourneyContent = getEl('chatJourneyContent');
  const chatDebugToggleBtn = getEl('chatDebugToggleBtn');
  const chatDebugPane = getEl('chatDebugPane');
  const chatDebugCloseBtn = getEl('chatDebugCloseBtn');
  const chatDebugContent = getEl('chatDebugContent');
  const chatDebugCopyBtn = getEl('chatDebugCopyBtn');
  const chatDebugTabMessages = getEl('chatDebugTabMessages');
  const chatDebugTabTools = getEl('chatDebugTabTools');
  const chatDebugTabMetrics = getEl('chatDebugTabMetrics');
  const chatDebugTabSystem = getEl('chatDebugTabSystem');
  const copyThreadBtn = getEl('copyThreadBtn');
  const exportThreadWikiBtn = getEl('exportThreadWikiBtn');

  const showToast = callbacks.showToastFn || (() => {});
  let activeDebugData = null;
  let activeDebugTab = 'messages';

  if (chatOptionsToggleBtn) {
    chatOptionsToggleBtn.addEventListener('click', () => {
      const isOpen = chatOptionsDrawer && !chatOptionsDrawer.classList.contains('hidden');
      toggleChatOptionsDrawer(!isOpen, {
        chatOptionsDrawer,
        chatOptionsToggleBtn,
        chatOptionsToggleIcon,
        loadChatSessionContextFn: () => loadChatSessionContext(state, {
          chatContextTokensBadge,
          chatContextProgressBar,
          chatToolsCountBadge,
        }),
      });
    });
  }

  if (chatOptionsCloseBtn) {
    chatOptionsCloseBtn.addEventListener('click', () => {
      toggleChatOptionsDrawer(false, {
        chatOptionsDrawer,
        chatOptionsToggleBtn,
        chatOptionsToggleIcon,
      });
    });
  }

  if (chatCompactBtn) {
    chatCompactBtn.addEventListener('click', async () => {
      await loadChatSessionContext(state.activeSessionId, {
        chatContextTokensBadge,
        chatContextProgressBar,
        chatToolsCountBadge,
        isCompact: true,
        showToastFn: showToast,
      });
    });
  }

  if (chatInspectToolsBtn) {
    chatInspectToolsBtn.addEventListener('click', () => {
      toggleToolsModal(true, {
        chatToolsModal,
        chatToolsModalList,
        chatToolsModalTitle,
        chatToolsModalBadge,
        chatToolsSearchInput,
        state,
        showToastFn: showToast,
      });
    });
  }

  if (chatToolsModalCloseBtn) {
    chatToolsModalCloseBtn.addEventListener('click', () => {
      toggleToolsModal(false, { chatToolsModal });
    });
  }

  if (chatToolsSearchInput) {
    chatToolsSearchInput.addEventListener('input', (e) => {
      renderToolsModal(e.target.value, {
        chatToolsModalList,
        chatToolsModalBadge,
        state,
        showToastFn: showToast,
      });
    });
  }

  if (chatPromptCatalogBtn) {
    chatPromptCatalogBtn.addEventListener('click', () => {
      loadQuickPrompts({
        chatPromptsQuickPicker,
        chatPromptsModalList,
        promptInput,
        showToastFn: showToast,
      });
    });
  }

  if (chatClosePromptsModalBtn) {
    chatClosePromptsModalBtn.addEventListener('click', () => {
      if (chatPromptsQuickPicker) chatPromptsQuickPicker.classList.add('hidden');
    });
  }

  if (chatShowJourneyBtn) {
    chatShowJourneyBtn.addEventListener('click', () => {
      if (chatDebugPane) chatDebugPane.classList.add('hidden');
      if (chatJourneyDrawer) {
        const isHidden = chatJourneyDrawer.classList.toggle('hidden');
        if (!isHidden) {
          loadJourneyTimeline(state.activeSessionId, chatJourneyContent, {
            jobPhaseState: callbacks.getJobPhaseState ? callbacks.getJobPhaseState() : null,
            showToastFn: showToast,
          });
        }
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
        if (!isHidden) {
          loadChatDebug(state.activeSessionId, {
            chatDebugContent,
            activeDebugTab,
            tabs: {
              messages: chatDebugTabMessages,
              tools: chatDebugTabTools,
              metrics: chatDebugTabMetrics,
              system: chatDebugTabSystem,
            },
          }).then((data) => {
            activeDebugData = data;
          });
        }
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
      showToast(`Copied ${activeDebugTab} to clipboard`, 'success');
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
        renderChatDebugTab({
          chatDebugContent,
          activeDebugData,
          activeDebugTab,
          tabs: {
            messages: chatDebugTabMessages,
            tools: chatDebugTabTools,
            metrics: chatDebugTabMetrics,
            system: chatDebugTabSystem,
          },
        });
      });
    }
  });

  if (copyThreadBtn) {
    copyThreadBtn.addEventListener('click', () => {
      if (!state.messages || state.messages.length === 0) {
        showToast('No messages to copy', 'warning');
        return;
      }
      const text = state.messages
        .map((m) => `[${(m.role || 'USER').toUpperCase()}]:\n${m.content || ''}`)
        .join('\n\n---\n\n');
      copyToClipboard(text);
      showToast('Full conversation copied to clipboard', 'success');
    });
  }

  if (exportThreadWikiBtn) {
    exportThreadWikiBtn.addEventListener('click', () => {
      // Save to Wiki
      if (!state.messages || state.messages.length === 0) {
        showToast('No messages to export', 'warning');
        return;
      }
      if (typeof callbacks.exportSessionToWiki === 'function') {
        callbacks.exportSessionToWiki(state.activeSessionId);
      } else {
        showToast('Save to Wiki is not available (session export unwired)', 'error');
      }
    });
  }
}
