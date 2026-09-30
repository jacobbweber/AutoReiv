import { describe, it, expect } from 'vitest';
import { loadPageHtml } from './template_helper.js';

// CARD-478: the Auto-run ON chip must not share the goal chip's colour.
const family = (cls) => {
  const m = cls.match(/\bbg-([a-z]+)-\d{3}/);
  return m ? m[1] : null;
};
const chipClass = (html, id) => {
  const m = html.match(new RegExp(`<span id="${id}" class="([^"]*)"`));
  return m ? m[1] : '';
};

describe('CARD-478 Auto-run chip colour', () => {
  it('approvalBadge is teal and differs from goalBadge and verifyBadge [REQ-478-001]', () => {
    const html = loadPageHtml();
    const auto = family(chipClass(html, 'approvalBadge'));
    expect(auto).toBe('teal');
    expect(chipClass(html, 'approvalBadge')).toMatch(/text-teal-300/);
    expect(chipClass(html, 'approvalBadge')).toMatch(/border-teal-/);
    expect(auto).not.toBe(family(chipClass(html, 'goalBadge')));
    expect(auto).not.toBe(family(chipClass(html, 'verifyBadge')));
  });

  it('keeps the text "Auto-run ON" [REQ-478-002]', () => {
    const html = loadPageHtml();
    const chip = html.match(/<span id="approvalBadge"[^>]*>([\s\S]*?)<\/span>/);
    expect(chip[1].trim()).toBe('Auto-run ON');
  });
});
