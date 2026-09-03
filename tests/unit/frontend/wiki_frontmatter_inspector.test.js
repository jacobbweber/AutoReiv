import { describe, it, expect, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

describe('Wiki Note Responsive Header & Frontmatter Inspector [CARD-141]', () => {
  let html;

  beforeEach(() => {
    html = fs.readFileSync(path.resolve(__dirname, '../../../src/web/templates/index.html'), 'utf-8');
  });

  it('provides dedicated un-truncated note title and path layout [REQ-WIKI-UI-001]', () => {
    expect(html).toContain('id="activeWikiTitle"');
    expect(html).toContain('id="activeWikiPath"');
  });

  it('includes metadata toggle button in document action group [REQ-WIKI-UI-002]', () => {
    expect(html).toContain('id="wikiToggleFmBtn"');
    expect(html).toContain('id="wikiModePreviewBtn"');
    expect(html).toContain('id="wikiModeEditBtn"');
    expect(html).toContain('id="wikiSaveNoteBtn"');
    expect(html).toContain('id="wikiDeleteNoteBtn"');
  });

  it('features collapsible frontmatter summary bar and body [REQ-WIKI-UI-003]', () => {
    expect(html).toContain('id="wikiFrontmatterCard"');
    expect(html).toContain('id="wikiFmSummaryBar"');
    expect(html).toContain('id="wikiFmBody"');
  });

  it('supports Rendered and Raw view modes with copy button [REQ-WIKI-UI-004]', () => {
    expect(html).toContain('id="fmModeRenderedBtn"');
    expect(html).toContain('id="fmModeRawBtn"');
    expect(html).toContain('id="fmRenderedView"');
    expect(html).toContain('id="fmRawView"');
    expect(html).toContain('id="fmRawContent"');
    expect(html).toContain('id="fmCopyRawBtn"');
  });
});
