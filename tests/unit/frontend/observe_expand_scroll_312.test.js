import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('CARD-312 Observe expand scroll', () => {
  const html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');

  it('gives Observe panel min-h-0 + overflow-y scroll contract', () => {
    expect(html).toMatch(/id="view-observability"[^>]*min-h-0/);
    expect(html).toContain('CARD-312: Observe expand scrolls');
    expect(html).toContain('#view-observability details.obs-section[open]');
    expect(html).toContain('overflow: visible');
    expect(html).toContain('/static/app.js?v=2.0.49');
  });
});
