/**
 * Tools Studio — catalog browse and MCP attach [CARD-421].
 * Catalog is read-only. Skill-to-tool binding stays in Skill Studio.
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
  renderMcpServerListMarkup,
  serverToSaveBody,
} from './tools_studio_catalog.js';

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

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail || data.error || `HTTP ${res.status}`;
      throw new Error(typeof detail === 'string' ? detail : `HTTP ${res.status}`);
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
    const mountedNote = data.mounted === false && data.error
      ? `Saved ${body.name}, mount failed.`
      : `Saved ${body.name}.`;
    showToast(mountedNote, data.mounted === false ? 'warning' : 'success');
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
