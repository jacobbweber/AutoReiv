/**
 * Agent Studio: Tools, Baseline Callables, Remote MCP & Credential Grants Submodule [CARD-183, CARD-330, CARD-350, CARD-389, CARD-398]
 * Manages OS baseline tool representations, tool badges, capability gap triage,
 * remote MCP server lifecycle (mount, probe, add, delete), and credential vault grants.
 */

import { $, $queryAll, safeCreateIcons } from '../../dom.js';
import { escapeHtml } from '../../utils/formatters.js';
import { showToast } from '../../ui/toast.js';

export function renderToolBadgeHtml(tool, activeAgent = null) {
  const tObj = typeof tool === 'string' ? { name: tool } : (tool || {});
  const name = tObj.name || '';
  const isMcp = Boolean(
    tObj.is_mcp ||
    tObj.deliverable_type === 'mcp' ||
    tObj.type === 'mcp' ||
    name.startsWith('mcp_') ||
    (activeAgent && activeAgent.mcp_server && activeAgent.mcp_server.enabled)
  );
  return isMcp
    ? '<span class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-indigo-950/80 text-indigo-300 border border-indigo-800/80 uppercase tracking-wide">MCP Server</span>'
    : '<span class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-slate-800/80 text-slate-400 border border-slate-700/80 uppercase tracking-wide">Native Tool</span>';
}

export function baselineToolCardHtml(tool) {
  const tObj = typeof tool === 'string' ? { name: tool, description: '' } : (tool || {});
  const name = tObj.name || '';
  const desc = tObj.description || '';
  return `
    <div class="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-emerald-950/70 border border-emerald-700/60 text-xs text-slate-200 select-none shadow-sm" title="${escapeHtml(desc)}">
      <input type="checkbox" checked disabled class="hidden" title="Enforced platform required for all agents">
      <i data-lucide="lock" class="w-3 h-3 text-emerald-400 shrink-0"></i>
      <span class="font-mono text-[11px] font-semibold text-emerald-200">${escapeHtml(name)}</span>
      <span class="px-1 py-0.2 rounded text-[8px] font-mono font-bold bg-emerald-900/80 text-emerald-300 border border-emerald-600/50 uppercase">OS BASELINE</span>
    </div>
  `;
}

export function renderBaselineTools(gridEl = null) {
  const grid = gridEl || $('forgeBaselineGrid');
  if (!grid) return;
  const requiredPrimitives = [
    { name: 'activate_skill', description: 'Activate a procedural skill runbook into the current session context.' },
    { name: 'ask_clarification', description: 'Ask the human operator a clarifying question when requirements are ambiguous.' },
    { name: 'handoff_to_agent', description: 'Handoff the conversation or task to another agent specialist.' },
    { name: 'lookup_agents', description: 'Query available agents and their capabilities.' },
    { name: 'get_session_info', description: 'Inspect active session metadata and runtime state.' },
  ];
  grid.innerHTML = requiredPrimitives.map((t) => baselineToolCardHtml(t)).join('');
  safeCreateIcons();
}

export async function loadAgentCapabilityGaps(agentId, callbacks = {}) {
  const agentBacklogList = $('agentBacklogList');
  const agentBacklogCountBadge = $('agentBacklogCountBadge');
  const forgeTrainAgentBtn = $('forgeTrainAgentBtn');
  if (!agentBacklogList) return;
  if (!agentId) {
    agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
    if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = '0';
    return;
  }
  try {
    const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/gaps?status=pending`);
    const data = res.ok ? await res.json() : {};
    const items = Array.isArray(data) ? data : (data.gaps || []);
    if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = String(items.length);
    if (!items.length) {
      agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
      return;
    }
    agentBacklogList.innerHTML = items.map((gap) => `
      <div class="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800 space-y-1.5" data-gap-id="${escapeHtml(gap.id)}">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold text-amber-300 font-mono">${escapeHtml(gap.identified_capability || gap.missing_capability || 'Missing Capability')}</span>
          <div class="flex items-center space-x-1.5">
            <button type="button" class="btn-open-factory-gap px-2 py-0.5 rounded bg-brand-600 hover:bg-brand-500 text-white text-[10px] font-semibold transition" data-gap-id="${escapeHtml(gap.id)}" title="Open Training Factory for this agent">Open Training Factory</button>
            <button type="button" class="btn-dismiss-gap px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 text-[10px] font-medium transition" data-gap-id="${escapeHtml(gap.id)}">Dismiss</button>
          </div>
        </div>
        ${gap.suggested_tool_name ? `<div class="text-[10px] text-slate-400 font-mono">Suggested tool: <span class="text-emerald-400">${escapeHtml(gap.suggested_tool_name)}</span></div>` : ''}
        <p class="text-[11px] text-slate-400 whitespace-pre-wrap">${escapeHtml(gap.turn_text || gap.user_prompt || '')}</p>
      </div>
    `).join('');

    agentBacklogList.querySelectorAll('.btn-open-factory-gap').forEach((btn) => {
      btn.addEventListener('click', () => {
        // CARD-306: Forge does not launch a second lab — open Training Factory for this agent
        if (typeof callbacks.openFactoryStudio === 'function') {
          callbacks.openFactoryStudio(agentId);
        } else if (typeof window !== 'undefined' && typeof window.openFactoryStudioForAgent === 'function') {
          window.openFactoryStudioForAgent(agentId);
        } else if (typeof forgeTrainAgentBtn !== 'undefined' && forgeTrainAgentBtn) {
          forgeTrainAgentBtn.click();
        } else {
          showToast('Open Factory Studio from the dock to train this gap.', 'info');
        }
      });
    });

    agentBacklogList.querySelectorAll('.btn-dismiss-gap').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const gapId = e.currentTarget.dataset.gapId;
        try {
          const delRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/gaps/${encodeURIComponent(gapId)}`, { method: 'DELETE' });
          if (!delRes.ok) throw new Error('Failed to dismiss gap');
          showToast('Capability gap dismissed', 'info');
          await loadAgentCapabilityGaps(agentId, callbacks);
        } catch (err) {
          showToast(String(err.message || err), 'error');
        }
      });
    });
  } catch (err) {
    console.warn('[AutoReiv UI] Failed to load capability gaps:', err);
    agentBacklogList.innerHTML = '<p class="text-[11px] text-slate-500">No capability gaps queued.</p>';
    if (agentBacklogCountBadge) agentBacklogCountBadge.textContent = '0';
  }
}

export function renderAgentMcpServers(agentId, servers, { getActiveAgent = null, onServersChanged = null } = {}) {
  const forgeMcpServerList = $('forgeMcpServerList');
  const forgeMcpServerCountBadge = $('forgeMcpServerCountBadge');
  if (!forgeMcpServerList) return;
  if (forgeMcpServerCountBadge) {
    forgeMcpServerCountBadge.textContent = String(servers.length);
  }
  if (!servers.length) {
    forgeMcpServerList.innerHTML = '<p id="forgeMcpServerEmpty" class="text-[11px] text-slate-500">No remote MCP servers configured for this agent.</p>';
    return;
  }

  forgeMcpServerList.innerHTML = servers.map((s) => {
    const isMounted = Boolean(s.is_mounted);
    const isEnabled = s.enabled !== false;
    const toolCount = s.tool_count || (s.tools ? s.tools.length : 0);
    const target = s.url || s.command || 'N/A';
    return `
      <div class="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-2" data-server-name="${escapeHtml(s.name)}">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <span class="text-xs font-bold text-slate-200 font-mono">${escapeHtml(s.name)}</span>
            <span class="px-1.5 py-0.5 rounded text-[10px] font-mono uppercase bg-cyan-950/70 text-cyan-400 border border-cyan-800/60">${escapeHtml(s.transport || 'sse')}</span>
            ${isEnabled 
              ? (isMounted 
                  ? `<span class="px-1.5 py-0.5 rounded text-[10px] bg-emerald-950/70 text-emerald-400 border border-emerald-800/60 flex items-center space-x-1">
                      <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                      <span>Mounted (${toolCount} tools)</span>
                     </span>`
                  : '<span class="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700">Enabled</span>')
              : '<span class="px-1.5 py-0.5 rounded text-[10px] bg-slate-900 text-slate-500 border border-slate-800">Disabled</span>'
            }
          </div>
          <div class="flex items-center space-x-1.5">
            ${!isMounted && isEnabled ? `
              <button type="button" class="btn-mount-server px-2 py-1 bg-emerald-950/60 hover:bg-emerald-900 text-emerald-300 border border-emerald-800 rounded text-[11px] font-medium flex items-center space-x-1 transition" data-server-name="${escapeHtml(s.name)}" title="Connect/Mount this MCP server">
                <i data-lucide="play" class="w-3 h-3"></i>
                <span>Connect</span>
              </button>
            ` : ''}
            <button type="button" class="btn-probe-server px-2 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-800/60 rounded text-[11px] font-medium flex items-center space-x-1 transition" data-server-name="${escapeHtml(s.name)}" title="Test connection probe">
              <i data-lucide="activity" class="w-3 h-3"></i>
              <span>Probe</span>
            </button>
            <button type="button" class="btn-delete-server px-2 py-1 bg-slate-800 hover:bg-rose-900/60 text-slate-400 hover:text-rose-300 border border-slate-700 rounded text-[11px] font-medium flex items-center space-x-1 transition" data-server-name="${escapeHtml(s.name)}" title="Remove this MCP server">
              <i data-lucide="trash-2" class="w-3 h-3"></i>
              <span>Delete</span>
            </button>
          </div>
        </div>
        <div class="text-[11px] font-mono text-slate-400 truncate">
          <span class="text-slate-500">Endpoint:</span> ${escapeHtml(target)}
        </div>
        <div class="server-probe-result hidden p-2 rounded text-[11px] font-mono border"></div>
      </div>
    `;
  }).join('');

  safeCreateIcons();

  forgeMcpServerList.querySelectorAll('.btn-mount-server').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const sName = e.currentTarget.dataset.serverName;
      const card = btn.closest('[data-server-name]');
      const resultEl = card ? card.querySelector('.server-probe-result') : null;
      if (resultEl) {
        resultEl.classList.remove('hidden');
        resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-slate-900 border-slate-700 text-slate-300';
        resultEl.textContent = 'Connecting to MCP server...';
      }
      try {
        const mountRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp/${encodeURIComponent(sName)}/mount`, {
          method: 'POST',
        });
        const data = await mountRes.json();
        if (data.status === 'mounted') {
          await loadAgentMcpServers(agentId, { getActiveAgent, onServersChanged });
        } else {
          if (resultEl) {
            resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
            resultEl.textContent = `Mount failed: ${data.detail || 'Unknown error'}`;
          }
        }
      } catch (err) {
        if (resultEl) {
          resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
          resultEl.textContent = `Mount error: ${err.message || err}`;
        }
      }
    });
  });

  forgeMcpServerList.querySelectorAll('.btn-probe-server').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const sName = e.currentTarget.dataset.serverName;
      const card = btn.closest('[data-server-name]');
      const resultEl = card ? card.querySelector('.server-probe-result') : null;
      if (resultEl) {
        resultEl.classList.remove('hidden');
        resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-slate-900 border-slate-700 text-slate-300';
        resultEl.textContent = 'Testing connection...';
      }
      try {
        const testRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp/${encodeURIComponent(sName)}/probe`, {
          method: 'POST',
        });
        const data = await testRes.json();
        if (resultEl) {
          if (data.status === 'ok') {
            resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-emerald-950/60 border-emerald-800 text-emerald-300';
            resultEl.textContent = `✓ OK (${data.latency_ms}ms) - ${data.tools_count} tool(s) found: ${(data.tools || []).join(', ')}`;
          } else {
            resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
            resultEl.textContent = `✗ Probe failed: ${data.error || 'Unknown error'}`;
          }
        }
      } catch (err) {
        if (resultEl) {
          resultEl.className = 'server-probe-result p-2 rounded text-[11px] font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
          resultEl.textContent = `✗ Probe error: ${err.message || err}`;
        }
      }
    });
  });

  forgeMcpServerList.querySelectorAll('.btn-delete-server').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const sName = e.currentTarget.dataset.serverName;
      if (!window.confirm(`Remove MCP server '${sName}' from this agent?`)) return;
      try {
        const delRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp/${encodeURIComponent(sName)}`, {
          method: 'DELETE',
        });
        if (!delRes.ok) throw new Error('Failed to delete server');
        showToast(`MCP server '${sName}' removed`, 'info');
        await loadAgentMcpServers(agentId, { getActiveAgent, onServersChanged });
      } catch (err) {
        showToast(`Failed to delete server: ${err.message || err}`, 'error');
      }
    });
  });
}

export async function loadAgentMcpServers(agentId, { getActiveAgent = null, onServersChanged = null } = {}) {
  const forgeMcpServerList = $('forgeMcpServerList');
  const forgeMcpServerCountBadge = $('forgeMcpServerCountBadge');
  if (!forgeMcpServerList) return [];
  if (!agentId) {
    forgeMcpServerList.innerHTML = '<p id="forgeMcpServerEmpty" class="text-[11px] text-slate-500">No remote MCP servers configured for this agent.</p>';
    if (forgeMcpServerCountBadge) forgeMcpServerCountBadge.textContent = '0';
    return [];
  }
  try {
    const res = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp`);
    const servers = res.ok ? await res.json() : [];
    const currentAgentMcpServers = Array.isArray(servers) ? servers : [];
    const activeAgent = typeof getActiveAgent === 'function' ? getActiveAgent() : null;
    if (activeAgent) {
      activeAgent.mcp_servers = currentAgentMcpServers;
    }
    if (typeof onServersChanged === 'function') {
      onServersChanged(currentAgentMcpServers);
    }
    renderAgentMcpServers(agentId, currentAgentMcpServers, { getActiveAgent, onServersChanged });
    return currentAgentMcpServers;
  } catch (err) {
    console.warn('[AutoReiv UI] Failed to load agent MCP servers:', err);
    forgeMcpServerList.innerHTML = '<p id="forgeMcpServerEmpty" class="text-[11px] text-slate-500">Failed to load MCP servers.</p>';
    return [];
  }
}

export async function loadAgentCredentialGrants(agent) {
  const forgeCredentialGrantsList = $('forgeCredentialGrantsList');
  const forgeCredentialCountBadge = $('forgeCredentialCountBadge');
  if (!forgeCredentialGrantsList) return;
  const allowed = new Set(agent ? (agent.allowed_credentials || []) : []);
  try {
    const res = await fetch('/api/vault/credentials');
    if (!res.ok) {
      forgeCredentialGrantsList.innerHTML = '<p id="forgeCredentialEmpty" class="text-[11px] text-slate-500">Failed to load credentials from vault.</p>';
      if (forgeCredentialCountBadge) forgeCredentialCountBadge.textContent = '0';
      return;
    }
    const creds = await res.json();
    if (!Array.isArray(creds) || creds.length === 0) {
      forgeCredentialGrantsList.innerHTML = '<p id="forgeCredentialEmpty" class="text-[11px] text-slate-500">No credentials configured in Vault. Add credentials in Settings Studio.</p>';
      if (forgeCredentialCountBadge) forgeCredentialCountBadge.textContent = '0';
      return;
    }

    forgeCredentialGrantsList.innerHTML = creds.map((c) => {
      const isChecked = allowed.has(c.id);
      return `
        <label class="flex items-center space-x-2.5 p-2 rounded-lg bg-slate-800/60 border border-slate-700/60 hover:border-slate-600 transition cursor-pointer">
          <input type="checkbox" value="${escapeHtml(c.id)}" class="forge-credential-checkbox rounded border-slate-700 text-emerald-500 focus:ring-emerald-500/20 bg-slate-900 h-4 w-4" ${isChecked ? 'checked' : ''}>
          <div class="flex-1 min-w-0">
            <div class="flex items-center space-x-2">
              <span class="text-xs font-semibold text-slate-200 truncate">${escapeHtml(c.name)}</span>
              <span class="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-700/50 text-slate-300 border border-slate-600/40 uppercase">${escapeHtml(c.type || 'generic')}</span>
            </div>
            <span class="text-[10px] font-mono text-slate-400 truncate block">${escapeHtml(c.id)}</span>
          </div>
        </label>
      `;
    }).join('');

    const updateCount = () => {
      const checkedCount = $queryAll('.forge-credential-checkbox:checked', forgeCredentialGrantsList).length;
      if (forgeCredentialCountBadge) {
        forgeCredentialCountBadge.textContent = String(checkedCount);
      }
    };

    $queryAll('.forge-credential-checkbox', forgeCredentialGrantsList).forEach((cb) => {
      cb.addEventListener('change', updateCount);
    });

    updateCount();
  } catch (err) {
    console.warn('[AutoReiv UI] Failed to load credential grants:', err);
    forgeCredentialGrantsList.innerHTML = '<p id="forgeCredentialEmpty" class="text-[11px] text-slate-500">Failed to load credentials.</p>';
    if (forgeCredentialCountBadge) forgeCredentialCountBadge.textContent = '0';
  }
}

/**
 * Wires remote MCP Server add/test/save event listeners.
 */
export function setupAgentMcpControls({
  getActiveAgent = null,
  onServersChanged = null,
} = {}) {
  const _forgeMcpServersCard = $('forgeMcpServersCard');
  const forgeAddMcpServerBtn = $('forgeAddMcpServerBtn');
  const forgeMcpServerForm = $('forgeMcpServerForm');
  const forgeMcpServerFormCloseBtn = $('forgeMcpServerFormCloseBtn');
  const forgeMcpNameInput = $('forgeMcpNameInput');
  const forgeMcpTransportSelect = $('forgeMcpTransportSelect');
  const forgeMcpUrlGroup = $('forgeMcpUrlGroup');
  const forgeMcpUrlInput = $('forgeMcpUrlInput');
  const forgeMcpCommandGroup = $('forgeMcpCommandGroup');
  const forgeMcpCommandInput = $('forgeMcpCommandInput');
  const forgeMcpHeadersInput = $('forgeMcpHeadersInput');
  const forgeMcpEnabledCheckbox = $('forgeMcpEnabledCheckbox');
  const forgeMcpTestBtn = $('forgeMcpTestBtn');
  const forgeMcpSaveBtn = $('forgeMcpSaveBtn');
  const forgeMcpTestResult = $('forgeMcpTestResult');

  if (forgeAddMcpServerBtn && forgeMcpServerForm) {
    forgeAddMcpServerBtn.addEventListener('click', () => {
      forgeMcpServerForm.classList.remove('hidden');
      if (forgeMcpNameInput) forgeMcpNameInput.value = '';
      if (forgeMcpUrlInput) forgeMcpUrlInput.value = '';
      if (forgeMcpCommandInput) forgeMcpCommandInput.value = '';
      if (forgeMcpHeadersInput) forgeMcpHeadersInput.value = '';
      if (forgeMcpEnabledCheckbox) forgeMcpEnabledCheckbox.checked = true;
      if (forgeMcpTestResult) forgeMcpTestResult.classList.add('hidden');
    });
  }

  if (forgeMcpServerFormCloseBtn && forgeMcpServerForm) {
    forgeMcpServerFormCloseBtn.addEventListener('click', () => {
      forgeMcpServerForm.classList.add('hidden');
    });
  }

  if (forgeMcpTransportSelect) {
    forgeMcpTransportSelect.addEventListener('change', () => {
      const isStdio = forgeMcpTransportSelect.value === 'stdio';
      if (forgeMcpUrlGroup) forgeMcpUrlGroup.classList.toggle('hidden', isStdio);
      if (forgeMcpCommandGroup) forgeMcpCommandGroup.classList.toggle('hidden', !isStdio);
    });
  }

  if (forgeMcpTestBtn) {
    forgeMcpTestBtn.addEventListener('click', async () => {
      const name = forgeMcpNameInput ? forgeMcpNameInput.value.trim() : 'test-server';
      const transport = forgeMcpTransportSelect ? forgeMcpTransportSelect.value : 'sse';
      const url = forgeMcpUrlInput ? forgeMcpUrlInput.value.trim() : '';
      const command = forgeMcpCommandInput ? forgeMcpCommandInput.value.trim() : '';
      let headers = null;
      if (forgeMcpHeadersInput && forgeMcpHeadersInput.value.trim()) {
        try {
          headers = JSON.parse(forgeMcpHeadersInput.value.trim());
        } catch {
          showToast('Invalid JSON in custom headers', 'warning');
          return;
        }
      }
      const activeAgent = typeof getActiveAgent === 'function' ? getActiveAgent() : null;
      const agentId = activeAgent ? activeAgent.id : 'assistant';
      if (forgeMcpTestResult) {
        forgeMcpTestResult.classList.remove('hidden');
        forgeMcpTestResult.className = 'p-2.5 rounded text-xs font-mono border bg-slate-900 border-slate-700 text-slate-300';
        forgeMcpTestResult.textContent = 'Probing server...';
      }
      try {
        const testRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp/test`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, transport, url: url || null, command: command || null, headers, enabled: true }),
        });
        const data = await testRes.json();
        if (forgeMcpTestResult) {
          if (data.status === 'ok') {
            forgeMcpTestResult.className = 'p-2.5 rounded text-xs font-mono border bg-emerald-950/60 border-emerald-800 text-emerald-300';
            forgeMcpTestResult.textContent = `✓ OK (${data.latency_ms}ms) - ${data.tools_count} tool(s) found: ${(data.tools || []).join(', ')}`;
          } else {
            forgeMcpTestResult.className = 'p-2.5 rounded text-xs font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
            forgeMcpTestResult.textContent = `✗ Probe failed (${data.latency_ms}ms): ${data.error || 'Unknown error'}`;
          }
        }
      } catch (err) {
        if (forgeMcpTestResult) {
          forgeMcpTestResult.className = 'p-2.5 rounded text-xs font-mono border bg-rose-950/60 border-rose-800 text-rose-300';
          forgeMcpTestResult.textContent = `✗ Connection error: ${err.message || err}`;
        }
      }
    });
  }

  if (forgeMcpSaveBtn) {
    forgeMcpSaveBtn.addEventListener('click', async () => {
      const name = forgeMcpNameInput ? forgeMcpNameInput.value.trim() : '';
      if (!name) {
        showToast('Server name is required', 'warning');
        return;
      }
      const transport = forgeMcpTransportSelect ? forgeMcpTransportSelect.value : 'sse';
      const url = forgeMcpUrlInput ? forgeMcpUrlInput.value.trim() : '';
      const command = forgeMcpCommandInput ? forgeMcpCommandInput.value.trim() : '';
      if (transport === 'sse' && !url) {
        showToast('Remote URL is required for HTTP/SSE transport', 'warning');
        return;
      }
      let headers = null;
      if (forgeMcpHeadersInput && forgeMcpHeadersInput.value.trim()) {
        try {
          headers = JSON.parse(forgeMcpHeadersInput.value.trim());
        } catch {
          showToast('Invalid JSON in custom headers', 'warning');
          return;
        }
      }
      const enabled = forgeMcpEnabledCheckbox ? forgeMcpEnabledCheckbox.checked : true;
      const activeAgent = typeof getActiveAgent === 'function' ? getActiveAgent() : null;
      const agentId = activeAgent ? activeAgent.id : null;
      if (!agentId) {
        showToast('No active agent selected', 'error');
        return;
      }
      try {
        const saveRes = await fetch(`/api/agents/${encodeURIComponent(agentId)}/mcp`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, transport, url: url || null, command: command || null, headers, enabled }),
        });
        if (!saveRes.ok) throw new Error(`HTTP ${saveRes.status}`);
        showToast(`MCP server '${name}' saved`, 'success');
        if (forgeMcpServerForm) forgeMcpServerForm.classList.add('hidden');
        await loadAgentMcpServers(agentId, { getActiveAgent, onServersChanged });
      } catch (err) {
        showToast(`Failed to save server: ${err.message || err}`, 'error');
      }
    });
  }
}
