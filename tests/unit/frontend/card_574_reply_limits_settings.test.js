/**
 * CARD-574: Settings reply-limits fields read and save GET/PUT /api/settings/reply-limits.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { REPLY_LIMITS_URL, loadReplyLimits, parseLimitField, saveReplyLimits } from '../../../src/web/static/modules/studios/settings_reply_limits.js';

const ROOT = path.resolve(__dirname, '../../..');
const ok = (body) => ({ ok: true, status: 200, json: async () => body });
const fields = () => ({ tokens: { value: '' }, seconds: { value: '' }, status: { textContent: '', className: '' } });

describe('CARD-574 Settings reply limits', () => {
  it('loads the resolved limits into the fields', async () => {
    const els = fields();
    const calls = [];
    await loadReplyLimits(els, { fetchFn: async (url) => { calls.push(url); return ok({ max_tokens: 16384, max_seconds: 600 }); } });
    expect(calls).toEqual([REPLY_LIMITS_URL]);
    expect(els.tokens.value).toBe('16384');
    expect(els.seconds.value).toBe('600');
  });

  it('saves both fields with PUT; empty clears (0)', async () => {
    const els = fields();
    els.tokens.value = '2048';
    let sent = null;
    await saveReplyLimits(els, { fetchFn: async (url, init) => { sent = { url, init }; return ok({ max_tokens: 2048, max_seconds: 600 }); } });
    expect(sent.url).toBe(REPLY_LIMITS_URL);
    expect(sent.init.method).toBe('PUT');
    expect(JSON.parse(sent.init.body)).toEqual({ max_tokens: 2048, max_seconds: 0 });
    expect(els.seconds.value).toBe('600');
    expect(els.status.textContent).toContain('Saved');
  });

  it('a bad value is refused in the form and nothing is sent', async () => {
    const els = fields();
    els.tokens.value = '-5';
    let called = false;
    expect(await saveReplyLimits(els, { fetchFn: async () => { called = true; return ok({}); } })).toBeNull();
    expect(called).toBe(false);
    expect(els.status.textContent).toMatch(/whole number/);
    expect(parseLimitField('', 'x')).toBe(0);
    expect(() => parseLimitField('1.5', 'x')).toThrow();
  });

  it('a server error shows in the status line', async () => {
    const els = fields();
    els.tokens.value = '10';
    await saveReplyLimits(els, { fetchFn: async () => ({ ok: false, status: 400, json: async () => ({ detail: 'max_tokens must be a positive integer' }) }) });
    expect(els.status.textContent).toContain('max_tokens must be a positive integer');
  });

  it('the Settings screen has the card and settings.js wires it', () => {
    const html = fs.readFileSync(path.join(ROOT, 'src/web/templates/index.html'), 'utf-8');
    for (const id of ['settingsReplyLimitsCard', 'replyLimitMaxTokensInput', 'replyLimitMaxSecondsInput', 'replyLimitsSaveBtn', 'replyLimitsStatus']) {
      expect(html).toContain(`id="${id}"`);
    }
    const settings = fs.readFileSync(path.join(ROOT, 'src/web/static/modules/studios/settings.js'), 'utf-8');
    expect(settings).toMatch(/setupReplyLimits\(\);/);
  });
});
