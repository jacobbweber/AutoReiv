/**
 * CARD-719: Settings Studio > Connections > Web Search & Fetch.
 * Configures GET/PUT /api/settings/web-search (DuckDuckGo Lite free default,
 * Tavily Search API, or Brave Search API with Vault-encrypted tokens, plus
 * allow_private_urls for fetch_url).
 */

export const WEB_SEARCH_SETTINGS_URL = '/api/settings/web-search';

function byId(doc, id) {
  return doc && typeof doc.getElementById === 'function' ? doc.getElementById(id) : null;
}

export function buildWebSearchSavePayload({
  provider = 'duckduckgo',
  credentialId = '',
  apiKey = '',
  allowPrivateUrls = false,
  maxResults = 5,
} = {}) {
  const cleanProvider = String(provider || 'duckduckgo').trim().toLowerCase() || 'duckduckgo';
  const cleanCredId = String(credentialId || '').trim();
  const cleanKey = String(apiKey || '').trim();
  const parsedMax = parseInt(maxResults, 10);
  const safeMax = Number.isFinite(parsedMax) ? Math.max(1, Math.min(15, parsedMax)) : 5;
  return {
    provider: cleanProvider,
    credential_id: cleanCredId && cleanCredId !== 'direct' ? cleanCredId : null,
    api_key: cleanKey && !cleanKey.startsWith('••') ? cleanKey : null,
    allow_private_urls: Boolean(allowPrivateUrls),
    max_results: safeMax,
  };
}

export function formatWebSearchStatusBadge(data = {}) {
  const provider = String(data.provider || 'duckduckgo').toLowerCase();
  if (provider === 'duckduckgo') {
    return 'DuckDuckGo Lite · Free (No API Key)';
  }
  const label = provider === 'tavily' ? 'Tavily Search' : provider === 'brave' ? 'Brave Search' : provider;
  if (data.has_api_key) {
    const credLabel = data.credential_name || data.credential_id || 'Vault';
    return `${label} · Key in Vault (${credLabel})`;
  }
  return `${label} · API Key Needed`;
}

function setStatus(els, text, ok = true) {
  if (!els?.status) return;
  els.status.textContent = text;
  els.status.className = `text-[11px] font-medium ${ok ? 'text-emerald-400' : 'text-rose-400'}`;
  els.status.classList.remove('hidden');
}

function populateVaultDropdown(els, credentials = [], selectedId = null) {
  if (!els?.credentialSelect) return;
  const current = selectedId ?? els.credentialSelect.value;
  els.credentialSelect.innerHTML = '<option value="">-- Paste New Key Below (Auto-Saves to Vault) --</option>';
  (Array.isArray(credentials) ? credentials : []).forEach((cred) => {
    if (!cred || !cred.id) return;
    const opt = document.createElement('option');
    opt.value = cred.id;
    opt.textContent = `${cred.name || cred.id} (${cred.id})`;
    els.credentialSelect.appendChild(opt);
  });
  if (current && Array.from(els.credentialSelect.options).some((o) => o.value === current)) {
    els.credentialSelect.value = current;
  } else {
    els.credentialSelect.value = '';
  }
}

function syncProviderAuthVisibility(els, data = {}) {
  if (!els?.providerSelect) return;
  const provider = String(els.providerSelect.value || 'duckduckgo').toLowerCase();
  const isFree = provider === 'duckduckgo';
  if (els.authFields) {
    els.authFields.classList.toggle('hidden', isFree);
  }
  if (els.apiKeyInput) {
    if (!isFree && data.has_api_key && data.provider === provider) {
      els.apiKeyInput.placeholder = 'Encrypted in Vault (••••••••) — leave blank to keep';
    } else if (provider === 'tavily') {
      els.apiKeyInput.placeholder = 'tvly-...';
    } else if (provider === 'brave') {
      els.apiKeyInput.placeholder = 'BSA...';
    } else {
      els.apiKeyInput.placeholder = 'No API key needed for DuckDuckGo Lite';
    }
  }
  if (els.badge) {
    els.badge.textContent = formatWebSearchStatusBadge({
      ...data,
      provider,
      has_api_key: Boolean(data.has_api_key && (data.provider === provider || els.credentialSelect?.value)),
    });
  }
}

export async function loadWebSearchSettings(
  els,
  { fetchFn = typeof fetch !== 'undefined' ? fetch : null, state = null } = {},
) {
  if (!fetchFn || !els?.providerSelect) return null;
  try {
    const res = await fetchFn(WEB_SEARCH_SETTINGS_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    els.providerSelect.value = data.provider || 'duckduckgo';
    populateVaultDropdown(els, state?.vaultCredentials || [], data.credential_id || '');
    if (els.apiKeyInput) {
      els.apiKeyInput.value = '';
    }
    if (els.allowPrivateCheckbox) {
      els.allowPrivateCheckbox.checked = Boolean(data.allow_private_urls);
    }
    if (els.maxResultsInput && data.max_results) {
      els.maxResultsInput.value = String(data.max_results);
    }
    els._lastLoaded = data;
    syncProviderAuthVisibility(els, data);
    return data;
  } catch (err) {
    setStatus(els, `Could not load web search settings: ${err.message}`, false);
    return null;
  }
}

export async function saveWebSearchSettings(
  els,
  {
    fetchFn = typeof fetch !== 'undefined' ? fetch : null,
    state = null,
    onCredentialsRefresh = null,
  } = {},
) {
  if (!fetchFn || !els?.providerSelect) return null;
  const payload = buildWebSearchSavePayload({
    provider: els.providerSelect.value,
    credentialId: els.credentialSelect ? els.credentialSelect.value : '',
    apiKey: els.apiKeyInput ? els.apiKeyInput.value : '',
    allowPrivateUrls: els.allowPrivateCheckbox ? els.allowPrivateCheckbox.checked : false,
    maxResults: els.maxResultsInput ? els.maxResultsInput.value : 5,
  });

  try {
    const res = await fetchFn(WEB_SEARCH_SETTINGS_URL, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    if (payload.api_key && typeof onCredentialsRefresh === 'function') {
      await onCredentialsRefresh();
    }
    populateVaultDropdown(els, state?.vaultCredentials || [], data.credential_id || '');
    if (els.apiKeyInput) {
      els.apiKeyInput.value = '';
    }
    els._lastLoaded = data;
    syncProviderAuthVisibility(els, data);
    setStatus(els, `Saved (${formatWebSearchStatusBadge(data)})`, true);
    return data;
  } catch (err) {
    setStatus(els, `Save failed: ${err.message}`, false);
    return null;
  }
}

export function setupWebSearchSettings({
  doc = typeof document !== 'undefined' ? document : null,
  fetchFn = typeof fetch !== 'undefined' ? fetch : null,
  state = null,
  onCredentialsRefresh = null,
} = {}) {
  if (!doc) return null;
  const els = {
    card: byId(doc, 'settingsWebSearchCard'),
    providerSelect: byId(doc, 'webSearchProviderSelect'),
    credentialSelect: byId(doc, 'webSearchCredentialSelect'),
    apiKeyInput: byId(doc, 'webSearchApiKeyInput'),
    authFields: byId(doc, 'webSearchAuthFields'),
    allowPrivateCheckbox: byId(doc, 'webSearchAllowPrivateUrls'),
    maxResultsInput: byId(doc, 'webSearchMaxResultsInput'),
    saveBtn: byId(doc, 'saveWebSearchSettingsBtn'),
    status: byId(doc, 'webSearchSettingsStatus'),
    badge: byId(doc, 'webSearchProviderBadge'),
    _lastLoaded: {},
  };
  if (!els.providerSelect || !els.saveBtn) return null;

  if (els.saveBtn.dataset && els.saveBtn.dataset.wired !== '1') {
    els.saveBtn.dataset.wired = '1';
    els.providerSelect.addEventListener('change', () => {
      syncProviderAuthVisibility(els, els._lastLoaded || {});
    });
    els.saveBtn.addEventListener('click', () => {
      saveWebSearchSettings(els, { fetchFn, state, onCredentialsRefresh });
    });
  }

  loadWebSearchSettings(els, { fetchFn, state });
  return els;
}
