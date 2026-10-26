/**
 * Settings Studio > Voice / Talk (optional).
 * GET/PUT /api/settings/voice. Voice stays off unless an endpoint URL is set and enabled.
 */
export const VOICE_SETTINGS_URL = '/api/settings/voice';

const byId = (doc, id) => (doc && typeof doc.getElementById === 'function' ? doc.getElementById(id) : null);

export function buildVoiceSavePayload({ enabled = false, endpointUrl = '', voice = '', autoSpeak = true } = {}) {
  return {
    enabled: Boolean(enabled),
    endpoint_url: String(endpointUrl || '').trim(),
    voice: String(voice || '').trim(),
    auto_speak: Boolean(autoSpeak),
  };
}

export function formatVoiceBadge(data = {}) {
  if (data.enabled) return 'On';
  if (data.endpoint_url) return 'Off (endpoint saved)';
  return 'Not configured';
}

function setStatus(els, text, ok = true) {
  if (!els.status) return;
  els.status.textContent = text;
  els.status.className = `text-[11px] font-medium ${ok ? 'text-emerald-400' : 'text-rose-400'}`;
  els.status.classList.remove('hidden');
}

function fill(els, data) {
  if (els.enabled) els.enabled.checked = Boolean(data.enabled);
  if (els.url) els.url.value = data.endpoint_url || '';
  if (els.voice) els.voice.value = data.voice || '';
  if (els.autoSpeak) els.autoSpeak.checked = data.auto_speak !== false;
  if (els.badge) els.badge.textContent = formatVoiceBadge(data);
}

function notifyChanged() {
  if (typeof window !== 'undefined') window.dispatchEvent(new CustomEvent('autoreiv:voice-settings-changed'));
}

export async function loadVoiceSettings(els, fetchFn = fetch) {
  try {
    const res = await fetchFn(VOICE_SETTINGS_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    fill(els, data);
    return data;
  } catch (err) {
    setStatus(els, `Could not load voice settings: ${err.message}`, false);
    return null;
  }
}

export async function saveVoiceSettings(els, fetchFn = fetch) {
  const payload = buildVoiceSavePayload({
    enabled: els.enabled?.checked,
    endpointUrl: els.url?.value,
    voice: els.voice?.value,
    autoSpeak: els.autoSpeak?.checked,
  });
  try {
    const res = await fetchFn(VOICE_SETTINGS_URL, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `HTTP ${res.status}`);
    fill(els, data);
    notifyChanged();
    setStatus(els, data.enabled ? 'Saved. Talk button is on in chat.' : 'Saved. Voice is off.', true);
    return data;
  } catch (err) {
    setStatus(els, `Save failed: ${err.message}`, false);
    return null;
  }
}

export async function testVoiceEndpoint(els, fetchFn = fetch) {
  try {
    const res = await fetchFn('/api/voice/status');
    const data = await res.json();
    if (!data.enabled) return setStatus(els, 'Voice is off. Enable it and save first.', false);
    if (data.reachable) return setStatus(els, `Endpoint OK (speech-to-text: ${data.stt ? 'yes' : 'no'}, speech: ${data.tts ? 'yes' : 'no'})`, true);
    return setStatus(els, data.error || 'Endpoint not reachable.', false);
  } catch (err) {
    return setStatus(els, `Test failed: ${err.message}`, false);
  }
}

export function setupVoiceSettings({ doc = typeof document !== 'undefined' ? document : null, fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {}) {
  if (!doc || !fetchFn) return null;
  const els = {
    enabled: byId(doc, 'voiceEnabledToggle'),
    url: byId(doc, 'voiceEndpointInput'),
    voice: byId(doc, 'voiceNameInput'),
    autoSpeak: byId(doc, 'voiceAutoSpeakToggle'),
    saveBtn: byId(doc, 'saveVoiceSettingsBtn'),
    testBtn: byId(doc, 'testVoiceSettingsBtn'),
    status: byId(doc, 'voiceSettingsStatus'),
    badge: byId(doc, 'voiceStatusBadge'),
  };
  if (!els.saveBtn) return null;
  if (els.saveBtn.dataset.wired !== '1') {
    els.saveBtn.dataset.wired = '1';
    els.saveBtn.addEventListener('click', () => saveVoiceSettings(els, fetchFn));
    els.testBtn?.addEventListener('click', () => testVoiceEndpoint(els, fetchFn));
  }
  loadVoiceSettings(els, fetchFn);
  return els;
}
