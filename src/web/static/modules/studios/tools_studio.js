/**
 * Tools Studio — catalog browse, MCP attach, and tool intent [CARD-421, CARD-422].
 * Create, modify, and delete intents go through the form and the developer.
 * There is no code editor. Packaging preference is a note for the developer.
 * Native and MCP lanes are built by the developer, not by this form.
 * Platform attach uses /api/settings/mcp*. Agent attach uses /api/agents/{id}/mcp*.
 * MCP hosting stays in Settings.
 */

import { $, escapeHtml, safeCreateIcons } from '../dom.js';
import { showToast } from '../ui/toast.js';
import { storageSet } from '../utils/storage.js';
import { PICKER_KEYS } from './agent_picker.js';
import {
  TOOLS_STUDIO_LABEL,
  TOOLS_STUDIO_TAB,
  buildMcpSaveBody,
  fetchMcpServers,
  filterCatalogGroups,
  loadCatalogModel,
  mcpEndpoints,
  planToolsStudioDeepLink,
  renderCatalogMarkup,
  describeMcpSaveNotice,
  renderMcpServerListMarkup,
  serverToSaveBody,
} from './tools_studio_catalog.js';
import {
  TOOLS_AUTHORING_JOBS_URL,
  TOOLS_AUTHORING_TALK_URL,
  authoringErrorMessage,
  intentValidationError,
  interpretAuthoringSubmit,
  interpretAuthoringTalk,
  normalizeToolIntentDraft,
} from './tools_studio_authoring.js';

export { TOOLS_STUDIO_LABEL, TOOLS_STUDIO_TAB, planToolsStudioDeepLink };

let activeController = null;

export function getToolsStudio() {
  return activeController;
}

function setHidden(id, hidden) {
  const el = $(id);
  if (!el) return;
  el.classList.toggle('hidden', hidden);
}

export function initToolsStudio(_state, callbacks = {}) {
  const catalogEl = $('toolsStudioCatalog');
  const listEl = $('toolsStudioMcpList');
  const formEl = $('toolsStudioMcpForm');
  const resultEl = $('toolsStudioMcpTestResult');
  const scopeEl = $('toolsStudioScopeSelect');
  const agentEl = $('toolsStudioAgentSelect');
  const nameEl = $('toolsStudioMcpNameInput');
  const transportEl = $('toolsStudioMcpTransportSelect');
  const commandEl = $('toolsStudioMcpCommandInput');
  const urlEl = $('toolsStudioMcpUrlInput');
  const headersEl = $('toolsStudioMcpHeadersInput');
  const enabledEl = $('toolsStudioMcpEnabledCheckbox');
  const envRowsEl = $('toolsStudioMcpEnvRows');
  const searchEl = $('toolsStudioFilterSearch');
  const sourceEl = $('toolsStudioFilterSource');
  const statusEl = $('toolsStudioFilterStatus');
  const intentEl = $('toolsStudioIntentSelect');
  const toolNameEl = $('toolsStudioToolNameInput');
  const behaviorEl = $('toolsStudioBehaviorInput');
  const languageEl = $('toolsStudioLanguageInput');
  const runtimeEl = $('toolsStudioRuntimeInput');
  const pathEl = $('toolsStudioPathInput');
  const packagingEl = $('toolsStudioPackagingSelect');
  const authoringStatusEl = $('toolsStudioAuthoringStatus');
  let authoringBusy = false;

  let queuedLink = null;
  let shownServers = [];
  let editingName = '';
  let catalogGroups = [];
  let listBound = false;

  function readScope() {
    return scopeEl && scopeEl.value === 'agent' ? 'agent' : 'platform';
  }

  function readAgentId() {
    return agentEl ? String(agentEl.value || '').trim() : '';
  }

  function readFilters() {
    return {
      search: searchEl ? searchEl.value : '',
      source: sourceEl ? sourceEl.value : '',
      status: statusEl ? statusEl.value : '',
    };
  }

  function syncScopeChrome() {
    const agentScope = readScope() === 'agent';
    setHidden('toolsStudioAgentField', !agentScope);
  }

  function syncTransportChrome() {
    const sse = transportEl && transportEl.value === 'sse';
    setHidden('toolsStudioMcpCommandGroup', Boolean(sse));
    setHidden('toolsStudioMcpUrlGroup', !sse);
    setHidden('toolsStudioMcpHeadersGroup', !sse);
  }

  function paintCatalog() {
    if (!catalogEl) return;
    catalogEl.innerHTML = renderCatalogMarkup(filterCatalogGroups(catalogGroups, readFilters()));
  }

  function paintList() {
    if (!listEl) return;
    listEl.innerHTML = renderMcpServerListMarkup(shownServers, { scope: readScope() });
  }

  function showResult(kind, html) {
    if (!resultEl) return;
    resultEl.classList.remove('hidden');
    if (kind === 'ok') {
      resultEl.className = 'p-3 rounded-lg border border-emerald-800/80 bg-emerald-950/40 text-emerald-300 text-xs space-y-1';
    } else if (kind === 'error') {
      resultEl.className = 'p-3 rounded-lg border border-rose-800/80 bg-rose-950/40 text-rose-300 text-xs space-y-1';
    } else {
      resultEl.className = 'p-3 rounded-lg border border-white/[0.06] bg-[#08090c] text-slate-300 text-xs';
    }
    resultEl.innerHTML = html;
    safeCreateIcons();
  }

  function clearForm() {
    editingName = '';
    if (nameEl) {
      nameEl.value = '';
      nameEl.readOnly = false;
    }
    if (transportEl) transportEl.value = 'stdio';
    if (commandEl) commandEl.value = '';
    if (urlEl) urlEl.value = '';
    if (headersEl) headersEl.value = '';
    if (enabledEl) enabledEl.checked = true;
    if (envRowsEl) envRowsEl.innerHTML = '';
    if (resultEl) resultEl.classList.add('hidden');
    syncTransportChrome();
    const title = $('toolsStudioMcpFormTitle');
    if (title) title.textContent = 'Add MCP server';
  }

  function addEnvRow(key = '', val = '') {
    if (!envRowsEl) return;
    const row = document.createElement('div');
    row.className = 'tools-studio-env-row flex items-center gap-2';
    row.innerHTML = `
      <input type="text" value="${escapeHtml(key)}" placeholder="KEY" class="tools-studio-env-key flex-1 bg-[#08090c] border border-white/[0.08] rounded-lg px-2 py-1 text-xs font-mono text-slate-100">
      <input type="password" value="${escapeHtml(val)}" placeholder="Value" class="tools-studio-env-val flex-1 bg-[#08090c] border border-white/[0.08] rounded-lg px-2 py-1 text-xs font-mono text-slate-100">
      <button type="button" class="tools-studio-env-remove px-2 py-1 text-[11px] text-slate-400 hover:text-rose-300">Remove</button>
    `;
    const removeBtn = row.querySelector('.tools-studio-env-remove');
    if (removeBtn) removeBtn.addEventListener('click', () => row.remove());
    envRowsEl.appendChild(row);
  }

  function readEnv() {
    const env = {};
    if (!envRowsEl) return env;
    envRowsEl.querySelectorAll('.tools-studio-env-row').forEach((row) => {
      const key = row.querySelector('.tools-studio-env-key');
      const val = row.querySelector('.tools-studio-env-val');
      const k = key ? key.value.trim() : '';
      if (k) env[k] = val ? val.value : '';
    });
    return env;
  }

  function formFields(enabledOverride) {
    return {
      name: nameEl ? nameEl.value : '',
      transport: transportEl ? transportEl.value : 'stdio',
      commandText: commandEl ? commandEl.value : '',
      url: urlEl ? urlEl.value : '',
      headersText: headersEl ? headersEl.value : '',
      env: readEnv(),
      enabled: enabledOverride == null ? Boolean(enabledEl && enabledEl.checked) : Boolean(enabledOverride),
    };
  }

  function fillForm(server) {
    if (!formEl) return;
    formEl.classList.remove('hidden');
    editingName = String(server.name || '');
    if (nameEl) {
      nameEl.value = editingName;
      nameEl.readOnly = true;
    }
    const transport = server.transport || (server.url ? 'sse' : 'stdio');
    if (transportEl) transportEl.value = transport === 'sse' ? 'sse' : 'stdio';
    if (commandEl) {
      commandEl.value = Array.isArray(server.command) ? server.command.join(' ') : String(server.command || '');
    }
    if (urlEl) urlEl.value = server.url || '';
    if (headersEl) headersEl.value = server.headers ? JSON.stringify(server.headers) : '';
    if (enabledEl) enabledEl.checked = server.enabled !== false;
    if (envRowsEl) envRowsEl.innerHTML = '';
    const env = server.env && typeof server.env === 'object' ? server.env : {};
    Object.keys(env).forEach((key) => addEnvRow(key, env[key]));
    syncTransportChrome();
    const title = $('toolsStudioMcpFormTitle');
    if (title) title.textContent = `Edit ${editingName}`;
  }

  function findServer(name) {
    return shownServers.find((server) => server && server.name === name) || null;
  }

  async function refreshCatalog() {
    try {
      const catalogAgentId = readScope() === 'agent' ? readAgentId() : '';
      catalogGroups = await loadCatalogModel(fetch, { agentId: catalogAgentId });
    } catch (err) {
      console.error('[Tools Studio] Failed to load catalog:', err);
      catalogGroups = [];
      showToast('Could not load the tool catalog.', 'error');
    }
    paintCatalog();
  }

  async function refreshMcpList() {
    const scope = readScope();
    const agentId = readAgentId();
    if (scope === 'agent' && !agentId) {
      shownServers = [];
      paintList();
      return;
    }
    try {
      shownServers = await fetchMcpServers(fetch, scope, agentId);
    } catch (err) {
      console.error('[Tools Studio] Failed to load MCP servers:', err);
      shownServers = [];
      showToast('Could not load MCP servers.', 'error');
    }
    paintList();
  }

  async function refresh() {
    syncScopeChrome();
    await Promise.all([refreshCatalog(), refreshMcpList()]);
  }

  function applyDeepLink(link) {
    const plan = planToolsStudioDeepLink(link || {});
    if (scopeEl) scopeEl.value = plan.scope;
    if (plan.agentId) {
      storageSet(PICKER_KEYS.tools, plan.agentId);
      if (agentEl) agentEl.value = plan.agentId;
    }
    syncScopeChrome();
  }

  function readIntentDraft() {
    return normalizeToolIntentDraft({
      intent: intentEl ? intentEl.value : 'create',
      tool_name: toolNameEl ? toolNameEl.value : '',
      behavior: behaviorEl ? behaviorEl.value : '',
      language_hint: languageEl ? languageEl.value : '',
      runtime_hint: runtimeEl ? runtimeEl.value : '',
      path_context: pathEl ? pathEl.value : '',
      packaging_preference: packagingEl ? packagingEl.value : '',
    });
  }

  function showAuthoringStatus(kind, html) {
    if (!authoringStatusEl) return;
    authoringStatusEl.classList.remove('hidden');
    if (kind === 'ok') {
      authoringStatusEl.className = 'p-3 rounded-lg border border-emerald-800/80 bg-emerald-950/40 text-emerald-200 text-xs space-y-2';
    } else if (kind === 'error') {
      authoringStatusEl.className = 'p-3 rounded-lg border border-rose-800/80 bg-rose-950/40 text-rose-200 text-xs space-y-1';
    } else {
      authoringStatusEl.className = 'p-3 rounded-lg border border-white/[0.06] bg-[#08090c] text-slate-300 text-xs';
    }
    authoringStatusEl.innerHTML = html;
  }

  function fillIntent(intent, toolName) {
    if (intentEl) intentEl.value = intent === 'modify' || intent === 'delete' ? intent : 'create';
    if (toolNameEl) toolNameEl.value = toolName || '';
    const form = $('toolsStudioIntentForm');
    if (form && typeof form.scrollIntoView === 'function') form.scrollIntoView({ block: 'nearest' });
    if (behaviorEl) behaviorEl.focus();
  }

  async function openDeveloperChat(plan) {
    if (typeof callbacks.switchTab === 'function') callbacks.switchTab('chat');
    const chat = typeof callbacks.getChatCtrl === 'function' ? callbacks.getChatCtrl() : null;
    if (chat && typeof chat.openDeveloperSession === 'function') {
      await chat.openDeveloperSession(plan.sessionId, plan.prompt);
      return;
    }
    const promptInput = $('promptInput');
    if (promptInput && plan.prompt) {
      promptInput.value = plan.prompt;
      promptInput.focus();
    }
  }

  async function onTalk() {
    let draft;
    try {
      draft = readIntentDraft();
    } catch (err) {
      showAuthoringStatus('error', `<div>${escapeHtml(err.message || String(err))}</div>`);
      return;
    }
    const problem = intentValidationError(draft);
    if (problem) {
      showAuthoringStatus('error', `<div>${escapeHtml(problem)}</div>`);
      showToast(problem, 'warning');
      return;
    }
    if (authoringBusy) return;
    authoringBusy = true;
    try {
      const data = await postJson(TOOLS_AUTHORING_TALK_URL, { intent: draft.intent, draft });
      const plan = interpretAuthoringTalk(data, draft);
      showAuthoringStatus('ok', `<div>Opened developer chat <span class="font-mono">${escapeHtml(plan.sessionId)}</span> with this tool intent.</div>`);
      await openDeveloperChat(plan);
      showToast('Opened a new developer chat with this tool intent.', 'success');
    } catch (err) {
      showAuthoringStatus('error', `<div>${escapeHtml(err.message || String(err))}</div>`);
      showToast(err.message || String(err), 'error');
    } finally {
      authoringBusy = false;
    }
  }

  async function onSubmitIntent() {
    let draft;
    try {
      draft = readIntentDraft();
    } catch (err) {
      showAuthoringStatus('error', `<div>${escapeHtml(err.message || String(err))}</div>`);
      return;
    }
    const problem = intentValidationError(draft);
    if (problem) {
      showAuthoringStatus('error', `<div>${escapeHtml(problem)}</div>`);
      showToast(problem, 'warning');
      return;
    }
    if (authoringBusy) return;
    authoringBusy = true;
    showAuthoringStatus('info', '<div>Asking the developer to run this tool intent…</div>');
    try {
      const res = await fetch(TOOLS_AUTHORING_JOBS_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intent: draft.intent, draft }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(authoringErrorMessage(data, res.status));
      const plan = interpretAuthoringSubmit(data);
      const openBtn = `<button type="button" id="toolsStudioOpenDeveloperChatBtn" data-testid="tools-studio-open-developer-chat" class="px-2.5 py-1 rounded-lg bg-cyan-700 hover:bg-cyan-600 text-white text-[11px] font-semibold">Open developer chat</button>`;
      showAuthoringStatus(
        'ok',
        `<div>Developer job <span class="font-mono">${escapeHtml(plan.jobId)}</span> is ${escapeHtml(plan.status)}. Packaging was not applied.</div><div class="whitespace-pre-wrap text-slate-100">${escapeHtml(plan.reply)}</div>${openBtn}`,
      );
      const open = $('toolsStudioOpenDeveloperChatBtn');
      if (open) open.addEventListener('click', () => { openDeveloperChat(plan).catch((err) => showToast(err.message || String(err), 'error')); });
      showToast(`Developer job ${plan.jobId} is ${plan.status}.`, 'success');
    } catch (err) {
      showAuthoringStatus('error', `<div>${escapeHtml(err.message || String(err))}</div>`);
      showToast(err.message || String(err), 'error');
    } finally {
      authoringBusy = false;
    }
  }

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail || data.error || data.message;
      if (typeof detail === 'string' && detail.trim()) throw new Error(detail.trim());
      if (detail && typeof detail.message === 'string' && detail.message.trim()) throw new Error(detail.message.trim());
      throw new Error(authoringErrorMessage(data, res.status));
    }
    return data;
  }

  function describeProbe(data) {
    if (data && data.status === 'ok') {
      const tools = Array.isArray(data.tools) ? data.tools : [];
      const names = tools.map((tool) => (typeof tool === 'string' ? tool : tool.name)).filter(Boolean);
      const count = data.tools_count != null ? data.tools_count : names.length;
      return {
        kind: 'ok',
        html: `<div>Handshake ok (${escapeHtml(String(data.latency_ms || 0))} ms). ${escapeHtml(String(count))} tools.</div><div class="font-mono text-[11px]">${escapeHtml(names.join(', ') || 'No tool names returned.')}</div>`,
      };
    }
    return {
      kind: 'error',
      html: `<div>Handshake failed${data && data.latency_ms != null ? ` (${escapeHtml(String(data.latency_ms))} ms)` : ''}.</div><div class="font-mono text-[11px] whitespace-pre-wrap">${escapeHtml((data && (data.error || data.detail)) || 'Unknown error')}</div>`,
    };
  }

  async function saveBody(body) {
    const scope = readScope();
    const agentId = readAgentId();
    if (scope === 'agent' && !agentId) {
      showToast('Select an agent before saving an agent MCP server.', 'warning');
      return null;
    }
    const endpoints = mcpEndpoints(scope, agentId);
    const data = await postJson(endpoints.save, body);
    const notice = describeMcpSaveNotice(body, data);
    showToast(notice.message, notice.kind === 'warning' ? 'warning' : 'success');
    if (data.error) showResult('error', `<div>${escapeHtml(String(data.error))}</div>`);
    return data;
  }

  async function onSave() {
    const built = buildMcpSaveBody(formFields());
    if (!built.ok) {
      showResult('error', `<div>${escapeHtml(built.error)}</div>`);
      return;
    }
    try {
      const data = await saveBody(built.body);
      if (!data) return;
      if (formEl) formEl.classList.add('hidden');
      clearForm();
      await refresh();
    } catch (err) {
      showResult('error', `<div>${escapeHtml(err.message || String(err))}</div>`);
    }
  }

  async function onTestForm() {
    const built = buildMcpSaveBody(formFields(true));
    if (!built.ok) {
      showResult('error', `<div>${escapeHtml(built.error)}</div>`);
      return;
    }
    const scope = readScope();
    const agentId = readAgentId();
    if (scope === 'agent' && !agentId) {
      showToast('Select an agent before testing an agent MCP server.', 'warning');
      return;
    }
    try {
      showResult('info', '<div>Testing handshake…</div>');
      const data = await postJson(mcpEndpoints(scope, agentId).test, built.body);
      const view = describeProbe(data);
      showResult(view.kind, view.html);
    } catch (err) {
      showResult('error', `<div>${escapeHtml(err.message || String(err))}</div>`);
    }
  }

  async function onToggle(server) {
    const next = server.enabled === false;
    try {
      await saveBody(serverToSaveBody(server, next));
      await refresh();
    } catch (err) {
      showToast(err.message || String(err), 'error');
    }
  }

  async function onDelete(server) {
    const name = server.name;
    if (typeof window !== 'undefined' && typeof window.confirm === 'function') {
      const ok = window.confirm(`Remove MCP server '${name}'?`);
      if (!ok) return;
    }
    const scope = readScope();
    const agentId = readAgentId();
    try {
      const res = await fetch(mcpEndpoints(scope, agentId).delete(name), { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showToast(`Removed ${name}.`, 'info');
      await refresh();
    } catch (err) {
      showToast(err.message || String(err), 'error');
    }
  }

  async function onConnect(server) {
    const scope = readScope();
    const agentId = readAgentId();
    const endpoints = mcpEndpoints(scope, agentId);
    try {
      if (scope === 'agent' && endpoints.mount) {
        const data = await postJson(endpoints.mount(server.name), {});
        if (data.status && data.status !== 'mounted') {
          showToast(data.error || data.detail || 'Connect failed.', 'error');
        } else {
          showToast(`Connected ${server.name}.`, 'success');
        }
      } else {
        await saveBody(serverToSaveBody(server, true));
      }
      await refresh();
    } catch (err) {
      showToast(err.message || String(err), 'error');
    }
  }

  async function onTestSaved(server) {
    const scope = readScope();
    const agentId = readAgentId();
    try {
      showResult('info', '<div>Testing handshake…</div>');
      const data = await postJson(mcpEndpoints(scope, agentId).test, serverToSaveBody(server, true));
      const view = describeProbe(data);
      showResult(view.kind, view.html);
    } catch (err) {
      showResult('error', `<div>${escapeHtml(err.message || String(err))}</div>`);
    }
  }

  function bindList() {
    if (!listEl || listBound) return;
    listBound = true;
    listEl.addEventListener('click', (event) => {
      const target = event.target;
      if (!target || typeof target.closest !== 'function') return;
      const btn = target.closest('[data-action]');
      if (!btn || !listEl.contains(btn)) return;
      const action = btn.getAttribute('data-action');
      const name = btn.getAttribute('data-server-name');
      const server = findServer(name);
      if (!server) return;
      if (action === 'edit') fillForm(server);
      else if (action === 'toggle') onToggle(server);
      else if (action === 'delete') onDelete(server);
      else if (action === 'connect') onConnect(server);
      else if (action === 'test-saved') onTestSaved(server);
    });
  }

  function bindChrome() {
    bindList();
    if (scopeEl) {
      scopeEl.addEventListener('change', () => {
        refresh().catch((err) => console.error('[Tools Studio] Scope refresh failed:', err));
      });
    }
    if (agentEl) {
      agentEl.addEventListener('change', () => {
        if (agentEl.value) storageSet(PICKER_KEYS.tools, agentEl.value);
        refresh().catch((err) => console.error('[Tools Studio] Agent refresh failed:', err));
      });
    }
    [searchEl, sourceEl, statusEl].forEach((el) => {
      if (!el) return;
      el.addEventListener('input', paintCatalog);
      el.addEventListener('change', paintCatalog);
    });
    if (catalogEl && !catalogEl.dataset.intentBound) {
      catalogEl.dataset.intentBound = '1';
      catalogEl.addEventListener('click', (event) => {
        const target = event.target;
        if (!target || typeof target.closest !== 'function') return;
        const btn = target.closest('[data-action]');
        if (!btn || !catalogEl.contains(btn)) return;
        const action = btn.getAttribute('data-action');
        const toolName = btn.getAttribute('data-tool-name') || '';
        if (action === 'tools-studio-modify') fillIntent('modify', toolName);
        else if (action === 'tools-studio-delete-intent') fillIntent('delete', toolName);
      });
    }
    const newIntentBtn = $('toolsStudioNewIntentBtn');
    if (newIntentBtn) {
      newIntentBtn.addEventListener('click', () => {
        fillIntent('create', '');
        if (behaviorEl) behaviorEl.value = '';
        if (languageEl) languageEl.value = '';
        if (runtimeEl) runtimeEl.value = '';
        if (pathEl) pathEl.value = '';
        if (packagingEl) packagingEl.value = '';
      });
    }
    const intentForm = $('toolsStudioIntentForm');
    if (intentForm) {
      intentForm.addEventListener('submit', (event) => {
        event.preventDefault();
        onTalk();
      });
    }
    const talkBtn = $('toolsStudioTalkBtn');
    if (talkBtn) talkBtn.addEventListener('click', () => { onTalk(); });
    const submitBtn = $('toolsStudioSubmitBtn');
    if (submitBtn) submitBtn.addEventListener('click', () => { onSubmitIntent(); });
    const clearBtn = $('toolsStudioFilterClearBtn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (searchEl) searchEl.value = '';
        if (sourceEl) sourceEl.value = '';
        if (statusEl) statusEl.value = '';
        paintCatalog();
      });
    }
    if (transportEl) transportEl.addEventListener('change', syncTransportChrome);
    const addBtn = $('toolsStudioAddMcpBtn');
    if (addBtn && formEl) {
      addBtn.addEventListener('click', () => {
        clearForm();
        formEl.classList.remove('hidden');
      });
    }
    const cancelBtn = $('toolsStudioMcpCancelBtn');
    if (cancelBtn && formEl) {
      cancelBtn.addEventListener('click', () => {
        formEl.classList.add('hidden');
        clearForm();
      });
    }
    const addEnvBtn = $('toolsStudioAddEnvRowBtn');
    if (addEnvBtn) addEnvBtn.addEventListener('click', () => addEnvRow());
    const saveBtn = $('toolsStudioMcpSaveBtn');
    if (saveBtn) saveBtn.addEventListener('click', () => { onSave(); });
    const testBtn = $('toolsStudioMcpTestBtn');
    if (testBtn) testBtn.addEventListener('click', () => { onTestForm(); });
    syncTransportChrome();
    syncScopeChrome();
  }

  bindChrome();

  const controller = {
    queueDeepLink(link) {
      queuedLink = planToolsStudioDeepLink(link || {});
    },
    async loadToolsStudio() {
      if (queuedLink) {
        applyDeepLink(queuedLink);
        queuedLink = null;
      }
      await refresh();
    },
  };

  activeController = controller;
  if (typeof window !== 'undefined' && typeof callbacks.openToolsStudio === 'function') {
    window.openToolsStudio = (link = {}) => {
      const plan = planToolsStudioDeepLink(link);
      callbacks.openToolsStudio(plan.agentId, plan.scope);
    };
  }
  return controller;
}
