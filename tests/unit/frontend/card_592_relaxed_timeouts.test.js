/**
 * CARD-592: Settings > Reply limits also holds the model-call waits; long client waits are relaxed.
 */
import { describe, it, expect } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';
import { LIMIT_FIELDS, loadReplyLimits, saveReplyLimits } from '../../../src/web/static/modules/studios/settings_reply_limits.js';

const ROOT = path.resolve(__dirname, '../../..');
const ok = (body) => ({ ok: true, status: 200, json: async () => body });
const allFields = () => ({
  tokens: { value: '' }, seconds: { value: '' }, idle: { value: '' }, phase: { value: '' }, helper: { value: '' },
  status: { textContent: '', className: '' },
});
const resolved = { max_tokens: 32768, max_seconds: 7200, provider_idle_seconds: 1800, phase_seconds: 21600, helper_seconds: 1800 };

describe('CARD-592 relaxed timeouts', () => {
  it('loads and saves every wait on the card', async () => {
    const els = allFields();
    await loadReplyLimits(els, { fetchFn: async () => ok(resolved) });
    expect([els.seconds.value, els.idle.value, els.phase.value, els.helper.value]).toEqual(['7200', '1800', '21600', '1800']);
    els.idle.value = '3600';
    els.helper.value = '';
    let sent = null;
    await saveReplyLimits(els, { fetchFn: async (url, init) => { sent = JSON.parse(init.body); return ok({ ...resolved, provider_idle_seconds: 3600 }); } });
    expect(sent).toEqual({ max_tokens: 32768, max_seconds: 7200, provider_idle_seconds: 3600, phase_seconds: 21600, helper_seconds: 0 });
    expect(els.idle.value).toBe('3600');
  });

  it('the Settings card has an input for each field', () => {
    const html = fs.readFileSync(path.join(ROOT, 'src/web/templates/index.html'), 'utf-8');
    for (const f of LIMIT_FIELDS) expect(html).toContain(`id="${f.id}"`);
    expect(html).toContain('placeholder="7200"');
  });

  it('long client waits are relaxed', () => {
    const hitl = fs.readFileSync(path.join(ROOT, 'src/web/static/modules/studios/chat/hitl.js'), 'utf-8');
    expect(hitl).toMatch(/timeoutMs = 6 \* 60 \* 60 \* 1000/);
    const edu = fs.readFileSync(path.join(ROOT, 'src/web/static/modules/studios/education.js'), 'utf-8');
    expect(edu).toMatch(/mintTimeoutMs = 30 \* 60 \* 1000/);
  });
});
