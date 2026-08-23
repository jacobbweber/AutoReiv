/**
 * AutoReiv Control Plane - Single-Page Application Client Logic
 * [REQ-WEB-001 - REQ-WEB-006]
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide Icons
  if (window.lucide) {
    window.lucide.createIcons();
  }

  // Application State
  const state = {
    activeTab: 'chat',
    agents: [],
    selectedAgentId: 'general-assistant',
    sessions: [],
    activeSessionId: null,
    messages: [],
    isStreaming: false,
  };

  // DOM Elements
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const closeSidebarBtn = document.getElementById('closeSidebarBtn');
  const sidebar = document.getElementById('sidebar');
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabViews = document.querySelectorAll('.tab-view');
  const agentSelect = document.getElementById('agentSelect');
  const sessionList = document.getElementById('sessionList');
  const newChatBtn = document.getElementById('newChatBtn');
  const activeAgentTitle = document.getElementById('activeAgentTitle');
  const activeAgentTone = document.getElementById('activeAgentTone');
  const messagesContainer = document.getElementById('messagesContainer');
  const chatForm = document.getElementById('chatForm');
  const promptInput = document.getElementById('promptInput');
  const sendBtn = document.getElementById('sendBtn');
  const copyThreadBtn = document.getElementById('copyThreadBtn');
  const exportThreadWikiBtn = document.getElementById('exportThreadWikiBtn');
  const verifyToggle = document.getElementById('verifyToggle');
  const verifyBadge = document.getElementById('verifyBadge');
  const goalToggle = document.getElementById('goalToggle');
  const goalBadge = document.getElementById('goalBadge');

  // Routines DOM
  const routinesGrid = document.getElementById('routinesGrid');
  const refreshRoutinesBtn = document.getElementById('refreshRoutinesBtn');

  // Observability DOM
  const refreshKpiBtn = document.getElementById('refreshKpiBtn');
  const kpiTotalTurns = document.getElementById('kpiTotalTurns');
  const kpiTotalTokens = document.getElementById('kpiTotalTokens');
  const kpiAvgDuration = document.getElementById('kpiAvgDuration');
  const kpiErrorRate = document.getElementById('kpiErrorRate');
  const agentKpiTableBody = document.getElementById('agentKpiTableBody');
  const toolKpiTableBody = document.getElementById('toolKpiTableBody');

  // Settings DOM
  const saveProvidersBtn = document.getElementById('saveProvidersBtn');
  const provPresetSelect = document.getElementById('provPresetSelect');
  const provHostInput = document.getElementById('provHostInput');
  const provKeyInput = document.getElementById('provKeyInput');
  const provModelSelect = document.getElementById('provModelSelect');
  const discoverModelsBtn = document.getElementById('discoverModelsBtn');
  const activeProviderTag = document.getElementById('activeProviderTag');
  const modelDiscoveryStatus = document.getElementById('modelDiscoveryStatus');
  const saveMatrixBtn = document.getElementById('saveMatrixBtn');
  const refreshModelsBtn = document.getElementById('refreshModelsBtn');
  const recalcFitBtn = document.getElementById('recalcFitBtn');
  const customRamInput = document.getElementById('customRamInput');
  const modelFitTableBody = document.getElementById('modelFitTableBody');

  // Agent Forge Studio DOM
  const forgeAgentSelect = document.getElementById('forgeAgentSelect');
  const newAgentBtn = document.getElementById('newAgentBtn');
  const saveAgentBtn = document.getElementById('saveAgentBtn');
  const deleteAgentBtn = document.getElementById('deleteAgentBtn');
  const forgeStatusBanner = document.getElementById('forgeStatusBanner');
  const forgeBuiltinBadge = document.getElementById('forgeBuiltinBadge');
  const forgeAvatarIcon = document.getElementById('forgeAvatarIcon');
  const forgeAvatarSelect = document.getElementById('forgeAvatarSelect');
  const forgeNameInput = document.getElementById('forgeNameInput');
  const forgeIdInput = document.getElementById('forgeIdInput');
  const forgeDescInput = document.getElementById('forgeDescInput');
  const forgeToneSelect = document.getElementById('forgeToneSelect');
  const forgeMaxTurnsInput = document.getElementById('forgeMaxTurnsInput');
  const forgePurposeSelect = document.getElementById('forgePurposeSelect');
  const forgeModelSelect = document.getElementById('forgeModelSelect');
  const forgeSystemPrompt = document.getElementById('forgeSystemPrompt');
  const forgeSkillsGrid = document.getElementById('forgeSkillsGrid');
  const selectAllToolsBtn = document.getElementById('selectAllToolsBtn');
  const clearAllToolsBtn = document.getElementById('clearAllToolsBtn');
  const forgeStatTurns = document.getElementById('forgeStatTurns');
  const forgeStatTokens = document.getElementById('forgeStatTokens');
  const forgeStatTools = document.getElementById('forgeStatTools');
  const forgeStatErrors = document.getElementById('forgeStatErrors');
  const forgeStatLatency = document.getElementById('forgeStatLatency');

  // Co-Pilot DOM
  const copilotForm = document.getElementById('copilotForm');
  const copilotInput = document.getElementById('copilotInput');
  const copilotMessages = document.getElementById('copilotMessages');
  const applyBlueprintBtn = document.getElementById('applyBlueprintBtn');
  const copilotChips = document.querySelectorAll('.copilot-chip');

  // -------------------------------------------------------------
  // Tab Switching
  // -------------------------------------------------------------
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.dataset.tab;
      switchTab(targetTab);
    });
  });

  function switchTab(tabName) {
    state.activeTab = tabName;
    tabBtns.forEach(b => {
      if (b.dataset.tab === tabName) {
        b.className = 'tab-btn active w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition bg-brand-600 text-white shadow-sm shadow-brand-500/20';
      } else {
        b.className = 'tab-btn w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition text-slate-400 hover:text-white hover:bg-slate-800';
      }
    });

    tabViews.forEach(v => {
      if (v.id === `view-${tabName}`) {
        v.classList.remove('hidden');
        v.classList.add('flex');
      } else {
        v.classList.add('hidden');
        v.classList.remove('flex');
      }
    });

    if (tabName === 'routines') loadRoutines();
    if (tabName === 'observability') loadObservability();
    if (tabName === 'agents') loadAgentForge();
    if (tabName === 'settings') loadSettings();

    // Close mobile drawer on tab select
    if (window.innerWidth < 768) {
      sidebar.classList.add('-translate-x-full');
    }
  }

  // Mobile Drawer Toggle
  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', () => {
      sidebar.classList.toggle('-translate-x-full');
    });
  }
  if (closeSidebarBtn) {
    closeSidebarBtn.addEventListener('click', () => {
      sidebar.classList.add('-translate-x-full');
    });
  }

  // -------------------------------------------------------------
  // Agent & Session Management [REQ-WEB-002]
  // -------------------------------------------------------------
  async function loadAgents() {
    try {
      const res = await fetch('/api/agents');
      state.agents = await res.json();
      agentSelect.innerHTML = '';
      state.agents.forEach(agent => {
        const opt = document.createElement('option');
        opt.value = agent.id;
        opt.textContent = `${agent.name} (${agent.tone})`;
        agentSelect.appendChild(opt);
      });
      if (state.agents.length > 0) {
        state.selectedAgentId = state.agents[0].id;
        updateActiveAgentHeader();
        await loadSessions();
      }
    } catch (err) {
      console.error('Failed to load agents:', err);
    }
  }

  agentSelect.addEventListener('change', async (e) => {
    state.selectedAgentId = e.target.value;
    updateActiveAgentHeader();
    await loadSessions();
  });

  function updateActiveAgentHeader() {
    const agent = state.agents.find(a => a.id === state.selectedAgentId);
    if (agent) {
      activeAgentTitle.textContent = agent.name;
      activeAgentTone.textContent = `Tone: ${agent.tone.toUpperCase()} • Tools: ${agent.allowed_tools.length}`;
    }
  }

  async function loadSessions() {
    try {
      const res = await fetch(`/api/sessions?agent_id=${state.selectedAgentId}`);
      state.sessions = await res.json();
      renderSessionList();
      if (state.sessions.length > 0) {
        selectSession(state.sessions[0].id);
      } else {
        await createNewSession();
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }

  function renderSessionList() {
    sessionList.innerHTML = '';
    state.sessions.forEach(sess => {
      const item = document.createElement('div');
      const isActive = sess.id === state.activeSessionId;
      item.className = `p-2 rounded-lg cursor-pointer text-xs flex items-center justify-between transition ${
        isActive ? 'bg-slate-800 text-white font-medium border border-slate-700' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
      }`;
      item.innerHTML = `
        <span class="truncate max-w-[170px]">${escapeHtml(sess.title)}</span>
      `;
      item.addEventListener('click', () => selectSession(sess.id));
      sessionList.appendChild(item);
    });
  }

  newChatBtn.addEventListener('click', createNewSession);

  async function createNewSession() {
    const agent = state.agents.find(a => a.id === state.selectedAgentId);
    const title = `${agent ? agent.name : 'Agent'} Chat`;
    try {
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: state.selectedAgentId, title }),
      });
      const sess = await res.json();
      state.sessions.unshift(sess);
      selectSession(sess.id);
    } catch (err) {
      console.error('Failed to create session:', err);
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
      state.messages = await res.json();
      renderMessages();
    } catch (err) {
      console.error('Failed to load messages:', err);
    }
  }

  function renderMessages() {
    messagesContainer.innerHTML = '';
    if (state.messages.length === 0) {
      messagesContainer.innerHTML = `
        <div class="text-center py-12 text-slate-400 space-y-2">
          <div class="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-brand-400">
            <i data-lucide="bot" class="w-6 h-6"></i>
          </div>
          <p class="text-sm font-medium">Start a new conversation with ${escapeHtml(activeAgentTitle.textContent)}.</p>
        </div>
      `;
      if (window.lucide) window.lucide.createIcons();
      return;
    }

    state.messages.forEach((msg, idx) => {
      appendMessageBubble(msg.role, msg.content, idx);
    });

    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    if (window.lucide) window.lucide.createIcons();
  }

  function appendMessageBubble(role, content, msgIdx = null) {
    const isUser = role.toLowerCase() === 'user';
    const bubble = document.createElement('div');
    bubble.className = `flex ${isUser ? 'justify-end' : 'justify-start'} w-full`;

    const htmlContent = window.marked ? window.marked.parse(content || '') : escapeHtml(content);

    const copyBtnHtml = !isUser ? `
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
    ` : '';

    bubble.innerHTML = `
      <div class="max-w-2xl rounded-2xl p-4 shadow-sm ${
        isUser
          ? 'bg-brand-600 text-white rounded-br-none'
          : 'bg-slate-900 border border-slate-800 text-slate-100 rounded-bl-none'
      }">
        <div class="text-xs font-bold uppercase tracking-wider mb-1 opacity-70">
          ${isUser ? 'You' : escapeHtml(activeAgentTitle.textContent)}
        </div>
        <div class="prose prose-invert text-sm break-words leading-relaxed">
          ${htmlContent}
        </div>
        ${copyBtnHtml}
      </div>
    `;

    messagesContainer.appendChild(bubble);

    // Bind individual copy & wiki buttons
    bubble.querySelectorAll('.copy-msg-btn').forEach(b => {
      b.addEventListener('click', () => {
        navigator.clipboard.writeText(b.dataset.content);
        b.querySelector('span').textContent = 'Copied!';
        setTimeout(() => (b.querySelector('span').textContent = 'Copy'), 2000);
      });
    });

    bubble.querySelectorAll('.wiki-msg-btn').forEach(b => {
      b.addEventListener('click', async () => {
        const text = b.dataset.content;
        await exportMessageToWiki(text);
        b.querySelector('span').textContent = 'Saved to Wiki!';
        setTimeout(() => (b.querySelector('span').textContent = 'Save to Wiki'), 2000);
      });
    });
  }

  // -------------------------------------------------------------
  // Interactive Streaming Chat [REQ-WEB-001]
  // -------------------------------------------------------------
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const prompt = promptInput.value.trim();
    if (!prompt || state.isStreaming || !state.activeSessionId) return;

    promptInput.value = '';
    state.isStreaming = true;
    sendBtn.disabled = true;

    // Append user message immediately
    state.messages.push({ role: 'user', content: prompt });
    appendMessageBubble('user', prompt);

    // Create streaming assistant container
    const streamBubble = document.createElement('div');
    streamBubble.className = 'flex justify-start w-full';
    streamBubble.innerHTML = `
      <div class="max-w-2xl rounded-2xl p-4 bg-slate-900 border border-slate-800 text-slate-100 rounded-bl-none space-y-2">
        <div class="text-xs font-bold uppercase tracking-wider opacity-70 flex items-center space-x-2">
          <span>${escapeHtml(activeAgentTitle.textContent)}</span>
          <span class="w-1.5 h-1.5 rounded-full bg-brand-500 animate-ping"></span>
        </div>
        <div id="reasoningBox" class="hidden p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-400 font-mono">
          <div class="flex items-center space-x-1.5 font-semibold text-slate-300 mb-1">
            <i data-lucide="brain" class="w-3.5 h-3.5 text-indigo-400"></i>
            <span>Thought Process</span>
          </div>
          <div id="reasoningContent" class="whitespace-pre-wrap"></div>
        </div>
        <div id="toolStatusBadge" class="hidden text-xs py-1 px-2.5 rounded bg-indigo-950/80 border border-indigo-800 text-indigo-300 font-mono">
          <span>Executing tool...</span>
        </div>
        <div id="streamContent" class="prose prose-invert text-sm break-words leading-relaxed"></div>
      </div>
    `;
    messagesContainer.appendChild(streamBubble);
    if (window.lucide) window.lucide.createIcons();

    const streamContentEl = streamBubble.querySelector('#streamContent');
    const reasoningBoxEl = streamBubble.querySelector('#reasoningBox');
    const reasoningContentEl = streamBubble.querySelector('#reasoningContent');
    const toolStatusBadgeEl = streamBubble.querySelector('#toolStatusBadge');

    let fullAssistantText = '';
    let fullReasoningText = '';

    const isGoalMode = (goalToggle && goalToggle.checked) || prompt.toLowerCase().startsWith('/goal');
    const goalText = prompt.toLowerCase().startsWith('/goal') ? prompt.slice(5).trim() : prompt;

    try {
      if (isGoalMode) {
        toolStatusBadgeEl.classList.remove('hidden');
        toolStatusBadgeEl.className = 'text-xs py-1 px-2.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300 font-mono';
        toolStatusBadgeEl.textContent = '🎯 Formulating & Executing Plan Graph...';

        const response = await fetch('/api/chat/goal', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: state.selectedAgentId,
            session_id: state.activeSessionId,
            goal: goalText,
          }),
        });

        const data = await response.json();
        fullAssistantText = data.output || '';

        toolStatusBadgeEl.textContent = `✓ Goal Graph Completed (${data.plan?.steps?.length || 0} milestones)`;

        if (data.plan && data.plan.steps) {
          const stepsHtml = data.plan.steps.map((s, idx) => `
            <div class="flex items-start space-x-2 py-1.5 border-b border-slate-800/80 last:border-0 text-xs">
              <span class="text-emerald-400 font-bold">✓</span>
              <div class="flex-1">
                <div class="font-medium text-slate-200">${escapeHtml(s.title)}</div>
                ${s.result_summary ? `<div class="text-[11px] text-slate-400 mt-0.5">${escapeHtml(s.result_summary.slice(0, 150))}...</div>` : ''}
              </div>
              ${s.duration_ms ? `<span class="text-[10px] text-slate-500 font-mono">${s.duration_ms.toFixed(0)}ms</span>` : ''}
            </div>
          `).join('');

          reasoningBoxEl.classList.remove('hidden');
          reasoningBoxEl.innerHTML = `
            <div class="flex items-center space-x-1.5 font-semibold text-amber-300 mb-2">
              <i data-lucide="target" class="w-3.5 h-3.5 text-amber-400"></i>
              <span>Execution Plan (${data.plan.steps.length} Milestones)</span>
            </div>
            <div class="space-y-1">${stepsHtml}</div>
          `;
          if (window.lucide) window.lucide.createIcons();
        }

        streamContentEl.innerHTML = window.marked ? window.marked.parse(fullAssistantText) : escapeHtml(fullAssistantText);
        state.messages.push({ role: 'assistant', content: fullAssistantText });
      } else if (verifyToggle && verifyToggle.checked) {
        toolStatusBadgeEl.classList.remove('hidden');
        toolStatusBadgeEl.textContent = 'Running Reflexion Self-Verification Loop...';

        const response = await fetch('/api/chat/verified', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: state.selectedAgentId,
            session_id: state.activeSessionId,
            content: prompt,
            max_refinements: 3,
          }),
        });

        const data = await response.json();
        fullAssistantText = data.output || '';

        toolStatusBadgeEl.classList.remove('hidden');
        if (data.verification_passed) {
          toolStatusBadgeEl.className = 'text-xs py-1 px-2.5 rounded bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-mono';
          toolStatusBadgeEl.textContent = `✓ Verified (Attempt ${data.attempts_taken}/3)`;
        } else {
          toolStatusBadgeEl.className = 'text-xs py-1 px-2.5 rounded bg-amber-950/80 border border-amber-800 text-amber-300 font-mono';
          toolStatusBadgeEl.textContent = `⚠ Verification budget exhausted (${data.attempts_taken} attempts)`;
        }

        if (data.critique_history && data.critique_history.length > 0) {
          reasoningBoxEl.classList.remove('hidden');
          reasoningContentEl.textContent = data.critique_history.join('\n\n');
        }

        streamContentEl.innerHTML = window.marked ? window.marked.parse(fullAssistantText) : escapeHtml(fullAssistantText);
        state.messages.push({ role: 'assistant', content: fullAssistantText });
      } else {
        const response = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: state.selectedAgentId,
            session_id: state.activeSessionId,
            content: prompt,
          }),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop();

          for (const block of lines) {
            if (!block.trim()) continue;
            const eventMatch = block.match(/event:\s*([^\n]+)/);
            const dataMatch = block.match(/data:\s*([^\n]+)/);
            const eventType = eventMatch ? eventMatch[1].trim() : 'message';
            const rawData = dataMatch ? dataMatch[1].trim() : '{}';
            const payload = JSON.parse(rawData);

            if (eventType === 'reasoning') {
              reasoningBoxEl.classList.remove('hidden');
              fullReasoningText += payload.text || '';
              reasoningContentEl.textContent = fullReasoningText;
            } else if (eventType === 'token') {
              fullAssistantText += payload.text || '';
              streamContentEl.innerHTML = window.marked ? window.marked.parse(fullAssistantText) : escapeHtml(fullAssistantText);
            } else if (eventType === 'tool_start') {
              toolStatusBadgeEl.classList.remove('hidden');
              toolStatusBadgeEl.textContent = `Invoking ${payload.tool_name}...`;
            } else if (eventType === 'tool_output') {
              toolStatusBadgeEl.textContent = `Completed tool execution.`;
              setTimeout(() => toolStatusBadgeEl.classList.add('hidden'), 2500);
            } else if (eventType === 'turn_done') {
              toolStatusBadgeEl.classList.add('hidden');
            }
          }
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        state.messages.push({ role: 'assistant', content: fullAssistantText });
      }
    } catch (err) {
      console.error('Chat execution error:', err);
      streamContentEl.innerHTML += `<p class="text-rose-400 font-mono text-xs">Error executing turn: ${escapeHtml(err.message)}</p>`;
    } finally {
      state.isStreaming = false;
      sendBtn.disabled = false;
      promptInput.focus();
    }
  });

  // Toggle verify & goal badges on checkbox change
  if (verifyToggle) {
    verifyToggle.addEventListener('change', () => {
      if (verifyBadge) {
        verifyBadge.classList.toggle('hidden', !verifyToggle.checked);
      }
    });
  }

  if (goalToggle) {
    goalToggle.addEventListener('change', () => {
      if (goalBadge) {
        goalBadge.classList.toggle('hidden', !goalToggle.checked);
      }
    });
  }

  // Prompt input Enter key handling
  promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event('submit'));
    }
  });

  // -------------------------------------------------------------
  // One-Click Wiki & Copy Actions [REQ-WEB-003]
  // -------------------------------------------------------------
  copyThreadBtn.addEventListener('click', () => {
    const threadText = state.messages.map(m => `${m.role.toUpperCase()}:\n${m.content}\n`).join('\n---\n\n');
    navigator.clipboard.writeText(threadText);
    copyThreadBtn.querySelector('span').textContent = 'Copied!';
    setTimeout(() => (copyThreadBtn.querySelector('span').textContent = 'Copy'), 2000);
  });

  exportThreadWikiBtn.addEventListener('click', async () => {
    if (state.messages.length === 0) return;
    const title = `${activeAgentTitle.textContent} Conversation - ${new Date().toISOString().split('T')[0]}`;
    try {
      const res = await fetch('/api/export/wiki', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          messages: state.messages,
          agent_id: state.selectedAgentId,
          session_id: state.activeSessionId,
          category: '03_Resources',
          tags: ['chat_thread', state.selectedAgentId],
        }),
      });
      const data = await res.json();
      exportThreadWikiBtn.querySelector('span').textContent = 'Saved to Wiki!';
      setTimeout(() => (exportThreadWikiBtn.querySelector('span').textContent = 'Export to Wiki'), 2000);
    } catch (err) {
      console.error('Failed to export thread to wiki:', err);
    }
  });

  async function exportMessageToWiki(content) {
    const title = `${activeAgentTitle.textContent} Note - ${new Date().toISOString().split('T')[0]}`;
    try {
      await fetch('/api/export/wiki', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          content,
          agent_id: state.selectedAgentId,
          session_id: state.activeSessionId,
          category: '03_Resources',
          tags: ['single_note', state.selectedAgentId],
        }),
      });
    } catch (err) {
      console.error('Failed to export message to wiki:', err);
    }
  }

  // -------------------------------------------------------------
  // Routines View [REQ-WEB-006]
  // -------------------------------------------------------------
  async function loadRoutines() {
    try {
      const res = await fetch('/api/routines');
      const routines = await res.json();
      routinesGrid.innerHTML = '';
      routines.forEach(r => {
        const card = document.createElement('div');
        card.className = 'p-5 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between space-y-4';
        card.innerHTML = `
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-semibold px-2 py-0.5 rounded bg-brand-950 text-brand-400 border border-brand-800">${escapeHtml(r.agent_id)}</span>
              <span class="text-[11px] font-mono text-slate-400">${r.schedule_type.toUpperCase()} (${r.cron_expression || `${r.interval_seconds}s`})</span>
            </div>
            <h3 class="font-bold text-base text-white">${escapeHtml(r.name)}</h3>
            <p class="text-xs text-slate-400 mt-1 leading-relaxed">${escapeHtml(r.description || '')}</p>
          </div>
          <div class="pt-3 border-t border-slate-800 flex items-center justify-between">
            <span class="text-xs text-slate-400">Status: <strong class="text-emerald-400">${r.last_status}</strong></span>
            <button class="trigger-routine-btn px-3 py-1.5 bg-slate-800 hover:bg-brand-600 border border-slate-700 text-xs font-medium text-white rounded-lg transition" data-id="${r.id}">
              Run Now
            </button>
          </div>
        `;
        routinesGrid.appendChild(card);

        card.querySelector('.trigger-routine-btn').addEventListener('click', async (e) => {
          const btn = e.currentTarget;
          btn.textContent = 'Running...';
          btn.disabled = true;
          try {
            await fetch(`/api/routines/${r.id}/trigger`, { method: 'POST' });
            btn.textContent = 'Triggered!';
            setTimeout(() => {
              btn.textContent = 'Run Now';
              btn.disabled = false;
              loadRoutines();
            }, 2000);
          } catch (err) {
            btn.textContent = 'Error';
            btn.disabled = false;
          }
        });
      });
    } catch (err) {
      console.error('Failed to load routines:', err);
    }
  }

  if (refreshRoutinesBtn) refreshRoutinesBtn.addEventListener('click', loadRoutines);

  // -------------------------------------------------------------
  // Observability & KPI Dashboard [REQ-WEB-005]
  // -------------------------------------------------------------
  async function loadObservability() {
    try {
      const res = await fetch('/api/observability/kpi');
      const data = await res.json();

      kpiTotalTurns.textContent = data.overview.total_turns || 0;
      kpiTotalTokens.textContent = (data.overview.total_tokens || 0).toLocaleString();
      kpiAvgDuration.textContent = `${data.overview.avg_turn_duration_ms || 0} ms`;
      kpiErrorRate.textContent = `${data.overview.error_rate_pct || 0}%`;

      // Render Agents table
      agentKpiTableBody.innerHTML = '';
      data.agents.forEach(a => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td class="p-2.5 font-medium text-white">${escapeHtml(a.agent_id)}</td>
          <td class="p-2.5">${a.turn_count}</td>
          <td class="p-2.5 font-mono text-indigo-400">${a.total_tokens.toLocaleString()}</td>
          <td class="p-2.5">${a.tool_call_count}</td>
          <td class="p-2.5 text-rose-400">${a.error_count}</td>
          <td class="p-2.5">${a.avg_duration_ms} ms</td>
        `;
        agentKpiTableBody.appendChild(row);
      });

      // Render Tools table
      toolKpiTableBody.innerHTML = '';
      data.tools.forEach(t => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td class="p-2.5 font-medium text-white">${escapeHtml(t.tool_name)}</td>
          <td class="p-2.5">${t.total_invocations}</td>
          <td class="p-2.5 text-emerald-400">${t.success_count}</td>
          <td class="p-2.5 text-rose-400">${t.failure_count}</td>
          <td class="p-2.5 font-bold text-cyan-400">${t.success_rate_pct}%</td>
          <td class="p-2.5">${t.avg_duration_ms} ms</td>
        `;
        toolKpiTableBody.appendChild(row);
      });
    } catch (err) {
      console.error('Failed to load observability data:', err);
    }
  }

  if (refreshKpiBtn) refreshKpiBtn.addEventListener('click', loadObservability);

  // -------------------------------------------------------------
  // Settings Studio, Presets, & Model Discovery [REQ-SET-001..005]
  // -------------------------------------------------------------

  const PRESETS_DEFAULTS = {
    ollama: { url: 'http://127.0.0.1:11434', keyPlaceholder: 'Optional for Local' },
    openai: { url: 'https://api.openai.com/v1', keyPlaceholder: 'sk-...' },
    anthropic: { url: 'https://api.anthropic.com/v1', keyPlaceholder: 'sk-ant-...' },
    openrouter: { url: 'https://openrouter.ai/api/v1', keyPlaceholder: 'sk-or-...' },
    groq: { url: 'https://api.groq.com/openai/v1', keyPlaceholder: 'gsk_...' },
    deepseek: { url: 'https://api.deepseek.com/v1', keyPlaceholder: 'sk-...' },
    together: { url: 'https://api.together.xyz/v1', keyPlaceholder: '...' },
    vllm: { url: 'http://127.0.0.1:8000/v1', keyPlaceholder: 'Optional' },
  };

  if (provPresetSelect) {
    provPresetSelect.addEventListener('change', () => {
      const p = provPresetSelect.value;
      if (PRESETS_DEFAULTS[p]) {
        provHostInput.value = PRESETS_DEFAULTS[p].url;
  // -------------------------------------------------------------
  // Agent Forge Studio & Co-Pilot [REQ-FORGE-006]
  // -------------------------------------------------------------
  let activeForgeAgent = null;
  let activeBlueprint = null;
  let cachedSkillsCatalog = null;

  async function loadAgentForge() {
    try {
      // 1. Fetch skills catalog & models if not cached
      if (!cachedSkillsCatalog) {
        const catRes = await fetch('/api/skills/catalog');
        cachedSkillsCatalog = await catRes.json();
        renderSkillsCatalog(cachedSkillsCatalog);
      }

      // 2. Fetch models to populate Model Override select
      try {
        const modRes = await fetch('/api/models/discover');
        const modData = await modRes.json();
        if (forgeModelSelect) {
          const curVal = forgeModelSelect.value;
          forgeModelSelect.innerHTML = '<option value="default">Inherit from Purpose Slot / Global Default</option>';
          (modData.models || []).forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.name;
            opt.textContent = `${m.name} (${m.provider})`;
            forgeModelSelect.appendChild(opt);
          });
          if (curVal) forgeModelSelect.value = curVal;
        }
      } catch (e) {
        console.warn('Failed to load models for forge select:', e);
      }

      // 3. Fetch agent list
      const res = await fetch('/api/agents');
      const agents = await res.json();
      state.agents = agents;

      if (forgeAgentSelect) {
        const selectedId = forgeAgentSelect.value || (agents[0] ? agents[0].id : null);
        forgeAgentSelect.innerHTML = '';
        agents.forEach(a => {
          const opt = document.createElement('option');
          opt.value = a.id;
          opt.textContent = `${a.name} ${a.is_builtin ? '(Built-in)' : '(Custom)'}`;
          forgeAgentSelect.appendChild(opt);
        });

        if (selectedId && agents.some(a => a.id === selectedId)) {
          forgeAgentSelect.value = selectedId;
        } else if (agents.length > 0) {
          forgeAgentSelect.value = agents[0].id;
        }

        const targetAgent = agents.find(a => a.id === forgeAgentSelect.value) || agents[0];
        if (targetAgent) {
          renderAgentToForge(targetAgent);
        }
      }
    } catch (err) {
      console.error('Failed to load Agent Forge:', err);
    }
  }

  function renderSkillsCatalog(catalog) {
    if (!forgeSkillsGrid || !catalog || !catalog.tools) return;
    forgeSkillsGrid.innerHTML = '';

    catalog.tools.forEach(t => {
      const label = document.createElement('label');
      label.className = 'flex items-start space-x-2 p-2 rounded-lg bg-slate-800/60 border border-slate-700/60 hover:border-slate-600 transition cursor-pointer text-xs';
      label.innerHTML = `
        <input type="checkbox" value="${t.name}" class="forge-tool-checkbox mt-0.5 rounded border-slate-700 text-brand-500 focus:ring-brand-500">
        <div class="flex-1 min-w-0">
          <span class="font-mono text-slate-200 block text-[11px] font-semibold truncate">${escapeHtml(t.name)}</span>
          <span class="text-slate-400 block text-[10px] line-clamp-2 leading-tight">${escapeHtml(t.description || '')}</span>
        </div>
      `;
      forgeSkillsGrid.appendChild(label);
    });
  }

  async function renderAgentToForge(agent) {
    activeForgeAgent = agent;
    if (!agent) return;

    if (forgeNameInput) forgeNameInput.value = agent.name || '';
    if (forgeIdInput) {
      forgeIdInput.value = agent.id || '';
      forgeIdInput.disabled = true; // Cannot alter ID of saved agent
    }
    if (forgeDescInput) forgeDescInput.value = agent.description || '';
    if (forgeSystemPrompt) forgeSystemPrompt.value = agent.system_prompt || '';
    if (forgeToneSelect) forgeToneSelect.value = agent.tone || 'default';
    if (forgeMaxTurnsInput) forgeMaxTurnsInput.value = agent.max_turns || 10;
    if (forgePurposeSelect) forgePurposeSelect.value = agent.purpose || 'general';
    if (forgeAvatarSelect) forgeAvatarSelect.value = agent.avatar_icon || 'bot';
    if (forgeModelSelect) forgeModelSelect.value = agent.model || 'default';

    updateAvatarPreview(agent.avatar_icon || 'bot');

    if (forgeBuiltinBadge) {
      if (agent.is_builtin) {
        forgeBuiltinBadge.textContent = 'Built-in Baseline';
        forgeBuiltinBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800';
      } else {
        forgeBuiltinBadge.textContent = 'Custom Agent';
        forgeBuiltinBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800';
      }
    }

    if (deleteAgentBtn) {
      if (agent.is_builtin) {
        deleteAgentBtn.disabled = true;
        deleteAgentBtn.classList.add('opacity-40', 'cursor-not-allowed');
      } else {
        deleteAgentBtn.disabled = false;
        deleteAgentBtn.classList.remove('opacity-40', 'cursor-not-allowed');
      }
    }

    // Set Tool Checkboxes
    const allowed = new Set(agent.allowed_tool_names || agent.allowed_tools || []);
    const checkboxes = document.querySelectorAll('.forge-tool-checkbox');
    checkboxes.forEach(cb => {
      cb.checked = allowed.has(cb.value);
    });

    // Load Agent Telemetry
    loadAgentTelemetry(agent.id);
  }

  function updateAvatarPreview(iconName) {
    if (forgeAvatarPreview) {
      forgeAvatarPreview.innerHTML = `<i data-lucide="${iconName}" class="w-7 h-7"></i>`;
      if (window.lucide) window.lucide.createIcons();
    }
  }

  async function loadAgentTelemetry(agentId) {
    try {
      const res = await fetch(`/api/observability/kpi?agent_id=${encodeURIComponent(agentId)}`);
      if (!res.ok) return;
      const data = await res.json();
      if (forgeStatTurns) forgeStatTurns.textContent = data.total_turns || 0;
      if (forgeStatTokens) forgeStatTokens.textContent = (data.total_tokens || 0).toLocaleString();
      if (forgeStatTools) forgeStatTools.textContent = data.total_tool_calls || 0;
      if (forgeStatErrors) forgeStatErrors.textContent = `${(data.error_rate_pct || 0).toFixed(1)}%`;
      if (forgeStatLatency) forgeStatLatency.textContent = `${(data.avg_duration_ms || 0).toFixed(0)}ms`;
    } catch (e) {
      console.warn('Failed to load agent telemetry:', e);
    }
  }

  if (forgeAgentSelect) {
    forgeAgentSelect.addEventListener('change', () => {
      const selectedId = forgeAgentSelect.value;
      const agent = (state.agents || []).find(a => a.id === selectedId);
      if (agent) renderAgentToForge(agent);
    });
  }

  if (forgeAvatarSelect) {
    forgeAvatarSelect.addEventListener('change', () => {
      updateAvatarPreview(forgeAvatarSelect.value);
    });
  }

  if (newAgentBtn) {
    newAgentBtn.addEventListener('click', () => {
      activeForgeAgent = null;
      if (forgeNameInput) forgeNameInput.value = '';
      if (forgeIdInput) {
        forgeIdInput.value = '';
        forgeIdInput.disabled = false;
        forgeIdInput.focus();
      }
      if (forgeDescInput) forgeDescInput.value = '';
      if (forgeSystemPrompt) forgeSystemPrompt.value = 'You are AutoReiv\'s custom agent. Execute your assigned tasks safely and concisely.';
      if (forgeToneSelect) forgeToneSelect.value = 'technical';
      if (forgeMaxTurnsInput) forgeMaxTurnsInput.value = 10;
      if (forgePurposeSelect) forgePurposeSelect.value = 'task_execution';
      if (forgeAvatarSelect) forgeAvatarSelect.value = 'terminal';
      if (forgeModelSelect) forgeModelSelect.value = 'default';

      updateAvatarPreview('terminal');

      if (forgeBuiltinBadge) {
        forgeBuiltinBadge.textContent = 'New Custom';
        forgeBuiltinBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded bg-brand-950 text-brand-400 border border-brand-800';
      }
      if (deleteAgentBtn) {
        deleteAgentBtn.disabled = true;
        deleteAgentBtn.classList.add('opacity-40', 'cursor-not-allowed');
      }

      // Check default safe tools
      const checkboxes = document.querySelectorAll('.forge-tool-checkbox');
      checkboxes.forEach(cb => {
        cb.checked = cb.value === 'system_info';
      });

      if (forgeStatusBanner) {
        forgeStatusBanner.textContent = 'Creating new custom agent. Fill in identity, prompt, and skills, then click Save Profile.';
        forgeStatusBanner.className = 'px-4 py-2 text-xs font-medium text-center border-b border-brand-800 bg-brand-950/60 text-brand-300 block';
        setTimeout(() => forgeStatusBanner.classList.add('hidden'), 4000);
      }
    });
  }

  if (selectAllToolsBtn) {
    selectAllToolsBtn.addEventListener('click', () => {
      document.querySelectorAll('.forge-tool-checkbox').forEach(cb => (cb.checked = true));
    });
  }

  if (clearAllToolsBtn) {
    clearAllToolsBtn.addEventListener('click', () => {
      document.querySelectorAll('.forge-tool-checkbox').forEach(cb => (cb.checked = false));
    });
  }

  if (saveAgentBtn) {
    saveAgentBtn.addEventListener('click', async () => {
      const name = forgeNameInput ? forgeNameInput.value.trim() : '';
      let id = forgeIdInput ? forgeIdInput.value.trim() : '';
      if (!name) {
        alert('Agent name is required.');
        return;
      }
      if (!id) {
        id = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      }

      const checkedTools = [];
      document.querySelectorAll('.forge-tool-checkbox:checked').forEach(cb => checkedTools.push(cb.value));

      const payload = {
        id: id,
        name: name,
        description: forgeDescInput ? forgeDescInput.value.trim() : '',
        system_prompt: forgeSystemPrompt ? forgeSystemPrompt.value.trim() : '',
        purpose: forgePurposeSelect ? forgePurposeSelect.value : 'general',
        tone: forgeToneSelect ? forgeToneSelect.value : 'default',
        avatar_icon: forgeAvatarSelect ? forgeAvatarSelect.value : 'bot',
        model: forgeModelSelect ? forgeModelSelect.value : 'default',
        allowed_tool_names: checkedTools,
        max_turns: parseInt(forgeMaxTurnsInput ? forgeMaxTurnsInput.value : 10, 10) || 10,
      };

      const isExisting = Boolean(activeForgeAgent && activeForgeAgent.id === id);
      const url = isExisting ? `/api/agents/${encodeURIComponent(id)}` : '/api/agents';
      const method = isExisting ? 'PUT' : 'POST';

      try {
        saveAgentBtn.disabled = true;
        saveAgentBtn.innerHTML = '<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Saving...</span>';
        if (window.lucide) window.lucide.createIcons();

        const res = await fetch(url, {
          method: method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const errData = await res.json();
          throw new Error(errData.detail || 'Failed to save agent profile');
        }

        saveAgentBtn.innerHTML = '<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400"></i><span>Saved!</span>';
        setTimeout(() => {
          saveAgentBtn.innerHTML = '<i data-lucide="save" class="w-3.5 h-3.5"></i><span>Save Profile</span>';
          saveAgentBtn.disabled = false;
          if (window.lucide) window.lucide.createIcons();
        }, 2000);

        if (forgeStatusBanner) {
          forgeStatusBanner.textContent = `Agent "${name}" saved successfully!`;
          forgeStatusBanner.className = 'px-4 py-2 text-xs font-medium text-center border-b border-emerald-800 bg-emerald-950/60 text-emerald-300 block';
          setTimeout(() => forgeStatusBanner.classList.add('hidden'), 3500);
        }

        // Refresh agent lists across app
        await loadAgents();
        await loadAgentForge();
        if (forgeAgentSelect) forgeAgentSelect.value = id;
      } catch (err) {
        console.error('Save agent error:', err);
        alert(`Error saving agent: ${err.message}`);
        saveAgentBtn.innerHTML = '<i data-lucide="save" class="w-3.5 h-3.5"></i><span>Save Profile</span>';
        saveAgentBtn.disabled = false;
        if (window.lucide) window.lucide.createIcons();
      }
    });
  }

  if (deleteAgentBtn) {
    deleteAgentBtn.addEventListener('click', async () => {
      if (!activeForgeAgent || activeForgeAgent.is_builtin) return;
      if (!confirm(`Are you sure you want to permanently delete custom agent "${activeForgeAgent.name}"?`)) return;

      try {
        const res = await fetch(`/api/agents/${encodeURIComponent(activeForgeAgent.id)}`, { method: 'DELETE' });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Failed to delete agent');
        }

        if (forgeStatusBanner) {
          forgeStatusBanner.textContent = `Agent "${activeForgeAgent.name}" deleted.`;
          forgeStatusBanner.className = 'px-4 py-2 text-xs font-medium text-center border-b border-rose-800 bg-rose-950/60 text-rose-300 block';
          setTimeout(() => forgeStatusBanner.classList.add('hidden'), 3500);
        }

        await loadAgents();
        await loadAgentForge();
      } catch (err) {
        console.error('Delete agent error:', err);
        alert(`Error deleting agent: ${err.message}`);
      }
    });
  }

  // -------------------------------------------------------------
  // System Agent AI Co-Pilot Chat
  // -------------------------------------------------------------
  if (copilotForm) {
    copilotForm.addEventListener('submit', async e => {
      e.preventDefault();
      const prompt = copilotInput ? copilotInput.value.trim() : '';
      if (!prompt) return;
      copilotInput.value = '';

      // Append user bubble
      appendCopilotMessage('user', prompt);

      // Append assistant placeholder
      const msgDiv = appendCopilotMessage('assistant', '<span class="text-slate-400">Architecting agent specification...</span>');

      try {
        const res = await fetch('/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agent_id: 'system-agent',
            session_id: 'copilot-studio-session',
            content: `You are the AutoReiv System Architect Agent. The operator wants to design/configure an agent. Request: "${prompt}".\nIf appropriate, output a structured JSON specification block with keys: id, name, description, system_prompt, purpose, tone, avatar_icon, allowed_tool_names, max_turns.`,
          }),
        });

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        msgDiv.innerHTML = '';

        let currentEvent = null;
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
              const payload = line.slice(6).trim();
              if (payload === '[DONE]') continue;
              try {
                const dataObj = JSON.parse(payload);
                if (currentEvent === 'token' && dataObj.text) {
                  fullText += dataObj.text;
                  msgDiv.innerHTML = escapeHtml(fullText).replace(/\n/g, '<br>');
                } else if (currentEvent === 'tool_output' && dataObj.result) {
                  if (typeof dataObj.result === 'object') {
                    checkForBlueprint(dataObj.result);
                  }
                }
              } catch (err) {
                // non-JSON stream chunk
              }
            }
          }
        }

        // Try extracting JSON blueprint from fullText
        extractAndOfferBlueprint(fullText);
      } catch (err) {
        msgDiv.innerHTML = `<span class="text-rose-400">Error: ${err.message}</span>`;
      }
    });
  }

  function appendCopilotMessage(role, htmlContent) {
    if (!copilotMessages) return null;
    const div = document.createElement('div');
    div.className =
      role === 'user'
        ? 'p-2.5 rounded-lg bg-brand-950/70 border border-brand-800 text-brand-100 text-xs ml-4'
        : 'p-2.5 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-200 text-xs mr-4 space-y-1';

    div.innerHTML =
      role === 'user'
        ? `<p class="font-semibold text-brand-400 text-[10px] mb-0.5">Operator</p><div>${htmlContent}</div>`
        : `<p class="font-semibold text-cyan-400 text-[10px] mb-0.5">System Architect</p><div class="copilot-body leading-relaxed">${htmlContent}</div>`;

    copilotMessages.appendChild(div);
    copilotMessages.scrollTop = copilotMessages.scrollHeight;
    return div.querySelector('.copilot-body') || div;
  }

  function extractAndOfferBlueprint(text) {
    const jsonMatch = text.match(/\{[\s\S]*"system_prompt"[\s\S]*\}/);
    if (jsonMatch) {
      try {
        const spec = JSON.parse(jsonMatch[0]);
        checkForBlueprint(spec);
      } catch (e) {
        // ignore parse error
      }
    }
  }

  function checkForBlueprint(spec) {
    if (spec && (spec.system_prompt || spec.name)) {
      activeBlueprint = spec;
      if (applyBlueprintBtn) {
        applyBlueprintBtn.classList.remove('hidden');
        applyBlueprintBtn.classList.add('flex');
      }
    }
  }

  if (applyBlueprintBtn) {
    applyBlueprintBtn.addEventListener('click', () => {
      if (!activeBlueprint) return;
      renderAgentToForge(activeBlueprint);
      if (forgeIdInput) forgeIdInput.disabled = false;
      if (forgeBuiltinBadge) {
        forgeBuiltinBadge.textContent = 'AI Blueprint Applied';
        forgeBuiltinBadge.className = 'text-[10px] font-mono px-2 py-0.5 rounded bg-brand-950 text-brand-400 border border-brand-800';
      }
      if (forgeStatusBanner) {
        forgeStatusBanner.textContent = `Applied AI Blueprint for "${activeBlueprint.name || 'Custom Agent'}". Review settings and click Save Profile.`;
        forgeStatusBanner.className = 'px-4 py-2 text-xs font-medium text-center border-b border-brand-800 bg-brand-950/60 text-brand-300 block';
        setTimeout(() => forgeStatusBanner.classList.add('hidden'), 4000);
      }
    });
  }

  copilotChips.forEach(chip => {
    chip.addEventListener('click', () => {
      if (copilotInput) {
        copilotInput.value = chip.dataset.prompt;
        if (copilotForm) copilotForm.dispatchEvent(new Event('submit'));
      }
    });
  });

  async function loadSettings() {
    try {
      const res = await fetch('/api/settings');
      const data = await res.json();

      if (data.providers) {
        const defaultProv = data.providers.default_provider_id || 'ollama';
        if (provPresetSelect) provPresetSelect.value = defaultProv;
        if (activeProviderTag) activeProviderTag.textContent = defaultProv;

        if (defaultProv === 'ollama') {
          if (provHostInput) provHostInput.value = data.providers.ollama_host || 'http://127.0.0.1:11434';
        } else {
          if (provHostInput) provHostInput.value = data.providers.openai_base_url || 'https://api.openai.com/v1';
          if (provKeyInput) provKeyInput.value = data.providers.openai_api_key || '';
        }
      }

      if (data.hardware && customRamInput) {
        customRamInput.value = data.hardware.available_ram_gb || data.hardware.total_ram_gb || 16;
      }

      // Populate matrix values if already saved
      if (data.matrix && data.matrix.purposes) {
        state.savedMatrix = data.matrix.purposes;
      }

      // Initial model discovery
      await discoverAndPopulateModels();
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  }

  async function discoverAndPopulateModels() {
    const customRam = parseFloat(customRamInput ? customRamInput.value : 16) || 16;
    const selectedPreset = provPresetSelect ? provPresetSelect.value : 'ollama';
    const currentHost = provHostInput ? provHostInput.value.trim() : '';
    const currentKey = provKeyInput ? provKeyInput.value.trim() : '';

    if (modelDiscoveryStatus) modelDiscoveryStatus.textContent = 'Querying active provider models...';
    if (discoverModelsBtn) {
      discoverModelsBtn.disabled = true;
      discoverModelsBtn.innerHTML = '<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i><span>Querying...</span>';
      if (window.lucide) window.lucide.createIcons();
    }

    try {
      let queryUrl = `/api/models/discover?available_ram_gib=${customRam}&provider_id=${encodeURIComponent(selectedPreset)}`;
      if (currentHost) {
        queryUrl += `&host_url=${encodeURIComponent(currentHost)}`;
      }
      if (currentKey) {
        queryUrl += `&api_key=${encodeURIComponent(currentKey)}`;
      }

      const res = await fetch(queryUrl);
      const data = await res.json();
      const models = data.models || [];

      if (modelDiscoveryStatus) {
        modelDiscoveryStatus.textContent = `Discovered ${models.length} model(s) from ${selectedPreset} (${currentHost || 'default'}).`;
      }

      // Populate Default Model dropdown
      if (provModelSelect) {
        provModelSelect.innerHTML = '<option value="default">Auto-Select Default (e.g. llama3.2:latest)</option>';
        models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m.name;
          opt.textContent = `${m.name} (${m.provider})`;
          provModelSelect.appendChild(opt);
        });
      }

      // Populate Purpose Routing Matrix Dropdowns
      const matrixSelects = document.querySelectorAll('.matrix-select');
      matrixSelects.forEach(sel => {
        const currentVal = sel.value;
        sel.innerHTML = '<option value="default">default</option>';
        models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m.name;
          opt.textContent = `${m.name} (${m.provider})`;
          sel.appendChild(opt);
        });
        if (state.savedMatrix) {
          const purposeKey = sel.id.replace('matrix', '').toLowerCase();
          for (const [k, v] of Object.entries(state.savedMatrix)) {
            if (k.toLowerCase().includes(purposeKey) || purposeKey.includes(k.toLowerCase())) {
              sel.value = v;
            }
          }
        } else if (currentVal && currentVal !== 'default') {
          sel.value = currentVal;
        }
      });

      // Populate Hardware Fit Table
      if (modelFitTableBody) {
        modelFitTableBody.innerHTML = '';
        if (models.length === 0) {
          modelFitTableBody.innerHTML = '<tr><td colspan="5" class="p-3 text-center text-slate-400">No models discovered from active providers.</td></tr>';
        } else {
          models.forEach(r => {
            const fitText = r.fit_status || 'runnable';
            const badgeColor =
              fitText === 'optimal'
                ? 'bg-emerald-950 text-emerald-400 border-emerald-800'
                : fitText === 'runnable'
                ? 'bg-cyan-950 text-cyan-400 border-cyan-800'
                : fitText === 'cloud'
                ? 'bg-indigo-950 text-indigo-400 border-indigo-800'
                : 'bg-rose-950 text-rose-400 border-rose-800';

            const row = document.createElement('tr');
            row.innerHTML = `
              <td class="p-2.5 font-medium text-white">${escapeHtml(r.name)}</td>
              <td class="p-2.5">${r.param_size_b ? `${r.param_size_b}B` : 'Cloud'}</td>
              <td class="p-2.5 font-mono text-slate-400">${escapeHtml(r.quantization || 'cloud')}</td>
              <td class="p-2.5 font-mono text-indigo-400">${r.estimated_ram_gb > 0 ? `${r.estimated_ram_gb} GB` : 'API-Based'}</td>
              <td class="p-2.5">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${badgeColor}">
                  ${fitText}
                </span>
              </td>
            `;
            modelFitTableBody.appendChild(row);
          });
        }
      }

      if (discoverModelsBtn) {
        discoverModelsBtn.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i><span>Found (${models.length})</span>`;
        setTimeout(() => {
          discoverModelsBtn.innerHTML = '<i data-lucide="refresh-cw" class="w-3 h-3"></i><span>Refresh Models</span>';
          discoverModelsBtn.disabled = false;
          if (window.lucide) window.lucide.createIcons();
        }, 2500);
      }
    } catch (err) {
      console.error('Failed to discover models:', err);
      if (modelDiscoveryStatus) modelDiscoveryStatus.textContent = `Error querying provider: ${err.message}`;
      if (discoverModelsBtn) {
        discoverModelsBtn.innerHTML = '<i data-lucide="alert-circle" class="w-3 h-3 text-rose-400"></i><span>Error</span>';
        setTimeout(() => {
          discoverModelsBtn.innerHTML = '<i data-lucide="refresh-cw" class="w-3 h-3"></i><span>Refresh Models</span>';
          discoverModelsBtn.disabled = false;
          if (window.lucide) window.lucide.createIcons();
        }, 2500);
      }
    }
  }

  if (discoverModelsBtn) discoverModelsBtn.addEventListener('click', discoverAndPopulateModels);
  if (refreshModelsBtn) refreshModelsBtn.addEventListener('click', discoverAndPopulateModels);
  if (recalcFitBtn) recalcFitBtn.addEventListener('click', discoverAndPopulateModels);

  if (saveProvidersBtn) {
    saveProvidersBtn.addEventListener('click', async () => {
      const selectedPreset = provPresetSelect ? provPresetSelect.value : 'ollama';
      const hostUrl = provHostInput ? provHostInput.value.trim() : 'http://127.0.0.1:11434';
      const keyVal = provKeyInput ? provKeyInput.value.trim() : null;

      const payload = {
        ollama_host: selectedPreset === 'ollama' ? hostUrl : 'http://127.0.0.1:11434',
        openai_base_url: selectedPreset !== 'ollama' ? hostUrl : 'https://api.openai.com/v1',
        openai_api_key: keyVal,
        default_provider_id: selectedPreset,
      };

      try {
        await fetch('/api/settings/providers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        saveProvidersBtn.textContent = 'Saved!';
        setTimeout(() => (saveProvidersBtn.textContent = 'Save Provider'), 2000);
        await discoverAndPopulateModels();
      } catch (err) {
        console.error('Failed to save provider settings:', err);
      }
    });
  }

  if (saveMatrixBtn) {
    saveMatrixBtn.addEventListener('click', async () => {
      const payload = {
        default_model: provModelSelect ? provModelSelect.value : 'default',
        purposes: {
          general: document.getElementById('matrixGeneral')?.value || 'default',
          reasoning: document.getElementById('matrixReasoning')?.value || 'default',
          task_execution: document.getElementById('matrixTask')?.value || 'default',
          vision: document.getElementById('matrixVision')?.value || 'default',
          auxiliary: document.getElementById('matrixAux')?.value || 'default',
          fast: document.getElementById('matrixFast')?.value || 'default',
        },
      };
      try {
        await fetch('/api/settings/matrix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        saveMatrixBtn.textContent = 'Saved!';
        setTimeout(() => (saveMatrixBtn.textContent = 'Save Matrix'), 2000);
      } catch (err) {
        console.error('Failed to save matrix:', err);
      }
    });
  }

  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Initial Bootstrap
  loadAgents();
  loadSettings();
});
