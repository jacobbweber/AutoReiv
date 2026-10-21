/**
 * Settings Studio Module [REQ-FE-001, REQ-SET-001..005]
 */

import { $, safeCreateIcons } from '../dom.js';
import { escapeHtml } from '../utils/formatters.js';
import { renderSettingsMcpStatus } from './tools_studio_catalog.js';
import { modelVisionCell, wireModelVisionToggles } from './settings_model_vision.js';
import { setupReplyLimits } from './settings_reply_limits.js'; // CARD-574
import { setupAllowedOrigins } from './settings_allowed_origins.js'; // CARD-602
import { setupWebSearchSettings } from './settings_web_search.js'; // CARD-719
import { initSettingsDataAndBackups } from './settings/data_backup.js';
import { initSettingsVaultAndRemoteHosts } from './settings/vault_remote.js';
import { initSettingsUpdates } from './settings/updates.js';

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

/**
 * CARD-290: pick Active Default from live discover only — never inject ghost Custom/Saved.
 * @param {{ liveModelNames: string[], savedDefault?: string|null, currentSelected?: string|null }} args
 * @returns {{ selected: string, staleSaved: string|null, usedLiveFallback: boolean }}
 */
export function resolveActiveDefaultModelSelection({ liveModelNames, savedDefault = null, currentSelected = null }) {
  const live = Array.isArray(liveModelNames) ? liveModelNames.filter(Boolean) : [];
  const liveSet = new Set(live);
  const preferred =
    savedDefault && savedDefault !== 'default'
      ? savedDefault
      : currentSelected && currentSelected !== 'default'
        ? currentSelected
        : null;

  if (preferred && liveSet.has(preferred)) {
    return { selected: preferred, staleSaved: null, usedLiveFallback: false };
  }
  if (preferred && !liveSet.has(preferred)) {
    return {
      selected: live.length ? live[0] : 'default',
      staleSaved: preferred,
      usedLiveFallback: true,
    };
  }
  return { selected: 'default', staleSaved: null, usedLiveFallback: false };
}

export function initSettingsStudio(state, callbacks = {}) {
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

  const { loadDataDir, loadBackupCatalogAndConfig } = initSettingsDataAndBackups();
  const { loadCredentials, loadRemoteHosts } = initSettingsVaultAndRemoteHosts(state, {
    populateVaultCredDropdown,
  });
  const {
    loadSystemVersionInfo,
    loadUpdateConfig,
    loadAutoUpdateStatus,
    loadUpdateHistory,
    loadBranchList,
  } = initSettingsUpdates();

  async function loadSettings() {
    loadDataDir();
    setupReplyLimits(); // CARD-574: reply limits fields
    setupAllowedOrigins(); // CARD-602: extra browser origins
    loadBackupCatalogAndConfig();
    if (!state.vaultCredentials || state.vaultCredentials.length === 0) {
      await loadCredentials();
    }
    setupWebSearchSettings({ state, onCredentialsRefresh: loadCredentials }); // CARD-719
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
      const fetchOpts = {};
      if (currentKey && !currentKey.startsWith('••')) {
        fetchOpts.headers = { 'X-Provider-Api-Key': currentKey };
      }

      const res = await fetch(queryUrl, fetchOpts);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const models = data.models || [];

      const usingFallback = Boolean(data.using_fallback_presets);
      if (modelDiscoveryStatus) {
        if (usingFallback || data.discovery_error) {
          modelDiscoveryStatus.textContent = `Could not reach ${selectedPreset} (${currentHost || 'default'}): ${data.discovery_error || 'host unreachable'} — showing preset placeholders.`;
        } else {
          modelDiscoveryStatus.textContent = `Discovered ${models.length} model(s) from ${selectedPreset} (${currentHost || 'default'}).`;
        }
      }

      if (provModelSelect) {
        const curSelected = provModelSelect.value || state.savedDefaultModel || 'default';
        provModelSelect.innerHTML = '<option value="default">Auto-Select Default (e.g. llama3.2:latest)</option>';
        models.forEach((m) => {
          const opt = document.createElement('option');
          opt.value = m.name;
          opt.textContent = usingFallback
            ? `${m.name} (${m.provider} — preset)`
            : `${m.name} (${m.provider})`;
          provModelSelect.appendChild(opt);
        });

        // CARD-290: live inventory only — never inject Custom/Saved ghosts
        const resolution = resolveActiveDefaultModelSelection({
          liveModelNames: models.map((m) => m.name),
          savedDefault: state.savedDefaultModel,
          currentSelected: curSelected,
        });
        provModelSelect.value = resolution.selected;
        state.savedDefaultModel = resolution.selected;
        if (resolution.staleSaved && modelDiscoveryStatus && !usingFallback) {
          modelDiscoveryStatus.textContent =
            `Discovered ${models.length} model(s) from ${selectedPreset} (${currentHost || 'default'}). ` +
            `Saved default "${resolution.staleSaved}" is not on this endpoint — cleared; pick a live model.`;
        }
      }

      if (modelFitTableBody) {
        modelFitTableBody.innerHTML = '';
        if (models.length === 0) {
          modelFitTableBody.innerHTML =
            '<tr><td colspan="6" class="p-3 text-center text-slate-400">No models discovered from active providers.</td></tr>';
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
              ${modelVisionCell(r, escapeHtml)}
            `;
            modelFitTableBody.appendChild(row);
          });
          wireModelVisionToggles(modelFitTableBody);
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
      let selectedModel = provModelSelect ? provModelSelect.value : state.savedDefaultModel || 'default';
      // CARD-290: never persist a picker value that is not a live option / Auto-Select
      if (provModelSelect && selectedModel && selectedModel !== 'default') {
        const liveOk = Array.from(provModelSelect.options).some((o) => o.value === selectedModel);
        if (!liveOk) {
          selectedModel = 'default';
          provModelSelect.value = 'default';
        }
      }
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

        // CARD-412 / OC-1: persist default context window (orphaned when CARD-153 retired Save Matrix)
        const defaultCtxRaw = ($('defaultContextInput')?.value || '').trim();
        const defaultCtxParsed = parseInt(defaultCtxRaw, 10);
        const existingCtx =
          state.settings && state.settings.matrix
            ? state.settings.matrix.default_context_window
            : null;
        let defaultCtx = null;
        if (Number.isFinite(defaultCtxParsed) && defaultCtxParsed > 0) {
          defaultCtx = defaultCtxParsed;
        } else if (defaultCtxRaw === '' && existingCtx) {
          defaultCtx = existingCtx;
        } else {
          defaultCtx = null;
        }
        try {
          const matrixRes = await fetch('/api/settings/matrix', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              default_model: selectedModel || state.savedDefaultModel || 'default',
              default_context_window: defaultCtx,
              purposes: state.savedMatrix || {},
              model_context_windows: state.savedModelWindows || {},
            }),
          });
          if (matrixRes.ok) {
            const matrixResult = await matrixRes.json();
            if (matrixResult.matrix) {
              state.savedMatrix = matrixResult.matrix.purposes || state.savedMatrix || {};
              state.savedModelWindows = matrixResult.matrix.model_context_windows || {};
              state.settings = { ...(state.settings || {}), matrix: matrixResult.matrix };
              const defaultCtxInput = $('defaultContextInput');
              if (defaultCtxInput) {
                defaultCtxInput.value = matrixResult.matrix.default_context_window
                  ? matrixResult.matrix.default_context_window
                  : '';
              }
            }
          } else {
            console.error('[AutoReiv UI] Provider saved but context window matrix save failed:', matrixRes.status);
          }
        } catch (matrixErr) {
          console.error('[AutoReiv UI] Failed to persist default_context_window:', matrixErr);
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

  // Platform MCP attach status. The writer lives in Tools Studio. Hosting stays here. [CARD-421]
  const settingsMcpAttachStatus = $('settingsMcpAttachStatus');
  const settingsOpenToolsStudioBtn = $('settingsOpenToolsStudioBtn');
  const mcpServerList = $('mcpServerList');

  async function loadMcpServers() {
    if (!mcpServerList && !settingsMcpAttachStatus) return;
    try {
      const res = await fetch('/api/settings/mcp');
      if (!res.ok) return;
      const servers = await res.json();
      const view = renderSettingsMcpStatus(Array.isArray(servers) ? servers : []);
      if (settingsMcpAttachStatus) settingsMcpAttachStatus.textContent = view.line;
      if (mcpServerList) mcpServerList.innerHTML = view.listHtml;
    } catch (err) {
      console.error('[AutoReiv UI] Failed to load MCP attach status:', err);
    }
  }

  if (settingsOpenToolsStudioBtn) {
    settingsOpenToolsStudioBtn.addEventListener('click', () => {
      if (typeof callbacks.openToolsStudio === 'function') {
        callbacks.openToolsStudio(null, 'platform');
      }
    });
  }

  loadMcpServers();
  loadCredentials().then(() => {
    setupWebSearchSettings({ state, onCredentialsRefresh: loadCredentials });
  });
  loadRemoteHosts();
  loadSystemVersionInfo();
  loadUpdateConfig();
  loadAutoUpdateStatus();
  loadUpdateHistory();
  loadBranchList();

  return {
    loadSettings,
    loadDataDir,
    loadBackupCatalogAndConfig,
    loadMcpServers,
    loadCredentials,
    loadRemoteHosts,
    loadSystemVersionInfo,
    loadUpdateConfig,
    discoverAndPopulateModels,
  };
}
