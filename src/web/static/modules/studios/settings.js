/**
 * Settings Studio Module [REQ-FE-001, REQ-SET-001..005]
 */

import { $, $queryAll, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';

export const PRESETS_DEFAULTS = {
  ollama: { url: 'http://127.0.0.1:11434', keyPlaceholder: 'Optional for Local' },
  openai: { url: 'https://api.openai.com/v1', keyPlaceholder: 'sk-...' },
  anthropic: { url: 'https://api.anthropic.com/v1', keyPlaceholder: 'sk-ant-...' },
  openrouter: { url: 'https://openrouter.ai/api/v1', keyPlaceholder: 'sk-or-...' },
  groq: { url: 'https://api.groq.com/openai/v1', keyPlaceholder: 'gsk_...' },
  deepseek: { url: 'https://api.deepseek.com/v1', keyPlaceholder: 'sk-...' },
  together: { url: 'https://api.together.xyz/v1', keyPlaceholder: '...' },
  vllm: { url: 'http://127.0.0.1:8000/v1', keyPlaceholder: 'Optional' },
};

export function initSettingsStudio(state, _callbacks = {}) {
  const saveProvidersBtn = $('saveProvidersBtn');
  const provPresetSelect = $('provPresetSelect');
  const provHostInput = $('provHostInput');
  const provKeyInput = $('provKeyInput');
  const provModelSelect = $('provModelSelect');
  const discoverModelsBtn = $('discoverModelsBtn');
  const activeProviderTag = $('activeProviderTag');
  const modelDiscoveryStatus = $('modelDiscoveryStatus');
  const saveMatrixBtn = $('saveMatrixBtn');
  const refreshModelsBtn = $('refreshModelsBtn');
  const recalcFitBtn = $('recalcFitBtn');
  const customRamInput = $('customRamInput');
  const modelFitTableBody = $('modelFitTableBody');

  if (provPresetSelect) {
    provPresetSelect.addEventListener('change', () => {
      const p = provPresetSelect.value;
      if (PRESETS_DEFAULTS[p]) {
        if (provHostInput) provHostInput.value = PRESETS_DEFAULTS[p].url;
        if (provKeyInput) provKeyInput.placeholder = PRESETS_DEFAULTS[p].keyPlaceholder;
      }
      if (activeProviderTag) activeProviderTag.textContent = p;
      state.savedDefaultModel = 'default';
      discoverAndPopulateModels();
    });
  }

  async function loadSettings() {
    try {
      const res = await fetch('/api/settings');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      state.settings = data;

      if (data.providers) {
        const defaultProv = data.providers.default_provider_id || 'ollama';
        if (provPresetSelect) provPresetSelect.value = defaultProv;
        if (activeProviderTag) activeProviderTag.textContent = defaultProv;
        state.savedDefaultModel =
          data.providers.default_model_id || (data.matrix && data.matrix.default_model) || 'default';

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

      if (data.matrix && data.matrix.purposes) {
        state.savedMatrix = data.matrix.purposes;
      }
      state.savedModelWindows = (data.matrix && data.matrix.model_context_windows) || {};
      const defaultCtxInput = $('defaultContextInput');
      if (defaultCtxInput) {
        defaultCtxInput.value =
          data.matrix && data.matrix.default_context_window ? data.matrix.default_context_window : '';
      }

      await discoverAndPopulateModels();
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load settings:', err);
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
      discoverModelsBtn.innerHTML =
        '<i data-lucide="loader-2" class="w-3 h-3 animate-spin"></i><span>Querying...</span>';
      safeCreateIcons();
    }

    try {
      let queryUrl = `/api/models/discover?available_ram_gib=${customRam}&provider_id=${encodeURIComponent(selectedPreset)}`;
      if (currentHost) queryUrl += `&host_url=${encodeURIComponent(currentHost)}`;
      if (currentKey) queryUrl += `&api_key=${encodeURIComponent(currentKey)}`;

      const res = await fetch(queryUrl);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const models = data.models || [];

      if (modelDiscoveryStatus) {
        modelDiscoveryStatus.textContent = `Discovered ${models.length} model(s) from ${selectedPreset} (${currentHost || 'default'}).`;
      }

      if (provModelSelect) {
        const curSelected = provModelSelect.value || state.savedDefaultModel || 'default';
        provModelSelect.innerHTML = '<option value="default">Auto-Select Default (e.g. llama3.2:latest)</option>';
        models.forEach((m) => {
          const opt = document.createElement('option');
          opt.value = m.name;
          opt.textContent = `${m.name} (${m.provider})`;
          provModelSelect.appendChild(opt);
        });

        const targetModel = state.savedDefaultModel || curSelected;
        if (targetModel && targetModel !== 'default') {
          if (!Array.from(provModelSelect.options).some((o) => o.value === targetModel)) {
            const savedOpt = document.createElement('option');
            savedOpt.value = targetModel;
            savedOpt.textContent = `${targetModel} (Custom / Saved)`;
            provModelSelect.appendChild(savedOpt);
          }
          provModelSelect.value = targetModel;
        }
      }

      const matrixSelects = $queryAll('.matrix-select');
      matrixSelects.forEach((sel) => {
        const currentVal = sel.value;
        sel.innerHTML = '<option value="default">default</option>';
        models.forEach((m) => {
          const opt = document.createElement('option');
          opt.value = m.name;
          opt.textContent = `${m.name} (${m.provider})`;
          sel.appendChild(opt);
        });
        if (state.savedMatrix) {
          const purposeKey = sel.id.replace('matrix', '').toLowerCase();
          for (const [k, v] of Object.entries(state.savedMatrix)) {
            if (k.toLowerCase().includes(purposeKey) || purposeKey.includes(k.toLowerCase())) {
              if (v && v !== 'default' && !Array.from(sel.options).some((o) => o.value === v)) {
                const opt = document.createElement('option');
                opt.value = v;
                opt.textContent = `${v} (Saved)`;
                sel.appendChild(opt);
              }
              sel.value = v;
            }
          }
        } else if (currentVal && currentVal !== 'default') {
          sel.value = currentVal;
        }
      });

      const ctxBySelect = {
        matrixGeneral: 'matrixGeneralCtx',
        matrixReasoning: 'matrixReasoningCtx',
        matrixTask: 'matrixTaskCtx',
        matrixVision: 'matrixVisionCtx',
        matrixAux: 'matrixAuxCtx',
        matrixFast: 'matrixFastCtx',
      };
      Object.entries(ctxBySelect).forEach(([selId, ctxId]) => {
        const sel = $(selId);
        const ctx = $(ctxId);
        if (!sel || !ctx) return;
        const model = sel.value;
        const saved = state.savedModelWindows && model && state.savedModelWindows[model];
        ctx.value = saved || '';
      });

      if (modelFitTableBody) {
        modelFitTableBody.innerHTML = '';
        if (models.length === 0) {
          modelFitTableBody.innerHTML =
            '<tr><td colspan="5" class="p-3 text-center text-slate-400">No models discovered from active providers.</td></tr>';
        } else {
          models.forEach((r) => {
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
          safeCreateIcons();
        }, 2500);
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to discover models:', err);
      if (modelDiscoveryStatus) modelDiscoveryStatus.textContent = `Error querying provider: ${err.message}`;
      if (discoverModelsBtn) {
        discoverModelsBtn.innerHTML =
          '<i data-lucide="alert-circle" class="w-3 h-3 text-rose-400"></i><span>Error</span>';
        setTimeout(() => {
          discoverModelsBtn.innerHTML = '<i data-lucide="refresh-cw" class="w-3 h-3"></i><span>Refresh Models</span>';
          discoverModelsBtn.disabled = false;
          safeCreateIcons();
        }, 2500);
      }
    }
  }

  if (provModelSelect) {
    provModelSelect.addEventListener('change', () => {
      state.savedDefaultModel = provModelSelect.value;
    });
  }

  if (discoverModelsBtn) discoverModelsBtn.addEventListener('click', discoverAndPopulateModels);
  if (refreshModelsBtn) refreshModelsBtn.addEventListener('click', discoverAndPopulateModels);
  if (recalcFitBtn) recalcFitBtn.addEventListener('click', discoverAndPopulateModels);

  if (saveProvidersBtn) {
    saveProvidersBtn.addEventListener('click', async () => {
      const selectedPreset = provPresetSelect ? provPresetSelect.value : 'ollama';
      const hostUrl = provHostInput ? provHostInput.value.trim() : 'http://127.0.0.1:11434';
      const keyVal = provKeyInput ? provKeyInput.value.trim() : null;
      const selectedModel = provModelSelect ? provModelSelect.value : state.savedDefaultModel || 'default';

      state.savedDefaultModel = selectedModel;

      const payload = {
        ollama_host:
          selectedPreset === 'ollama' ? hostUrl : state.settings?.providers?.ollama_host || 'http://127.0.0.1:11434',
        openai_base_url:
          selectedPreset !== 'ollama'
            ? hostUrl
            : state.settings?.providers?.openai_base_url || 'https://api.openai.com/v1',
        openai_api_key: keyVal || state.settings?.providers?.openai_api_key || '',
        default_provider_id: selectedPreset,
        default_model_id: selectedModel,
      };

      try {
        const res = await fetch('/api/settings/providers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const result = await res.json();
        if (result.providers) {
          state.settings = { ...(state.settings || {}), providers: result.providers };
        }
        saveProvidersBtn.textContent = 'Saved!';
        setTimeout(() => (saveProvidersBtn.textContent = 'Save Provider'), 2000);
        await discoverAndPopulateModels();
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save provider settings:', err);
        saveProvidersBtn.textContent = 'Error!';
        setTimeout(() => (saveProvidersBtn.textContent = 'Save Provider'), 2000);
      }
    });
  }

  if (saveMatrixBtn) {
    saveMatrixBtn.addEventListener('click', async () => {
      const parseCtx = (id) => {
        const raw = $(id)?.value;
        const n = parseInt(raw, 10);
        return Number.isFinite(n) && n > 0 ? n : null;
      };
      const modelWindows = {};
      const pairs = [
        ['matrixGeneral', 'matrixGeneralCtx'],
        ['matrixReasoning', 'matrixReasoningCtx'],
        ['matrixTask', 'matrixTaskCtx'],
        ['matrixVision', 'matrixVisionCtx'],
        ['matrixAux', 'matrixAuxCtx'],
        ['matrixFast', 'matrixFastCtx'],
      ];
      pairs.forEach(([selId, ctxId]) => {
        const model = $(selId)?.value;
        const n = parseCtx(ctxId);
        if (model && model !== 'default' && n) {
          modelWindows[model] = n;
        }
      });
      const payload = {
        default_model: provModelSelect ? provModelSelect.value : 'default',
        default_context_window: parseCtx('defaultContextInput'),
        purposes: {
          general: $('matrixGeneral')?.value || 'default',
          reasoning: $('matrixReasoning')?.value || 'default',
          task_execution: $('matrixTask')?.value || 'default',
          vision: $('matrixVision')?.value || 'default',
          auxiliary: $('matrixAux')?.value || 'default',
          fast: $('matrixFast')?.value || 'default',
        },
        model_context_windows: modelWindows,
      };
      try {
        const res = await fetch('/api/settings/matrix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const result = await res.json();
        if (result.matrix && result.matrix.purposes) {
          state.savedMatrix = result.matrix.purposes;
        }
        if (result.matrix) {
          state.savedModelWindows = result.matrix.model_context_windows || {};
        }
        saveMatrixBtn.textContent = 'Saved!';
        setTimeout(() => (saveMatrixBtn.textContent = 'Save Matrix'), 2000);
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save matrix:', err);
        saveMatrixBtn.textContent = 'Error!';
        setTimeout(() => (saveMatrixBtn.textContent = 'Save Matrix'), 2000);
      }
    });
  }

  // MCP Servers Management [REQ-MCP-005, REQ-MCP-007, REQ-MCP-009]
  const addMcpServerBtn = $('addMcpServerBtn');
  const mcpServerFormContainer = $('mcpServerFormContainer');
  const mcpServerNameInput = $('mcpServerNameInput');
  const mcpServerCommandInput = $('mcpServerCommandInput');
  const mcpEnvRows = $('mcpEnvRows');
  const addMcpEnvRowBtn = $('addMcpEnvRowBtn');
  const testMcpServerBtn = $('testMcpServerBtn');
  const mcpTestResultBox = $('mcpTestResultBox');
  const cancelMcpServerBtn = $('cancelMcpServerBtn');
  const saveMcpServerBtn = $('saveMcpServerBtn');
  const mcpServerList = $('mcpServerList');

  function addMcpEnvRow(key = '', val = '') {
    if (!mcpEnvRows) return;
    const row = document.createElement('div');
    row.className = 'mcp-env-row flex items-center space-x-2';
    row.innerHTML = `
      <input type="text" placeholder="KEY_NAME (e.g. GITHUB_TOKEN)" value="${escapeHtml(key)}" class="mcp-env-key flex-1 bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono text-xs focus:outline-none focus:border-brand-500">
      <input type="password" placeholder="Value / Secret" value="${escapeHtml(val)}" class="mcp-env-val flex-1 bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 font-mono text-xs focus:outline-none focus:border-brand-500">
      <button type="button" class="remove-env-row-btn p-1.5 text-slate-400 hover:text-rose-400 rounded hover:bg-slate-800 transition">
        <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
      </button>
    `;
    const rmBtn = row.querySelector('.remove-env-row-btn');
    if (rmBtn) {
      rmBtn.addEventListener('click', () => row.remove());
    }
    mcpEnvRows.appendChild(row);
    safeCreateIcons();
  }

  function getMcpEnvData() {
    const env = {};
    if (!mcpEnvRows) return env;
    const rows = mcpEnvRows.querySelectorAll('.mcp-env-row');
    rows.forEach((r) => {
      const k = r.querySelector('.mcp-env-key')?.value.trim();
      const v = r.querySelector('.mcp-env-val')?.value.trim();
      if (k) {
        env[k] = v || '';
      }
    });
    return env;
  }

  if (addMcpEnvRowBtn) {
    addMcpEnvRowBtn.addEventListener('click', () => addMcpEnvRow());
  }

  async function loadMcpServers() {
    if (!mcpServerList) return;
    try {
      const res = await fetch('/api/settings/mcp');
      if (!res.ok) return;
      const servers = await res.json();
      renderMcpServers(servers);
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load MCP servers:', err);
    }
  }

  function renderMcpServers(servers) {
    if (!mcpServerList) return;
    if (!servers || servers.length === 0) {
      mcpServerList.innerHTML =
        '<div class="text-xs text-slate-500 italic p-3 text-center bg-slate-950/40 rounded-lg border border-slate-800/60">No external MCP servers configured. Click \'Add MCP Server\' to mount tools.</div>';
      return;
    }

    mcpServerList.innerHTML = '';
    servers.forEach((srv) => {
      const card = document.createElement('div');
      card.className =
        'p-3.5 rounded-lg bg-slate-800/40 border border-slate-700/60 flex items-center justify-between gap-3 text-xs';
      const statusBadge = srv.is_mounted
        ? '<span class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800 text-[10px]"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span><span>Connected (' +
          srv.tool_count +
          ' tools)</span></span>'
        : '<span class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 text-[10px]"><span>Configured</span></span>';

      const cmdStr = Array.isArray(srv.command) ? srv.command.join(' ') : srv.command || '';
      const envKeys = srv.env && typeof srv.env === 'object' ? Object.keys(srv.env) : [];
      const envBadge =
        envKeys.length > 0
          ? `<span class="text-[10px] text-amber-400/90 font-mono bg-amber-950/50 px-1.5 py-0.5 rounded border border-amber-900/60">${envKeys.length} secrets</span>`
          : '';

      card.innerHTML = `
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="font-bold text-white font-mono">${escapeHtml(srv.name)}</span>
            ${statusBadge}
            ${envBadge}
          </div>
          <div class="font-mono text-[11px] text-slate-400 truncate max-w-lg">${escapeHtml(cmdStr)}</div>
        </div>
        <button data-server-name="${escapeHtml(srv.name)}" class="delete-mcp-btn px-2 py-1 rounded bg-slate-800 hover:bg-rose-950/60 text-slate-400 hover:text-rose-300 border border-slate-700 transition flex items-center space-x-1">
          <i data-lucide="trash-2" class="w-3 h-3"></i>
          <span>Remove</span>
        </button>
      `;

      const delBtn = card.querySelector('.delete-mcp-btn');
      if (delBtn) {
        delBtn.addEventListener('click', async () => {
          try {
            await fetch(`/api/settings/mcp/${encodeURIComponent(srv.name)}`, { method: 'DELETE' });
            await loadMcpServers();
          } catch (err) {
            console.error('[AutoReiv UI] Failed to delete MCP server:', err);
          }
        });
      }

      mcpServerList.appendChild(card);
    });
    safeCreateIcons();
  }

  if (addMcpServerBtn && mcpServerFormContainer) {
    addMcpServerBtn.addEventListener('click', () => {
      mcpServerFormContainer.classList.toggle('hidden');
      if (mcpTestResultBox) mcpTestResultBox.classList.add('hidden');
    });
  }

  if (cancelMcpServerBtn && mcpServerFormContainer) {
    cancelMcpServerBtn.addEventListener('click', () => {
      mcpServerFormContainer.classList.add('hidden');
      if (mcpTestResultBox) mcpTestResultBox.classList.add('hidden');
    });
  }

  if (testMcpServerBtn) {
    testMcpServerBtn.addEventListener('click', async () => {
      const name = mcpServerNameInput?.value.trim() || 'test-server';
      const rawCmd = mcpServerCommandInput?.value.trim();
      if (!rawCmd) {
        if (mcpTestResultBox) {
          mcpTestResultBox.className = 'p-3 rounded-lg border border-rose-800 bg-rose-950/40 text-rose-300 text-xs';
          mcpTestResultBox.innerHTML = '<strong>Error:</strong> Please enter a command to test.';
          mcpTestResultBox.classList.remove('hidden');
        }
        return;
      }
      const command = rawCmd.split(/\s+/);
      const env = getMcpEnvData();
      const payload = { name, command, env, enabled: true };

      try {
        testMcpServerBtn.disabled = true;
        testMcpServerBtn.innerHTML =
          '<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Testing Handshake...</span>';
        safeCreateIcons();

        const res = await fetch('/api/settings/mcp/test', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();

        if (mcpTestResultBox) {
          mcpTestResultBox.classList.remove('hidden');
          if (data.status === 'ok') {
            mcpTestResultBox.className =
              'p-3 rounded-lg border border-emerald-800/80 bg-emerald-950/40 text-emerald-300 text-xs space-y-2';
            const toolsList = (data.tools || [])
              .map(
                (t) =>
                  `<span class="inline-block px-2 py-0.5 rounded bg-emerald-900/60 border border-emerald-700 text-[11px] font-mono text-emerald-200" title="${escapeHtml(t.description || '')}">${escapeHtml(t.name)}</span>`
              )
              .join(' ');
            mcpTestResultBox.innerHTML = `
              <div class="flex items-center justify-between">
                <span class="font-bold text-emerald-400 flex items-center space-x-1"><i data-lucide="check-circle" class="w-3.5 h-3.5"></i><span>Handshake Successful (${data.latency_ms}ms)</span></span>
                <span class="text-[11px] text-emerald-400/80">${data.tools_count} tools discovered</span>
              </div>
              <div class="flex flex-wrap gap-1.5 pt-1">${toolsList || '<span class="italic text-slate-400">0 tools advertised</span>'}</div>
            `;
          } else {
            mcpTestResultBox.className =
              'p-3 rounded-lg border border-rose-800/80 bg-rose-950/40 text-rose-300 text-xs space-y-1';
            mcpTestResultBox.innerHTML = `
              <div class="font-bold text-rose-400 flex items-center space-x-1"><i data-lucide="alert-circle" class="w-3.5 h-3.5"></i><span>Handshake Failed (${data.latency_ms || 0}ms)</span></div>
              <div class="font-mono text-[11px] text-rose-300/90 whitespace-pre-wrap">${escapeHtml(data.error || 'Unknown error')}</div>
            `;
          }
          safeCreateIcons();
        }
      } catch (err) {
        if (mcpTestResultBox) {
          mcpTestResultBox.className = 'p-3 rounded-lg border border-rose-800 bg-rose-950/40 text-rose-300 text-xs';
          mcpTestResultBox.innerHTML = `<strong>Error:</strong> ${escapeHtml(err.message)}`;
          mcpTestResultBox.classList.remove('hidden');
        }
      } finally {
        testMcpServerBtn.disabled = false;
        testMcpServerBtn.innerHTML =
          '<i data-lucide="play" class="w-3.5 h-3.5"></i><span>Test Handshake & Discover</span>';
        safeCreateIcons();
      }
    });
  }

  if (saveMcpServerBtn) {
    saveMcpServerBtn.addEventListener('click', async () => {
      const name = mcpServerNameInput?.value.trim();
      const rawCmd = mcpServerCommandInput?.value.trim();
      if (!name || !rawCmd) return;

      const command = rawCmd.split(/\s+/);
      const env = getMcpEnvData();
      const payload = {
        name,
        command,
        env,
        enabled: true,
      };

      try {
        saveMcpServerBtn.textContent = 'Mounting...';
        const res = await fetch('/api/settings/mcp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (mcpServerNameInput) mcpServerNameInput.value = '';
        if (mcpServerCommandInput) mcpServerCommandInput.value = '';
        if (mcpEnvRows) mcpEnvRows.innerHTML = '';
        if (mcpTestResultBox) mcpTestResultBox.classList.add('hidden');
        if (mcpServerFormContainer) mcpServerFormContainer.classList.add('hidden');
        saveMcpServerBtn.textContent = 'Save & Mount';
        await loadMcpServers();
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save MCP server:', err);
        saveMcpServerBtn.textContent = 'Error!';
        setTimeout(() => (saveMcpServerBtn.textContent = 'Save & Mount'), 2000);
      }
    });
  }

  loadMcpServers();

  return {
    loadSettings,
    loadMcpServers,
    discoverAndPopulateModels,
  };
}
