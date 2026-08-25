/**
 * Chat Studio Module [REQ-FE-001, REQ-WEB-001, REQ-WEB-002]
 */

import { $, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { copyToClipboard } from '../utils/clipboard.js';
import { storageGet, storageSet } from '../utils/storage.js';

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
  const verifyBadge = $('verifyBadge');
  const goalToggle = $('goalToggle');
  const goalBadge = $('goalBadge');

  async function loadAgents() {
    try {
      const res = await fetch('/api/agents');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      state.agents = await res.json();

      if (agentSelect) {
        agentSelect.innerHTML = '';
        state.agents.forEach((agent) => {
          const opt = document.createElement('option');
          opt.value = agent.id;
          opt.textContent = `${agent.name} (${agent.tone})`;
          agentSelect.appendChild(opt);
        });
      }

      if (chatTopBarAgentSelect) {
        chatTopBarAgentSelect.innerHTML = '';
        state.agents.forEach((agent) => {
          const opt = document.createElement('option');
          opt.value = agent.id;
          opt.textContent = agent.name;
          chatTopBarAgentSelect.appendChild(opt);
        });
      }

      const savedAgentId = storageGet('autoreiv_active_agent_id');
      if (savedAgentId && state.agents.some((a) => a.id === savedAgentId)) {
        state.selectedAgentId = savedAgentId;
      } else if (!state.selectedAgentId || !state.agents.some((a) => a.id === state.selectedAgentId)) {
        state.selectedAgentId = state.agents.length > 0 ? state.agents[0].id : 'general-assistant';
      }

      if (agentSelect) agentSelect.value = state.selectedAgentId;
      if (chatTopBarAgentSelect) chatTopBarAgentSelect.value = state.selectedAgentId;

      updateActiveAgentHeader();
      await loadSessions();
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

    const sidebar = $('sidebar');
    if (window.innerWidth < 768 && sidebar) {
      sidebar.classList.add('-translate-x-full');
    }

    await loadSessions();
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
    }
  }

  async function loadSessions() {
    try {
      const res = await fetch(`/api/sessions?agent_id=${state.selectedAgentId}`);
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
    renderSessionList();
    await loadMessages(sessionId);
  }

  async function loadMessages(sessionId) {
    try {
      const res = await fetch(`/api/sessions/${sessionId}/messages`);
      const data = await res.json();
      if (state.activeSessionId !== sessionId) return;
      state.messages = Array.isArray(data) ? data : [];
      if (state.isStreaming) return;
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
      appendMessageBubble(msg.role, msg.content, idx);
    });

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    safeCreateIcons();
  }

  async function renderMarkdown(targetEl, rawMarkdown) {
    if (!targetEl) return;
    if (!window.marked) {
      targetEl.innerHTML = `<pre class="whitespace-pre-wrap font-mono text-xs text-slate-200">${escapeHtml(rawMarkdown)}</pre>`;
      return;
    }

    try {
      const parsedHtml = window.marked.parse(rawMarkdown || '');
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
        safeCreateIcons();
      }
    } catch (err) {
      console.warn('[AutoReiv UI] Markdown rendering error:', err);
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

  if (goalToggle) {
    goalToggle.addEventListener('change', (e) => {
      state.goalEnabled = e.target.checked;
      if (goalBadge) goalBadge.classList.toggle('hidden', !state.goalEnabled);
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

  async function executeChatTurn(userPrompt) {
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
        <div class="tool-status-badge hidden p-2 rounded-lg bg-slate-800/80 border border-slate-700 text-xs text-brand-300 items-center space-x-2"></div>
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
    const toolStatusBadgeEl = streamBubble.querySelector('.tool-status-badge');
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
        body: JSON.stringify({
          agent_id: state.selectedAgentId,
          session_id: state.activeSessionId,
          content: userPrompt,
        }),
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
            if (eventType === 'token') {
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
      const threadText = state.messages.map((m) => `**${m.role.toUpperCase()}**:\n${m.content}\n`).join('\n---\n\n');
      copyToClipboard(threadText);
    });
  }

  if (exportThreadWikiBtn) {
    exportThreadWikiBtn.addEventListener('click', () => {
      const threadText = state.messages.map((m) => `### ${m.role.toUpperCase()}\n\n${m.content}`).join('\n\n---\n\n');
      if (callbacks.exportMessageToWiki) callbacks.exportMessageToWiki(threadText);
    });
  }

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
