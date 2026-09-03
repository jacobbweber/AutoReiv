import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Wiki Graph Removal [CARD-140]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('removes obsolete wikiGraphViewBtn from toolbar [REQ-CLEAN-001]', () => {
    expect(html).not.toContain('id="wikiGraphViewBtn"');
  });

  it('removes obsolete wikiGraphModal from DOM [REQ-CLEAN-002]', () => {
    expect(html).not.toContain('id="wikiGraphModal"');
  });

  it('preserves interactive Mind Map explorer [REQ-CLEAN-003]', () => {
    expect(html).toContain('id="wikiMindMapViewBtn"');
    expect(html).toContain('id="wikiMindMapModal"');
  });
});
