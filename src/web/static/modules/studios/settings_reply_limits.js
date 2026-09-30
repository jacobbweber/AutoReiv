/**
 * CARD-574: Settings > Models: reply limits (CARD-567) for every streaming model reply.
 * Reads and saves GET/PUT /api/settings/reply-limits. An empty or 0 field clears the saved value
 * (back to env AUTOREIV_MAX_REPLY_TOKENS / AUTOREIV_MAX_REPLY_SECONDS, then the defaults 32768 / 600).
 */

export const REPLY_LIMITS_URL = '/api/settings/reply-limits';

function byId(doc, id) {
  return doc && typeof doc.getElementById === 'function' ? doc.getElementById(id) : null;
}

/** Field value -> number to send (0 clears). Throws on a negative or non-number value. */
export function parseLimitField(raw, label) {
  const text = String(raw ?? '').trim();
  if (!text) return 0;
  const n = Number(text);
  if (!Number.isInteger(n) || n < 0) throw new Error(`${label} must be a whole number of 0 or more.`);
  return n;
}

function show(els, data) {
  if (els.tokens) els.tokens.value = data && data.max_tokens ? String(data.max_tokens) : '';
  if (els.seconds) els.seconds.value = data && data.max_seconds ? String(data.max_seconds) : '';
}

function setStatus(els, text, ok) {
  if (!els.status) return;
  els.status.textContent = text;
  els.status.className = `text-[11px] ${ok ? 'text-emerald-400' : 'text-rose-400'}`;
}

/** Load the current limits into the fields. Returns the API body or null. */
export async function loadReplyLimits(els, { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {}) {
  if (!fetchFn) return null;
  try {
    const res = await fetchFn(REPLY_LIMITS_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    show(els, data);
    return data;
  } catch (err) {
    setStatus(els, `Could not load reply limits: ${err.message}`, false);
    return null;
  }
}

/** Save both fields; the fields then show what the server resolved. */
export async function saveReplyLimits(els, { fetchFn = typeof fetch !== 'undefined' ? fetch : null } = {}) {
  let body;
  try {
    body = {
      max_tokens: parseLimitField(els.tokens && els.tokens.value, 'Max tokens per reply'),
      max_seconds: parseLimitField(els.seconds && els.seconds.value, 'Max seconds per reply'),
    };
  } catch (err) {
    setStatus(els, err.message, false);
    return null;
  }
  try {
    const res = await fetchFn(REPLY_LIMITS_URL, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    show(els, data);
    setStatus(els, `Saved: ${data.max_tokens} tokens, ${data.max_seconds} s per reply.`, true);
    return data;
  } catch (err) {
    setStatus(els, `Could not save reply limits: ${err.message}`, false);
    return null;
  }
}

/** Wire the Settings card once and load the values. */
export function setupReplyLimits(doc = typeof document !== 'undefined' ? document : null, { fetchFn } = {}) {
  const els = {
    tokens: byId(doc, 'replyLimitMaxTokensInput'),
    seconds: byId(doc, 'replyLimitMaxSecondsInput'),
    save: byId(doc, 'replyLimitsSaveBtn'),
    status: byId(doc, 'replyLimitsStatus'),
  };
  if (!els.tokens || !els.seconds) return null;
  const opts = fetchFn ? { fetchFn } : {};
  if (els.save && els.save.dataset && els.save.dataset.wired !== '1') {
    els.save.dataset.wired = '1';
    els.save.addEventListener('click', () => { saveReplyLimits(els, opts); });
  }
  loadReplyLimits(els, opts);
  return els;
}
