import { describe, it, expect } from 'vitest';
import { loadPageHtml } from './template_helper.js';

describe('CARD-312 Observe expand scroll', () => {
  const html = loadPageHtml();

  it('gives Observe panel min-h-0 + overflow-y scroll contract', () => {
    expect(html).toMatch(/id="view-observability"[^>]*min-h-0/);
    expect(html).toContain('CARD-312: Observe expand scrolls');
    expect(html).toContain('#view-observability details.obs-section[open]');
    expect(html).toContain('overflow: visible');
    expect(html).toMatch(/\/static\/app\.js\?v=2\.0\.\d+/);
  });
});
