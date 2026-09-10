/**
 * Settings Studio Module [REQ-FE-001, REQ-SET-001..005]
 */

import { $, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';

export const PRESETS_DEFAULTS = {
  ollama: { url: 'http://127.0.0.1:11434', keyPlaceholder: 'Optional for Local' },
  lmstudio: { url: 'http://127.0.0.1:1234/v1', keyPlaceholder: 'Optional for Local' },
  vllm: { url: 'http://127.0.0.1:8000/v1', keyPlaceholder: 'Optional for Local' },
  gemini: { url: 'https://generativelanguage.googleapis.com/v1beta/openai', keyPlaceholder: 'AIzaSy...' },
  openai: { url: 'https://api.openai.com/v1', keyPlaceholder: 'sk-...' },
  anthropic: { url: 'https://api.anthropic.com/v1', keyPlaceholder: 'sk-ant-...' },
  openrouter: { url: 'https://openrouter.ai/api/v1', keyPlaceholder: 'sk-or-...' },
  groq: { url: 'https://api.groq.com/openai/v1', keyPlaceholder: 'gsk_...' },
  deepseek: { url: 'https://api.deepseek.com/v1', keyPlaceholder: 'sk-...' },
  together: { url: 'https://api.together.xyz/v1', keyPlaceholder: '...' },
};

export function initSettingsStudio(state, _callbacks = {}) {
  const saveProvidersBtn = $('saveProvidersBtn');
  const provPresetSelect = $('provPresetSelect');
  const provHostInput = $('provHostInput');
  const provVaultCredSelect = $('provVaultCredSelect');
  const provKeyInput = $('provKeyInput');
  const provModelSelect = $('provModelSelect');
  const discoverModelsBtn = $('discoverModelsBtn');
  const activeProviderTag = $('activeProviderTag');
  const modelDiscoveryStatus = $('modelDiscoveryStatus');
  const refreshModelsBtn = $('refreshModelsBtn');
  const recalcFitBtn = $('recalcFitBtn');
  const customRamInput = $('customRamInput');
  const modelFitTableBody = $('modelFitTableBody');

  function updateKeyInputForVaultSelection() {
    if (!provVaultCredSelect) return;
    const val = provVaultCredSelect.value;
    const badge = $('provKeyVaultBadge');
    const badgeText = $('provKeyVaultBadgeText');

    if (val && val !== 'direct') {
      const cred = (state.vaultCredentials || []).find((c) => c.id === val);
      if (provKeyInput) {
        provKeyInput.value = '';
        provKeyInput.disabled = true;
        provKeyInput.placeholder = `Linked to Vault: ${cred?.name || val}`;
        provKeyInput.classList.add('opacity-50', 'cursor-not-allowed');
      }
      if (badge) {
        badge.classList.remove('hidden');
        badge.classList.add('inline-flex');
      }
      if (badgeText) {
        badgeText.textContent = `Linked: ${cred?.name || val}`;
      }
    } else {
      if (provKeyInput) {
        provKeyInput.disabled = false;
        provKeyInput.classList.remove('opacity-50', 'cursor-not-allowed');
        const p = provPresetSelect ? provPresetSelect.value : 'ollama';
        const provMap = state.settings?.providers?.providers || {};
        const saved = provMap[p];
        if (saved && saved.has_key) {
          provKeyInput.placeholder = 'Key encrypted in Vault (••••••••) — leave blank to keep';
        } else if (PRESETS_DEFAULTS[p]) {
          provKeyInput.placeholder = PRESETS_DEFAULTS[p].keyPlaceholder;
        }
      }
      const p = provPresetSelect ? provPresetSelect.value : 'ollama';
      const provMap = state.settings?.providers?.providers || {};
      const saved = provMap[p];
      const hasKey = Boolean(saved && saved.has_key);
      if (badge) {
        badge.classList.toggle('hidden', !hasKey);
        badge.classList.toggle('inline-flex', hasKey);
      }
      if (badgeText) {
        badgeText.textContent = 'Encrypted in Vault';
      }
    }
  }

  function populateVaultCredDropdown(creds = null) {
    if (!provVaultCredSelect) return;
    const list = creds || state.vaultCredentials || [];
    const curVal = provVaultCredSelect.value;
    provVaultCredSelect.innerHTML = '<option value="direct">Direct Secret Input (Auto-Vault)</option>';

    list.forEach((c) => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = `${c.name} (${c.id})`;
      provVaultCredSelect.appendChild(opt);
    });

    if (curVal && Array.from(provVaultCredSelect.options).some((o) => o.value === curVal)) {
      provVaultCredSelect.value = curVal;
    } else {
      provVaultCredSelect.value = 'direct';
    }
    updateKeyInputForVaultSelection();
  }

  if (provVaultCredSelect) {
    provVaultCredSelect.addEventListener('change', () => {
      updateKeyInputForVaultSelection();
    });
  }

  if (provPresetSelect) {
    provPresetSelect.addEventListener('change', () => {
      const p = provPresetSelect.value;
      const provMap = state.settings?.providers?.providers || {};
      const saved = provMap[p];

      if (saved && saved.base_url) {
        if (provHostInput) provHostInput.value = saved.base_url;
      } else if (PRESETS_DEFAULTS[p]) {
        if (provHostInput) provHostInput.value = PRESETS_DEFAULTS[p].url;
      }

      if (provVaultCredSelect) {
        const targetCredId = saved?.vault_cred_id;
        const existsInDropdown =
          targetCredId && Array.from(provVaultCredSelect.options).some((o) => o.value === targetCredId);
        if (existsInDropdown) {
          provVaultCredSelect.value = targetCredId;
        } else {
          provVaultCredSelect.value = 'direct';
        }
      }

      if (provKeyInput) {
        provKeyInput.value = '';
      }

      updateKeyInputForVaultSelection();

      if (activeProviderTag) activeProviderTag.textContent = p;
      state.savedDefaultModel = saved?.default_model_id || 'default';
      discoverAndPopulateModels();
    });
  }

  async function loadDataDir() {
    const rootEl = $('dataDirRoot');
    if (!rootEl) return;
    try {
      const res = await fetch('/api/data-dir');
      if (!res.ok) return;
      const data = await res.json();
      rootEl.textContent = data.root || '-';
      const dbEl = $('dataDirDb');
      const wikiEl = $('dataDirWiki');
      const skillsEl = $('dataDirSkills');
      if (dbEl) dbEl.textContent = data.db_path || '-';
      if (wikiEl) wikiEl.textContent = data.wiki_path || '-';
      if (skillsEl) skillsEl.textContent = data.skills_path || '-';
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load data dir:', err);
    }
  }

  function setDataDirStatus(message, isError) {
    const statusEl = $('dataDirBackupStatus');
    if (!statusEl) return;
    statusEl.textContent = message || '';
    statusEl.classList.toggle('hidden', !message);
    statusEl.classList.toggle('text-rose-400', Boolean(isError));
    statusEl.classList.toggle('text-slate-400', !isError);
  }

  function filenameFromDisposition(header, fallback) {
    if (!header) return fallback;
    const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
    if (star && star[1]) {
      try {
        return decodeURIComponent(star[1]);
      } catch {
        return star[1];
      }
    }
    const quoted = /filename="([^"]+)"/i.exec(header);
    if (quoted && quoted[1]) return quoted[1];
    const plain = /filename=([^;]+)/i.exec(header);
    if (plain && plain[1]) return plain[1].trim();
    return fallback;
  }

  async function backupDataDir() {
    const btn = $('backupDataDirBtn');
    try {
      if (btn) btn.disabled = true;
      setDataDirStatus('Creating backup...');
      const res = await fetch('/api/data-dir/backup', { method: 'POST' });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const filename = filenameFromDisposition(
        res.headers.get('Content-Disposition'),
        'autoreiv-data.zip',
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setDataDirStatus(`Backup downloaded: ${filename}`);
    } catch (err) {
      console.error('[AutoReiv UI] Backup failed:', err);
      setDataDirStatus(`Backup failed: ${err.message}`, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  async function restoreDataDir(file) {
    if (!file) return;
    const ok = window.confirm(
      'Restore will replace the data directory with this backup. The live tree is replaced, not merged. Continue?',
    );
    if (!ok) {
      setDataDirStatus('Restore cancelled; live tree unchanged.');
      return;
    }
    const btn = $('restoreDataDirBtn');
    try {
      if (btn) btn.disabled = true;
      setDataDirStatus('Restoring...');
      const fd = new FormData();
      fd.append('archive', file);
      fd.append('confirm', 'true');
      const res = await fetch('/api/data-dir/restore', { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      setDataDirStatus('Restore complete. Reloading paths...');
      await loadDataDir();
    } catch (err) {
      console.error('[AutoReiv UI] Restore failed:', err);
      setDataDirStatus(`Restore failed: ${err.message}`, true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  const backupDataDirBtn = $('backupDataDirBtn');
  if (backupDataDirBtn) {
    backupDataDirBtn.addEventListener('click', () => backupDataDir());
  }
  const restoreDataDirBtn = $('restoreDataDirBtn');
  const restoreDataDirFile = $('restoreDataDirFile');
  if (restoreDataDirBtn && restoreDataDirFile) {
    restoreDataDirBtn.addEventListener('click', () => restoreDataDirFile.click());
    restoreDataDirFile.addEventListener('change', () => {
      const file = restoreDataDirFile.files && restoreDataDirFile.files[0];
      restoreDataDir(file).finally(() => {
        restoreDataDirFile.value = '';
      });
    });
  }

  async function loadSettings() {
    loadDataDir();
    if (!state.vaultCredentials || state.vaultCredentials.length === 0) {
      await loadCredentials();
    }
    try {
      const res = await fetch('/api/settings');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      state.settings = data;

      if (data.providers) {
        const defaultProv = data.providers.default_provider_id || 'ollama';
        if (provPresetSelect) provPresetSelect.value = defaultProv;
        if (activeProviderTag) activeProviderTag.textContent = defaultProv;

        const provMap = data.providers.providers || {};
        const saved = provMap[defaultProv];

        state.savedDefaultModel =
          saved?.default_model_id ||
          data.providers.default_model_id ||
          (data.matrix && data.matrix.default_model) ||
          'default';

        if (saved && saved.base_url) {
          if (provHostInput) provHostInput.value = saved.base_url;
        } else if (defaultProv === 'ollama') {
          if (provHostInput) provHostInput.value = data.providers.ollama_host || 'http://127.0.0.1:11434';
        } else {
          if (provHostInput) provHostInput.value = data.providers.openai_base_url || 'https://api.openai.com/v1';
        }

        if (provVaultCredSelect) {
          const targetCredId = saved?.vault_cred_id;
          const existsInDropdown =
            targetCredId && Array.from(provVaultCredSelect.options).some((o) => o.value === targetCredId);
          if (existsInDropdown) {
            provVaultCredSelect.value = targetCredId;
          } else {
            provVaultCredSelect.value = 'direct';
          }
        }

        if (provKeyInput) {
          provKeyInput.value = '';
        }

        updateKeyInputForVaultSelection();
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
      if (currentKey && !currentKey.startsWith('••')) queryUrl += `&api_key=${encodeURIComponent(currentKey)}`;

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
      const typedKey = provKeyInput ? provKeyInput.value.trim() : '';
      const selectedModel = provModelSelect ? provModelSelect.value : state.savedDefaultModel || 'default';
      const selectedVaultCred = provVaultCredSelect ? provVaultCredSelect.value : 'direct';

      state.savedDefaultModel = selectedModel;

      const payload = {
        provider_id: selectedPreset,
        base_url: hostUrl,
        api_key: selectedVaultCred === 'direct' && typedKey && !typedKey.startsWith('••') ? typedKey : undefined,
        vault_cred_id: selectedVaultCred,
        default_model_id: selectedModel,
        set_as_default: true,
        ollama_host:
          selectedPreset === 'ollama' ? hostUrl : state.settings?.providers?.ollama_host || 'http://127.0.0.1:11434',
        openai_base_url:
          selectedPreset !== 'ollama'
            ? hostUrl
            : state.settings?.providers?.openai_base_url || 'https://api.openai.com/v1',
        default_provider_id: selectedPreset,
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
          const provMap = result.providers.providers || {};
          const saved = provMap[selectedPreset];

          if (provVaultCredSelect) {
            const targetCredId = saved?.vault_cred_id;
            const existsInDropdown =
              targetCredId && Array.from(provVaultCredSelect.options).some((o) => o.value === targetCredId);
            if (existsInDropdown) {
              provVaultCredSelect.value = targetCredId;
            } else {
              provVaultCredSelect.value = 'direct';
            }
          }

          if (provKeyInput) {
            provKeyInput.value = '';
          }

          updateKeyInputForVaultSelection();
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

  // --- Credential Vault [CARD-168, CARD-188] ---
  const addCredentialBtn = $('addCredentialBtn');
  const credentialFormContainer = $('credentialFormContainer');
  const cancelCredentialBtn = $('cancelCredentialBtn');
  const saveCredentialBtn = $('saveCredentialBtn');
  const credNameInput = $('credNameInput');
  const credIdInput = $('credIdInput');
  const credTypeSelect = $('credTypeSelect');
  const credSecretInput = $('credSecretInput');
  const toggleCredSecretVisibilityBtn = $('toggleCredSecretVisibilityBtn');
  const credDescInput = $('credDescInput');
  const credentialsTableBody = $('credentialsTableBody');

  if (toggleCredSecretVisibilityBtn && credSecretInput) {
    toggleCredSecretVisibilityBtn.addEventListener('click', () => {
      const isPassword = credSecretInput.type === 'password';
      credSecretInput.type = isPassword ? 'text' : 'password';
      toggleCredSecretVisibilityBtn.innerHTML = isPassword
        ? '<i data-lucide="eye-off" class="w-3.5 h-3.5"></i>'
        : '<i data-lucide="eye" class="w-3.5 h-3.5"></i>';
      safeCreateIcons();
    });
  }

  if (addCredentialBtn && credentialFormContainer) {
    addCredentialBtn.addEventListener('click', () => {
      credentialFormContainer.classList.toggle('hidden');
      if (!credentialFormContainer.classList.contains('hidden')) {
        if (credNameInput) credNameInput.value = '';
        if (credIdInput) {
          credIdInput.value = '';
          credIdInput.disabled = false;
        }
        if (credSecretInput) {
          credSecretInput.value = '';
          credSecretInput.placeholder = 'Paste sensitive token or key...';
          credSecretInput.type = 'password';
        }
        if (toggleCredSecretVisibilityBtn) {
          toggleCredSecretVisibilityBtn.innerHTML = '<i data-lucide="eye" class="w-3.5 h-3.5"></i>';
        }
        if (credDescInput) credDescInput.value = '';
        if (saveCredentialBtn) saveCredentialBtn.textContent = 'Save & Encrypt';
        if (credNameInput) credNameInput.focus();
        safeCreateIcons();
      }
    });
  }

  if (cancelCredentialBtn && credentialFormContainer) {
    cancelCredentialBtn.addEventListener('click', () => {
      credentialFormContainer.classList.add('hidden');
      if (credIdInput) credIdInput.disabled = false;
    });
  }

  async function loadCredentials() {
    try {
      const res = await fetch('/api/vault/credentials');
      if (!res.ok) return;
      const creds = await res.json();
      state.vaultCredentials = creds;
      populateVaultCredDropdown(creds);
      if (!credentialsTableBody) return;
      if (!creds || creds.length === 0) {
        credentialsTableBody.innerHTML = `<tr><td colspan="5" class="p-3 text-center text-slate-500 italic">No credentials in vault. Click 'Add Credential' to encrypt a new secret.</td></tr>`;
        return;
      }
      credentialsTableBody.innerHTML = creds.map(c => `
        <tr class="hover:bg-slate-800/40 transition">
          <td class="p-2.5">
            <div class="font-medium text-slate-100">${escapeHtml(c.name)}</div>
            <div class="font-mono text-[10px] text-slate-500">${escapeHtml(c.id)}</div>
          </td>
          <td class="p-2.5">
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-brand-300 border border-slate-700">${escapeHtml(c.type || 'token')}</span>
          </td>
          <td class="p-2.5 text-slate-400 text-xs">${escapeHtml(c.description || '-')}</td>
          <td class="p-2.5">
            <div class="flex items-center space-x-1.5">
              <span id="cred-preview-${escapeHtml(c.id)}" class="font-mono text-[11px] text-emerald-400">${escapeHtml(c.masked_preview || '••••••••')}</span>
              <button data-reveal-cred="${escapeHtml(c.id)}" class="p-1 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded transition" title="Show/Hide Secret">
                <i data-lucide="eye" class="w-3.5 h-3.5"></i>
              </button>
            </div>
          </td>
          <td class="p-2.5 text-right">
            <button data-edit-cred="${escapeHtml(c.id)}" class="p-1.5 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded transition mr-1" title="Edit Credential">
              <i data-lucide="pencil" class="w-3.5 h-3.5"></i>
            </button>
            <button data-delete-cred="${escapeHtml(c.id)}" class="p-1.5 hover:bg-rose-900/50 text-slate-400 hover:text-rose-300 rounded transition" title="Delete Credential">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </td>
        </tr>
      `).join('');
      safeCreateIcons();

      credentialsTableBody.querySelectorAll('[data-reveal-cred]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-reveal-cred');
          const previewEl = $(`cred-preview-${id}`);
          if (!previewEl) return;
          const isRevealed = btn.getAttribute('data-revealed') === 'true';
          if (isRevealed) {
            const credObj = (state.vaultCredentials || []).find(x => x.id === id);
            previewEl.textContent = credObj?.masked_preview || '••••••••';
            btn.setAttribute('data-revealed', 'false');
            btn.innerHTML = '<i data-lucide="eye" class="w-3.5 h-3.5"></i>';
            safeCreateIcons();
          } else {
            try {
              btn.disabled = true;
              const res = await fetch(`/api/vault/credentials/${id}/reveal`);
              if (!res.ok) throw new Error(`HTTP ${res.status}`);
              const data = await res.json();
              previewEl.textContent = data.secret;
              btn.setAttribute('data-revealed', 'true');
              btn.innerHTML = '<i data-lucide="eye-off" class="w-3.5 h-3.5"></i>';
              safeCreateIcons();
            } catch (err) {
              console.error('[AutoReiv UI] Failed to reveal credential:', err);
              alert(`Could not reveal credential: ${err.message}`);
            } finally {
              btn.disabled = false;
            }
          }
        });
      });

      credentialsTableBody.querySelectorAll('[data-edit-cred]').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = btn.getAttribute('data-edit-cred');
          const cred = (state.vaultCredentials || []).find(x => x.id === id);
          if (!cred) return;
          if (credentialFormContainer) credentialFormContainer.classList.remove('hidden');
          if (credNameInput) credNameInput.value = cred.name || '';
          if (credIdInput) {
            credIdInput.value = cred.id;
            credIdInput.disabled = true;
          }
          if (credTypeSelect) credTypeSelect.value = cred.type || 'token';
          if (credDescInput) credDescInput.value = cred.description || '';
          if (credSecretInput) {
            credSecretInput.value = '';
            credSecretInput.placeholder = 'Leave blank to keep existing secret';
            credSecretInput.type = 'password';
          }
          if (toggleCredSecretVisibilityBtn) {
            toggleCredSecretVisibilityBtn.innerHTML = '<i data-lucide="eye" class="w-3.5 h-3.5"></i>';
          }
          if (saveCredentialBtn) saveCredentialBtn.textContent = 'Update & Encrypt';
          if (credNameInput) credNameInput.focus();
          safeCreateIcons();
        });
      });

      credentialsTableBody.querySelectorAll('[data-delete-cred]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-delete-cred');
          if (!confirm(`Are you sure you want to delete credential '${id}' from the vault? Agents granted this credential will lose access immediately.`)) return;
          try {
            await fetch(`/api/vault/credentials/${id}`, { method: 'DELETE' });
            await loadCredentials();
          } catch (err) {
            console.error('[AutoReiv UI] Failed to delete credential:', err);
          }
        });
      });
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load credentials:', err);
    }
  }

  if (saveCredentialBtn) {
    saveCredentialBtn.addEventListener('click', async () => {
      const name = credNameInput?.value.trim();
      const secret = credSecretInput?.value.trim();
      const isEdit = credIdInput?.disabled;
      if (!name) {
        alert('Name is required.');
        return;
      }
      if (!isEdit && !secret) {
        alert('Name and Secret Value are required.');
        return;
      }
      const payload = {
        name,
        secret: secret || undefined,
        id: credIdInput?.value.trim() || undefined,
        type: credTypeSelect?.value || 'token',
        description: credDescInput?.value.trim() || '',
      };
      try {
        saveCredentialBtn.textContent = isEdit ? 'Updating...' : 'Encrypting...';
        const res = await fetch('/api/vault/credentials', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (credNameInput) credNameInput.value = '';
        if (credIdInput) {
          credIdInput.value = '';
          credIdInput.disabled = false;
        }
        if (credSecretInput) {
          credSecretInput.value = '';
          credSecretInput.placeholder = 'Paste sensitive token or key...';
          credSecretInput.type = 'password';
        }
        if (credDescInput) credDescInput.value = '';
        if (credentialFormContainer) credentialFormContainer.classList.add('hidden');
        saveCredentialBtn.textContent = 'Save & Encrypt';
        await loadCredentials();
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save credential:', err);
        saveCredentialBtn.textContent = 'Error!';
        setTimeout(() => (saveCredentialBtn.textContent = isEdit ? 'Update & Encrypt' : 'Save & Encrypt'), 2000);
      }
    });
  }

  loadMcpServers();
  loadCredentials();

  // --- Remote SSH Hosts [CARD-160, CARD-188] ---
  const addRemoteHostBtn = $('addRemoteHostBtn');
  const remoteHostFormContainer = $('remoteHostFormContainer');
  const closeRemoteHostFormBtn = $('closeRemoteHostFormBtn');
  const cancelRemoteHostBtn = $('cancelRemoteHostBtn');
  const saveRemoteHostBtn = $('saveRemoteHostBtn');
  const hostLabelInput = $('hostLabelInput');
  const hostIdInput = $('hostIdInput');
  const hostAddressInput = $('hostAddressInput');
  const hostPortInput = $('hostPortInput');
  const hostAuthTypeSelect = $('hostAuthTypeSelect');
  const hostUsernameInput = $('hostUsernameInput');
  const hostCredentialSelect = $('hostCredentialSelect');
  const hostTestResultAlert = $('hostTestResultAlert');
  const remoteHostsTableBody = $('remoteHostsTableBody');

  function populateHostCredentialSelect() {
    if (!hostCredentialSelect) return;
    const creds = state.vaultCredentials || [];
    const currentVal = hostCredentialSelect.value;
    hostCredentialSelect.innerHTML = '<option value="">-- No Vault Credential --</option>' +
      creds.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.name)} (${escapeHtml(c.id)})</option>`).join('');
    if (currentVal) hostCredentialSelect.value = currentVal;
  }

  if (addRemoteHostBtn && remoteHostFormContainer) {
    addRemoteHostBtn.addEventListener('click', () => {
      remoteHostFormContainer.classList.toggle('hidden');
      if (!remoteHostFormContainer.classList.contains('hidden')) {
        populateHostCredentialSelect();
        if (hostLabelInput) hostLabelInput.value = '';
        if (hostIdInput) {
          hostIdInput.value = '';
          hostIdInput.disabled = false;
        }
        if (hostAddressInput) hostAddressInput.value = '';
        if (hostPortInput) hostPortInput.value = '22';
        if (hostUsernameInput) hostUsernameInput.value = '';
        if (hostCredentialSelect) hostCredentialSelect.value = '';
        if (saveRemoteHostBtn) saveRemoteHostBtn.textContent = 'Save Remote Host';
        if (hostLabelInput) hostLabelInput.focus();
      }
    });
  }

  if (closeRemoteHostFormBtn && remoteHostFormContainer) {
    closeRemoteHostFormBtn.addEventListener('click', () => {
      remoteHostFormContainer.classList.add('hidden');
      if (hostIdInput) hostIdInput.disabled = false;
    });
  }

  if (cancelRemoteHostBtn && remoteHostFormContainer) {
    cancelRemoteHostBtn.addEventListener('click', () => {
      remoteHostFormContainer.classList.add('hidden');
      if (hostIdInput) hostIdInput.disabled = false;
    });
  }

  async function loadRemoteHosts() {
    if (!remoteHostsTableBody) return;
    try {
      const res = await fetch('/api/remote_hosts');
      if (!res.ok) return;
      const hosts = await res.json();
      state.remoteHosts = hosts;
      if (!hosts || hosts.length === 0) {
        remoteHostsTableBody.innerHTML = `<tr><td colspan="6" class="p-3 text-center text-slate-500 italic">No remote hosts configured. Click 'Add Remote Host' to configure an SSH connection.</td></tr>`;
        return;
      }
      remoteHostsTableBody.innerHTML = hosts.map(h => `
        <tr class="hover:bg-slate-800/40 transition">
          <td class="p-2.5">
            <div class="font-medium text-slate-100">${escapeHtml(h.label)}</div>
            <div class="font-mono text-[10px] text-slate-500">${escapeHtml(h.id)}</div>
          </td>
          <td class="p-2.5 font-mono text-xs text-sky-400">${escapeHtml(h.host)}</td>
          <td class="p-2.5 font-mono text-xs text-slate-300">${escapeHtml(String(h.port || 22))}</td>
          <td class="p-2.5 font-mono text-xs text-slate-300">${escapeHtml(h.username)}</td>
          <td class="p-2.5">
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-brand-300 border border-slate-700">${escapeHtml(h.credential_id || 'None')}</span>
          </td>
          <td class="p-2.5 text-right">
            <button data-edit-host="${escapeHtml(h.id)}" class="p-1.5 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded transition mr-1" title="Edit Host">
              <i data-lucide="pencil" class="w-3.5 h-3.5"></i>
            </button>
            <button data-test-host="${escapeHtml(h.id)}" class="p-1.5 hover:bg-sky-900/50 text-slate-400 hover:text-sky-300 rounded transition mr-1" title="Test SSH Handshake">
              <i data-lucide="activity" class="w-3.5 h-3.5"></i>
            </button>
            <button data-delete-host="${escapeHtml(h.id)}" class="p-1.5 hover:bg-rose-900/50 text-slate-400 hover:text-rose-300 rounded transition" title="Delete Host">
              <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
            </button>
          </td>
        </tr>
      `).join('');
      safeCreateIcons();

      remoteHostsTableBody.querySelectorAll('[data-edit-host]').forEach(btn => {
        btn.addEventListener('click', () => {
          const id = btn.getAttribute('data-edit-host');
          const host = (state.remoteHosts || []).find(x => x.id === id);
          if (!host) return;
          if (remoteHostFormContainer) remoteHostFormContainer.classList.remove('hidden');
          populateHostCredentialSelect();
          if (hostLabelInput) hostLabelInput.value = host.label || '';
          if (hostIdInput) {
            hostIdInput.value = host.id;
            hostIdInput.disabled = true;
          }
          if (hostAddressInput) hostAddressInput.value = host.host || '';
          if (hostPortInput) hostPortInput.value = host.port || 22;
          if (hostAuthTypeSelect) hostAuthTypeSelect.value = host.auth_type || 'password';
          if (hostUsernameInput) hostUsernameInput.value = host.username || '';
          if (hostCredentialSelect) hostCredentialSelect.value = host.credential_id || '';
          if (saveRemoteHostBtn) saveRemoteHostBtn.textContent = 'Update Remote Host';
          if (hostLabelInput) hostLabelInput.focus();
        });
      });

      remoteHostsTableBody.querySelectorAll('[data-test-host]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-test-host');
          btn.disabled = true;
          const originalHtml = btn.innerHTML;
          btn.innerHTML = '<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i>';
          safeCreateIcons();
          try {
            const res = await fetch(`/api/remote_hosts/${id}/test`, { method: 'POST' });
            const data = await res.json();
            if (res.ok && data.status === 'ok') {
              alert(`SSH connection to '${id}' successful! Latency: ${data.latency_ms}ms`);
            } else {
              alert(`SSH connection probe failed for '${id}':\n${data.message || 'Unknown error'}`);
            }
          } catch (err) {
            alert(`SSH probe failed: ${err.message}`);
          } finally {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
            safeCreateIcons();
          }
        });
      });

      remoteHostsTableBody.querySelectorAll('[data-delete-host]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-delete-host');
          if (!confirm(`Are you sure you want to delete remote host '${id}'?`)) return;
          try {
            await fetch(`/api/remote_hosts/${id}`, { method: 'DELETE' });
            await loadRemoteHosts();
          } catch (err) {
            console.error('[AutoReiv UI] Failed to delete remote host:', err);
          }
        });
      });
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load remote hosts:', err);
    }
  }

  if (saveRemoteHostBtn) {
    saveRemoteHostBtn.addEventListener('click', async () => {
      const label = hostLabelInput?.value.trim();
      const host = hostAddressInput?.value.trim();
      const username = hostUsernameInput?.value.trim();
      const port = parseInt(hostPortInput?.value.trim() || '22', 10);
      const authType = hostAuthTypeSelect?.value || 'password';
      const credentialId = hostCredentialSelect?.value || '';
      const customId = hostIdInput?.value.trim() || undefined;

      if (!label || !host || !username) {
        alert('Friendly Label, Hostname/IP, and Username are required.');
        return;
      }

      const payload = {
        label,
        host,
        port: isNaN(port) ? 22 : port,
        username,
        auth_type: authType,
        credential_id: credentialId || null,
        id: customId,
      };

      try {
        saveRemoteHostBtn.textContent = hostIdInput?.disabled ? 'Updating...' : 'Saving...';
        const res = await fetch('/api/remote_hosts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (hostLabelInput) hostLabelInput.value = '';
        if (hostIdInput) {
          hostIdInput.value = '';
          hostIdInput.disabled = false;
        }
        if (hostAddressInput) hostAddressInput.value = '';
        if (hostPortInput) hostPortInput.value = '22';
        if (hostUsernameInput) hostUsernameInput.value = '';
        if (hostCredentialSelect) hostCredentialSelect.value = '';
        if (remoteHostFormContainer) remoteHostFormContainer.classList.add('hidden');
        saveRemoteHostBtn.textContent = 'Save Remote Host';
        await loadRemoteHosts();
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save remote host:', err);
        saveRemoteHostBtn.textContent = 'Error!';
        setTimeout(() => (saveRemoteHostBtn.textContent = 'Save Remote Host'), 2000);
      }
    });
  }

  // --- System & Software Updates [CARD-196, REQ-UPD-001..005] ---
  const systemVersionPill = $('systemVersionPill');
  const systemDeploymentBadge = $('systemDeploymentBadge');
  const systemCommitSha = $('systemCommitSha');
  const systemBranchName = $('systemBranchName');
  const systemTreeStatus = $('systemTreeStatus');
  const systemPlatform = $('systemPlatform');
  const updateRepoUrlInput = $('updateRepoUrlInput');
  const updateBranchInput = $('updateBranchInput');
  const saveUpdateConfigBtn = $('saveUpdateConfigBtn');
  const saveUpdateConfigStatus = $('saveUpdateConfigStatus');
  const checkForUpdatesBtn = $('checkForUpdatesBtn');
  const applyUpdateBtn = $('applyUpdateBtn');
  const updateStatusBanner = $('updateStatusBanner');
  const updateStatusDot = $('updateStatusDot');
  const updateStatusMessage = $('updateStatusMessage');
  const updateNotesContainer = $('updateNotesContainer');
  const updateReleaseNotesText = $('updateReleaseNotesText');
  const updateManualDockerHelper = $('updateManualDockerHelper');

  let currentSystemVersion = null;

  async function loadSystemVersionInfo() {
    try {
      const res = await fetch('/api/system/version');
      if (!res.ok) return;
      const data = await res.json();
      currentSystemVersion = data;

      if (systemVersionPill) {
        systemVersionPill.textContent = data.current_version ? `v${data.current_version}` : '-';
      }
      if (systemDeploymentBadge) {
        const modeLabels = {
          git: 'Git Clone',
          docker: 'Docker Container',
          systemd: 'Systemd Service',
          windows_service: 'Windows Service',
          standalone: 'Standalone',
        };
        systemDeploymentBadge.textContent = modeLabels[data.deployment_mode] || data.deployment_mode || '-';
      }
      if (systemCommitSha) {
        systemCommitSha.textContent = data.commit || 'unknown';
      }
      if (systemBranchName) {
        systemBranchName.textContent = data.branch || '-';
      }
      if (systemTreeStatus) {
        if (data.is_dirty) {
          systemTreeStatus.textContent = 'Dirty (Uncommitted)';
          systemTreeStatus.className = 'text-amber-400 font-semibold';
        } else {
          systemTreeStatus.textContent = 'Clean';
          systemTreeStatus.className = 'text-emerald-400';
        }
      }
      if (systemPlatform) {
        systemPlatform.textContent = `${data.platform || '-'} (Py ${data.python_version || '-'})`;
      }
      if (updateManualDockerHelper) {
        updateManualDockerHelper.classList.toggle('hidden', data.deployment_mode !== 'docker');
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load system version info:', err);
    }
  }

  async function loadUpdateConfig() {
    try {
      const res = await fetch('/api/system/updates/config');
      if (!res.ok) return;
      const data = await res.json();
      if (updateRepoUrlInput && !updateRepoUrlInput.value) {
        updateRepoUrlInput.value = data.upstream_repo_url || '';
      }
      if (updateBranchInput && !updateBranchInput.value) {
        updateBranchInput.value = data.tracked_branch || '';
      }
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load update config:', err);
    }
  }

  if (saveUpdateConfigBtn) {
    saveUpdateConfigBtn.addEventListener('click', async () => {
      const repoUrl = updateRepoUrlInput?.value.trim() || '';
      const branch = updateBranchInput?.value.trim() || '';
      if (!repoUrl) {
        alert('Repository URL cannot be empty.');
        return;
      }
      try {
        saveUpdateConfigBtn.disabled = true;
        saveUpdateConfigBtn.textContent = 'Saving...';
        const res = await fetch('/api/system/updates/config', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            upstream_repo_url: repoUrl,
            tracked_branch: branch || 'qa',
          }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (saveUpdateConfigStatus) {
          saveUpdateConfigStatus.textContent = 'Settings saved.';
          saveUpdateConfigStatus.classList.remove('hidden', 'text-rose-400');
          saveUpdateConfigStatus.classList.add('text-emerald-400');
          setTimeout(() => saveUpdateConfigStatus.classList.add('hidden'), 3000);
        }
      } catch (err) {
        console.error('[AutoReiv UI] Failed to save update config:', err);
        if (saveUpdateConfigStatus) {
          saveUpdateConfigStatus.textContent = 'Failed to save settings.';
          saveUpdateConfigStatus.classList.remove('hidden', 'text-emerald-400');
          saveUpdateConfigStatus.classList.add('text-rose-400');
        }
      } finally {
        saveUpdateConfigBtn.disabled = false;
        saveUpdateConfigBtn.textContent = 'Save Repository Settings';
      }
    });
  }

  if (checkForUpdatesBtn) {
    checkForUpdatesBtn.addEventListener('click', async () => {
      try {
        checkForUpdatesBtn.disabled = true;
        const origHtml = checkForUpdatesBtn.innerHTML;
        checkForUpdatesBtn.innerHTML = '<span>Checking...</span>';

        const branch = updateBranchInput?.value.trim() || '';
        const query = branch ? `?branch=${encodeURIComponent(branch)}` : '';
        const res = await fetch(`/api/system/updates/check${query}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (updateStatusBanner) {
          updateStatusBanner.classList.remove('hidden');
        }

        if (data.error) {
          if (updateStatusDot) updateStatusDot.className = 'w-2 h-2 rounded-full bg-rose-500';
          if (updateStatusMessage) {
            updateStatusMessage.textContent = `Check failed: ${data.error}`;
          }
          if (updateNotesContainer) updateNotesContainer.classList.add('hidden');
          if (applyUpdateBtn) applyUpdateBtn.classList.add('hidden');
        } else if (data.update_available) {
          if (updateStatusDot) updateStatusDot.className = 'w-2 h-2 rounded-full bg-amber-400';
          const behindTxt = data.commits_behind ? ` (${data.commits_behind} commit(s) ahead on upstream)` : '';
          if (updateStatusMessage) {
            updateStatusMessage.textContent = `Update Available: ${data.remote_commit || 'Newer version'}${behindTxt}`;
          }
          if (data.release_notes && updateNotesContainer && updateReleaseNotesText) {
            updateReleaseNotesText.textContent = data.release_notes;
            updateNotesContainer.classList.remove('hidden');
          } else if (updateNotesContainer) {
            updateNotesContainer.classList.add('hidden');
          }

          if (applyUpdateBtn) {
            const isCleanGit = currentSystemVersion?.is_git && !currentSystemVersion?.is_dirty;
            applyUpdateBtn.classList.toggle('hidden', !isCleanGit);
          }
        } else {
          if (updateStatusDot) updateStatusDot.className = 'w-2 h-2 rounded-full bg-emerald-400';
          if (updateStatusMessage) {
            updateStatusMessage.textContent = `AutoReiv is up to date (${data.current_commit || 'HEAD'}).`;
          }
          if (updateNotesContainer) updateNotesContainer.classList.add('hidden');
          if (applyUpdateBtn) applyUpdateBtn.classList.add('hidden');
        }

        checkForUpdatesBtn.innerHTML = origHtml;
        checkForUpdatesBtn.disabled = false;
        safeCreateIcons();
      } catch (err) {
        console.error('[AutoReiv UI] Update check error:', err);
        if (updateStatusBanner) updateStatusBanner.classList.remove('hidden');
        if (updateStatusDot) updateStatusDot.className = 'w-2 h-2 rounded-full bg-rose-500';
        if (updateStatusMessage) updateStatusMessage.textContent = 'Upstream remote unreachable or offline.';
        checkForUpdatesBtn.disabled = false;
        checkForUpdatesBtn.innerHTML = '<span>Check for Updates</span>';
      }
    });
  }

  if (applyUpdateBtn) {
    applyUpdateBtn.addEventListener('click', async () => {
      const ok = confirm(
        'Apply update now?\n\n' +
        'AutoReiv will create a timestamped backup snapshot of your database and pull upstream changes using fast-forward merge.\n\n' +
        'Continue?'
      );
      if (!ok) return;

      try {
        applyUpdateBtn.disabled = true;
        applyUpdateBtn.textContent = 'Applying Update...';
        const res = await fetch('/api/system/updates/apply', { method: 'POST' });
        const data = await res.json();

        if (data.success) {
          alert(`Update Successful!\n\n${data.message}\n\nBackup created at: ${data.backup_path || 'data directory'}`);
          await loadSystemVersionInfo();
          applyUpdateBtn.classList.add('hidden');
          if (updateStatusMessage) {
            updateStatusMessage.textContent = `Updated to ${data.new_commit}. Restart recommended.`;
          }
        } else {
          alert(`Update Aborted:\n\n${data.message}`);
        }
      } catch (err) {
        console.error('[AutoReiv UI] Failed to apply update:', err);
        alert('Failed to execute update: ' + err.message);
      } finally {
        applyUpdateBtn.disabled = false;
        applyUpdateBtn.textContent = 'Apply Update (Fast-Forward)';
      }
    });
  }

  loadRemoteHosts();
  loadSystemVersionInfo();
  loadUpdateConfig();

  return {
    loadSettings,
    loadMcpServers,
    loadCredentials,
    loadRemoteHosts,
    loadSystemVersionInfo,
    loadUpdateConfig,
    discoverAndPopulateModels,
  };
}
