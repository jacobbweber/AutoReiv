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
  const newRoutineBtn = document.getElementById('newRoutineBtn');
  const routineStatusBanner = document.getElementById('routineStatusBanner');
  const routineModal = document.getElementById('routineModal');
  const routineModalTitle = document.getElementById('routineModalTitle');
  const routineModalForm = document.getElementById('routineModalForm');
  const closeRoutineModalBtn = document.getElementById('closeRoutineModalBtn');
  const cancelRoutineModalBtn = document.getElementById('cancelRoutineModalBtn');
  const routineNameInput = document.getElementById('routineNameInput');
  const routineIdInput = document.getElementById('routineIdInput');
  const routineAgentSelect = document.getElementById('routineAgentSelect');
  const routinePresetSelect = document.getElementById('routinePresetSelect');
  const routineCronInput = document.getElementById('routineCronInput');
  const routineHumanPreview = document.getElementById('routineHumanPreview');
  const routinePromptInput = document.getElementById('routinePromptInput');
  const routineEnabledInput = document.getElementById('routineEnabledInput');
  const saveRoutineBtn = document.getElementById('saveRoutineBtn');

  // Agent Forge Assigned Routines DOM
  const linkRoutineForAgentBtn = document.getElementById('linkRoutineForAgentBtn');
  const forgeAssignedRoutinesList = document.getElementById('forgeAssignedRoutinesList');

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

  // System Documentation & Specs DOM
  const docsNavTree = document.getElementById('docsNavTree');
  const docsSearchInput = document.getElementById('docsSearchInput');
  const activeDocTitle = document.getElementById('activeDocTitle');
  const activeDocPath = document.getElementById('activeDocPath');
  const copyDocPathBtn = document.getElementById('copyDocPathBtn');
  const docViewerContent = document.getElementById('docViewerContent');
  const refreshDocsNavBtn = document.getElementById('refreshDocsNavBtn');

  // Mermaid Inspector Modal DOM
  const mermaidZoomModal = document.getElementById('mermaidZoomModal');
  const mermaidModalCard = document.getElementById('mermaidModalCard');
  const mermaidModalTitle = document.getElementById('mermaidModalTitle');
  const mermaidViewport = document.getElementById('mermaidViewport');
  const mermaidCanvas = document.getElementById('mermaidCanvas');
  const mermaidZoomLevel = document.getElementById('mermaidZoomLevel');
  const mermaidZoomInBtn = document.getElementById('mermaidZoomInBtn');
  const mermaidZoomOutBtn = document.getElementById('mermaidZoomOutBtn');
  const mermaidZoomResetBtn = document.getElementById('mermaidZoomResetBtn');
  const mermaidFullscreenBtn = document.getElementById('mermaidFullscreenBtn');
  const mermaidCloseModalBtn = document.getElementById('mermaidCloseModalBtn');

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
    if (tabName === 'docs') loadSystemDocsNav();
    if (tabName === 'wiki') loadWikiVault();

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

  async function renderMarkdown(targetEl, rawMarkdown) {
    if (!targetEl) return;
    if (!window.marked) {
      targetEl.innerHTML = `<pre class="whitespace-pre-wrap font-mono text-xs text-slate-200">${escapeHtml(rawMarkdown)}</pre>`;
      return;
    }

    try {
      const parsedHtml = window.marked.parse(rawMarkdown || '');
      targetEl.innerHTML = parsedHtml;

      // Extract and convert any mermaid diagram blocks
      const mermaidBlocks = targetEl.querySelectorAll('pre code.language-mermaid, pre code.lang-mermaid, pre code.mermaid');
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

            const triggerInspector = () => openMermaidInspector(svg, 'Architecture Diagram');
            actionsDiv.querySelector('.mermaid-inspect-btn')?.addEventListener('click', (e) => {
              e.stopPropagation();
              triggerInspector();
            });
            containerDiv.addEventListener('click', triggerInspector);
          } catch (mErr) {
            console.warn('Mermaid syntax rendering fallback:', mErr);
            if (preEl) {
              preEl.classList.add('border-amber-700/60');
            }
          }
        }
        if (window.lucide) window.lucide.createIcons();
      }
    } catch (err) {
      console.warn('Markdown rendering error:', err);
    }
  }

  function appendMessageBubble(role, content, msgIdx = null) {
    const isUser = role.toLowerCase() === 'user';
    const bubble = document.createElement('div');
    bubble.className = `flex ${isUser ? 'justify-end' : 'justify-start'} w-full`;

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
        <div class="msg-body prose prose-invert text-sm break-words leading-relaxed">
        </div>
        ${copyBtnHtml}
      </div>
    `;

    messagesContainer.appendChild(bubble);
    const bodyEl = bubble.querySelector('.msg-body');
    renderMarkdown(bodyEl, content || '');

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

        await renderMarkdown(streamContentEl, fullAssistantText);
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

        await renderMarkdown(streamContentEl, fullAssistantText);
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
              if (payload.tool_name === 'handoff_to_agent') {
                const targetId = payload.arguments?.target_agent_id || 'Specialist';
                toolStatusBadgeEl.className = 'inline-flex items-center gap-1.5 px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded-full font-mono text-xs animate-pulse';
                toolStatusBadgeEl.innerHTML = `<span>🔄</span> Delegating to subagent: <strong class="text-amber-200">${escapeHtml(targetId)}</strong>...`;
              } else if (payload.tool_name === 'lookup_agents') {
                const query = payload.arguments?.query || '';
                toolStatusBadgeEl.className = 'inline-flex items-center gap-1.5 px-3 py-1 bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 rounded-full font-mono text-xs';
                toolStatusBadgeEl.innerHTML = `<span>🔍</span> JIT Agent Lookup: <em class="text-cyan-200">${escapeHtml(query)}</em>...`;
              } else {
                toolStatusBadgeEl.className = 'inline-flex items-center gap-1.5 px-3 py-1 bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 rounded-full font-mono text-xs';
                toolStatusBadgeEl.textContent = `Invoking ${payload.tool_name}...`;
              }
            } else if (eventType === 'tool_output') {
              if (toolStatusBadgeEl.textContent.includes('Delegating')) {
                toolStatusBadgeEl.className = 'inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded-full font-mono text-xs';
                toolStatusBadgeEl.innerHTML = `<span>✓</span> Subagent completed execution`;
              } else {
                toolStatusBadgeEl.textContent = `Completed tool execution.`;
              }
              setTimeout(() => toolStatusBadgeEl.classList.add('hidden'), 3500);
            } else if (eventType === 'turn_done') {
              toolStatusBadgeEl.classList.add('hidden');
            }
          }
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        await renderMarkdown(streamContentEl, fullAssistantText);
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
  // Routines Studio Management [REQ-WEB-006, REQ-ROUT-001 - REQ-ROUT-004]
  // -------------------------------------------------------------

  function getHumanCronPreview(cronStr) {
    const s = (cronStr || '').trim();
    if (!s) return 'Invalid cron expression';
    if (s === '* * * * *') return 'Every minute';
    if (s.startsWith('*/') && s.endsWith('* * * *')) return `Every ${s.slice(2, s.indexOf(' '))} minutes`;
    if (s === '0 * * * *') return 'Every hour at minute 0';
    if (s === '0 */2 * * *') return 'Every 2 hours';
    if (s === '0 8 * * *') return 'Daily at 08:00 UTC';
    if (s === '0 0 * * 0') return 'Weekly on Sunday at 00:00 UTC';
    return `Cron schedule: ${s}`;
  }

  function showRoutineBanner(msg, isError = false) {
    if (!routineStatusBanner) return;
    routineStatusBanner.textContent = msg;
    routineStatusBanner.className = `px-4 py-2 rounded-lg text-xs font-medium text-center border ${
      isError
        ? 'bg-rose-950/70 text-rose-300 border-rose-800'
        : 'bg-emerald-950/70 text-emerald-300 border-emerald-800'
    }`;
    routineStatusBanner.classList.remove('hidden');
    setTimeout(() => routineStatusBanner.classList.add('hidden'), 4000);
  }

  function populateRoutineAgentSelect(selectedAgentId = null) {
    if (!routineAgentSelect) return;
    routineAgentSelect.innerHTML = '';
    (state.agents || []).forEach(a => {
      const opt = document.createElement('option');
      opt.value = a.id;
      opt.textContent = `${a.avatar_icon ? '' : '🤖 '}${a.name} (${a.id})`;
      if (selectedAgentId && a.id === selectedAgentId) opt.selected = true;
      routineAgentSelect.appendChild(opt);
    });
  }

  function openRoutineModal(routine = null, preselectedAgentId = null) {
    if (!routineModal) return;
    populateRoutineAgentSelect(routine ? routine.agent_id : preselectedAgentId);

    if (routine) {
      if (routineModalTitle) {
        routineModalTitle.innerHTML = `<i data-lucide="edit-3" class="w-4 h-4 text-brand-400"></i><span>Edit Routine: ${escapeHtml(routine.name)}</span>`;
      }
      if (routineNameInput) routineNameInput.value = routine.name || '';
      if (routineIdInput) {
        routineIdInput.value = routine.id || '';
        routineIdInput.disabled = true;
      }
      if (routineAgentSelect) routineAgentSelect.value = routine.agent_id;
      if (routineCronInput) routineCronInput.value = routine.cron_expression || '0 * * * *';
      if (routinePresetSelect) {
        const matchingOpt = Array.from(routinePresetSelect.options).find(o => o.value === routine.cron_expression);
        routinePresetSelect.value = matchingOpt ? routine.cron_expression : 'custom';
      }
      if (routinePromptInput) routinePromptInput.value = routine.prompt || '';
      if (routineEnabledInput) routineEnabledInput.checked = routine.enabled !== false;
      if (routineHumanPreview) {
        routineHumanPreview.textContent = `Schedule: ${routine.human_schedule || getHumanCronPreview(routine.cron_expression)}`;
      }
    } else {
      if (routineModalTitle) {
        routineModalTitle.innerHTML = `<i data-lucide="plus-circle" class="w-4 h-4 text-brand-400"></i><span>Create Autonomous Routine</span>`;
      }
      if (routineNameInput) routineNameInput.value = '';
      if (routineIdInput) {
        routineIdInput.value = '';
        routineIdInput.disabled = false;
      }
      if (routinePresetSelect) routinePresetSelect.value = '0 * * * *';
      if (routineCronInput) routineCronInput.value = '0 * * * *';
      if (routinePromptInput) routinePromptInput.value = '';
      if (routineEnabledInput) routineEnabledInput.checked = true;
      if (routineHumanPreview) {
        routineHumanPreview.textContent = 'Schedule: Every hour at minute 0';
      }
    }

    routineModal.classList.remove('hidden');
    if (window.lucide) window.lucide.createIcons();
  }

  function closeRoutineModal() {
    if (routineModal) routineModal.classList.add('hidden');
  }

  async function loadRoutines() {
    try {
      const res = await fetch('/api/routines');
      const routines = await res.json();
      if (!routinesGrid) return;
      routinesGrid.innerHTML = '';

      if (routines.length === 0) {
        routinesGrid.innerHTML = `
          <div class="col-span-full p-8 text-center bg-slate-900/40 rounded-xl border border-slate-800 text-slate-400 text-xs">
            No routines configured. Click <strong>+ New Routine</strong> to create one!
          </div>
        `;
        return;
      }

      routines.forEach(r => {
        const isBuiltin = ['routine-sre-health', 'morning-briefing', 'routine-daily-brief', 'routine-wiki-prune'].includes(r.id);
        const card = document.createElement('div');
        card.className = `p-5 rounded-2xl bg-slate-900 border ${
          r.enabled ? 'border-slate-800' : 'border-slate-800/50 opacity-75'
        } flex flex-col justify-between space-y-4 hover:border-slate-700 transition shadow-sm`;

        const lastRunText = r.last_run_at ? new Date(r.last_run_at).toLocaleString() : 'Never executed';
        const statusBadge = r.enabled
          ? `<span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center space-x-1"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span><span>Active</span></span>`
          : `<span class="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 flex items-center space-x-1"><span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span><span>Paused</span></span>`;

        card.innerHTML = `
          <div class="space-y-3">
            <div class="flex items-start justify-between gap-2">
              <div>
                <div class="flex items-center space-x-2 mb-1">
                  <span class="text-xs font-semibold px-2 py-0.5 rounded bg-brand-950 text-brand-400 border border-brand-800 font-mono">${escapeHtml(r.agent_id)}</span>
                  ${statusBadge}
                </div>
                <h3 class="font-bold text-base text-white tracking-tight">${escapeHtml(r.name)}</h3>
                <span class="text-[10px] font-mono text-slate-500">${escapeHtml(r.id)}</span>
              </div>
            </div>

            <!-- Schedule & Frequency Details -->
            <div class="p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-1">
              <div class="flex items-center justify-between text-xs">
                <span class="text-slate-300 font-medium">${escapeHtml(r.human_schedule || r.cron_expression)}</span>
                <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-700">${escapeHtml(r.cron_expression || `${r.interval_seconds}s`)}</span>
              </div>
              <div class="text-[11px] text-brand-400 font-mono flex items-center space-x-1">
                <i data-lucide="clock" class="w-3 h-3"></i>
                <span>Next run ${escapeHtml(r.next_run_eta || 'scheduled')}</span>
              </div>
            </div>

            <!-- Directive Preview -->
            <div class="text-xs text-slate-300 line-clamp-2 bg-slate-950/40 p-2 rounded-lg border border-slate-800/80 font-mono text-[11px] leading-relaxed">
              "${escapeHtml(r.prompt || r.description || '')}"
            </div>

            <!-- Last Run Telemetry -->
            <div class="flex items-center justify-between text-[11px] text-slate-400 pt-1">
              <span>Last Run: <span class="text-slate-300">${lastRunText}</span></span>
              <span>Status: <strong class="${r.last_status === 'success' ? 'text-emerald-400' : 'text-slate-400'}">${escapeHtml(r.last_status)}</strong></span>
            </div>
          </div>

          <!-- Card Actions Footer -->
          <div class="pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
            <div class="flex items-center space-x-1.5">
              <button class="edit-routine-btn px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 rounded-lg transition" title="Edit Schedule & Prompt">
                Edit
              </button>
              <button class="toggle-routine-btn px-2.5 py-1 ${r.enabled ? 'bg-amber-950/40 hover:bg-amber-900/60 text-amber-300 border-amber-800/60' : 'bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-300 border-emerald-800/60'} border text-xs font-medium rounded-lg transition" title="${r.enabled ? 'Pause Routine' : 'Resume Routine'}">
                ${r.enabled ? 'Pause' : 'Resume'}
              </button>
              ${
                !isBuiltin
                  ? `<button class="delete-routine-btn px-2 py-1 bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 border border-rose-800/60 text-xs font-medium rounded-lg transition" title="Delete Routine">Delete</button>`
                  : ''
              }
            </div>
            <button class="trigger-routine-btn px-3 py-1 bg-brand-600 hover:bg-brand-500 text-xs font-semibold text-white rounded-lg shadow-sm transition flex items-center space-x-1" data-id="${r.id}">
              <i data-lucide="play" class="w-3 h-3"></i>
              <span>Run Now</span>
            </button>
          </div>
        `;
        routinesGrid.appendChild(card);

        // Edit listener
        card.querySelector('.edit-routine-btn')?.addEventListener('click', () => openRoutineModal(r));

        // Toggle listener
        card.querySelector('.toggle-routine-btn')?.addEventListener('click', async () => {
          try {
            await fetch(`/api/routines/${r.id}/toggle`, { method: 'POST' });
            showRoutineBanner(`Routine '${r.name}' ${r.enabled ? 'paused' : 'resumed'}.`);
            await loadRoutines();
          } catch (err) {
            showRoutineBanner(`Failed to toggle routine: ${err.message}`, true);
          }
        });

        // Delete listener
        card.querySelector('.delete-routine-btn')?.addEventListener('click', async () => {
          if (!confirm(`Are you sure you want to delete routine '${r.name}'?`)) return;
          try {
            const delRes = await fetch(`/api/routines/${r.id}`, { method: 'DELETE' });
            if (!delRes.ok) {
              const err = await delRes.json();
              throw new Error(err.detail || 'Delete failed');
            }
            showRoutineBanner(`Routine '${r.name}' deleted.`);
            await loadRoutines();
          } catch (err) {
            showRoutineBanner(`Failed to delete: ${err.message}`, true);
          }
        });

        // Trigger listener
        card.querySelector('.trigger-routine-btn')?.addEventListener('click', async (e) => {
          const btn = e.currentTarget;
          const origHtml = btn.innerHTML;
          btn.innerHTML = `<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i><span>Running...</span>`;
          btn.disabled = true;
          try {
            const runRes = await fetch(`/api/routines/${r.id}/run`, { method: 'POST' });
            const runData = await runRes.json();
            btn.innerHTML = `<span>Completed!</span>`;
            showRoutineBanner(`Routine '${r.name}' finished with status: ${runData.status} (${runData.duration_ms || 0}ms)`);
            setTimeout(() => {
              btn.innerHTML = origHtml;
              btn.disabled = false;
              loadRoutines();
            }, 2500);
          } catch (err) {
            btn.innerHTML = `<span>Failed</span>`;
            showRoutineBanner(`Routine execution error: ${err.message}`, true);
            setTimeout(() => {
              btn.innerHTML = origHtml;
              btn.disabled = false;
            }, 2500);
          }
        });
      });

      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      console.error('Failed to load routines:', err);
    }
  }

  // Routine Modal Listeners
  if (newRoutineBtn) {
    newRoutineBtn.addEventListener('click', () => openRoutineModal(null));
  }

  if (closeRoutineModalBtn) {
    closeRoutineModalBtn.addEventListener('click', closeRoutineModal);
  }

  if (cancelRoutineModalBtn) {
    cancelRoutineModalBtn.addEventListener('click', closeRoutineModal);
  }

  if (routinePresetSelect) {
    routinePresetSelect.addEventListener('change', () => {
      if (routinePresetSelect.value !== 'custom') {
        if (routineCronInput) routineCronInput.value = routinePresetSelect.value;
        if (routineHumanPreview) {
          routineHumanPreview.textContent = `Schedule: ${getHumanCronPreview(routinePresetSelect.value)}`;
        }
      }
    });
  }

  if (routineCronInput) {
    routineCronInput.addEventListener('input', () => {
      if (routineHumanPreview) {
        routineHumanPreview.textContent = `Schedule: ${getHumanCronPreview(routineCronInput.value)}`;
      }
    });
  }

  if (routineModalForm) {
    routineModalForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = (routineNameInput?.value || '').trim();
      const id = (routineIdInput?.value || '').trim();
      const agent_id = routineAgentSelect?.value || 'system-agent';
      const cron_expr = (routineCronInput?.value || '0 * * * *').trim();
      const prompt_template = (routinePromptInput?.value || '').trim();
      const enabled = routineEnabledInput ? routineEnabledInput.checked : true;

      if (!name || !prompt_template) {
        alert('Please provide a Routine Name and Mission Prompt.');
        return;
      }

      const payload = {
        name,
        agent_id,
        cron_expr,
        prompt_template,
        enabled,
      };
      if (id) payload.id = id;

      try {
        if (saveRoutineBtn) saveRoutineBtn.disabled = true;
        let res;
        if (id && routineIdInput?.disabled) {
          // Update existing
          res = await fetch(`/api/routines/${encodeURIComponent(id)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
        } else {
          // Create new
          res = await fetch('/api/routines', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
        }

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Save failed');
        }

        closeRoutineModal();
        showRoutineBanner(`Routine '${name}' saved successfully!`);
        await loadRoutines();
        if (activeForgeAgent) {
          await loadAgentAssignedRoutines(activeForgeAgent.id);
        }
      } catch (err) {
        alert(`Failed to save routine: ${err.message}`);
      } finally {
        if (saveRoutineBtn) saveRoutineBtn.disabled = false;
      }
    });
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
        provKeyInput.placeholder = PRESETS_DEFAULTS[p].keyPlaceholder;
      }
      if (activeProviderTag) activeProviderTag.textContent = p;
    });
  }

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
    if (!forgeSkillsGrid || !catalog) return;
    forgeSkillsGrid.innerHTML = '';

    const packs = catalog.skill_packs || [
      {
        id: 'standard-tools',
        name: 'Standard Tools',
        description: 'Available platform tools',
        icon: 'cpu',
        tools: catalog.tools || [],
      },
    ];

    packs.forEach(pack => {
      const packCard = document.createElement('div');
      packCard.className = 'p-3 rounded-xl bg-slate-800/70 border border-slate-700/80 space-y-2 col-span-full shadow-sm';

      const toolsHtml = (pack.tools || []).map(t => `
        <label class="flex items-start space-x-2 p-2 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition cursor-pointer text-xs">
          <input type="checkbox" value="${t.name}" class="forge-tool-checkbox mt-0.5 rounded border-slate-700 text-brand-500 focus:ring-brand-500" data-pack="${pack.id}">
          <div class="flex-1 min-w-0">
            <span class="font-mono text-slate-200 block text-[11px] font-semibold truncate">${escapeHtml(t.name)}</span>
            <span class="text-slate-400 block text-[10px] line-clamp-2 leading-tight">${escapeHtml(t.description || '')}</span>
          </div>
        </label>
      `).join('');

      packCard.innerHTML = `
        <div class="flex items-center justify-between pb-2 border-b border-slate-700/60">
          <div class="flex items-center space-x-2.5">
            <input type="checkbox" class="pack-master-checkbox rounded border-slate-700 text-brand-500 focus:ring-brand-500 cursor-pointer" data-pack="${pack.id}">
            <div class="w-6 h-6 rounded-lg bg-brand-600/30 border border-brand-500/50 flex items-center justify-center text-brand-400">
              <i data-lucide="${pack.icon || 'cpu'}" class="w-3.5 h-3.5"></i>
            </div>
            <div>
              <span class="font-bold text-xs text-white block">${escapeHtml(pack.name)}</span>
              <span class="text-[10px] text-slate-400 block">${escapeHtml(pack.description || '')}</span>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-700">${(pack.tools || []).length} tools</span>
            <button type="button" class="pack-collapse-btn text-slate-400 hover:text-white p-1 rounded">
              <i data-lucide="chevron-down" class="w-4 h-4 transition-transform duration-200"></i>
            </button>
          </div>
        </div>
        <div class="pack-tools-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 pt-1">
          ${toolsHtml}
        </div>
      `;

      forgeSkillsGrid.appendChild(packCard);

      // Pack Master Checkbox handler
      const masterCb = packCard.querySelector('.pack-master-checkbox');
      const toolCbs = packCard.querySelectorAll(`.forge-tool-checkbox[data-pack="${pack.id}"]`);

      masterCb.addEventListener('change', () => {
        toolCbs.forEach(cb => (cb.checked = masterCb.checked));
      });

      toolCbs.forEach(cb => {
        cb.addEventListener('change', () => {
          const allChecked = Array.from(toolCbs).every(c => c.checked);
          const someChecked = Array.from(toolCbs).some(c => c.checked);
          masterCb.checked = allChecked;
          masterCb.indeterminate = someChecked && !allChecked;
        });
      });

      // Collapse / Expand toggle
      const collapseBtn = packCard.querySelector('.pack-collapse-btn');
      const toolsGrid = packCard.querySelector('.pack-tools-grid');
      const chevron = collapseBtn.querySelector('svg, i');

      collapseBtn.addEventListener('click', () => {
        const isHidden = toolsGrid.classList.toggle('hidden');
        if (chevron) {
          chevron.style.transform = isHidden ? 'rotate(-90deg)' : 'rotate(0deg)';
        }
      });
    });

    if (window.lucide) window.lucide.createIcons();
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

    // Set Tool Checkboxes and update Pack Master checkboxes
    const allowed = new Set(agent.allowed_tool_names || agent.allowed_tools || []);
    const checkboxes = document.querySelectorAll('.forge-tool-checkbox');
    checkboxes.forEach(cb => {
      cb.checked = allowed.has(cb.value);
    });

    const masterCheckboxes = document.querySelectorAll('.pack-master-checkbox');
    masterCheckboxes.forEach(masterCb => {
      const packId = masterCb.dataset.pack;
      const packToolCbs = document.querySelectorAll(`.forge-tool-checkbox[data-pack="${packId}"]`);
      if (packToolCbs.length > 0) {
        const allChecked = Array.from(packToolCbs).every(c => c.checked);
        const someChecked = Array.from(packToolCbs).some(c => c.checked);
        masterCb.checked = allChecked;
        masterCb.indeterminate = someChecked && !allChecked;
      }
    });

    // Load Agent Telemetry & Assigned Routines
    loadAgentTelemetry(agent.id);
    loadAgentAssignedRoutines(agent.id);
  }

  function updateAvatarPreview(iconName) {
    if (forgeAvatarPreview) {
      forgeAvatarPreview.innerHTML = `<i data-lucide="${iconName}" class="w-7 h-7"></i>`;
      if (window.lucide) window.lucide.createIcons();
    }
  }

  async function loadAgentAssignedRoutines(agentId) {
    if (!forgeAssignedRoutinesList) return;
    try {
      const res = await fetch(`/api/routines?agent_id=${encodeURIComponent(agentId)}`);
      if (!res.ok) return;
      const routines = await res.json();
      forgeAssignedRoutinesList.innerHTML = '';

      if (routines.length === 0) {
        forgeAssignedRoutinesList.innerHTML = `
          <p class="text-[11px] text-slate-500 italic py-1">No scheduled background routines currently assigned to this agent.</p>
        `;
        return;
      }

      routines.forEach(r => {
        const item = document.createElement('div');
        item.className = 'p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/60 flex items-center justify-between text-xs space-x-2';
        item.innerHTML = `
          <div class="min-w-0 flex-1">
            <div class="flex items-center space-x-2">
              <span class="font-semibold text-slate-200 truncate">${escapeHtml(r.name)}</span>
              <span class="text-[9px] font-mono px-1.5 py-0.2 rounded ${r.enabled ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-amber-950 text-amber-400 border border-amber-800'}">${r.enabled ? 'Active' : 'Paused'}</span>
            </div>
            <div class="text-[10px] text-slate-400 flex items-center space-x-2 mt-0.5">
              <span>${escapeHtml(r.human_schedule || r.cron_expression)}</span>
              <span class="text-brand-400 font-mono">Next: ${escapeHtml(r.next_run_eta || 'scheduled')}</span>
            </div>
          </div>
          <div class="flex items-center space-x-1 flex-shrink-0">
            <button class="forge-routine-run-btn p-1.5 rounded bg-slate-700 hover:bg-brand-600 text-slate-200 hover:text-white transition" title="Run Routine Now">
              <i data-lucide="play" class="w-3 h-3"></i>
            </button>
            <button class="forge-routine-edit-btn p-1.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 transition" title="Edit Routine">
              <i data-lucide="edit-3" class="w-3 h-3"></i>
            </button>
          </div>
        `;
        forgeAssignedRoutinesList.appendChild(item);

        item.querySelector('.forge-routine-edit-btn')?.addEventListener('click', () => {
          const routinesTabBtn = document.querySelector('.tab-btn[data-tab="routines"]');
          if (routinesTabBtn) routinesTabBtn.click();
          openRoutineModal(r);
        });

        item.querySelector('.forge-routine-run-btn')?.addEventListener('click', async (e) => {
          const btn = e.currentTarget;
          btn.innerHTML = `<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i>`;
          try {
            await fetch(`/api/routines/${r.id}/run`, { method: 'POST' });
            btn.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i>`;
            setTimeout(() => {
              btn.innerHTML = `<i data-lucide="play" class="w-3 h-3"></i>`;
              if (window.lucide) window.lucide.createIcons();
            }, 2000);
          } catch (err) {
            btn.innerHTML = `<i data-lucide="alert-circle" class="w-3 h-3 text-rose-400"></i>`;
          }
        });
      });

      if (window.lucide) window.lucide.createIcons();
    } catch (e) {
      console.warn('Failed to load agent assigned routines:', e);
    }
  }

  if (linkRoutineForAgentBtn) {
    linkRoutineForAgentBtn.addEventListener('click', () => {
      const agentId = activeForgeAgent ? activeForgeAgent.id : (forgeAgentSelect ? forgeAgentSelect.value : null);
      openRoutineModal(null, agentId);
    });
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

  // -------------------------------------------------------------
  // System Documentation & Platform Specs Browser [REQ-SKIL-005, REQ-DOCS-001, REQ-DOCS-002]
  // -------------------------------------------------------------
  let cachedDocsNav = null;
  let activeDocPathStr = '';
  const expandedFolderPaths = new Set();
  const collapsedCategoryTitles = new Set();

  // -------------------------------------------------------------
  // Mermaid Pan-Tilt-Zoom (PTZ) Engine [REQ-DOCS-003, REQ-DOCS-004]
  // -------------------------------------------------------------
  const ptz = {
    scale: 1.0,
    panX: 0,
    panY: 0,
    isDragging: false,
    startX: 0,
    startY: 0,
  };

  function updateMermaidTransform() {
    if (!mermaidCanvas) return;
    mermaidCanvas.style.transform = `translate(${ptz.panX}px, ${ptz.panY}px) scale(${ptz.scale})`;
    if (mermaidZoomLevel) {
      mermaidZoomLevel.textContent = `${Math.round(ptz.scale * 100)}%`;
    }
  }

  function resetMermaidPTZ() {
    ptz.scale = 1.0;
    ptz.panX = 0;
    ptz.panY = 0;
    updateMermaidTransform();
  }

  function openMermaidInspector(svgHtml, title = 'Architecture Diagram') {
    if (!mermaidZoomModal || !mermaidCanvas) return;
    mermaidCanvas.innerHTML = svgHtml;
    if (mermaidModalTitle) mermaidModalTitle.textContent = title;
    resetMermaidPTZ();
    mermaidZoomModal.classList.remove('hidden');
    if (window.lucide) window.lucide.createIcons();
  }

  function closeMermaidInspector() {
    if (!mermaidZoomModal) return;
    mermaidZoomModal.classList.add('hidden');
  }

  if (mermaidCloseModalBtn) {
    mermaidCloseModalBtn.addEventListener('click', closeMermaidInspector);
  }

  if (mermaidZoomInBtn) {
    mermaidZoomInBtn.addEventListener('click', () => {
      ptz.scale = Math.min(5.0, Math.round((ptz.scale + 0.25) * 100) / 100);
      updateMermaidTransform();
    });
  }

  if (mermaidZoomOutBtn) {
    mermaidZoomOutBtn.addEventListener('click', () => {
      ptz.scale = Math.max(0.2, Math.round((ptz.scale - 0.25) * 100) / 100);
      updateMermaidTransform();
    });
  }

  if (mermaidZoomResetBtn) {
    mermaidZoomResetBtn.addEventListener('click', resetMermaidPTZ);
  }

  if (mermaidFullscreenBtn) {
    mermaidFullscreenBtn.addEventListener('click', () => {
      if (mermaidModalCard) {
        const isFull = mermaidModalCard.classList.toggle('max-w-none');
        mermaidModalCard.classList.toggle('h-screen', isFull);
        mermaidModalCard.classList.toggle('rounded-none', isFull);
        mermaidModalCard.classList.toggle('h-[85vh]', !isFull);
        mermaidModalCard.classList.toggle('max-w-6xl', !isFull);
        mermaidModalCard.classList.toggle('rounded-2xl', !isFull);
      }
    });
  }

  if (mermaidViewport) {
    // Mouse wheel zoom
    mermaidViewport.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
      ptz.scale = Math.max(0.2, Math.min(5.0, Math.round(ptz.scale * zoomFactor * 100) / 100));
      updateMermaidTransform();
    }, { passive: false });

    // Drag to Pan
    mermaidViewport.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      ptz.isDragging = true;
      ptz.startX = e.clientX - ptz.panX;
      ptz.startY = e.clientY - ptz.panY;
      mermaidViewport.classList.add('cursor-grabbing');
    });

    window.addEventListener('mousemove', (e) => {
      if (!ptz.isDragging) return;
      ptz.panX = e.clientX - ptz.startX;
      ptz.panY = e.clientY - ptz.startY;
      updateMermaidTransform();
    });

    window.addEventListener('mouseup', () => {
      if (ptz.isDragging) {
        ptz.isDragging = false;
        if (mermaidViewport) mermaidViewport.classList.remove('cursor-grabbing');
      }
    });

    // Close on backdrop click
    mermaidZoomModal?.addEventListener('click', (e) => {
      if (e.target === mermaidZoomModal) closeMermaidInspector();
    });

    // Close on Escape key
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && mermaidZoomModal && !mermaidZoomModal.classList.contains('hidden')) {
        closeMermaidInspector();
      }
    });
  }

  async function loadSystemDocsNav() {
    if (!docsNavTree) return;
    try {
      const res = await fetch('/api/system-info/topics');
      if (!res.ok) throw new Error('Failed to fetch system info topics');
      const data = await res.json();
      cachedDocsNav = data.categories || [];
      renderDocsNav(cachedDocsNav, docsSearchInput ? docsSearchInput.value : '');
    } catch (err) {
      console.error('Failed to load system info topics:', err);
      docsNavTree.innerHTML = `<p class="text-xs text-rose-400 p-2">Failed to load system info index.</p>`;
    }
  }

  function renderDocsNav(categories, filterText = '') {
    if (!docsNavTree || !categories) return;
    docsNavTree.innerHTML = '';

    const query = filterText.toLowerCase().trim();

    categories.forEach(cat => {
      const matchingTopics = (cat.topics || []).filter(t => {
        if (!query) return true;
        return (
          t.title.toLowerCase().includes(query) ||
          t.summary.toLowerCase().includes(query) ||
          t.id.toLowerCase().includes(query) ||
          cat.title.toLowerCase().includes(query)
        );
      });

      if (matchingTopics.length === 0 && query) return;

      const isCategoryExpanded = query ? true : !collapsedCategoryTitles.has(cat.title);

      const catContainer = document.createElement('div');
      catContainer.className = 'space-y-1';

      const catHeader = document.createElement('button');
      catHeader.type = 'button';
      catHeader.className = 'w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group text-left';
      catHeader.innerHTML = `
        <div class="flex items-center space-x-1.5 min-w-0 truncate">
          <i data-lucide="${isCategoryExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform flex-shrink-0"></i>
          <i data-lucide="${cat.icon || 'layers'}" class="w-3.5 h-3.5 text-brand-400 flex-shrink-0"></i>
          <span class="truncate">${escapeHtml(cat.title)}</span>
        </div>
        <span class="text-slate-600 font-mono text-[10px]">(${matchingTopics.length})</span>
      `;

      catHeader.addEventListener('click', () => {
        if (collapsedCategoryTitles.has(cat.title)) {
          collapsedCategoryTitles.delete(cat.title);
        } else {
          collapsedCategoryTitles.add(cat.title);
        }
        renderDocsNav(categories, filterText);
      });

      catContainer.appendChild(catHeader);

      const catBody = document.createElement('div');
      catBody.className = `space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isCategoryExpanded ? '' : 'hidden'}`;

      matchingTopics.forEach(topic => {
        const isActive = topic.id === activeDocPathStr;
        const topicBtn = document.createElement('button');
        topicBtn.type = 'button';
        topicBtn.dataset.topicId = topic.id;
        topicBtn.className = `doc-nav-item w-full text-left px-2.5 py-2 rounded-lg text-xs transition block flex flex-col space-y-0.5 ${isActive ? 'bg-brand-600/30 text-brand-200 font-semibold border border-brand-500/40 shadow-sm' : 'text-slate-300 hover:text-white hover:bg-slate-800/70 border border-transparent'}`;
        topicBtn.innerHTML = `
          <div class="flex items-center space-x-1.5 min-w-0 truncate">
            <i data-lucide="${topic.icon || 'file-text'}" class="w-3.5 h-3.5 text-amber-400 flex-shrink-0"></i>
            <span class="truncate font-medium">${escapeHtml(topic.title)}</span>
          </div>
          <p class="text-[10px] text-slate-400 line-clamp-1 pl-5 font-normal">${escapeHtml(topic.summary)}</p>
        `;
        topicBtn.addEventListener('click', () => loadSystemInfoTopic(topic.id));
        catBody.appendChild(topicBtn);
      });

      catContainer.appendChild(catBody);
      docsNavTree.appendChild(catContainer);
    });

    if (window.lucide) window.lucide.createIcons();

    // Default load first topic if none loaded
    if (!activeDocPathStr && categories.length > 0 && categories[0].topics && categories[0].topics.length > 0) {
      loadSystemInfoTopic(categories[0].topics[0].id);
    }
  }

  async function loadSystemInfoTopic(topicId) {
    if (!docViewerContent) return;
    activeDocPathStr = topicId;

    // Update active highlight in sidebar
    document.querySelectorAll('.doc-nav-item').forEach(btn => {
      if (btn.dataset.topicId === topicId) {
        btn.className = 'doc-nav-item w-full text-left px-2.5 py-2 rounded-lg text-xs transition block flex flex-col space-y-0.5 bg-brand-600/30 text-brand-200 font-semibold border border-brand-500/40 shadow-sm';
      } else {
        btn.className = 'doc-nav-item w-full text-left px-2.5 py-2 rounded-lg text-xs transition block flex flex-col space-y-0.5 text-slate-300 hover:text-white hover:bg-slate-800/70 border border-transparent';
      }
    });

    if (activeDocPath) activeDocPath.textContent = `#${topicId}`;
    if (activeDocTitle) activeDocTitle.textContent = topicId.replace(/-/g, ' ').toUpperCase();

    docViewerContent.innerHTML = `
      <div class="p-8 text-center text-slate-400">
        <i data-lucide="loader-2" class="w-8 h-8 mx-auto mb-2 text-brand-400 animate-spin"></i>
        <p class="text-xs">Loading system manual topic...</p>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();

    try {
      const res = await fetch(`/api/system-info/topic/${encodeURIComponent(topicId)}`);
      if (!res.ok) throw new Error('Failed to load topic content');
      const data = await res.json();

      if (activeDocTitle) activeDocTitle.textContent = data.title || topicId;

      await renderMarkdown(docViewerContent, data.content);

      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      console.error('Failed to fetch topic content:', err);
      docViewerContent.innerHTML = `
        <div class="p-6 rounded-xl bg-rose-950/40 border border-rose-900 text-rose-300 text-xs">
          <p class="font-bold mb-1">Failed to load topic</p>
          <p class="font-mono">${escapeHtml(err.message)}</p>
        </div>
      `;
    }
  }

  if (docsSearchInput) {
    docsSearchInput.addEventListener('input', () => {
      if (cachedDocsNav) {
        renderDocsNav(cachedDocsNav, docsSearchInput.value);
      }
    });
  }

  if (refreshDocsNavBtn) {
    refreshDocsNavBtn.addEventListener('click', () => {
      loadSystemDocsNav();
    });
  }

  if (copyDocPathBtn) {
    copyDocPathBtn.addEventListener('click', async () => {
      if (activeDocPathStr) {
        await navigator.clipboard.writeText(window.location.origin + '/#topic=' + activeDocPathStr);
        copyDocPathBtn.querySelector('span').textContent = 'Copied!';
        setTimeout(() => (copyDocPathBtn.querySelector('span').textContent = 'Copy Link'), 2000);
      }
    });
  }

  // -------------------------------------------------------------
  // Wiki Studio & Knowledge Warehouse Controller [REQ-WIKI-006]
  // -------------------------------------------------------------
  const wikiNavTree = document.getElementById('wikiNavTree');
  const wikiSearchInput = document.getElementById('wikiSearchInput');
  const refreshWikiTreeBtn = document.getElementById('refreshWikiTreeBtn');
  const wikiNewNoteBtn = document.getElementById('wikiNewNoteBtn');
  const wikiGraphViewBtn = document.getElementById('wikiGraphViewBtn');

  const activeWikiTitle = document.getElementById('activeWikiTitle');
  const activeWikiPath = document.getElementById('activeWikiPath');
  const wikiModePreviewBtn = document.getElementById('wikiModePreviewBtn');
  const wikiModeEditBtn = document.getElementById('wikiModeEditBtn');
  const wikiSaveNoteBtn = document.getElementById('wikiSaveNoteBtn');
  const wikiDeleteNoteBtn = document.getElementById('wikiDeleteNoteBtn');

  const wikiFrontmatterCard = document.getElementById('wikiFrontmatterCard');
  const fmUidBadge = document.getElementById('fmUidBadge');
  const fmTypeBadge = document.getElementById('fmTypeBadge');
  const fmStatusBadge = document.getElementById('fmStatusBadge');
  const fmDomainPill = document.getElementById('fmDomainPill');
  const fmTopicPill = document.getElementById('fmTopicPill');
  const fmTelemetryPill = document.getElementById('fmTelemetryPill');
  const fmSummaryText = document.getElementById('fmSummaryText');
  const fmTagsContainer = document.getElementById('fmTagsContainer');

  const wikiViewerContent = document.getElementById('wikiViewerContent');
  const wikiEditorTextarea = document.getElementById('wikiEditorTextarea');

  // Modals
  const wikiNewNoteModal = document.getElementById('wikiNewNoteModal');
  const wikiNewNoteCloseBtn = document.getElementById('wikiNewNoteCloseBtn');
  const wikiNewNoteCancelBtn = document.getElementById('wikiNewNoteCancelBtn');
  const wikiNewNoteSubmitBtn = document.getElementById('wikiNewNoteSubmitBtn');
  const newNoteTitleInput = document.getElementById('newNoteTitleInput');
  const newNoteCategorySelect = document.getElementById('newNoteCategorySelect');
  const newNoteInboxPrioGroup = document.getElementById('newNoteInboxPrioGroup');
  const newNoteInboxPrioSelect = document.getElementById('newNoteInboxPrioSelect');
  const newNoteTypeGroup = document.getElementById('newNoteTypeGroup');
  const newNoteTypeSelect = document.getElementById('newNoteTypeSelect');
  const newNoteDomainGroup = document.getElementById('newNoteDomainGroup');
  const newNoteDomainInput = document.getElementById('newNoteDomainInput');
  const newNoteTopicInput = document.getElementById('newNoteTopicInput');
  const newNoteTagsInput = document.getElementById('newNoteTagsInput');
  const newNoteSummaryInput = document.getElementById('newNoteSummaryInput');
  const newNoteBodyInput = document.getElementById('newNoteBodyInput');

  const wikiGraphModal = document.getElementById('wikiGraphModal');
  const wikiGraphCloseBtn = document.getElementById('wikiGraphCloseBtn');
  const wikiGraphContainer = document.getElementById('wikiGraphContainer');

  let cachedWikiTree = null;
  let activeWikiNotePath = '';
  let activeWikiNoteData = null;
  let wikiEditorMode = 'preview'; // 'preview' | 'edit'
  const expandedWikiFolders = new Set(['inbox', 'notes', 'resources']);

  async function loadWikiVault() {
    if (!wikiNavTree) return;
    try {
      const res = await fetch('/api/wiki/tree');
      if (!res.ok) throw new Error('Failed to load wiki tree');
      cachedWikiTree = await res.json();
      renderWikiTree(cachedWikiTree, wikiSearchInput ? wikiSearchInput.value : '');
    } catch (err) {
      console.error('Failed to load wiki tree:', err);
      wikiNavTree.innerHTML = `<p class="text-xs text-rose-400 p-2">Failed to load wiki tree: ${escapeHtml(err.message)}</p>`;
    }
  }

  function renderWikiTree(tree, filterText = '') {
    if (!wikiNavTree || !tree) return;
    wikiNavTree.innerHTML = '';
    const query = filterText.toLowerCase().trim();

    // 1. INBOX Section
    const inboxEntries = tree.inbox || {};
    const totalInboxNotes = Object.values(inboxEntries).reduce((acc, arr) => acc + arr.length, 0);

    const inboxWrapper = document.createElement('div');
    inboxWrapper.className = 'space-y-1';
    const isInboxExpanded = query ? true : expandedWikiFolders.has('inbox');

    inboxWrapper.innerHTML = `
      <button type="button" class="wiki-folder-toggle w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group text-left">
        <div class="flex items-center space-x-1.5 min-w-0 truncate">
          <i data-lucide="${isInboxExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
          <i data-lucide="inbox" class="w-3.5 h-3.5 text-amber-400"></i>
          <span>inbox (Staging)</span>
        </div>
        <span class="text-slate-600 font-mono text-[10px]">(${totalInboxNotes})</span>
      </button>
      <div class="wiki-inbox-body space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isInboxExpanded ? '' : 'hidden'}"></div>
    `;

    const inboxToggle = inboxWrapper.querySelector('.wiki-folder-toggle');
    inboxToggle.addEventListener('click', () => {
      if (expandedWikiFolders.has('inbox')) expandedWikiFolders.delete('inbox');
      else expandedWikiFolders.add('inbox');
      renderWikiTree(tree, filterText);
    });

    const inboxBody = inboxWrapper.querySelector('.wiki-inbox-body');
    ['need_to_do', 'should_do', 'want_to_do'].forEach(prio => {
      const notes = inboxEntries[prio] || [];
      const matching = notes.filter(n => !query || n.title.toLowerCase().includes(query) || (n.tags || []).some(t => t.toLowerCase().includes(query)));
      if (matching.length === 0 && query) return;

      const subWrapper = document.createElement('div');
      subWrapper.className = 'space-y-0.5';
      subWrapper.innerHTML = `
        <div class="text-[10px] font-semibold text-slate-400 px-2 py-0.5 flex items-center justify-between">
          <span class="font-mono text-slate-500">${prio}</span>
          <span class="text-[9px] text-slate-600">(${matching.length})</span>
        </div>
      `;
      matching.forEach(n => {
        const itemBtn = createNoteTreeButton(n);
        subWrapper.appendChild(itemBtn);
      });
      inboxBody.appendChild(subWrapper);
    });

    wikiNavTree.appendChild(inboxWrapper);

    // 2. NOTES (Warehouse) Section
    const notesTree = tree.notes || {};
    let totalWarehouseNotes = 0;
    Object.values(notesTree).forEach(dom => {
      Object.values(dom).forEach(topicNotes => totalWarehouseNotes += topicNotes.length);
    });

    const notesWrapper = document.createElement('div');
    notesWrapper.className = 'space-y-1';
    const isNotesExpanded = query ? true : expandedWikiFolders.has('notes');

    notesWrapper.innerHTML = `
      <button type="button" class="wiki-folder-toggle w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group text-left">
        <div class="flex items-center space-x-1.5 min-w-0 truncate">
          <i data-lucide="${isNotesExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
          <i data-lucide="book-marked" class="w-3.5 h-3.5 text-brand-400"></i>
          <span>notes (Warehouse)</span>
        </div>
        <span class="text-slate-600 font-mono text-[10px]">(${totalWarehouseNotes})</span>
      </button>
      <div class="wiki-notes-body space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isNotesExpanded ? '' : 'hidden'}"></div>
    `;

    const notesToggle = notesWrapper.querySelector('.wiki-folder-toggle');
    notesToggle.addEventListener('click', () => {
      if (expandedWikiFolders.has('notes')) expandedWikiFolders.delete('notes');
      else expandedWikiFolders.add('notes');
      renderWikiTree(tree, filterText);
    });

    const notesBody = notesWrapper.querySelector('.wiki-notes-body');
    Object.entries(notesTree).forEach(([domain, topicMap]) => {
      const domainKey = `notes_${domain}`;
      const isDomainExpanded = query ? true : expandedWikiFolders.has(domainKey);

      let domainCount = 0;
      Object.values(topicMap).forEach(arr => domainCount += arr.length);

      const domainWrapper = document.createElement('div');
      domainWrapper.className = 'space-y-0.5';
      domainWrapper.innerHTML = `
        <button type="button" class="w-full text-left px-2 py-1 rounded-md text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 flex items-center justify-between transition group">
          <div class="flex items-center space-x-1.5 min-w-0 truncate">
            <i data-lucide="${isDomainExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
            <i data-lucide="graduation-cap" class="w-3.5 h-3.5 text-amber-400"></i>
            <span class="truncate text-[11px] font-mono">${escapeHtml(domain)}</span>
          </div>
          <span class="text-[10px] font-mono text-slate-500">(${domainCount})</span>
        </button>
        <div class="domain-topics-body space-y-0.5 pl-3 border-l border-slate-800/80 ml-2 ${isDomainExpanded ? '' : 'hidden'}"></div>
      `;

      domainWrapper.querySelector('button').addEventListener('click', () => {
        if (expandedWikiFolders.has(domainKey)) expandedWikiFolders.delete(domainKey);
        else expandedWikiFolders.add(domainKey);
        renderWikiTree(tree, filterText);
      });

      const topicsBody = domainWrapper.querySelector('.domain-topics-body');
      Object.entries(topicMap).forEach(([topic, noteList]) => {
        const matching = noteList.filter(n => !query || n.title.toLowerCase().includes(query) || (n.tags || []).some(t => t.toLowerCase().includes(query)) || domain.toLowerCase().includes(query) || topic.toLowerCase().includes(query));
        if (matching.length === 0 && query) return;

        const topicWrapper = document.createElement('div');
        topicWrapper.className = 'space-y-0.5';
        topicWrapper.innerHTML = `
          <div class="text-[10px] font-semibold text-slate-400 px-2 py-0.5 flex items-center space-x-1">
            <i data-lucide="folder" class="w-3 h-3 text-sky-400"></i>
            <span class="font-mono text-sky-300">${escapeHtml(topic)}</span>
            <span class="text-[9px] text-slate-600">(${matching.length})</span>
          </div>
        `;
        matching.forEach(n => {
          const itemBtn = createNoteTreeButton(n);
          topicWrapper.appendChild(itemBtn);
        });
        topicsBody.appendChild(topicWrapper);
      });

      notesBody.appendChild(domainWrapper);
    });

    wikiNavTree.appendChild(notesWrapper);

    // 3. RESOURCES Section
    const resTree = tree.resources || {};
    let totalResNotes = 0;
    Object.values(resTree).forEach(arr => totalResNotes += arr.length);

    const resWrapper = document.createElement('div');
    resWrapper.className = 'space-y-1';
    const isResExpanded = query ? true : expandedWikiFolders.has('resources');

    resWrapper.innerHTML = `
      <button type="button" class="wiki-folder-toggle w-full flex items-center justify-between text-slate-400 hover:text-white font-bold uppercase tracking-wider text-[10px] px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition group text-left">
        <div class="flex items-center space-x-1.5 min-w-0 truncate">
          <i data-lucide="${isResExpanded ? 'chevron-down' : 'chevron-right'}" class="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition-transform"></i>
          <i data-lucide="archive" class="w-3.5 h-3.5 text-purple-400"></i>
          <span>resources (Aids/Templates)</span>
        </div>
        <span class="text-slate-600 font-mono text-[10px]">(${totalResNotes})</span>
      </button>
      <div class="wiki-res-body space-y-1 pl-2 border-l border-slate-800/80 ml-2.5 ${isResExpanded ? '' : 'hidden'}"></div>
    `;

    const resToggle = resWrapper.querySelector('.wiki-folder-toggle');
    resToggle.addEventListener('click', () => {
      if (expandedWikiFolders.has('resources')) expandedWikiFolders.delete('resources');
      else expandedWikiFolders.add('resources');
      renderWikiTree(tree, filterText);
    });

    const resBody = resWrapper.querySelector('.wiki-res-body');
    ['operating_manuals', 'templates'].forEach(sub => {
      const notes = resTree[sub] || [];
      const matching = notes.filter(n => !query || n.title.toLowerCase().includes(query));
      if (matching.length === 0 && query) return;

      const subWrapper = document.createElement('div');
      subWrapper.className = 'space-y-0.5';
      subWrapper.innerHTML = `
        <div class="text-[10px] font-semibold text-slate-400 px-2 py-0.5 flex items-center justify-between">
          <span class="font-mono text-purple-400">${sub}</span>
          <span class="text-[9px] text-slate-600">(${matching.length})</span>
        </div>
      `;
      matching.forEach(n => {
        const itemBtn = createNoteTreeButton(n);
        subWrapper.appendChild(itemBtn);
      });
      resBody.appendChild(subWrapper);
    });

    wikiNavTree.appendChild(resWrapper);

    if (window.lucide) window.lucide.createIcons();
  }

  function createNoteTreeButton(note) {
    const isActive = note.path === activeWikiNotePath;
    const itemBtn = document.createElement('button');
    itemBtn.type = 'button';
    itemBtn.dataset.path = note.path;
    itemBtn.className = `wiki-note-item w-full text-left px-2 py-1 rounded-md text-xs transition truncate block flex items-center justify-between ${isActive ? 'bg-brand-600/30 text-brand-300 font-semibold border border-brand-500/30' : 'text-slate-300 hover:text-white hover:bg-slate-800/70'}`;
    itemBtn.innerHTML = `
      <div class="flex items-center space-x-1.5 min-w-0 truncate">
        <i data-lucide="file-text" class="w-3 h-3 text-slate-400 flex-shrink-0"></i>
        <span class="truncate text-[11px]">${escapeHtml(note.title)}</span>
      </div>
    `;
    itemBtn.addEventListener('click', () => loadWikiNote(note.path));
    return itemBtn;
  }

  async function loadWikiNote(relPath) {
    if (!wikiViewerContent || !wikiEditorTextarea) return;
    activeWikiNotePath = relPath;

    // Highlight in sidebar
    document.querySelectorAll('.wiki-note-item').forEach(btn => {
      if (btn.dataset.path === relPath) {
        btn.className = 'wiki-note-item w-full text-left px-2 py-1 rounded-md text-xs transition truncate block flex items-center justify-between bg-brand-600/30 text-brand-300 font-semibold border border-brand-500/30';
      } else {
        btn.className = 'wiki-note-item w-full text-left px-2 py-1 rounded-md text-xs transition truncate block flex items-center justify-between text-slate-300 hover:text-white hover:bg-slate-800/70';
      }
    });

    if (activeWikiPath) activeWikiPath.textContent = relPath;
    if (activeWikiTitle) activeWikiTitle.textContent = relPath.split('/').pop().replace(/\.md$/, '').replace(/_/g, ' ').toUpperCase();

    wikiViewerContent.innerHTML = `
      <div class="p-8 text-center text-slate-400">
        <i data-lucide="loader-2" class="w-8 h-8 mx-auto mb-2 text-brand-400 animate-spin"></i>
        <p class="text-xs">Loading note...</p>
      </div>
    `;
    if (window.lucide) window.lucide.createIcons();

    try {
      const res = await fetch(`/api/wiki/note?path=${encodeURIComponent(relPath)}`);
      if (!res.ok) throw new Error('Failed to load note');
      const data = await res.json();
      activeWikiNoteData = data;

      if (activeWikiTitle) activeWikiTitle.textContent = data.title || (data.meta && data.meta.title) || relPath;

      // Populate Frontmatter Inspector
      if (wikiFrontmatterCard && data.meta) {
        const meta = data.meta;
        if (fmUidBadge) fmUidBadge.textContent = meta.uid ? `UID: ${meta.uid}` : '';
        if (fmTypeBadge) fmTypeBadge.textContent = meta.document_type || 'note';
        if (fmStatusBadge) fmStatusBadge.textContent = meta.status || 'draft';
        if (fmDomainPill) fmDomainPill.textContent = meta.domain ? `🎓 ${meta.domain}` : '';
        if (fmTopicPill) fmTopicPill.textContent = meta.topic ? `📖 ${meta.topic}` : '';
        if (fmTelemetryPill) fmTelemetryPill.textContent = `Words: ${meta.word_count || 0} | Tokens: ${meta.context_tokens || 0}`;

        if (fmSummaryText) {
          fmSummaryText.textContent = meta.summary || 'No summary provided.';
          fmSummaryText.classList.toggle('hidden', !meta.summary);
        }

        if (fmTagsContainer) {
          fmTagsContainer.innerHTML = (meta.tags || []).map(t => `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[9px] border border-slate-700">#${escapeHtml(t)}</span>`).join('');
        }
        wikiFrontmatterCard.classList.remove('hidden');
      }

      // Populate Body
      wikiEditorTextarea.value = data.content || '';
      await renderMarkdown(wikiViewerContent, data.content || '');

      setWikiViewMode('preview');
      if (window.lucide) window.lucide.createIcons();
    } catch (err) {
      console.error('Failed to load note content:', err);
      wikiViewerContent.innerHTML = `
        <div class="p-6 rounded-xl bg-rose-950/40 border border-rose-900 text-rose-300 text-xs">
          <p class="font-bold mb-1">Failed to load note</p>
          <p class="font-mono">${escapeHtml(err.message)}</p>
        </div>
      `;
    }
  }

  function setWikiViewMode(mode) {
    wikiEditorMode = mode;
    if (mode === 'edit') {
      wikiViewerContent.classList.add('hidden');
      wikiEditorTextarea.classList.remove('hidden');
      wikiModeEditBtn.className = 'px-2 py-1 text-[11px] font-medium rounded-md bg-brand-600 text-white transition';
      wikiModePreviewBtn.className = 'px-2 py-1 text-[11px] font-medium rounded-md text-slate-400 hover:text-slate-200 transition';
      wikiEditorTextarea.focus();
    } else {
      wikiEditorTextarea.classList.add('hidden');
      wikiViewerContent.classList.remove('hidden');
      wikiModePreviewBtn.className = 'px-2 py-1 text-[11px] font-medium rounded-md bg-brand-600 text-white transition';
      wikiModeEditBtn.className = 'px-2 py-1 text-[11px] font-medium rounded-md text-slate-400 hover:text-slate-200 transition';
      if (wikiViewerContent && wikiEditorTextarea) {
        renderMarkdown(wikiViewerContent, wikiEditorTextarea.value);
      }
    }
  }

  if (wikiModePreviewBtn) wikiModePreviewBtn.addEventListener('click', () => setWikiViewMode('preview'));
  if (wikiModeEditBtn) wikiModeEditBtn.addEventListener('click', () => setWikiViewMode('edit'));

  if (wikiSaveNoteBtn) {
    wikiSaveNoteBtn.addEventListener('click', async () => {
      if (!activeWikiNotePath) return;
      const content = wikiEditorTextarea.value;
      try {
        const res = await fetch('/api/wiki/note', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            path: activeWikiNotePath,
            content: content,
          }),
        });
        if (!res.ok) throw new Error('Failed to save note');
        wikiSaveNoteBtn.querySelector('span').textContent = 'Saved!';
        setTimeout(() => (wikiSaveNoteBtn.querySelector('span').textContent = 'Save'), 2000);
        await loadWikiNote(activeWikiNotePath);
      } catch (err) {
        console.error('Failed to save note:', err);
        alert('Failed to save note: ' + err.message);
      }
    });
  }

  if (wikiDeleteNoteBtn) {
    wikiDeleteNoteBtn.addEventListener('click', async () => {
      if (!activeWikiNotePath) return;
      if (!confirm(`Are you sure you want to delete note '${activeWikiNotePath}'?`)) return;
      try {
        const res = await fetch(`/api/wiki/note?path=${encodeURIComponent(activeWikiNotePath)}`, {
          method: 'DELETE',
        });
        if (!res.ok) throw new Error('Failed to delete note');
        activeWikiNotePath = '';
        activeWikiNoteData = null;
        if (wikiFrontmatterCard) wikiFrontmatterCard.classList.add('hidden');
        wikiViewerContent.innerHTML = `<div class="p-8 text-center text-slate-400"><p class="text-sm">Note deleted.</p></div>`;
        await loadWikiVault();
      } catch (err) {
        console.error('Failed to delete note:', err);
        alert('Failed to delete note: ' + err.message);
      }
    });
  }

  if (wikiSearchInput) {
    wikiSearchInput.addEventListener('input', () => {
      if (cachedWikiTree) renderWikiTree(cachedWikiTree, wikiSearchInput.value);
    });
  }

  if (refreshWikiTreeBtn) {
    refreshWikiTreeBtn.addEventListener('click', () => loadWikiVault());
  }

  // New Note Modal Handlers
  if (wikiNewNoteBtn) {
    wikiNewNoteBtn.addEventListener('click', () => {
      if (wikiNewNoteModal) {
        wikiNewNoteModal.classList.remove('hidden');
        if (newNoteTitleInput) newNoteTitleInput.value = '';
        if (newNoteSummaryInput) newNoteSummaryInput.value = '';
        if (newNoteTagsInput) newNoteTagsInput.value = '';
        if (newNoteBodyInput) newNoteBodyInput.value = '';
        if (window.lucide) window.lucide.createIcons();
      }
    });
  }

  if (wikiNewNoteCloseBtn) wikiNewNoteCloseBtn.addEventListener('click', () => wikiNewNoteModal.classList.add('hidden'));
  if (wikiNewNoteCancelBtn) wikiNewNoteCancelBtn.addEventListener('click', () => wikiNewNoteModal.classList.add('hidden'));

  if (newNoteCategorySelect) {
    newNoteCategorySelect.addEventListener('change', () => {
      const val = newNoteCategorySelect.value;
      if (newNoteInboxPrioGroup) newNoteInboxPrioGroup.classList.toggle('hidden', val !== 'inbox');
      if (newNoteDomainGroup) newNoteDomainGroup.classList.toggle('hidden', val === 'inbox' || val === 'resources');
      if (newNoteTypeGroup) newNoteTypeGroup.classList.toggle('hidden', val === 'inbox');
    });
  }

  if (wikiNewNoteSubmitBtn) {
    wikiNewNoteSubmitBtn.addEventListener('click', async () => {
      const title = newNoteTitleInput.value.trim();
      if (!title) {
        alert('Please enter a note title.');
        return;
      }
      const category = newNoteCategorySelect.value;
      const domain = newNoteDomainInput.value.trim() || 'general';
      const topic = newNoteTopicInput.value.trim() || 'general';
      const inbox_priority = newNoteInboxPrioSelect.value;
      const document_type = newNoteTypeSelect.value;
      const tags = newNoteTagsInput.value.split(',').map(t => t.trim()).filter(Boolean);
      const summary = newNoteSummaryInput.value.trim();
      const content = newNoteBodyInput.value.trim();

      try {
        const res = await fetch('/api/wiki/note', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title,
            category,
            domain,
            topic,
            inbox_priority,
            document_type,
            tags,
            summary,
            content,
          }),
        });
        if (!res.ok) throw new Error('Failed to create note');
        const data = await res.json();
        wikiNewNoteModal.classList.add('hidden');
        await loadWikiVault();
        if (data.path) await loadWikiNote(data.path);
      } catch (err) {
        console.error('Failed to create note:', err);
        alert('Failed to create note: ' + err.message);
      }
    });
  }

  // Knowledge Graph Modal
  if (wikiGraphViewBtn) {
    wikiGraphViewBtn.addEventListener('click', async () => {
      if (!wikiGraphModal || !wikiGraphContainer) return;
      wikiGraphContainer.innerHTML = `<i data-lucide="loader-2" class="w-8 h-8 mx-auto text-indigo-400 animate-spin"></i>`;
      wikiGraphModal.classList.remove('hidden');
      if (window.lucide) window.lucide.createIcons();

      try {
        const res = await fetch('/api/wiki/graph');
        if (!res.ok) throw new Error('Failed to load wiki graph');
        const graph = await res.json();

        if (graph.nodes.length === 0) {
          wikiGraphContainer.innerHTML = `<p class="text-xs text-slate-400">No notes in the wiki yet.</p>`;
          return;
        }

        // Build Mermaid Flowchart diagram
        let mermaidSrc = 'flowchart TD\n';
        graph.nodes.forEach(n => {
          const safeId = n.id.replace(/[^a-zA-Z0-9]/g, '_');
          const label = n.title.replace(/"/g, "'");
          mermaidSrc += `  ${safeId}["${label}"]\n`;
        });
        graph.edges.forEach(e => {
          const srcId = e.source.replace(/[^a-zA-Z0-9]/g, '_');
          const tgtId = e.target.replace(/[^a-zA-Z0-9]/g, '_');
          mermaidSrc += `  ${srcId} --> ${tgtId}\n`;
        });

        wikiGraphContainer.innerHTML = `<div class="mermaid">${mermaidSrc}</div>`;
        if (window.mermaid) {
          await window.mermaid.run({ nodes: wikiGraphContainer.querySelectorAll('.mermaid') });
        }
      } catch (err) {
        console.error('Failed to render graph:', err);
        wikiGraphContainer.innerHTML = `<p class="text-xs text-rose-400">Failed to render graph: ${escapeHtml(err.message)}</p>`;
      }
    });
  }

  if (wikiGraphCloseBtn) wikiGraphCloseBtn.addEventListener('click', () => wikiGraphModal.classList.add('hidden'));

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
